-- Conformed mart, rebuilt from staging on every run.
--
-- This file is the part you are meant to edit. Staging mirrors whatever the
-- source system emits; this layer turns it into the handful of tables a budget
-- analyst actually reasons about, and the v_ views are the only thing Power BI
-- should ever connect to.
--
-- Two conventions run through everything below:
--   1. Money is integer cents in fact tables and dollars in views. Aggregate
--      the cents, divide once at the end.
--   2. When the same report arrives twice for the same as-of date -- a rerun,
--      a correction -- the later file wins. v_current_file encodes that, and
--      every fact selects through it, so a corrected report supersedes the
--      original without anyone deleting anything.

DROP VIEW IF EXISTS v_current_file;
CREATE VIEW v_current_file AS
SELECT report_code, as_of_date, MAX(file_id) AS file_id
FROM ingest_file
WHERE status = 'loaded'
GROUP BY report_code, as_of_date;


-- ---------------------------------------------------------------------------
-- Dimensions
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS dim_fcp;
CREATE TABLE dim_fcp AS
WITH named AS (
    SELECT s.fcp,
           s.fcp_name,
           ROW_NUMBER() OVER (PARTITION BY s.fcp ORDER BY s.as_of_date DESC) AS rn
    FROM stg_sof s
    JOIN v_current_file c ON c.file_id = s.file_id
    WHERE s.fcp IS NOT NULL
),
seen AS (
    SELECT fcp, MIN(as_of_date) AS first_seen, MAX(as_of_date) AS last_seen
    FROM (
        SELECT fcp, as_of_date FROM stg_sof
        UNION ALL SELECT fcp, as_of_date FROM stg_cpa
        UNION ALL SELECT fcp, as_of_date FROM stg_obl1358
    )
    WHERE fcp IS NOT NULL
    GROUP BY fcp
)
SELECT seen.fcp,
       COALESCE(named.fcp_name, '(name not on any Status of Funds report)') AS fcp_name,
       seen.first_seen,
       seen.last_seen
FROM seen
LEFT JOIN named ON named.fcp = seen.fcp AND named.rn = 1;

CREATE UNIQUE INDEX ux_dim_fcp ON dim_fcp(fcp);


DROP TABLE IF EXISTS dim_boc;
CREATE TABLE dim_boc AS
WITH seen AS (
    SELECT boc FROM stg_cpa WHERE boc IS NOT NULL
    UNION
    SELECT boc FROM stg_fmsact WHERE boc IS NOT NULL
)
SELECT seen.boc,
       COALESCE(r.boc_name, '(unmapped)') AS boc_name,
       COALESCE(r.boc_category, 'Unmapped') AS boc_category
FROM seen
LEFT JOIN ref_boc_category r ON r.boc = seen.boc;

CREATE UNIQUE INDEX ux_dim_boc ON dim_boc(boc);


DROP TABLE IF EXISTS dim_vendor;
CREATE TABLE dim_vendor AS
WITH seen AS (
    SELECT vendor_name FROM stg_cpa WHERE vendor_name IS NOT NULL
    UNION
    SELECT vendor_name FROM stg_ipps WHERE vendor_name IS NOT NULL
)
SELECT vendor_name,
       UPPER(TRIM(vendor_name)) AS vendor_key
FROM seen;

CREATE UNIQUE INDEX ux_dim_vendor ON dim_vendor(vendor_name);


-- ---------------------------------------------------------------------------
-- Facts
-- ---------------------------------------------------------------------------

-- Status of Funds: a true daily snapshot. Every day is kept, which is what
-- makes trend, burn rate and "what did we think on the 15th" possible at all.
-- The current Excel chain overwrites, so none of those questions can be asked.
DROP TABLE IF EXISTS fact_fcp_daily_balance;
CREATE TABLE fact_fcp_daily_balance AS
SELECT s.as_of_date,
       s.fcp,
       s.allocation_cents,
       s.commitments_cents,
       s.obligations_cents,
       s.expenditures_cents,
       s.balance_cents
FROM stg_sof s
JOIN v_current_file c ON c.file_id = s.file_id
WHERE s.fcp IS NOT NULL;

