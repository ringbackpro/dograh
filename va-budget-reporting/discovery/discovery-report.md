# Automating VA budget reporting: IFCAP, FMS and IPPS into a local database

**Question asked.** Can IFCAP (inside VistA), FMS and IPPS be made to generate
budget data on a schedule — a cron job or equivalent — and land it in a local
database inside VA infrastructure, feeding daily / monthly / quarterly / annual
Power BI dashboards, without making the budget subsystem harder to use or less
available to anyone in VA?

**Short answer.** Yes for scheduling, with an important qualification about
*where* to invest. VistA has a native scheduler and it is the right mechanism,
but the highest-value move is not to build a new extract against IFCAP. Three
findings drive the recommendation:

1. **The scheduling primitive already exists and does not require new code.**
   VistA's TaskMan is the cron of VistA: `Schedule/Unschedule Options`
   [XUTM SCHEDULE] on the Taskman Management menu schedules existing menu
   options to run at set times, and most VistA print options are queueable by
   design. Scheduling a *national* option that already exists is a
   configuration change, not software development — which matters enormously,
   because it is the difference between a request your IRM/OIT office can
   action and one that runs into VA Directive 6402.

2. **Building a bespoke IFCAP extract in 2026 buys a depreciating asset.**
   FMS and IFCAP are being replaced by iFAMS under the Financial Management
   Business Transformation program. Waves 7 and 8 deployed in August 2025,
   including the first VHA users, and the remaining VHA wave represents more
   than 92% of iFAMS users. Anything welded tightly to IFCAP's data shapes has
   a limited and partly unknowable service life.

3. **Someone inside VA may already publish what is wanted.** The VA Financial
   Services Center runs a **Data Analytics Service** — an enterprise business
   intelligence platform, accessible VA-wide on approval of VA Form 9957,
   already delivering dashboards and reporting tools from FSC financial systems
   using Power BI. FSC operates IPPS and FMS. The cheapest possible integration
   is a request form rather than a pipeline.

The recommendation that follows from this is: **put the durable investment in
the destination — a local database, a single semantic model, and the
dashboards — and keep the source layer deliberately thin and swappable.** Do
the local ingest now because it is entirely within your own authority and
retires the fragile workbook chain immediately; pursue supported feeds in
parallel on their slower timeline.

> **On sourcing.** Everything cited here comes from public documentation, listed
> at the end. Several specifics — your station's IFCAP menu options, whether an
> FSC DAS product already covers your need, your VISN's SQL and Power BI
> hosting, local ISSO expectations — exist only on the VA intranet and cannot be
> verified from outside. Those are collected in
> [`open-questions.md`](open-questions.md) with the office to ask. Nothing in
> this document should be quoted to a governance board without that local
> confirmation pass.

---

## 1. What is actually wrong today

The current system is not failing because Excel is bad. It is failing for four
specific structural reasons, and it is worth naming them, because a redesign
that does not fix all four just relocates the problem.

| Symptom you described | Underlying cause | What fixes it |
|---|---|---|
| Workbooks too heavy to use | Formula-per-cell over full extracts; every open recalculates everything | Aggregate in a database; ship a model, not formulas |
| Too fragile to be trusted | No validation — a truncated report looks identical to a complete one | Control totals and freshness checks on every load |
| Only a few people can use it | Knowledge lives in cell references and macro code | One documented dataset; readers get a dashboard, not a workbook |
| Cannot auto-generate | Screen-scraping needs an interactive session with a signed-in user | Scheduled generation at the source, or scheduled ingest of the files |
| Cannot answer "what changed" | Each refresh overwrites the last | Keep daily snapshots; history becomes queryable |

That last row is the one most often missed. The current process destroys
yesterday's numbers to produce today's. Burn rate, run-rate projection,
month-over-month variance and "what did we believe on the 15th" are not hard
questions being answered slowly — they are impossible, because the data needed
to answer them was overwritten. A snapshot-retaining database makes an entire
class of budget questions available for the first time, independent of any
source-system integration.

---

## 2. Source systems: what each one is and how data can leave it

### 2.1 IFCAP, inside VistA

IFCAP (Integrated Funds Distribution, Control Point Activity, Accounting and
Procurement) automates funds distribution, control point activity and
procurement for A&MM, Fiscal and requesting services. Fiscal Service establishes
Fund Control Points through it and tracks funding for budget purposes. It is a
VistA package: MUMPS routines over FileMan files, in the `PRC` namespace, with
control point activity, fund control point and procurement/accounting
transaction file groups (files in the 410–414, 417–420 and 441–442 ranges).

