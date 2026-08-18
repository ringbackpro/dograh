"""Command line entry point.

    python -m vabudget sample  --out ./inbox      # make synthetic reports
    python -m vabudget ingest  --inbox ./inbox    # parse, stage, rebuild the mart
    python -m vabudget check                      # run the data-quality rulebook
    python -m vabudget status                     # what is loaded, what is stale

Exit codes matter, because this is meant to run unattended under a scheduler:
0 means everything is fine, 1 means an error-severity problem that a person
needs to look at, 2 means the tool was misconfigured or misinvoked.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import ConfigError, load_reports
from .db import connect, ensure_schema, rebuild_marts
from .loader import ingest
from .quality import CheckConfigError, load_checks, run_checks, worst_severity
from .samples import generate

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS = PIPELINE_ROOT / "config" / "reports.toml"
DEFAULT_CHECKS = PIPELINE_ROOT / "config" / "checks.toml"
DEFAULT_DB = Path("budget.db")
DEFAULT_INBOX = Path("inbox")

EXIT_OK, EXIT_PROBLEM, EXIT_MISUSE = 0, 1, 2


def _parse_date(text: str) -> date:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {text!r}")


def _open(args) -> tuple:
    reports = load_reports(args.config)
    conn = connect(args.db)
    ensure_schema(conn, reports)
    return conn, reports


def _rule(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def cmd_init(args) -> int:
    conn, reports = _open(args)
    print(f"Initialised {args.db} with {len(reports)} report definition(s):")
    for report in reports:
        print(f"  {report.code:<10} {report.source_system:<8} -> {report.staging_table}")
    conn.close()
    return EXIT_OK


def cmd_sample(args) -> int:
    end = args.end or date.today()
    start = args.start or (end - timedelta(days=args.days))
    written = generate(args.out, start, end, seed=args.seed, inject_faults=args.inject_faults)
    print(f"Wrote {len(written)} sample file(s) to {args.out} covering {start} to {end}.")
    if args.inject_faults:
        print(
            "Faults injected: one missing business day, and the newest Status of\n"
            "Funds capture truncated with its printed total left intact."
        )
    return EXIT_OK


def cmd_ingest(args) -> int:
    if not args.inbox.is_dir():
        print(f"error: inbox {args.inbox} does not exist", file=sys.stderr)
        return EXIT_MISUSE

    conn, reports = _open(args)
    summary = ingest(conn, reports, args.inbox, force=args.force)

    _rule(f"Ingest run {summary.run_id}")
    print(
        f"{summary.loaded} loaded, {summary.skipped} already present, "
        f"{summary.failed} failed, {summary.rows:,} rows staged"
    )
    for outcome in summary.outcomes:
        if outcome.status == "failed":
            print(f"  FAILED  {outcome.path.name}: {outcome.message}")
        elif outcome.status == "loaded" and outcome.message:
            print(f"  warn    {outcome.path.name}: {outcome.message}")

    exit_code = EXIT_PROBLEM if summary.failed else EXIT_OK

    if not args.no_check:
        exit_code = max(exit_code, _report_checks(conn, args, summary.run_id))

    conn.close()
    return exit_code


def _report_checks(conn, args, run_id: int | None = None) -> int:
    checks = load_checks(args.checks)
    results = run_checks(conn, checks, run_id)

    _rule("Data quality")
    failures = [r for r in results if not r.passed]
    if not failures:
        print(f"All {len(results)} checks passed.")
        return EXIT_OK

    for result in failures:
        print(f"  [{result.check.severity.upper():<5}] {result.check.name}: {result.observed}")
        if result.detail:
            print(f"          {result.detail}")
    passed = len(results) - len(failures)
    print(f"\n{passed} passed, {len(failures)} failed.")

    return EXIT_PROBLEM if worst_severity(results) == "error" else EXIT_OK


def cmd_check(args) -> int:
    conn, _ = _open(args)
    code = _report_checks(conn, args)
    conn.close()
    return code


def cmd_rebuild(args) -> int:
    conn, _ = _open(args)
    rebuild_marts(conn)
    print("Mart rebuilt from current staging contents.")
    conn.close()
    return EXIT_OK


def cmd_status(args) -> int:
    conn, _ = _open(args)

    run = conn.execute(
        "SELECT * FROM ingest_run ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    _rule("Most recent run")
    if run is None:
        print("Nothing has been ingested yet.")
    else:
        print(
            f"run {run['run_id']}  {run['status']}  started {run['started_at']}\n"
            f"{run['files_loaded']} loaded, {run['files_skipped']} skipped, "
            f"{run['files_failed']} failed, {run['rows_loaded']:,} rows"
        )

    _rule("Report freshness")
    rows = conn.execute(
        "SELECT report_code, source_system, latest_as_of, snapshots_loaded,"
        " days_stale, freshness_status FROM v_report_freshness ORDER BY report_code"
    ).fetchall()
    print(f"{'REPORT':<10}{'SYSTEM':<9}{'LATEST':<12}{'SNAPSHOTS':>10}  STATUS")
    for row in rows:
        latest = row["latest_as_of"] or "-"
        status = row["freshness_status"]
        if status == "stale":
            status = f"STALE ({row['days_stale']}d)"
        print(
            f"{row['report_code']:<10}{row['source_system']:<9}{latest:<12}"
            f"{row['snapshots_loaded']:>10}  {status}"
        )

    _rule("Control totals")
    mismatches = conn.execute(
        "SELECT filename, report_control_total, parsed_total FROM v_ingest_audit"
        " WHERE control_total_check = 'MISMATCH'"
    ).fetchall()
    if not mismatches:
        print("No control-total mismatches.")
    for row in mismatches:
        print(
            f"  {row['filename']}: report says {row['report_control_total']:,.2f}, "
            f"parsed {row['parsed_total']:,.2f}"
        )

    conn.close()
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vabudget",
        description="Load recurring budget reports into a single local database.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite file (default: budget.db)")
    parser.add_argument("--config", type=Path, default=DEFAULT_REPORTS, help="report definitions TOML")
    parser.add_argument("--checks", type=Path, default=DEFAULT_CHECKS, help="data-quality TOML")

    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create the database and staging tables")
    p_init.set_defaults(func=cmd_init)

    p_sample = sub.add_parser("sample", help="write synthetic reports for testing")
    p_sample.add_argument("--out", type=Path, default=DEFAULT_INBOX)
    p_sample.add_argument("--start", type=_parse_date)
    p_sample.add_argument("--end", type=_parse_date)
    p_sample.add_argument("--days", type=int, default=60, help="window length if --start is omitted")
    p_sample.add_argument("--seed", type=int, default=20260817)
    p_sample.add_argument("--inject-faults", action="store_true", help="break things on purpose")
    p_sample.set_defaults(func=cmd_sample)

    p_ingest = sub.add_parser("ingest", help="load everything in the inbox")
    p_ingest.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    p_ingest.add_argument("--force", action="store_true", help="reload files already loaded")
    p_ingest.add_argument("--no-check", action="store_true", help="skip data-quality checks")
    p_ingest.set_defaults(func=cmd_ingest)

    p_check = sub.add_parser("check", help="run the data-quality rulebook")
    p_check.set_defaults(func=cmd_check)

    p_rebuild = sub.add_parser("rebuild", help="rebuild the mart from staging")
    p_rebuild.set_defaults(func=cmd_rebuild)

    p_status = sub.add_parser("status", help="show what is loaded and what is stale")
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, CheckConfigError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_MISUSE
    except FileNotFoundError as exc:
        print(f"file not found: {exc}", file=sys.stderr)
        return EXIT_MISUSE


if __name__ == "__main__":
    sys.exit(main())