CREATE UNIQUE INDEX ux_fact_fcp_daily ON fact_fcp_daily_balance(as_of_date, fcp);


-- Control point activity arrives as a fiscal-year-to-date cumulative extract,
-- so the newest snapshot in each fiscal year already contains that whole year.
-- Taking only the winning snapshot per FY avoids multiplying every transaction
-- by the number of days it has appeared on a report.
DROP TABLE IF EXISTS fact_cp_transaction;
CREATE TABLE fact_cp_transaction AS
WITH snap AS (
    SELECT c.file_id, c.as_of_date, d.fiscal_year
    FROM v_current_file c
    JOIN dim_date d ON d.date_key = c.as_of_date
    WHERE c.report_code = 'CPA'
),
winner AS (
    SELECT fiscal_year, MAX(as_of_date) AS as_of_date
    FROM snap
    GROUP BY fiscal_year
)
SELECT s.txn_date,
       s.doc_number,
       s.doc_type,
       s.fcp,
       s.boc,
       s.vendor_name,
       s.description,
       s.amount_cents,
       s.status,
       snap.fiscal_year,
       snap.as_of_date AS snapshot_date
FROM stg_cpa s
JOIN snap ON snap.file_id = s.file_id
JOIN winner ON winner.fiscal_year = snap.fiscal_year
           AND winner.as_of_date = snap.as_of_date;

CREATE INDEX ix_fact_cp_txn_fcp ON fact_cp_transaction(fcp, txn_date);


DROP TABLE IF EXISTS fact_1358_balance;
CREATE TABLE fact_1358_balance AS
SELECT s.as_of_date,
       s.obligation_number,
       s.fcp,
       s.description,
       s.authorized_cents,
       s.obligated_cents,
       s.liquidated_cents,
       s.remaining_cents
FROM stg_obl1358 s
JOIN v_current_file c ON c.file_id = s.file_id
WHERE s.obligation_number IS NOT NULL;

CREATE UNIQUE INDEX ux_fact_1358 ON fact_1358_balance(as_of_date, obligation_number);


-- Invoices are a status list: an invoice appears while it is in flight and may
-- drop off once settled. Keeping the most recent row per invoice number across
-- all snapshots preserves the full population instead of only today's open items.
DROP TABLE IF EXISTS fact_invoice;
CREATE TABLE fact_invoice AS
WITH ranked AS (
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY s.invoice_number
               ORDER BY s.as_of_date DESC, s.row_id DESC
           ) AS rn
    FROM stg_ipps s
    JOIN v_current_file c ON c.file_id = s.file_id
    WHERE s.invoice_number IS NOT NULL
)
SELECT invoice_number,
       po_number,
       vendor_name,
       invoice_date,
       received_date,
       certified_date,
       paid_date,
       amount_cents,
       status,
       as_of_date AS last_seen_date
FROM ranked
WHERE rn = 1;

CREATE UNIQUE INDEX ux_fact_invoice ON fact_invoice(invoice_number);


-- FMS/iFAMS general ledger actuals, the authoritative side of any reconciliation.
DROP TABLE IF EXISTS fact_gl_actual;
CREATE TABLE fact_gl_actual AS
WITH ranked AS (
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY s.fiscal_year, s.accounting_period, s.fund,
                            s.cost_center, s.boc
               ORDER BY s.as_of_date DESC, s.row_id DESC
           ) AS rn
    FROM stg_fmsact s
    JOIN v_current_file c ON c.file_id = s.file_id
)
SELECT fiscal_year,
       accounting_period,
       fund,
       cost_center,
       boc,
       obligations_cents,
       expenditures_cents,
       as_of_date AS last_seen_date
FROM ranked
WHERE rn = 1;

CREATE UNIQUE INDEX ux_fact_gl_actual
    ON fact_gl_actual(fiscal_year, accounting_period, fund, cost_center, boc);