The Budget Analyst menu is organised as a Funds Distribution Program Menu
(transactions, budget utilities, a **Print Menu** to monitor funding activity,
and FMS Document Inquiry/Error Processing). The Print Menu is the relevant part:
those are the report options a scheduled task would run.

**Ways data can leave IFCAP, best to worst:**

| Route | Mechanism | New code? | Realistic verdict |
|---|---|---|---|
| Scheduled national report option | TaskMan `XUTM SCHEDULE` runs an existing Print Menu option on a timer, output to a host file or mail group | **No** | **Best internal route.** Configuration, not development |
| FileMan Export Tool | FileMan's import/export tools do ASCII delimited or fixed-length export; can be driven from a saved template | No | Good, but needs FileMan access and privileges most budget staff do not hold |
| Read-only SQL via Caché/IRIS | InterSystems ships a utility converting FileMan files into IRIS classes, giving object and SQL/ODBC access | No (vendor utility) | Technically real, governance-heavy. See §4.3 |
| New local MUMPS routine | Custom extract in a local namespace | **Yes** | **Avoid.** Class III local development — see §5.1 |
| Screen scraping | Reflection macro drives a terminal session | No | What you do today. Fragile, needs a signed-in human, invisible failure modes |

The middle column is the whole argument. **Scheduling something that already
exists is a fundamentally different governance conversation from writing
something new**, and the first conversation is one your IRM office can usually
have without escalation.

**On output destination.** A tasked VistA report needs somewhere to write. Two
established patterns: a Host File Server device pointed at a network share, or
delivery to a MailMan mail group. MailMan is used both for interpersonal mail
and for data transmission to the Austin data centre, and IFCAP itself already
triggers MailMan messages on obligation events — so report-to-mail-group is
well-trodden ground. Which is available at your station is a local question for
IRM.

### 2.2 FMS — and the iFAMS clock

FMS is VA's core accounting system, roughly 30 years old and hosted centrally.
IFCAP does not merely coexist with it: IFCAP creates FMS documents
electronically, transmits them to Austin on obligation, and provides an FMS
Document Inquiry/Error Process for handling rejects. The IFCAP → FMS interface
is a real, documented, one-directional data flow.

For budget reporting this matters in one specific way: **FMS is the
authoritative side of any reconciliation.** IFCAP is where obligations are
initiated; FMS is where they are booked. A dashboard that reports IFCAP figures
without ever reconciling to the accounting system will eventually be
contradicted by Fiscal, and that is exactly the moment a reporting product
loses its audience. The reference implementation therefore ships an
IFCAP-versus-general-ledger reconciliation view and a variance check as a
first-class feature, not an add-on.

**The clock.** FMS is scheduled for replacement by iFAMS, a Momentum-based ERP,
under FMBT — VA's third attempt at this replacement, with a lifecycle cost
estimated around $8.6bn through 2050 and a history of schedule slippage. Waves
7–8 went live in August 2025 covering Loan Guaranty and the first VHA users.
Practical consequences:

- Do not hard-code FMS/IFCAP field layouts into anything expensive. Keep parsing
  declarative and swappable — the reference implementation puts every column
  offset in a config file for exactly this reason.
- Model the *business* concepts (fund control point, budget object code,
  obligation, expenditure, accounting period), which survive the migration,
  rather than the *file* shapes, which will not.
- Track FMBT's VHA wave schedule as a project dependency with a named owner.
- Treat the FMBT **Data Estate** as the probable long-term source and ask about
  field-user access early, not after cutover.

### 2.3 IPPS

IPPS is the Invoice Payment Processing System, run by the VA Financial Services
Center on the Pega platform; FSC reports it cut invoice processing costs by
about a third. FSC also runs a web invoice tool that emails status
notifications as invoices are processed, scheduled to pay, and paid, with
accounting system information refreshed to the web nightly.

For budget management IPPS answers questions IFCAP cannot: where invoices are
in the certification-to-payment pipeline, ageing, prompt-payment exposure, and
which obligations have actually been liquidated. The reference implementation
models invoice lifecycle dates and ships an ageing view.

Public documentation does not expose a self-service extract API. The realistic
routes are an existing FSC report export, or — better — an FSC DAS product
(§3.1).

### 2.4 Sources you did not name but will want

