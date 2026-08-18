# Connecting Power BI

The goal is **one dataset, many reports**. That is what "single sourced" means
in practice, and it is the thing that stops workbook sprawl from reappearing in
a new technology. If four dashboards each carry their own copy of the logic, the
old problem has been rebuilt with different tooling.

---

## Connecting to SQLite

Power BI has no native SQLite connector, so you need an ODBC driver — and
**driver installation on a VA workstation needs approval**. Establish that
before planning around it. Two routes:

**ODBC.** Install the SQLite ODBC driver, create a System DSN pointing at
`budget.db`, then *Get Data → ODBC*. Import mode, not DirectQuery.

**No driver available.** Two fallbacks that need nothing installed:

- Have the nightly job export the views to CSV in a `curated/` folder and point
  Power BI at the folder. You keep the database benefits — validation, history,
  reconciliation — and Power BI reads flat files.
- Move the database to SQL Server, which Power BI connects to natively. This is
  the end state anyway once readership grows.

If the pipeline database is promoted to SQL Server, use *Get Data → SQL Server*,
Import mode, and select only the `v_*` views.

---

## Connect to views only

Import `v_*`. Never `stg_*`, never `fact_*` directly.

The views are a contract. Anything behind them — column renames, grain changes,
mart refactoring — can change without breaking a single report, as long as the
views keep their shape. Import the underlying tables and every refactor becomes
a report-breaking change.

| Import | Purpose |
|---|---|
| `v_fcp_daily_balance` | Core fact — daily balances by control point |
| `v_fcp_burn_rate` | Burn rate and projected exhaustion |
| `v_cp_transaction` | Transaction detail |
| `v_invoice_aging` | Invoice pipeline and ageing |
| `v_ifcap_vs_fms_monthly` | Reconciliation to the accounting system |
| `v_report_freshness` | Staleness — put this on every page |
| `dim_date`, `dim_fcp`, `dim_boc` | Dimensions |

---

## Model setup

**Mark `dim_date` as a date table.** Power BI's time intelligence needs this,
and the federal fiscal year makes it more important than usual: fiscal year 2026
runs 1 October 2025 to 30 September 2026, so calendar-year defaults are wrong
for essentially every measure you care about. `dim_date` already carries
`fiscal_year`, `fiscal_quarter`, `fiscal_period`, `fiscal_label` and
`fiscal_quarter_label` — use those on axes, never the calendar columns.

**Relationships.** `dim_date[date_key]` → the `as_of_date` / `txn_date` columns,
one-to-many, single direction. `dim_fcp[fcp]` and `dim_boc[boc]` likewise. Keep
filters single-direction unless you have a specific reason; bidirectional
filtering creates ambiguity that surfaces later as numbers nobody can explain.

**Currency columns.** Set to *Fixed Decimal Number*. The views already divide
integer cents by 100; Fixed Decimal keeps it exact from there.

**Sort ordering.** Sort `fiscal_label` by `fiscal_period` and
`fiscal_quarter_label` by `fiscal_quarter`, or months appear alphabetically.

---

## A starting set of measures

```dax
Obligations = SUM(v_fcp_daily_balance[obligations])
Allocation  = SUM(v_fcp_daily_balance[allocation])
Balance     = SUM(v_fcp_daily_balance[balance])

Pct Obligated =
DIVIDE([Obligations], [Allocation])

-- Snapshot facts must never be summed across dates. This is the single most
-- common way a daily-snapshot model produces nonsense: eight control points
-- across sixty days silently returns sixty times the real balance.
Balance (latest) =
CALCULATE(
    [Balance],
    LASTNONBLANK(dim_date[date_key], [Balance])
)

Obligations MTD =
CALCULATE([Obligations], DATESMTD(dim_date[date_key]))

Obligations FYTD =
CALCULATE(
    [Obligations],
    DATESYTD(dim_date[date_key], "09-30")   -- federal fiscal year end
)
```

Note the `"09-30"` argument on `DATESYTD`. Without it Power BI uses 31 December
and every year-to-date figure is wrong from October onward — quietly, and in a
way that looks plausible.

---

## Four dashboards, four decisions

Design each around the decision it supports. A page that does not change what
someone does is decoration.

**Daily — "is anything about to run out?"**
Freshness banner. Control points sorted by days-of-funding-remaining. Yesterday's
transactions. Exceptions from the quality checks.

**Monthly — "where are we against plan?"**
Obligation rate by control point. Month-over-month movement. **The FMS
reconciliation.** Invoice ageing.

**Quarterly — "what is the trend?"**
Quarter-over-quarter by budget object category. Burn rate trend. Projected
year-end position.

**Annual — "what happened, and what should next year's number be?"**
Full-year actuals against allocation. Seasonality. Vendor concentration.

---

## Put freshness on the face of every page

```dax
Data As Of = MAX(v_fcp_daily_balance[as_of_date])

Freshness Warning =
VAR Stale = CALCULATE(COUNTROWS(v_report_freshness),
                      v_report_freshness[freshness_status] <> "current")
RETURN IF(Stale > 0, "⚠ " & Stale & " report(s) stale", "")
```

A dashboard that silently shows yesterday's numbers as though they were today's
is the failure mode that ends trust permanently — and unlike a wrong number, it
produces no visible symptom. Showing the as-of date costs one card and removes
the entire category of problem.

---

## Refresh

Order matters: the ingest job runs, then the dataset refreshes. Scheduling the
refresh before the load leaves the dashboard a day behind while looking healthy.

- **Power BI Service:** scheduled refresh via an on-premises data gateway
  (standard mode, not personal). The gateway connects outbound only.
- **Report Server:** scheduled refresh plans on the server.
- **Neither available:** Power BI Desktop against the shared database, refreshed
  manually — still a large improvement, since the logic is in one model rather
  than scattered across linked workbooks.

Confirm what your VISN or facility actually provides before designing around any
of these — see question 7 in
[`../../discovery/open-questions.md`](../../discovery/open-questions.md). And do
not plan on Power BI Reports Scheduler: it is carried in the VA TRM as
*Unauthorized, Conditions Required (POA&M Required)*.
