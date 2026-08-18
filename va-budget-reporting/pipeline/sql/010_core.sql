-- Core tables: ingest audit trail, data-quality results, and the date dimension.
--
-- The audit tables exist because the trust problem is as important as the data
-- problem. A budget number nobody can trace is a number nobody will defend in a
-- meeting. Every staged row points at the file it came from; every file records
-- its hash, its as-of date, and whether its own printed control total agreed
-- with what we parsed.

CREATE TABLE IF NOT EXISTS ingest_run (
    run_id        INTEGER PRIMARY KEY,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    status        TEXT NOT NULL DEFAULT 'running',
    files_seen    INTEGER NOT NULL DEFAULT 0,
    files_loaded  INTEGER NOT NULL DEFAULT 0,
    files_skipped INTEGER NOT NULL DEFAULT 0,
    files_failed  INTEGER NOT NULL DEFAULT 0,
    rows_loaded   INTEGER NOT NULL DEFAULT 0,
    note          TEXT
);

CREATE TABLE IF NOT EXISTS ingest_file (
    file_id             INTEGER PRIMARY KEY,
    run_id              INTEGER NOT NULL REFERENCES ingest_run(run_id),
    report_code         TEXT NOT NULL,
    source_system       TEXT NOT NULL,
    filename            TEXT NOT NULL,
    source_path         TEXT NOT NULL,
    sha256              TEXT NOT NULL,
    as_of_date          TEXT NOT NULL,
    row_count           INTEGER NOT NULL DEFAULT 0,
    skipped_lines       INTEGER NOT NULL DEFAULT 0,
    control_total_cents INTEGER,
    parsed_total_cents  INTEGER,
    status              TEXT NOT NULL,
    message             TEXT,
    loaded_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ingest_file_report ON ingest_file(report_code, as_of_date);

-- A file is identified by report, as-of date and content hash together, never
-- by name. Re-running the loader over the same inbox cannot double-count. The
-- date has to be part of the key: a quiet day can produce a report that is
-- byte-identical to yesterday's, and that is still a real snapshot for a real
-- day, not a duplicate. Keying on the hash alone would silently erase it from
-- the history and put a hole in every trend line.
CREATE UNIQUE INDEX IF NOT EXISTS ux_ingest_file_identity
    ON ingest_file(report_code, as_of_date, sha256);

CREATE TABLE IF NOT EXISTS dq_result (
    result_id  INTEGER PRIMARY KEY,
    run_id     INTEGER NOT NULL REFERENCES ingest_run(run_id),
    check_name TEXT NOT NULL,
    severity   TEXT NOT NULL,
    status     TEXT NOT NULL,
    observed   TEXT,
    message    TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_dq_result_run ON dq_result(run_id, status);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key             TEXT PRIMARY KEY,
    fiscal_year          INTEGER NOT NULL,
    fiscal_quarter       INTEGER NOT NULL,
    fiscal_period        INTEGER NOT NULL,
    fiscal_label         TEXT NOT NULL,
    fiscal_quarter_label TEXT NOT NULL,
    calendar_year        INTEGER NOT NULL,
    calendar_month       INTEGER NOT NULL,
    month_name           TEXT NOT NULL,
    day_of_month         INTEGER NOT NULL,
    is_month_end         INTEGER NOT NULL,
    is_fiscal_year_end   INTEGER NOT NULL
);

-- Mirror of the configured report catalogue, refreshed on every run. Having it
-- in the database lets the freshness view answer "which report did not arrive
-- today" in pure SQL, including for reports that have never loaded at all.
CREATE TABLE IF NOT EXISTS ref_report (
    report_code           TEXT PRIMARY KEY,
    report_name           TEXT NOT NULL,
    source_system         TEXT NOT NULL,
    expected_cadence_days INTEGER NOT NULL
);

-- Budget object code groupings are facility- and appropriation-specific, so
-- this table ships empty on purpose. Populate it from your own BOC crosswalk;
-- anything not listed rolls up as 'Unmapped' rather than being silently binned.
CREATE TABLE IF NOT EXISTS ref_boc_category (
    boc          TEXT PRIMARY KEY,
    boc_name     TEXT,
    boc_category TEXT
);