Worth scoping now, because retrofitting a dimension later is painful:

- **Payroll / labour.** At a VA facility, salary is usually the largest single
  budget line. A budget dashboard without labour cost is answering a fraction of
  the question. Ask where facility-level labour actuals come from post-HR·Smart.
- **Managerial Cost Accounting (MCA, formerly DSS).** Activity-based cost
  allocation; MCA datasets sit in CDW and are how VA attributes cost to
  encounters. Relevant to any cost-per-workload view.
- **eCMS** for contract data — the IFCAP Budget Utilities menu already includes
  an eCMS/IFCAP transaction report, so the linkage is recognised.

---

## 3. Integration options, ranked

### 3.1 Option A — consume an existing enterprise product *(check first)*

Before building anything, establish whether the data is already published.

**FSC Data Analytics Service** is the strongest lead. It is described as an
enterprise-level integrated business intelligence and analytics platform with a
client/server architecture, accessible throughout VA on approval of VA Form
9957, staffed with data engineering and architecture expertise, delivering
dashboards, reporting tools and forecasts. FSC runs IPPS, FMS payment
operations and payroll services, and uses Power BI on Microsoft 365/GCC, with
FSC data science modernisation on Azure Databricks.

Also worth checking:

- **CDW**, VHA's national warehouse, accessed via the Data Access Request
  Tracker under National Data Systems. Strong for clinical and MCA cost data;
  whether facility-level IFCAP financial detail is available is a local
  question for the VHA Data Portal.
- **POWER** (Performance and Operational Web-Enabled Reports), a warehouse of
  VHA performance metrics obtained daily from individual VistA systems, with
  web analytics by VISN and station.
- **FMBT Data Estate**, the reporting layer for iFAMS — the probable long-term
  answer.

**Effort:** access requests and forms. **Timeline:** weeks to months, outside
your control. **Payoff:** highest — someone else owns the pipeline, the ATO and
the iFAMS migration. **Risk:** the products may not exist at the granularity a
facility budget analyst needs; you will not know until you ask.

This option is not a substitute for Option B — it is slower and uncertain. Run
both.

### 3.2 Option B — scheduled local ingest of the reports you already pull *(start here)*

Keep generating the reports you are authorised to generate; replace the Excel
macro assembly with a scheduled script that parses them into one local
database, validates them, and serves Power BI.

- **Access needed:** none beyond what you have. You already run these reports.
- **New system:** none. A database file on approved storage.
- **What it kills immediately:** the linked-workbook chain, the recalculation
  weight, the single-expert bottleneck, the silent-staleness problem.
- **What it does not fix:** a human still triggers the extract.

This is the Monday-morning option and it is fully within your own authority.
The working implementation is in [`../pipeline/`](../pipeline/).

Scheduling on the Windows side is ordinary Task Scheduler. Note that Power BI
Report Server's third-party scheduler, **Power BI Reports Scheduler (PBRS), is
listed in the VA TRM as "Unauthorized, Conditions Required (POA&M Required)"** —
so do not design around it. Use Task Scheduler and Power BI's own scheduled
refresh.

### 3.3 Option C — TaskMan-scheduled generation at the source *(the real answer to "cron")*

This is what you actually asked about, and it is achievable.

Ask IRM/OIT to schedule the existing IFCAP report options through
`Schedule/Unschedule Options` [XUTM SCHEDULE], writing output to a host file on
a share (or to a mail group), on a nightly recurrence.

**Why this is the right target state for the source layer:**

- No new software. Scheduling national options is configuration.
- No signed-in human. The report exists at 05:00 whether anyone logged in.
- The Reflection macros stop being load-bearing.
- Failures become visible — a file that did not arrive is detectable, where a
  half-scraped screen is not.
- Zero impact on other users. Adding a scheduled task does not change any menu,
  and off-hours scheduling avoids contention. This directly satisfies your
  "must not make the subsystem harder to use or unavailable" constraint.

**What to confirm locally:** that the specific report options are queueable,
that a suitable device or mail group exists, off-hours scheduling windows, and
who owns the request queue. All in [`open-questions.md`](open-questions.md).

### 3.4 Option D — read-only SQL against VistA

InterSystems ships a utility that converts FileMan files into IRIS classes,
providing object and SQL access, with control over SQL naming and the ability to
map one, many or all FileMan files in a namespace. So a governed read-only SQL
projection of IFCAP data is technically real rather than speculative.

