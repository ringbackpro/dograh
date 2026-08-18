"""Ingest orchestration.

Design rules, each of which exists because of a specific way the current
spreadsheet chain fails:

* **Content-addressed.** A file is identified by SHA-256, not by name. Running
  the loader twice over the same inbox, or re-downloading the same report,
  cannot double-count anything.
* **Failures are recorded, not fatal.** One malformed report does not stop the
  other nine. The bad file lands in the audit trail with the reason, and is
  retried automatically on the next run once the cause is fixed.
* **Nothing is deleted to fix a number.** A corrected report is simply loaded;
  the mart's ``v_current_file`` rule makes the later file win.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from .config import ReportDef
from .db import rebuild_marts
from .parsers import ParseError, parse_file


@dataclass
class FileOutcome:
    path: Path
    report_code: str
    status: str  # loaded | skipped | failed
    rows: int = 0
    message: str = ""


@dataclass
class RunSummary:
    run_id: int
    outcomes: list[FileOutcome] = field(default_factory=list)

    def _count(self, status: str) -> int:
        return sum(1 for o in self.outcomes if o.status == status)

    @property
    def loaded(self) -> int:
        return self._count("loaded")

    @property
    def skipped(self) -> int:
        return self._count("skipped")

    @property
    def failed(self) -> int:
        return self._count("failed")

    @property
    def rows(self) -> int:
        return sum(o.rows for o in self.outcomes)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def discover(inbox: Path, reports: tuple[ReportDef, ...]) -> list[tuple[ReportDef, Path]]:
    """Match every file in the inbox to the report definition that claims it.

    A file matched by more than one glob is a configuration mistake worth
    surfacing loudly rather than resolving arbitrarily.
    """
    found: dict[Path, ReportDef] = {}
    collisions: list[str] = []
    for report in reports:
        for path in sorted(inbox.glob(report.filename_glob)):
            if not path.is_file():
                continue
            if path in found:
                collisions.append(
                    f"{path.name} matches both '{found[path].code}' and "
                    f"'{report.code}'"
                )
                continue
            found[path] = report
    if collisions:
        raise ValueError(
            "filename_glob patterns overlap: " + "; ".join(collisions)
        )
    return sorted(((r, p) for p, r in found.items()), key=lambda x: (x[0].code, x[1].name))


def _existing_file(
    conn: sqlite3.Connection, report_code: str, as_of: str, sha: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT file_id, status FROM ingest_file"
        " WHERE report_code = ? AND as_of_date = ? AND sha256 = ?",
        (report_code, as_of, sha),
    ).fetchone()


def _insert_rows(
    conn: sqlite3.Connection, report: ReportDef, file_id: int, as_of: date, rows: list[dict]
) -> None:
    if not rows:
        return
    names = [c.name for c in report.columns]
    placeholders = ", ".join("?" for _ in range(len(names) + 2))
    sql = (
        f"INSERT INTO {report.staging_table} (file_id, as_of_date, "
        f"{', '.join(names)}) VALUES ({placeholders})"
    )
    payload = [
        (file_id, as_of.isoformat(), *(row.get(n) for n in names)) for row in rows
    ]
    conn.executemany(sql, payload)


def ingest(
    conn: sqlite3.Connection,
    reports: tuple[ReportDef, ...],
    inbox: Path,
    force: bool = False,
) -> RunSummary:
    """Load every recognised file in the inbox, then rebuild the mart."""
    cursor = conn.execute(
        "INSERT INTO ingest_run (started_at, status) VALUES (?, 'running')", (_now(),)
    )
    run_id = cursor.lastrowid
    summary = RunSummary(run_id=run_id)

    for report, path in discover(inbox, reports):
        sha = sha256_of(path)

        # Parse before checking for a duplicate, because the as-of date is part
        # of a file's identity and only parsing reveals it.
        try:
            parsed = parse_file(report, path)
        except (ParseError, OSError, ValueError) as exc:
            fallback = date.fromtimestamp(path.stat().st_mtime).isoformat()
            conn.execute(
                "DELETE FROM ingest_file WHERE report_code = ? AND as_of_date = ?"
                " AND sha256 = ?",
                (report.code, fallback, sha),
            )
            conn.execute(
                "INSERT INTO ingest_file (run_id, report_code, source_system, filename,"
                " source_path, sha256, as_of_date, status, message, loaded_at)"
                " VALUES (?,?,?,?,?,?,?, 'failed', ?, ?)",
                (run_id, report.code, report.source_system, path.name, str(path),
                 sha, fallback, str(exc), _now()),
            )
            summary.outcomes.append(FileOutcome(path, report.code, "failed", 0, str(exc)))
            continue

        as_of = parsed.as_of_date.isoformat()
        existing = _existing_file(conn, report.code, as_of, sha)
        if existing is not None:
            if existing["status"] == "loaded" and not force:
                summary.outcomes.append(
                    FileOutcome(path, report.code, "skipped", 0, "already loaded")
                )
                continue
            # A previously failed file, or an explicit --force: clear it out and
            # retry. The staging rows cascade away with the parent.
            conn.execute("DELETE FROM ingest_file WHERE file_id = ?", (existing["file_id"],))

        parsed_total = None
        if report.control_total is not None:
            column = report.control_total.column
            parsed_total = sum(
                row.get(column) or 0 for row in parsed.rows
            )

        message = ""
        if parsed.row_errors:
            shown = "; ".join(parsed.row_errors[:5])
            more = len(parsed.row_errors) - 5
            message = f"{len(parsed.row_errors)} unparseable row(s): {shown}"
            if more > 0:
                message += f" (+{more} more)"

        cursor = conn.execute(
            "INSERT INTO ingest_file (run_id, report_code, source_system, filename,"
            " source_path, sha256, as_of_date, row_count, skipped_lines,"
            " control_total_cents, parsed_total_cents, status, message, loaded_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?, 'loaded', ?, ?)",
            (run_id, report.code, report.source_system, path.name, str(path), sha,
             parsed.as_of_date.isoformat(), parsed.row_count, parsed.skipped_lines,
             parsed.control_total_cents, parsed_total, message, _now()),
        )
        _insert_rows(conn, report, cursor.lastrowid, parsed.as_of_date, parsed.rows)
        summary.outcomes.append(
            FileOutcome(path, report.code, "loaded", parsed.row_count, message)
        )

    conn.execute(
        "UPDATE ingest_run SET finished_at = ?, status = ?, files_seen = ?,"
        " files_loaded = ?, files_skipped = ?, files_failed = ?, rows_loaded = ?"
        " WHERE run_id = ?",
        (_now(), "completed" if summary.failed == 0 else "completed_with_errors",
         len(summary.outcomes), summary.loaded, summary.skipped, summary.failed,
         summary.rows, run_id),
    )
    conn.commit()

    rebuild_marts(conn)
    return summary
