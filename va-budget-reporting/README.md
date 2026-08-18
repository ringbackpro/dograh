# VA budget reporting — discovery and reference pipeline

Discovery work on replacing a chain of linked Excel workbooks — fed by
Reflection macros screen-scraping VistA — with a single-sourced, automatically
updated, locally-managed budget reporting system feeding Power BI dashboards.

> **Scope note.** This directory is self-contained and unrelated to the rest of
> this repository's application code. It touches no application, build or docs
> configuration, and can be moved out or deleted without affecting anything else.

## What's here

| | |
|---|---|
| [`discovery/discovery-report.md`](discovery/discovery-report.md) | **Start here.** Findings on IFCAP/VistA, FMS and IPPS integration, scheduling options, governance constraints, recommended architecture, phased plan, risks |
| [`discovery/open-questions.md`](discovery/open-questions.md) | What still needs answering on the VA intranet, who to ask, and what changes based on each answer |
| [`pipeline/`](pipeline/) | Working, tested reference implementation — reports in, one database out, Power BI-ready |
| [`pipeline/powerbi/CONNECTING.md`](pipeline/powerbi/CONNECTING.md) | Model setup, fiscal-year DAX, dashboard structure, refresh |
| [`HANDOFF.md`](HANDOFF.md) | **Everything above in one self-contained file**, plus instructions for a receiving account and full source. For moving this work elsewhere — no repo access needed |

`HANDOFF.md` is generated. After editing anything here, regenerate it with
`python3 handoff/build.py` so the export cannot drift from what it describes.

## The finding in brief

**Scheduled internal generation is achievable.** VistA's TaskMan
(`Schedule/Unschedule Options` [XUTM SCHEDULE]) is the cron of VistA, and most
VistA print options are queueable. Crucially, scheduling an *existing national
option* is configuration rather than software development — which keeps the
request clear of VA Directive 6402's restriction on local VistA modification,
and makes it something an IRM office can action.

**But the source layer is a depreciating asset.** FMS and IFCAP are being
replaced by iFAMS; waves 7–8 deployed in August 2025 including the first VHA
users, with the remaining VHA wave representing over 92% of iFAMS users.

**And someone inside VA may already publish this.** VA's Financial Services
Center runs a Data Analytics Service — an enterprise BI platform accessible
VA-wide on approval of VA Form 9957, already delivering Power BI products from
FSC financial systems. FSC operates IPPS and FMS payment processing.

So the recommendation is: **invest in the destination, keep the source layer
thin and swappable.**

1. **Now, entirely within your own authority** — load the reports you already
   download into one local database with validation and retained history. This
   alone retires the workbook chain.
2. **In parallel** — ask FSC DAS and CDW whether they already publish what you
   need. A form beats a pipeline.
3. **Then** — request TaskMan scheduling so no human has to log in to produce
   the data.
4. **Throughout** — model business concepts, not file layouts, so the iFAMS
   cutover is a source-adapter change rather than a rebuild.

## What the reference pipeline does

Standard library Python only — no `pip install`, which matters on a locked-down
workstation.

```bash
cd pipeline
python3 -m vabudget sample --out ./inbox --start 2025-10-01 --end 2025-12-19
python3 -m vabudget ingest --inbox ./inbox
python3 -m vabudget status
```

Config-driven parsers for fixed-width VistA captures and delimited exports; a
SQLite star schema retaining **daily snapshots** (so burn rate, trend and
as-of-date questions become answerable — they are impossible today, because each
refresh overwrites the last); a SQL-defined data-quality rulebook; a synthetic
data generator so it runs with no VA data present; 42 passing tests.

Two capabilities carry most of the trust argument:

- **Control totals.** A truncated screen capture looks completely normal — right
  format, plausible numbers, just fewer rows. Comparing the report's own printed
  total against the rows parsed is the only cheap way to catch it.
- **Published freshness.** A dashboard silently showing yesterday as today is
  the failure that ends trust permanently, and it has no visible symptom.
  Staleness appears on the dashboard.

## Before using it against real data

The five shipped report definitions are modelled on realistic shapes, **not
measured from real VA files**. Onboarding each real report means editing
`pipeline/config/reports.toml`.

One item needs local confirmation before anyone makes a decision on the output:
the pipeline assumes `balance = allocation − commitments − obligations`, with
expenditures inside obligations rather than deducted separately. If your Status
of Funds report treats them differently, **every balance shifts silently**. See
question 4 in [`discovery/open-questions.md`](discovery/open-questions.md).