Realistically this needs OIT/IRM sponsorship, a DBA, a strictly read-only
service account, a performance review against a production clinical system, and
security review. It is the most capable option and the slowest. Given the iFAMS
clock, weigh carefully whether a deep VistA SQL integration is worth building
now — for most facility budget offices, Option C plus Option B gets ~90% of the
value at a fraction of the governance cost.

### 3.5 Option E — supported RPA instead of personal macros

If screen automation must remain, move it off a personal Reflection macro and
onto VA's supported platform. VA has an RPA Center of Excellence that plans,
builds, secures, authorises and maintains automations; RPA is owned by the
Enterprise Management Program Office with OIT setting the technology standard,
all access approved and authenticated, and Nintex RPA carried in the TRM.

Slower to obtain than a macro, but it survives staff turnover, is defensible in
an audit, and is supported when it breaks. If your macros are genuinely
load-bearing today, this converts a personal dependency into an institutional
one.

### 3.6 Ranking

| | Option | Time to value | Effort | Durability | Do it? |
|---|---|---|---|---|---|
| 1 | **B — local scheduled ingest** | Days | Low | Medium | **Now.** Yours to do |
| 2 | **A — existing enterprise product** | Weeks–months | Low (forms) | High | **Start the ask in parallel** |
| 3 | **C — TaskMan scheduling** | Weeks | Medium | High | **Yes**, once B proves value |
| 4 | E — supported RPA | Months | Medium | Medium | Only if scraping must persist |
| 5 | D — read-only VistA SQL | Months | High | Medium* | Only with OIT sponsorship |

\* Durability is capped for C, D and E alike by the iFAMS transition.

---

## 4. Constraints that bound every option

### 4.1 Local software development is restricted

VA Directive 6402 controls variation in nationally released VistA software:
it is VA policy that all instances of VistA install the National VistA
Software, enhancement or modification of a specific VistA instance is
prohibited, and Class II/III requests for local modifications go through the
Innovation and Development Request Portal.

**Consequence:** designs that write new MUMPS into VistA are the wrong shape.
Designs that *schedule existing national options* and process the output
downstream are the right shape. This single distinction is the most important
governance insight in this report.

### 4.2 TRM authorisation is necessary, not sufficient

Power BI and its data gateway appear in the TRM as authorised with constraints;
Power BI Report Server and Report Builder are listed; PBRS is unauthorised
pending POA&M. Critically, the TRM states plainly that **authorisation is not
authorisation to implement** — each project team must consult the organisations
responsible for the target environments.

**Consequence:** "it's in the TRM" is not a green light. Confirm with whoever
owns your desktop, storage and Power BI environments.

### 4.3 Everything stays inside

Your hard constraint — no external systems, SSO-gated — is compatible with all
options above. Power BI in VA runs in Azure Government via VAEC, with
on-premises data gateways bridging internal sources; the gateway makes only
outbound connections. No option here requires an external service.

### 4.4 Do not make the subsystem harder to use

The design honours this by construction: nothing changes any IFCAP menu, screen
or user workflow. Option C adds an off-hours scheduled task. Option B touches
nothing in VistA at all. Availability is unaffected — but say so explicitly
when you brief IRM, because "budget office wants to automate against IFCAP" can
otherwise sound like a change to a production financial system.

### 4.5 Sensitivity

Budget data is largely not PHI, but vendor, invoice and procurement detail is
sensitive and some control point activity is attributable to individuals.
Confirm approved storage for the database, whether row-level security is needed
by control point or service, and your ISSO's expectations for a
locally-managed analytic database.

---

## 5. Recommended architecture

Layered, so each layer can be replaced without disturbing its neighbours. This
is what makes the iFAMS transition survivable: when the source changes, only the
first two layers change.

```
  SOURCES            LANDING          STAGING         MART            SEMANTIC        CONSUMERS
  ─────────────      ─────────        ─────────       ────────        ──────────      ──────────
  IFCAP  ─┐                                           dim_fcp
  FMS    ─┼─ scheduled ─> raw files ─> typed,     ─>  dim_boc      ─> one Power  ─>  daily
  IPPS   ─┘  or manual    immutable    per-report     fact_*          BI model       monthly
             extract      by date      tables         v_* views       (one source    quarterly
                                          │                            of truth)     annual
                                          └─> data quality gate: control totals,
                                              freshness, reconciliation to FMS
```

**Design rules, each earning its place:**