-- ---------------------------------------------------------------------------
-- Presentation views -- the Power BI contract
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS v_fcp_daily_balance;
CREATE VIEW v_fcp_daily_balance AS
SELECT f.as_of_date,
       d.fiscal_year,
       d.fiscal_quarter_label,
       d.fiscal_label,
       d.is_month_end,
       f.fcp,
       p.fcp_name,
       f.allocation_cents   / 100.0 AS allocation,
       f.commitments_cents  / 100.0 AS commitments,
       f.obligations_cents  / 100.0 AS obligations,
       f.expenditures_cents / 100.0 AS expenditures,
       f.balance_cents      / 100.0 AS balance,
       CASE WHEN f.allocation_cents > 0
            THEN ROUND(100.0 * f.obligations_cents / f.allocation_cents, 2)
       END AS pct_obligated
FROM fact_fcp_daily_balance f
JOIN dim_date d ON d.date_key = f.as_of_date
LEFT JOIN dim_fcp p ON p.fcp = f.fcp;


DROP VIEW IF EXISTS v_fcp_burn_rate;
CREATE VIEW v_fcp_burn_rate AS
WITH daily AS (
    SELECT fcp,
           as_of_date,
           obligations_cents,
           balance_cents,
           obligations_cents - LAG(obligations_cents)
               OVER (PARTITION BY fcp ORDER BY as_of_date) AS delta_cents
    FROM fact_fcp_daily_balance
),
smoothed AS (
    SELECT daily.*,
           AVG(delta_cents) OVER (
               PARTITION BY fcp ORDER BY as_of_date
               ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
           ) AS avg_daily_burn_cents
    FROM daily
)
SELECT s.fcp,
       p.fcp_name,
       s.as_of_date,
       d.fiscal_year,
       d.fiscal_label,
       s.delta_cents           / 100.0 AS obligations_change,
       s.avg_daily_burn_cents  / 100.0 AS avg_daily_burn_30d,
       s.balance_cents         / 100.0 AS balance,
       CASE WHEN s.avg_daily_burn_cents > 0
            THEN CAST(s.balance_cents / s.avg_daily_burn_cents AS INTEGER)
       END AS days_of_funding_remaining,
       CASE WHEN s.avg_daily_burn_cents > 0
            THEN DATE(s.as_of_date,
                      '+' || CAST(s.balance_cents / s.avg_daily_burn_cents AS INTEGER) || ' days')
       END AS projected_exhaustion_date
FROM smoothed s
JOIN dim_date d ON d.date_key = s.as_of_date
LEFT JOIN dim_fcp p ON p.fcp = s.fcp;


DROP VIEW IF EXISTS v_cp_transaction;
CREATE VIEW v_cp_transaction AS
SELECT t.txn_date,
       d.fiscal_year,
       d.fiscal_quarter_label,
       d.fiscal_label,
       t.doc_number,
       t.doc_type,
       t.fcp,
       p.fcp_name,
       t.boc,
       b.boc_category,
       t.vendor_name,
       t.description,
       t.status,
       t.amount_cents / 100.0 AS amount
FROM fact_cp_transaction t
LEFT JOIN dim_date d ON d.date_key = t.txn_date
LEFT JOIN dim_fcp p ON p.fcp = t.fcp
LEFT JOIN dim_boc b ON b.boc = t.boc;


-- Aging is measured against the newest snapshot rather than the clock, so the
-- same database always produces the same numbers.
DROP VIEW IF EXISTS v_invoice_aging;
CREATE VIEW v_invoice_aging AS
WITH asof AS (SELECT MAX(last_seen_date) AS d FROM fact_invoice)
SELECT i.invoice_number,
       i.po_number,
       i.vendor_name,
       i.invoice_date,
       i.received_date,
       i.certified_date,
       i.paid_date,
       i.status,
       i.amount_cents / 100.0 AS amount,
       (SELECT d FROM asof) AS as_of_date,
       CASE WHEN i.paid_date IS NOT NULL
            THEN CAST(julianday(i.paid_date) - julianday(i.invoice_date) AS INTEGER)
       END AS days_invoice_to_payment,
       CASE WHEN i.paid_date IS NULL
            THEN CAST(julianday((SELECT d FROM asof)) - julianday(i.invoice_date) AS INTEGER)
       END AS days_outstanding,
       CASE
           WHEN i.paid_date IS NOT NULL THEN 'Paid'
           WHEN julianday((SELECT d FROM asof)) - julianday(i.invoice_date) <= 30 THEN '0-30'
           WHEN julianday((SELECT d FROM asof)) - julianday(i.invoice_date) <= 60 THEN '31-60'
           WHEN julianday((SELECT d FROM asof)) - julianday(i.invoice_date) <= 90 THEN '61-90'
           ELSE '90+'
       END AS aging_bucket
