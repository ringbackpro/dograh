"""Data-quality checks, defined as SQL in configuration.

Every check is a query plus an expectation. Keeping them in TOML rather than in
Python means a budget analyst who can write SQL can add a rule -- and, more
importantly, that the rules are reviewable as a list rather than buried in code.

The expectation vocabulary is deliberately tiny:

``zero_rows``
    The query selects violations. No rows means the check passed. This covers
    almost everything.
``nonzero_rows``
    The query selects evidence that something exists. Used for "did anything at
    all load today".
"""

from __future__ import annotations

import sqlite3
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

VALID_SEVERITIES = {"error", "warn", "info"}
VALID_EXPECTATIONS = {"zero_rows", "nonzero_rows"}


class CheckConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Check:
    name: str
    sql: str
    severity: str = "error"
    expect: str = "zero_rows"
    message: str = ""


@dataclass
class CheckResult:
    check: Check
    passed: bool
    observed: str
    detail: str


def load_checks(path: Path) -> tuple[Check, ...]:
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    checks = []
    for entry in raw.get("check", []):
        name = entry.get("name")
        if not name:
            raise CheckConfigError("every [[check]] needs a 'name'")
        if "sql" not in entry:
            raise CheckConfigError(f"check '{name}': needs a 'sql' query")
        severity = entry.get("severity", "error")
        if severity not in VALID_SEVERITIES:
            raise CheckConfigError(
                f"check '{name}': severity must be one of {sorted(VALID_SEVERITIES)}"
            )
        expect = entry.get("expect", "zero_rows")
        if expect not in VALID_EXPECTATIONS:
            raise CheckConfigError(
                f"check '{name}': expect must be one of {sorted(VALID_EXPECTATIONS)}"
            )
        checks.append(
            Check(
                name=name,
                sql=entry["sql"],
                severity=severity,
                expect=expect,
                message=entry.get("message", ""),
            )
        )

    if not checks:
        raise CheckConfigError(f"{path}: no [[check]] definitions found")

    names = [c.name for c in checks]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise CheckConfigError(f"{path}: duplicate check names {sorted(dupes)}")
    return tuple(checks)


def _summarise(rows: list[sqlite3.Row], limit: int = 3) -> str:
    if not rows:
        return "no rows"
    shown = [
        "(" + ", ".join(f"{k}={row[k]!r}" for k in row.keys()) + ")"
        for row in rows[:limit]
    ]
    extra = len(rows) - limit
    text = "; ".join(shown)
    return text + (f" (+{extra} more)" if extra > 0 else "")


def run_checks(
    conn: sqlite3.Connection, checks: tuple[Check, ...], run_id: int | None = None
) -> list[CheckResult]:
    """Execute every check and persist the outcome to dq_result."""
    if run_id is None:
        row = conn.execute("SELECT MAX(run_id) AS r FROM ingest_run").fetchone()
        run_id = row["r"] if row and row["r"] is not None else 0

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results: list[CheckResult] = []

    for check in checks:
        try:
            rows = conn.execute(check.sql).fetchall()
        except sqlite3.Error as exc:
            results.append(
                CheckResult(check, False, "query error", f"{type(exc).__name__}: {exc}")
            )
            conn.execute(
                "INSERT INTO dq_result (run_id, check_name, severity, status,"
                " observed, message, created_at) VALUES (?,?,?,?,?,?,?)",
                (run_id, check.name, check.severity, "error", "query error",
                 str(exc), now),
            )
            continue

        passed = (len(rows) == 0) if check.expect == "zero_rows" else (len(rows) > 0)
        observed = f"{len(rows)} row(s)"
        detail = check.message if passed else (check.message + " -> " + _summarise(rows)).strip(" ->")

        results.append(CheckResult(check, passed, observed, detail))
        conn.execute(
            "INSERT INTO dq_result (run_id, check_name, severity, status, observed,"
            " message, created_at) VALUES (?,?,?,?,?,?,?)",
            (run_id, check.name, check.severity,
             "pass" if passed else "fail", observed, detail, now),
        )

    conn.commit()
    return results


def worst_severity(results: list[CheckResult]) -> str | None:
    """The most serious severity among failing checks, or None if all passed."""
    failed = [r.check.severity for r in results if not r.passed]
    for level in ("error", "warn", "info"):
        if level in failed:
            return level
    return None