1. **Land raw, never in place.** Keep the original file immutable and dated. If
   a number is challenged, you can reproduce it from the file the source
   produced. This is what makes the output defensible in a way the current
   workbook cannot be.
2. **Money is integer cents.** Aggregate in cents, divide once for display.
   Removes float drift from every total.
3. **Snapshots, not overwrites.** Retaining each day is what makes burn rate,
   trend and as-of-date reporting possible at all.
4. **Freshness is published, not assumed.** A dashboard silently showing
   yesterday as today is the failure that destroys trust permanently. Staleness
   appears on the dashboard.
5. **Reconcile to the accounting system.** Ship the IFCAP-vs-FMS variance view
   from day one, before anyone asks.
6. **Parsing is configuration.** Column offsets in a config file, not code, so
   a format change is an edit rather than a project.
7. **Power BI touches only views.** The view layer is a contract; refactoring
   behind it does not break reports.

### Where the database should live

| | Best for | Trade-off |
|---|---|---|
| **SQLite on approved share** | Starting now; one team | Single-writer; fine for one nightly load |
| **SQL Server Express** | A service or two | Needs a server and a DBA conversation |
| **VISN / OIT-hosted SQL Server** | Many readers; the end state | Needs sponsorship — VISN data warehouses exist (VISN 2 and VISN 5 have run such projects), so there is precedent |

Start with SQLite; the reference implementation's SQL is portable. Promote when
readership justifies it, not before.

### Power BI

Import mode against the views, scheduled refresh after the nightly load, an
on-premises data gateway if the source is on-prem and the dataset is in the
service. One dataset, many reports — that is what "single sourced" means in
practice, and it is what stops the workbook sprawl from reappearing in a new
format. Details in [`../pipeline/powerbi/CONNECTING.md`](../pipeline/powerbi/CONNECTING.md).

---

## 6. Phased plan

**Phase 0 — Inventory and freeze definitions (1–2 weeks).**
List every report currently pulled, its source, cadence, and what it feeds.
Write down what each number *means* — the definition arguments are the real
work, and they surface now or during your first contested briefing. Deliverable:
report inventory plus an agreed measure dictionary.

**Phase 1 — Local database from existing downloads (2–4 weeks).**
Stand up the pipeline against reports you already pull. Load history if you have
retained files. Deliverable: one database, loading on a schedule, with checks
passing.
*Gate: does it reproduce the current workbook's numbers exactly?* Run in
parallel until it does. Do not skip this — parallel reconciliation is what earns
the right to retire the workbook.

**Phase 2 — Dashboards and hand-over (3–6 weeks).**
Build the four dashboards on one model. Publish. Deliberately hand a
maintenance task to a second person; if only one person can maintain it, you
have rebuilt the original problem in a new technology.
*Gate: can someone other than the author refresh and explain it?*

**Phase 3 — Remove the human from extraction (parallel, 1–3 months).**
Request TaskMan scheduling (Option C). Simultaneously pursue FSC DAS / CDW
access (Option A). Retire the Reflection macros once a scheduled source proves
stable.
*Gate: does the pack exist without anyone logging in?*

**Phase 4 — Promote and prepare for iFAMS (ongoing).**
Move to a hosted SQL Server if readership warrants. Track the FMBT VHA wave.
When iFAMS arrives, write new source adapters; the mart, model and dashboards
should be unaffected — that is the point of the layering.

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| iFAMS cutover changes every source format | High | High | Config-driven parsing; model business concepts; track the wave schedule |
| Report format drifts silently | High | Medium | Header/offset validation fails loudly and names the report |
| Truncated capture goes unnoticed | High | **High** | Control-total check — the report's own printed total vs rows parsed |
| Becomes a one-person system again | Medium | High | Version control, docs, Phase 2 hand-over gate |
| Governance objection late | Medium | High | Brief ISSO/IRM in Phase 1, not Phase 3; lead with "no VistA changes" |
| Dashboard contradicts Fiscal | Medium | **High** | Ship the FMS reconciliation view from day one |
| Stale data read as current | Medium | High | Freshness published on the dashboard face |
| Scope creep into a facility-wide programme | Medium | Medium | Keep Phase 1 to reports you already pull |

---

## 8. What was built alongside this report

