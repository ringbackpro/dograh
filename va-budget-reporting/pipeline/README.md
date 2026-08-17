# Budget report pipeline

Turns the daily pile of `.csv` and `.txt` budget reports into one local SQLite
database with a stable set of views for Power BI — replacing the chain of linked
Excel workbooks.

**Standard library only.** No `pip install`, no dependencies, nothing to get
approved. Python 3.11 or later (it uses `tomllib`).

---

## Try it in two minutes

No VA data required — the sample generator writes realistically-shaped reports,
including fixed-width captures with page breaks and printed totals.

```bash
cd pipeline

python3 -m vabudget sample --out ./inbox --start 2025-10-01 --end 2025-12-19
python3 -m vabudget ingest --inbox ./inbox
python3 -m vabudget status
```

Then watch the checks catch things that are wrong:

```bash
python3 -m vabudget --db faulty.db sample --out ./faulty --inject-faults \
    --start 2025-10-01 --end 2025-12-19
python3 -m vabudget --db faulty.db ingest --inbox ./faulty
```

That injects the two failures most likely to happen in real life — a screen
capture that stopped early, and a day that silently never arrived — and both are
reported:

```
  [ERROR] control_total_match: 1 row(s)
          A report's printed total disagrees with the rows parsed from it,
          which usually means a truncated capture.
          -> (filename='SOF_20251219.txt', printed_total=3277625.95,
              parsed_total=2409561.24)
  [WARN ] snapshot_gaps: 1 row(s)
          -> (missing_business_day='2025-11-11')
```

The first is the one that matters most. A truncated report looks completely
normal — right format, plausible numbers, just fewer rows — and comparing
against the total the report printed on itself is the only cheap way to notice.

Run the tests:

```bash
python3 -m unittest discover -s tests -t .
```

---

## Commands

| Command | Does |
|---|---|
| `init` | Create the database and staging tables |
| `sample` | Write synthetic reports (`--inject-faults` to break things) |
| `ingest` | Parse everything in the inbox, rebuild the mart, run checks |
| `check` | Run the data-quality rulebook on its own |
| `rebuild` | Rebuild the mart from staging without re-reading files |
| `status` | What is loaded, what is stale, which control totals disagree |

Exit codes, because this runs unattended: **0** fine, **1** an error-severity
problem needing a human, **2** misconfigured or misinvoked.

---

## Onboarding a real report

This is the actual work, and it is config, not code. Every report is one
`[[report]]` block in `config/reports.toml`.

**Fixed-width** (a captured roll-and-scroll screen) — count offsets off the
printed report; `start` is 1-based:

```toml
[[report]]
code = "SOF"
name = "Status of Funds by Control Point"
source_system = "IFCAP"
format = "fixed"
filename_glob = "SOF_*.txt"
as_of_from = "filename"
as_of_pattern = 'SOF_(\d{8})\.txt'
row_pattern = '^\d{4}\s'          # data lines start with a 4-digit control point

  [report.control_total]           # the total the report prints on itself
  pattern = 'TOTAL OBLIGATIONS:\s+([\d,]+\.\d{2})'
  column = "obligations_cents"

  [[report.column]]
  name = "fcp"
  start = 1
  length = 8
```

**Delimited** — locate columns by header text:

```toml
  [[report.column]]
  name = "amount_cents"
  type = "amount"
  source = "Amount"
```

Three things worth knowing:

- **Amounts are integer cents** and the column name must end in `_cents`. The
  loader rejects the config otherwise, deliberately, so no downstream reader can
  mistake the unit. Parentheses, trailing `CR` and trailing `-` all parse as
  negative.
- **`row_pattern` beats `skip_patterns`** for fixed-width reports. Describing
  what a data row looks like is more robust than enumerating every kind of page
  furniture you hope to exclude.
- **Always define a `control_total` if the report prints one.** It is the single
  highest-value line of configuration you can write.

Then add checks in `config/checks.toml`. Each is a query selecting violations
plus a severity — no Python involved:

```toml
[[check]]
name = "negative_balance"
severity = "warn"
message = "A control point shows a negative available balance."
sql = "SELECT as_of_date, fcp FROM fact_fcp_daily_balance WHERE balance_cents < 0"
```

---

## How it is put together

```
inbox/*.csv,*.txt          files as downloaded, untouched
   │
   ├─ parse         config-driven; fixed-width or delimited
   ├─ stage         stg_<report>, append-only, every row traceable to its file
   ├─ build         dim_* / fact_*, rebuilt from staging each run
   └─ views         v_* — the only thing Power BI connects to
```

Three layers, because each answers a different question: staging answers "what
did the source actually say", the mart answers "what do we mean by this", and
the views answer "what should a reader see".

**Decisions worth knowing about:**

*A file is identified by report + as-of date + content hash.* Re-running over
the same inbox loads nothing. But a quiet day can produce a report
byte-identical to yesterday's, and that is still a real snapshot for a real day
— keying on the hash alone would erase it from history and put a hole in every
trend line.

*Corrections supersede without deleting.* Load a corrected report for a date
already loaded and both files are kept for audit, while `v_current_file` makes
the later one win. Nothing is ever hand-patched to fix a number.

*The mart is rebuilt from scratch every run*, so it is a pure function of the
staged files. A bad load is fixed by correcting staging and re-running.

*Daily snapshots are retained.* This is what makes burn rate, trend and
as-of-date reporting possible — the questions the overwrite-based workbook
cannot answer at all.

*Money is integer cents*, aggregated in cents and divided once at the view
layer.

*One bad file does not stop the others.* It lands in the audit trail with the
reason and is retried automatically next run once the cause is fixed.

---

## What the views give you

| View | For |
|---|---|
| `v_fcp_daily_balance` | Allocation, commitments, obligations, balance, % obligated |
| `v_fcp_burn_rate` | 30-day average burn, days of funding left, projected exhaustion date |
| `v_cp_transaction` | Transaction detail by control point, budget object code, vendor |
| `v_invoice_aging` | Invoice-to-payment days and ageing buckets |
| `v_ifcap_vs_fms_monthly` | **Reconciliation to the accounting system** |
| `v_report_freshness` | Which report is late, and by how long |
| `v_ingest_audit` | Every file loaded, with control-total verdict |

The last three matter more than they look. `v_ifcap_vs_fms_monthly` is what
stops Fiscal contradicting your dashboard in a meeting; `v_report_freshness`
stops it silently showing yesterday as today; `v_ingest_audit` is how you answer
"where did this number come from" with a filename and a hash.

---

## Scheduling it

Windows Task Scheduler, daily, after the reports land:

```bat
python -m vabudget --db "D:\budget\budget.db" ingest --inbox "D:\budget\inbox"
```

The exit code tells the scheduler whether a human is needed. Do not plan on
Power BI Reports Scheduler — it is carried in the VA TRM as *Unauthorized,
Conditions Required (POA&M Required)*.

---

## Adapting it

The five shipped reports are modelled on realistic shapes, **not measured from
real VA files**. The column offsets are illustrative. Expect to:

1. Replace offsets and header names in `config/reports.toml` with real ones.
2. **Verify the balance identity** in `config/checks.toml` against a real Status
   of Funds report. It currently assumes
   `balance = allocation − commitments − obligations`, with expenditures inside
   obligations. If your report treats them separately, every balance shifts —
   see question 4 in [`../discovery/open-questions.md`](../discovery/open-questions.md).
3. Adjust `sql/200_marts.sql` where your grain differs.
4. Populate `ref_boc_category` from your own budget object code crosswalk. It
   ships empty on purpose; unmapped codes roll up as `Unmapped` rather than
   being silently binned.