FROM fact_invoice i;


-- The reconciliation that decides whether anyone trusts the dashboard: does
-- what IFCAP thinks was obligated agree with what the accounting system booked?
DROP VIEW IF EXISTS v_ifcap_vs_fms_monthly;
CREATE VIEW v_ifcap_vs_fms_monthly AS
WITH ifcap AS (
    SELECT d.fiscal_year,
           d.fiscal_period,
           SUM(t.amount_cents) AS ifcap_cents
    FROM fact_cp_transaction t
    JOIN dim_date d ON d.date_key = t.txn_date
    GROUP BY d.fiscal_year, d.fiscal_period
),
fms AS (
    SELECT fiscal_year,
           accounting_period AS fiscal_period,
           SUM(obligations_cents) AS fms_cents
    FROM fact_gl_actual
    GROUP BY fiscal_year, accounting_period
)
SELECT COALESCE(ifcap.fiscal_year, fms.fiscal_year)   AS fiscal_year,
       COALESCE(ifcap.fiscal_period, fms.fiscal_period) AS fiscal_period,
       COALESCE(ifcap.ifcap_cents, 0) / 100.0 AS ifcap_obligations,
       COALESCE(fms.fms_cents, 0)     / 100.0 AS fms_obligations,
       (COALESCE(ifcap.ifcap_cents, 0) - COALESCE(fms.fms_cents, 0)) / 100.0 AS variance,
       CASE WHEN COALESCE(fms.fms_cents, 0) <> 0
            THEN ROUND(100.0 * (COALESCE(ifcap.ifcap_cents, 0) - fms.fms_cents)
                       / ABS(fms.fms_cents), 2)
       END AS variance_pct
FROM ifcap
FULL OUTER JOIN fms
     ON fms.fiscal_year = ifcap.fiscal_year
    AND fms.fiscal_period = ifcap.fiscal_period;


-- Freshness is a first-class measure. A dashboard that quietly shows yesterday's
-- number as though it were today's is the failure mode that destroys trust, so
-- staleness is published next to the data rather than left to be noticed.
DROP VIEW IF EXISTS v_report_freshness;
CREATE VIEW v_report_freshness AS
WITH latest AS (
    SELECT report_code, MAX(as_of_date) AS latest_as_of, COUNT(*) AS snapshots
    FROM ingest_file
    WHERE status = 'loaded'
    GROUP BY report_code
),
clock AS (SELECT MAX(as_of_date) AS today FROM ingest_file WHERE status = 'loaded')
SELECT r.report_code,
       r.report_name,
       r.source_system,
       r.expected_cadence_days,
       latest.latest_as_of,
       COALESCE(latest.snapshots, 0) AS snapshots_loaded,
       CAST(julianday((SELECT today FROM clock)) - julianday(latest.latest_as_of) AS INTEGER)
           AS days_stale,
       CASE
           WHEN latest.latest_as_of IS NULL THEN 'never loaded'
           WHEN julianday((SELECT today FROM clock)) - julianday(latest.latest_as_of)
                > r.expected_cadence_days THEN 'stale'
           ELSE 'current'
       END AS freshness_status
FROM ref_report r
LEFT JOIN latest ON latest.report_code = r.report_code;


DROP VIEW IF EXISTS v_ingest_audit;
CREATE VIEW v_ingest_audit AS
SELECT f.file_id,
       f.run_id,
       f.report_code,
       f.source_system,
       f.filename,
       f.as_of_date,
       f.row_count,
       f.status,
       f.message,
       f.loaded_at,
       f.sha256,
       f.control_total_cents / 100.0 AS report_control_total,
       f.parsed_total_cents  / 100.0 AS parsed_total,
       CASE
           WHEN f.control_total_cents IS NULL THEN 'no control total on report'
           WHEN f.control_total_cents = f.parsed_total_cents THEN 'match'
           ELSE 'MISMATCH'
       END AS control_total_check
FROM ingest_file f;