A working, tested reference implementation is in [`../pipeline/`](../pipeline/):
config-driven parsers for fixed-width VistA captures and delimited exports, a
SQLite star schema with daily snapshots, a SQL-defined data-quality rulebook, a
synthetic data generator so it runs with no VA data present, and 42 passing
tests. Standard library only — no `pip install`, which matters on a locked-down
workstation.

It is a reference, not a drop-in: the column offsets are modelled on realistic
report shapes, not measured from your actual files. Onboarding each real report
means editing `config/reports.toml`. That is the intended work.

---

## Sources

Public documentation consulted. VA intranet resources (VHA Data Portal, TRM
detail pages, FSC customer portal) could not be reached from this environment
and are flagged in [`open-questions.md`](open-questions.md).

- [IFCAP Technical Manual](https://www.va.gov/vdl/documents/Financial_Admin/IFCAP/PRC_TM.pdf) and [IFCAP Budget Analyst User's Guide](https://www.va.gov/vdl/documents/Financial_Admin/IFCAP/ifcp5_1budget_analyst.pdf), VA Software Document Library
- [IFCAP overview](https://www.fsc.va.gov/IFCAP.asp), VA Financial Services Center
- [Kernel 8.0 Systems Management: TaskMan User Guide](https://www.va.gov/vdl/documents/Infrastructure/Kernel/krn_8_0_sm_taskman_ug.pdf) — `XUTM SCHEDULE`, scheduled options
- [VA FileMan 22.2 Advanced User Manual](https://www.va.gov/vdl/documents/Infrastructure/Fileman/fm22_2um2.pdf) — import/export tools
- [VA Directive 6402](https://www.va.gov/vapubs/viewPublication.asp?Pub_ID=1413&FType=2) — modifications to standardised national software
- [VA Technical Reference Model](https://www.oit.va.gov/services/TRM/TRMHomePage.aspx): [Power BI](https://www.oit.va.gov/services/trm/ToolPage.aspx?tid=9713), [Data Gateway](https://www.oit.va.gov/Services/TRM/ToolPage.aspx?tid=11582), [Report Server](https://www.oit.va.gov/Services/TRM/ToolPage.aspx?tid=14451), [PBRS](https://www.oit.va.gov/Services/TRM/ToolPage.aspx?tid=15147)
- [VA Financial Services Center — Data Analytics Service](https://department.va.gov/administrations-and-offices/management/financial-management-business-transformation/va-financial-services-center-fsc/data-analytics-service/)
- [Financial Management System (FMS)](https://www.herc.research.va.gov/include/page.asp?id=financial-management-system) and [Managerial Cost Accounting](https://www.herc.research.va.gov/include/page.asp?id=managerial-cost-accounting), HERC
- [GAO-22-105059, VA Financial Management System](https://www.gao.gov/products/gao-22-105059); [iFAMS waves 7–8 deployment](https://www.prnewswire.com/news-releases/us-department-of-veterans-affairs-advances-financial-integrity-and-efficiency-with-ifams-deployments-302539521.html); [VA begins deploying iFAMS to VHA users](https://www.meritalk.com/articles/va-begins-deploying-ifams-to-vha-users/)
- [IPPS on Pega](https://www.pega.com/customers/veterans-affairs-platform); [VA Financial Policy Vol. VIII Ch. 02, Invoice Review and Certification](https://department.va.gov/financial-policy-documents/financial-document/chapter-02-invoice-review-and-certification/)
- [Corporate Data Warehouse](https://www.data.va.gov/dataset/Corporate-Data-Warehouse-CDW-/ftpi-epf7); [VINCI](https://www.research.va.gov/programs/vinci/) — DART access
- [POWER — Performance and Operational Web-Enabled Reports](https://catalog.data.gov/dataset/performance-and-operational-web-enabled-reports-power)
- [VA Robotic Process Automation](https://www.oit.va.gov/services/rpa/) and [RPA Platform Enterprise Technology Guideline](https://digital.va.gov/wp-content/uploads/2024/09/RPA-Platform-Enterprise-Technology-Guideline.docx)
- [Converting FileMan Files into InterSystems IRIS Classes](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSTU_convert_fileman)
- [VA Enterprise Cloud (VAEC)](https://www.voa.va.gov/DocumentView.aspx?DocumentID=4871); [Power BI on-premises data gateway](https://learn.microsoft.com/en-us/power-bi/connect-data/service-gateway-onprem)
- [Reflection Desktop VBA and .NET API](https://www.microfocus.com/documentation/reflection-desktop/18-0/guides-en/resources/vba-api.html)
