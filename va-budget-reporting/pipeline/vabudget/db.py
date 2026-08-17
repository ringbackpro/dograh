"""SQLite schema management.

The database has three layers, and the separation is deliberate:

* ``stg_*``  -- staging, one table per report, shaped by configuration. Raw,
  append-only, every row traceable to the file it came from.
* ``dim_*`` / ``fact_*`` -- the conformed mart, rebuilt from staging on every
  run by ``sql/200_marts.sql``. This is the layer you own and edit.
* ``v_*`` -- presentation views with dollars and derived measures. This is the
  only layer Power BI should touch.

Rebuilding the mart from scratch each run keeps the pipeline deterministic:
the mart is always a pure function of the staged files, so a bad load is fixed
by correcting staging and re-running, never by hand-patching a total.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from .config import ConfigError, ReportDef

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

DIM_DATE_START = date(2015, 10, 1)
DIM_DATE_END = date(2035, 9, 30)


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def fiscal_attributes(day: date) -> dict:
    """Federal fiscal calendar: FY2026 runs 2025-10-01 through 2026-09-30."""
    fiscal_year = day.year + 1 if day.month >= 10 else day.year
    fiscal_period = ((day.month - 10) % 12) + 1
    fiscal_quarter = ((fiscal_period - 1) // 3) + 1
    next_day = day + timedelta(days=1)
    return {
        "date_key": day.isoformat(),
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "fiscal_period": fiscal_period,
        "fiscal_label": f"FY{fiscal_year} P{fiscal_period:02d}",
        "fiscal_quarter_label": f"FY{fiscal_year} Q{fiscal_quarter}",
        "calendar_year": day.year,
        "calendar_month": day.month,
        "month_name": day.strftime("%B"),
        "day_of_month": day.day,
        "is_month_end": 1 if next_day.month != day.month else 0,
        "is_fiscal_year_end": 1 if day.month == 9 and day.day == 30 else 0,
    }


def _staging_ddl(report: ReportDef) -> str:
    if not _IDENT.fullmatch(report.staging_table):
        raise ConfigError(f"report code '{report.code}' is not a safe table name")

    cols = []
    for col in report.columns:
        if not _IDENT.fullmatch(col.name):
            raise ConfigError(
                f"report '{report.code}': column name '{col.name}' must be "
                "alphanumeric/underscore and start with a letter, because it "
                "becomes a SQL column name"
            )
        cols.append(f"    {col.name} {col.sql_type}")

    body = ",\n".join(cols)
    return (
        f"CREATE TABLE IF NOT EXISTS {report.staging_table} (\n"
        "    row_id INTEGER PRIMARY KEY,\n"
        "    file_id INTEGER NOT NULL REFERENCES ingest_file(file_id) ON DELETE CASCADE,\n"
        "    as_of_date TEXT NOT NULL,\n"
        f"{body}\n"
        ");\n"
        f"CREATE INDEX IF NOT EXISTS ix_{report.staging_table}_as_of\n"
        f"    ON {report.staging_table}(as_of_date);\n"
        f"CREATE INDEX IF NOT EXISTS ix_{report.staging_table}_file\n"
        f"    ON {report.staging_table}(file_id);\n"
    )


def _seed_dim_date(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS n FROM dim_date").fetchone()["n"]
    if existing:
        return
    rows = []
    day = DIM_DATE_START
    while day <= DIM_DATE_END:
        rows.append(tuple(fiscal_attributes(day).values()))
        day += timedelta(days=1)
    conn.executemany(
        "INSERT INTO dim_date (date_key, fiscal_year, fiscal_quarter, fiscal_period,"
        " fiscal_label, fiscal_quarter_label, calendar_year, calendar_month,"
        " month_name, day_of_month, is_month_end, is_fiscal_year_end)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )


def _run_sql_file(conn: sqlite3.Connection, name: str) -> None:
    conn.executescript((SQL_DIR / name).read_text(encoding="utf-8"))


def ensure_schema(conn: sqlite3.Connection, reports: tuple[ReportDef, ...]) -> None:
    """Create core tables, one staging table per configured report, and seed dates.

    Staging tables are created for every configured report whether or not a
    file has ever arrived, so the mart SQL can reference them unconditionally.
    """
    _run_sql_file(conn, "010_core.sql")
    for report in reports:
        conn.executescript(_staging_ddl(report))
    conn.executemany(
        "INSERT INTO ref_report (report_code, report_name, source_system,"
        " expected_cadence_days) VALUES (?,?,?,?)"
        " ON CONFLICT(report_code) DO UPDATE SET"
        "   report_name = excluded.report_name,"
        "   source_system = excluded.source_system,"
        "   expected_cadence_days = excluded.expected_cadence_days",
        [
            (r.code, r.name, r.source_system, r.expected_cadence_days)
            for r in reports
        ],
    )
    _seed_dim_date(conn)
    conn.commit()


def rebuild_marts(conn: sqlite3.Connection) -> None:
    """Rebuild every dim_/fact_/v_ object from current staging contents."""
    _run_sql_file(conn, "200_marts.sql")
    conn.commit()
