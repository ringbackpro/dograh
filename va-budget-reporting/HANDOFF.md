# VA budget reporting — complete handoff

**Self-contained export.** Everything needed to continue this work is in this
one document: the discovery findings, the open questions, and the full source of
a tested reference pipeline. No access to the original repository or session is
required — Part 5 explains how to rebuild the working tree from this file alone.

| | |
|---|---|
| **Origin** | `ringbackpro/dograh`, branch `claude/va-budget-reporting-discovery-6bst1o`, commit `c6a4830` |
| **Exported** | 18 August 2026 |
| **Contains** | Discovery report, open questions, reference implementation (23 files, 42 passing tests) |
| **Dependencies** | Python 3.11+ standard library only. No `pip install`. |

---

## Part 0 — Instructions for the receiving account

Read this part completely before acting on anything else in the document.

### 0.1 The situation

The user is a budget manager inside the VA. Their current process:

- A **Reflection workspace** (terminal emulator) is used to generate reports,
  which are downloaded daily as `.csv` and `.txt` files.
- Those files are organised by **Excel macros**. Some of the reports are pulled
  by macros too — i.e. macro-driven screen scraping of VistA.
- The output is a formula-heavy, tightly controlled Excel workbook that links to
  many other workbooks.

The problems they stated, in their words: the workbooks "tend to become too
heavy to use efficiently and too fragile to be trusted by many others — so
generally only a few can use the workbooks."

What they want: data pulled efficiently into databases, into a Power BI
subsystem, reporting into daily / monthly / quarterly / annual dashboards.

**Their hard constraints — these are non-negotiable and bound every option:**

- The budget management subsystem lives inside the VA IT system.
- Many external systems are unavailable without single sign-on authorisation.
- The solution must **not** make the subsystem any harder to use, and must
  **not** make it unavailable to anyone within the VA.

**Their stated end state:** "a usable, efficient, widely readable but locally
managed document that is single sourced, automatically updated and as accurate
as the current system manipulated daily already."

**What they asked for:** a discovery loop determining how **VA IFCAP inside
VistA, FMS and IPPS** could integrate internally to possibly run cron jobs or
scheduled routines to auto-generate the data and filter it into a local database
within VA infrastructure.

### 0.2 What has already been done

1. **Discovery completed** — public documentation research on IFCAP/VistA, FMS,
   iFAMS/FMBT, IPPS, CDW, FSC Data Analytics Service, VA Directive 6402, the VA
   Technical Reference Model, TaskMan scheduling, FileMan export, and the
   InterSystems FileMan-to-SQL mapping utility. Written up as Part 1.
2. **Open questions catalogued** — everything that could not be answered from
   outside the VA intranet, with the office to ask and what changes based on
   each answer. Part 2.
3. **Reference pipeline built and tested** — a working ingest-to-Power-BI
   pipeline, 42 passing tests, runnable on synthetic data with no VA data
   present. Parts 3 and 4.

### 0.3 The findings, condensed

**Yes, scheduled internal generation is achievable.** Three findings reframe
where the effort should go:

1. **VistA already has a scheduler, and using it need not be development.**
   TaskMan's `Schedule/Unschedule Options` [XUTM SCHEDULE] runs existing menu
   options on a recurrence, and most VistA print options are queueable by
   design. The critical distinction: scheduling an *existing national option* is
   configuration, not software development. That keeps the request clear of
   **VA Directive 6402**, which prohibits enhancement or modification of a
   specific VistA instance and routes Class II/III local modifications through
   the Innovation and Development Request Portal. It is the difference between a
   request a local IRM office can action and one that becomes a project.

2. **IFCAP and FMS are a depreciating asset.** They are being replaced by iFAMS
   under the Financial Management Business Transformation programme. Waves 7–8
   deployed August 2025 including the first VHA users; the remaining VHA wave
   represents more than 92% of iFAMS users. Anything welded tightly to IFCAP's
   file layouts has a limited and partly unknowable service life.

3. **Someone inside VA may already publish this.** The VA Financial Services
   Center runs a **Data Analytics Service** — an enterprise BI and analytics
   platform, described as accessible throughout VA on approval of **VA Form
   9957**, already delivering dashboards and reporting tools using Power BI from
   FSC financial systems. FSC operates IPPS and FMS payment processing. The
   cheapest possible integration is an access request rather than a pipeline.

**The resulting recommendation: invest in the destination, keep the source layer
thin and swappable.**

| Order | Action | Why |
|---|---|---|
| 1 | Load the reports they already download into one local database | Entirely within their own authority; retires the workbook chain immediately |
| 2 | *In parallel*, ask FSC DAS and CDW whether they already publish this | A form beats a pipeline; runs on someone else's timeline |
| 3 | Request TaskMan scheduling of existing report options | Removes the human from extraction; configuration, not development |
| 4 | Throughout, model business concepts rather than file layouts | Makes the iFAMS cutover a source-adapter change, not a rebuild |

**One structural insight worth repeating to the user**, because it is easy to
miss and it changes what is possible: their current process *destroys yesterday
to produce today*. Burn rate, run-rate projection, month-over-month variance and
"what did we believe on the 15th" are not slow to answer — they are impossible,
because the data needed was overwritten. Retaining daily snapshots makes an
entire class of budget questions answerable for the first time, with **no**
source-system integration at all. That is available in step 1.

### 0.4 Verified vs. unverified — read before repeating any claim

The research environment could reach public web search but **the egress proxy
blocked `va.gov`, `oit.va.gov`, `department.va.gov`, `digital.va.gov`,
`herc.research.va.gov`, `ihs.gov`, `hardhats.org` and `vistapedia.net`.** The
findings are therefore built from search-result summaries plus public
documentation, not from direct reads of the IFCAP technical manual.

| Claim | Confidence | How to firm it up |
|---|---|---|
| TaskMan schedules options via `XUTM SCHEDULE` | High — Kernel documentation | Confirm with local IRM which options are queueable |
| VA Directive 6402 restricts local VistA modification | High — directive text | Read the current directive on the intranet |
| iFAMS replacing FMS/IFCAP; waves 7–8 Aug 2025 | High — GAO, CGI, MeriTalk | Get the *local station* wave date from FMBT |
| FSC Data Analytics Service exists; VA Form 9957 | High — VA FSC pages | Contact FSC; confirm products and granularity |
| IFCAP file groups 410–414, 417–420, 441–442 | **Medium** — from search summaries, not a direct manual read | Verify in the IFCAP Technical Manual on the intranet |
| Power BI "Authorized w/ Constraints" in TRM; PBRS "Unauthorized, Conditions Required" | Medium–High — TRM search results | Re-check current TRM entries directly |
| CDW contains facility-grain IFCAP financial data | **Unknown** — genuinely unresolved | Ask VHA Data Portal / National Data Systems |
| Whether the user's station can schedule to a host file vs. MailMan | **Unknown** | Local IRM |

**Do not present medium/unknown items to a governance board as established.**
Part 2 exists precisely to drive them to resolution.

### 0.5 Critical caveats before the pipeline touches real data

**1. The balance identity is an assumption, and it is the highest-risk one.**
The pipeline assumes:

```
balance = allocation - commitments - obligations
```

with expenditures *inside* obligations rather than deducted separately. Whether
expenditures sit inside or beside obligations varies by report. **If this is
wrong, every balance on every dashboard shifts silently** — no error, no
symptom, just wrong numbers that look right. It is answerable in-house in
minutes by reading one real Status of Funds report. It is question 4 in Part 2
and it gates everything.

**2. The five shipped report definitions are modelled, not measured.** Column
offsets and header names are realistic in shape but were invented, not taken
from real VA files. Onboarding each real report means editing
`config/reports.toml`. That is the intended work, not a defect.

**3. All sample data is synthetic.** `vabudget/samples.py` generates fictional
control points, vendors and amounts. No VA data was available to this work and
none is embedded anywhere in this document.

**4. Never commit real VA data.** `pipeline/.gitignore` excludes `inbox/`,
`*.db` and generated output, but verify before any commit. Budget data is
largely not PHI, but vendor, invoice and procurement detail is sensitive and
some control point activity is attributable to individuals.

### 0.6 Constraints the receiving account must respect

- **Nothing external.** No SaaS, no external hosting, no uploading VA data
  anywhere — including to publish a dashboard or a document. The user's whole
  premise is that it stays inside VA infrastructure.
- **Never propose modifying national VistA software.** Directive 6402. Frame
  every VistA ask as *scheduling an existing national option*, and say so
  explicitly when advising them how to approach IRM — the framing is what makes
  the request actionable.
- **Do not design around Power BI Reports Scheduler (PBRS).** It is carried in
  the VA TRM as *Unauthorized, Conditions Required (POA&M Required)*. Use
  Windows Task Scheduler plus Power BI's own scheduled refresh.
- **TRM listing is not permission.** The TRM states plainly that authorisation
  is not authorisation to implement; local environment owners must be consulted.
- **Do not assume intranet facts.** If something is only knowable from inside
  VA, say so and add it to Part 2 rather than guessing.
- **Do not let this become a facility-wide programme.** Phase 1 is deliberately
  limited to reports the user already pulls, because that scope needs nobody
  else's approval.

### 0.7 What to do next

**Immediately actionable, no permissions needed:**

1. Confirm the balance identity (§0.5, Part 2 question 4).
2. Inventory every report currently pulled: source, cadence, what it feeds, and
   what each number *means*. The definition arguments are the real work and they
   surface now or during the first contested briefing.
3. Run the pipeline on real downloaded files: edit `config/reports.toml` offsets,
   ingest, compare against the existing workbook.

**Requires other people, start the asks early:**

4. Contact FSC Data Analytics Service (VA Form 9957) — Part 2 question 1.
5. Ask IRM about TaskMan scheduling — Part 2 question 5.
6. Ask the ISSO where the database may live — Part 2 question 6.
7. Get the station's iFAMS wave date — Part 2 question 3.

**The gate that matters:** do not retire the Excel workbook until the pipeline
reproduces its numbers exactly, in parallel. Parallel reconciliation is what
earns the right to switch, and skipping it is how these projects lose their
audience permanently.

### 0.8 Running the pipeline

```bash
cd pipeline

# Synthetic data - no VA data needed
python3 -m vabudget sample --out ./inbox --start 2025-10-01 --end 2025-12-19
python3 -m vabudget ingest --inbox ./inbox
python3 -m vabudget status

# Watch the checks catch a truncated capture and a silently missing day
python3 -m vabudget --db faulty.db sample --out ./faulty --inject-faults \
    --start 2025-10-01 --end 2025-12-19
python3 -m vabudget --db faulty.db ingest --inbox ./faulty

# Tests
python3 -m unittest discover -s tests -t .
```

Expected: 290 files loaded, 24,226 rows, all 12 checks passing, 42 tests OK.

### 0.9 Suggested prompts for continuing

- "Onboard my real Status of Funds report — here is a sample file with the
  sensitive values replaced. Work out the column offsets and update
  `reports.toml`."
- "Add labour/payroll actuals as a sixth source and extend the mart."
- "Write the briefing memo for my ISSO and IRM explaining what we are asking for
  and why it does not modify VistA."
- "Build the Power BI measures and page layout for the daily dashboard."
- "Draft the FSC Data Analytics Service enquiry."

Note the second-to-last one: a short, accurate briefing note aimed at IRM and
the ISSO is often the highest-leverage single artifact remaining, because the
technical work is largely done and the remaining blockers are all permissions.

---

## Part 1 — Discovery report

### Automating VA budget reporting: IFCAP, FMS and IPPS into a local database

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

#### 1. What is actually wrong today

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

#### 2. Source systems: what each one is and how data can leave it

##### 2.1 IFCAP, inside VistA

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

##### 2.2 FMS — and the iFAMS clock

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

##### 2.3 IPPS

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

##### 2.4 Sources you did not name but will want

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

#### 3. Integration options, ranked

##### 3.1 Option A — consume an existing enterprise product *(check first)*

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

##### 3.2 Option B — scheduled local ingest of the reports you already pull *(start here)*

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

##### 3.3 Option C — TaskMan-scheduled generation at the source *(the real answer to "cron")*

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

##### 3.4 Option D — read-only SQL against VistA

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

##### 3.5 Option E — supported RPA instead of personal macros

If screen automation must remain, move it off a personal Reflection macro and
onto VA's supported platform. VA has an RPA Center of Excellence that plans,
builds, secures, authorises and maintains automations; RPA is owned by the
Enterprise Management Program Office with OIT setting the technology standard,
all access approved and authenticated, and Nintex RPA carried in the TRM.

Slower to obtain than a macro, but it survives staff turnover, is defensible in
an audit, and is supported when it breaks. If your macros are genuinely
load-bearing today, this converts a personal dependency into an institutional
one.

##### 3.6 Ranking

| | Option | Time to value | Effort | Durability | Do it? |
|---|---|---|---|---|---|
| 1 | **B — local scheduled ingest** | Days | Low | Medium | **Now.** Yours to do |
| 2 | **A — existing enterprise product** | Weeks–months | Low (forms) | High | **Start the ask in parallel** |
| 3 | **C — TaskMan scheduling** | Weeks | Medium | High | **Yes**, once B proves value |
| 4 | E — supported RPA | Months | Medium | Medium | Only if scraping must persist |
| 5 | D — read-only VistA SQL | Months | High | Medium* | Only with OIT sponsorship |

\* Durability is capped for C, D and E alike by the iFAMS transition.

---

#### 4. Constraints that bound every option

##### 4.1 Local software development is restricted

VA Directive 6402 controls variation in nationally released VistA software:
it is VA policy that all instances of VistA install the National VistA
Software, enhancement or modification of a specific VistA instance is
prohibited, and Class II/III requests for local modifications go through the
Innovation and Development Request Portal.

**Consequence:** designs that write new MUMPS into VistA are the wrong shape.
Designs that *schedule existing national options* and process the output
downstream are the right shape. This single distinction is the most important
governance insight in this report.

##### 4.2 TRM authorisation is necessary, not sufficient

Power BI and its data gateway appear in the TRM as authorised with constraints;
Power BI Report Server and Report Builder are listed; PBRS is unauthorised
pending POA&M. Critically, the TRM states plainly that **authorisation is not
authorisation to implement** — each project team must consult the organisations
responsible for the target environments.

**Consequence:** "it's in the TRM" is not a green light. Confirm with whoever
owns your desktop, storage and Power BI environments.

##### 4.3 Everything stays inside

Your hard constraint — no external systems, SSO-gated — is compatible with all
options above. Power BI in VA runs in Azure Government via VAEC, with
on-premises data gateways bridging internal sources; the gateway makes only
outbound connections. No option here requires an external service.

##### 4.4 Do not make the subsystem harder to use

The design honours this by construction: nothing changes any IFCAP menu, screen
or user workflow. Option C adds an off-hours scheduled task. Option B touches
nothing in VistA at all. Availability is unaffected — but say so explicitly
when you brief IRM, because "budget office wants to automate against IFCAP" can
otherwise sound like a change to a production financial system.

##### 4.5 Sensitivity

Budget data is largely not PHI, but vendor, invoice and procurement detail is
sensitive and some control point activity is attributable to individuals.
Confirm approved storage for the database, whether row-level security is needed
by control point or service, and your ISSO's expectations for a
locally-managed analytic database.

---

#### 5. Recommended architecture

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

##### Where the database should live

| | Best for | Trade-off |
|---|---|---|
| **SQLite on approved share** | Starting now; one team | Single-writer; fine for one nightly load |
| **SQL Server Express** | A service or two | Needs a server and a DBA conversation |
| **VISN / OIT-hosted SQL Server** | Many readers; the end state | Needs sponsorship — VISN data warehouses exist (VISN 2 and VISN 5 have run such projects), so there is precedent |

Start with SQLite; the reference implementation's SQL is portable. Promote when
readership justifies it, not before.

##### Power BI

Import mode against the views, scheduled refresh after the nightly load, an
on-premises data gateway if the source is on-prem and the dataset is in the
service. One dataset, many reports — that is what "single sourced" means in
practice, and it is what stops the workbook sprawl from reappearing in a new
format. Details in [`../pipeline/powerbi/CONNECTING.md`](../pipeline/powerbi/CONNECTING.md).

---

#### 6. Phased plan

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

#### 7. Risks

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

#### 8. What was built alongside this report

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

#### Sources

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

---

## Part 2 — Open questions

### Open questions

Everything here needs someone with VA intranet access and the right local
contacts. They are ordered so that the answers which could most change the plan
come first — question 1 could make most of the build unnecessary, and question 4
could invalidate an assumption the whole design rests on.

Each entry states why it matters and what changes depending on the answer,
because a question whose answer changes nothing is not worth an office's time.

---

#### Priority 1 — could remove most of the work

##### 1. Does FSC's Data Analytics Service already publish what you need?

**Ask:** VA Financial Services Center, Data Analytics Service, via the FSC
customer engagement route. Access is described as VA-wide on approval of
**VA Form 9957**.

**Specifically:**
- Is there an existing product covering facility-level obligations, control
  point balances, or invoice/payment status?
- Can a facility budget office subscribe, or is it VACO-level only?
- Is there a data feed as well as dashboards — can we consume the underlying
  data, or only view their reports?
- What granularity: station? control point? transaction?

**Changes what:** an existing product at the right grain replaces Options B, C
and D for that subject area entirely. Ask before building anything you would
have to maintain.

##### 2. What financial content is in CDW, and can a budget office get at it?

**Ask:** VHA Data Portal (intranet) and National Data Systems; access runs
through the **Data Access Request Tracker (DART)**.

**Specifically:** is there an IFCAP or financial domain in CDW at facility
grain? Is DART access available for operational budget management, or is it
scoped to research? What is the realistic approval timeline?

**Changes what:** a CDW route would be more durable than local extracts and
would survive the iFAMS migration better. Note that CDW is VHA-oriented and
strongest on clinical and MCA cost data — the financial-detail answer is
genuinely uncertain and worth asking rather than assuming either way.

##### 3. What is the iFAMS wave date for your station?

**Ask:** FMBT programme office; your Fiscal Service chief will know the local
readiness activity.

**Specifically:** when does your facility cut over? What happens to IFCAP
locally at that point? What does budget reporting look like afterwards, and does
the FMBT Data Estate serve field users directly?

**Changes what:** everything about how much to invest in IFCAP-specific work. A
cutover 18 months out justifies Option C; a cutover in two quarters means do
Option B only and wait.

---

#### Priority 2 — needed before building

##### 4. Is the Status of Funds balance identity what the pipeline assumes?

**Ask:** your Fiscal Service / budget analyst colleagues — this one is answerable
in-house today, and you may already know it.

The reference implementation assumes
`balance = allocation − commitments − obligations`, with expenditures a subset
of obligations rather than a separate deduction. **Whether expenditures sit
inside obligations or beside them varies by report, and getting it wrong shifts
every balance on every dashboard silently.**

**Changes what:** one data-quality rule (`sof_balance_identity` in
`config/checks.toml`) and the meaning of every balance shown. Verify against a
real report before anyone makes a decision on the output. This is the single
most important local confirmation in this document.

##### 5. Can the IFCAP report options be scheduled through TaskMan?

**Ask:** local IRM / OIT VistA support.

**Specifically:**
- Are the Print Menu report options you use queueable/taskable?
- Can `Schedule/Unschedule Options` [XUTM SCHEDULE] run them on a recurrence?
- Can output go to a Host File Server device on a network share, or should it
  go to a MailMan mail group?
- What is the request process and expected turnaround?
- What off-hours window avoids contention?

**Changes what:** this is the difference between automated generation and a
human running reports forever. Lead with "we are asking to schedule existing
national options, not to modify VistA" — that framing matters, because it puts
the request outside VA Directive 6402's restriction on local modification.

##### 6. Where may the database live, and what does the ISSO expect?

**Ask:** local ISSO and OIT.

**Specifically:** approved storage for a database holding procurement and vendor
detail; whether a locally-managed analytic database needs any review or
registration; whether row-level security by control point or service is
expected; retention requirements.

**Changes what:** where the file goes, whether SQLite is acceptable or a managed
SQL Server is required, and how much governance overhead Phase 1 carries.

##### 7. What Power BI hosting do you actually have?

**Ask:** VISN or facility Power BI/BI support.

**Specifically:** is there a workspace your office can publish to? Power BI
Service in the VA tenant, or Report Server on-prem? Is an on-premises data
gateway available for a local database? Who administers it? Are Pro licences
available for the intended readers?

**Changes what:** whether dashboards are published centrally with scheduled
refresh, or distributed as files against a shared database. Note that PBRS is
carried in the TRM as **unauthorized pending POA&M**, so do not plan on it.

---

#### Priority 3 — completeness

##### 8. Where do labour and payroll actuals come from?

Salary is typically the largest line in a facility budget. A dashboard without
it answers a fraction of the question. Ask Fiscal where facility-level labour
actuals now come from and at what grain and cadence.

##### 9. Should MCA cost data be in scope?

Managerial Cost Accounting supports cost-per-workload views. Ask whether that is
part of the audience's question or a later phase — it is a meaningful scope
expansion, not a free addition.

##### 10. Who are the readers, and what decision does each make?

Not a technical question, but the one that determines whether the dashboards get
used. Four dashboards on four cadences serve different people making different
decisions. Identify the decision each is meant to support before designing it,
or you will build a report that is admired and ignored.

##### 11. Who is the second maintainer?

Name them in Phase 1, not Phase 4. The current system's core failure is that
only a few people can operate it. Rebuilding that property in a new technology
would be the most disappointing possible outcome of this work.

---

#### Answers log

Record answers here as they arrive, with date and source, so the reasoning
behind design changes stays traceable.

| # | Question | Answer | Answered by | Date |
|---|---|---|---|---|
| 1 | FSC DAS products | | | |
| 2 | CDW financial content | | | |
| 3 | iFAMS wave date | | | |
| 4 | Balance identity | | | |
| 5 | TaskMan scheduling | | | |
| 6 | Database location / ISSO | | | |
| 7 | Power BI hosting | | | |

---

## Part 3 — Reference pipeline documentation

### 3.1 Pipeline README

#### Budget report pipeline

Turns the daily pile of `.csv` and `.txt` budget reports into one local SQLite
database with a stable set of views for Power BI — replacing the chain of linked
Excel workbooks.

**Standard library only.** No `pip install`, no dependencies, nothing to get
approved. Python 3.11 or later (it uses `tomllib`).

---

##### Try it in two minutes

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

##### Commands

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

##### Onboarding a real report

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

##### How it is put together

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

##### What the views give you

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

##### Scheduling it

Windows Task Scheduler, daily, after the reports land:

```bat
python -m vabudget --db "D:\budget\budget.db" ingest --inbox "D:\budget\inbox"
```

The exit code tells the scheduler whether a human is needed. Do not plan on
Power BI Reports Scheduler — it is carried in the VA TRM as *Unauthorized,
Conditions Required (POA&M Required)*.

---

##### Adapting it

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

---

### 3.2 Connecting Power BI

#### Connecting Power BI

The goal is **one dataset, many reports**. That is what "single sourced" means
in practice, and it is the thing that stops workbook sprawl from reappearing in
a new technology. If four dashboards each carry their own copy of the logic, the
old problem has been rebuilt with different tooling.

---

##### Connecting to SQLite

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

##### Connect to views only

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

##### Model setup

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

##### A starting set of measures

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

##### Four dashboards, four decisions

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

##### Put freshness on the face of every page

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

##### Refresh

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

---

## Part 4 — Complete source code

Every file of the reference implementation, in reading order. Each block is
headed by its path relative to the project root. Part 5 explains how to turn
these back into a working tree.

### Package

#### `pipeline/vabudget/__init__.py`

```python
"""A single-source local database for recurring VA budget reports.

Replaces a chain of linked Excel workbooks with: files in, one SQLite database
out, data-quality checks on every load, and a stable set of views for Power BI.

Stdlib only -- no pip install, which matters on a locked-down workstation.
"""

__version__ = "0.1.0"
```

#### `pipeline/vabudget/__main__.py`

```python
import sys

from .cli import main

sys.exit(main())
```

### Configuration loading

#### `pipeline/vabudget/config.py`

```python
"""Report definitions, loaded from TOML.

A "report" is one recurring extract that lands in the inbox: either a
delimited export or a fixed-width capture of a VistA roll-and-scroll screen.
Everything the pipeline knows about a file's shape lives in configuration
rather than in code, so onboarding a new report is a config edit, not a
Python change.

Money is stored as integer cents everywhere. Amount columns must therefore be
named with a ``_cents`` suffix so that no downstream reader mistakes the unit.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

VALID_TYPES = {"string", "amount", "integer", "date"}
VALID_FORMATS = {"fixed", "delimited"}
VALID_AS_OF = {"filename", "content", "mtime"}

SQL_TYPES = {
    "string": "TEXT",
    "amount": "INTEGER",
    "integer": "INTEGER",
    "date": "TEXT",
}


class ConfigError(ValueError):
    """Raised with an actionable message when a report definition is wrong."""


@dataclass(frozen=True)
class Column:
    """One field extracted from a report line.

    Fixed-width reports locate a field by ``start`` (1-based, matching what you
    count off a printed report) and ``length``. Delimited reports locate it by
    ``source`` (header name) or ``index`` (0-based position).
    """

    name: str
    type: str = "string"
    start: int | None = None
    length: int | None = None
    source: str | None = None
    index: int | None = None
    date_format: str | None = None

    @property
    def sql_type(self) -> str:
        return SQL_TYPES[self.type]


@dataclass(frozen=True)
class ControlTotal:
    """A total printed on the report itself, used to prove nothing was lost.

    Screen-scraped extracts fail by truncation far more often than by
    corruption: a page break is missed, a session times out, the capture stops
    early. Comparing the report's own printed total against the sum of the rows
    we parsed is the cheapest possible detection of that failure.
    """

    pattern: str
    column: str
    tolerance_cents: int = 0


@dataclass(frozen=True)
class ReportDef:
    code: str
    name: str
    source_system: str
    format: str
    filename_glob: str
    columns: tuple[Column, ...]
    grain: tuple[str, ...] = ()
    as_of_from: str = "filename"
    as_of_pattern: str | None = None
    as_of_format: str = "%Y%m%d"
    delimiter: str = ","
    has_header: bool = True
    encoding: str = "utf-8-sig"
    skip_patterns: tuple[str, ...] = ()
    row_pattern: str | None = None
    control_total: ControlTotal | None = None
    expected_cadence_days: int = 1

    @property
    def staging_table(self) -> str:
        return f"stg_{self.code.lower()}"

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ConfigError(message)


def _parse_column(raw: dict, report_code: str, fmt: str) -> Column:
    where = f"report '{report_code}'"
    name = raw.get("name")
    _require(bool(name), f"{where}: every column needs a 'name'")

    unknown = set(raw) - {
        "name", "type", "start", "length", "source", "index", "date_format",
    }
    _require(not unknown, f"{where} column '{name}': unknown keys {sorted(unknown)}")

    ctype = raw.get("type", "string")
    _require(
        ctype in VALID_TYPES,
        f"{where} column '{name}': type '{ctype}' is not one of {sorted(VALID_TYPES)}",
    )

    if ctype == "amount":
        _require(
            name.endswith("_cents"),
            f"{where} column '{name}': amount columns are stored as integer cents "
            f"and must be named with a '_cents' suffix (e.g. '{name}_cents')",
        )

    if fmt == "fixed":
        _require(
            raw.get("start") is not None and raw.get("length") is not None,
            f"{where} column '{name}': fixed-width columns need 'start' (1-based) "
            "and 'length'",
        )
        _require(
            raw["start"] >= 1,
            f"{where} column '{name}': 'start' is 1-based, so it cannot be {raw['start']}",
        )
        _require(
            raw["length"] >= 1,
            f"{where} column '{name}': 'length' must be at least 1",
        )
    else:
        _require(
            raw.get("source") is not None or raw.get("index") is not None,
            f"{where} column '{name}': delimited columns need 'source' (a header "
            "name) or 'index' (0-based position)",
        )

    return Column(
        name=name,
        type=ctype,
        start=raw.get("start"),
        length=raw.get("length"),
        source=raw.get("source"),
        index=raw.get("index"),
        date_format=raw.get("date_format"),
    )


def _parse_report(raw: dict) -> ReportDef:
    code = raw.get("code")
    _require(bool(code), "every [[report]] needs a 'code'")
    _require(
        bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", code)),
        f"report code '{code}' must be alphanumeric/underscore and start with a letter, "
        "because it becomes a SQL table name",
    )
    where = f"report '{code}'"

    unknown = set(raw) - {
        "code", "name", "source_system", "format", "filename_glob", "column",
        "grain", "as_of_from", "as_of_pattern", "as_of_format", "delimiter",
        "has_header", "encoding", "skip_patterns", "row_pattern",
        "control_total", "expected_cadence_days",
    }
    _require(not unknown, f"{where}: unknown keys {sorted(unknown)}")

    fmt = raw.get("format")
    _require(
        fmt in VALID_FORMATS,
        f"{where}: format must be one of {sorted(VALID_FORMATS)}, got {fmt!r}",
    )

    as_of_from = raw.get("as_of_from", "filename")
    _require(
        as_of_from in VALID_AS_OF,
        f"{where}: as_of_from must be one of {sorted(VALID_AS_OF)}, got {as_of_from!r}",
    )
    if as_of_from in {"filename", "content"}:
        _require(
            raw.get("as_of_pattern") is not None,
            f"{where}: as_of_from='{as_of_from}' needs an 'as_of_pattern' regex with "
            "one capture group holding the date",
        )

    raw_columns = raw.get("column") or []
    _require(bool(raw_columns), f"{where}: needs at least one [[report.column]]")
    columns = tuple(_parse_column(c, code, fmt) for c in raw_columns)

    names = [c.name for c in columns]
    dupes = {n for n in names if names.count(n) > 1}
    _require(not dupes, f"{where}: duplicate column names {sorted(dupes)}")

    grain = tuple(raw.get("grain", ()))
    for g in grain:
        _require(
            g in names,
            f"{where}: grain column '{g}' is not one of the defined columns {names}",
        )

    control_total = None
    if "control_total" in raw:
        ct = raw["control_total"]
        _require(
            "pattern" in ct and "column" in ct,
            f"{where}: [report.control_total] needs 'pattern' and 'column'",
        )
        _require(
            ct["column"] in names,
            f"{where}: control_total column '{ct['column']}' is not a defined column",
        )
        control_total = ControlTotal(
            pattern=ct["pattern"],
            column=ct["column"],
            tolerance_cents=ct.get("tolerance_cents", 0),
        )

    return ReportDef(
        code=code,
        name=raw.get("name", code),
        source_system=raw.get("source_system", "UNKNOWN"),
        format=fmt,
        filename_glob=raw.get("filename_glob", f"{code}*"),
        columns=columns,
        grain=grain,
        as_of_from=as_of_from,
        as_of_pattern=raw.get("as_of_pattern"),
        as_of_format=raw.get("as_of_format", "%Y%m%d"),
        delimiter=raw.get("delimiter", ","),
        has_header=raw.get("has_header", True),
        encoding=raw.get("encoding", "utf-8-sig"),
        skip_patterns=tuple(raw.get("skip_patterns", ())),
        row_pattern=raw.get("row_pattern"),
        control_total=control_total,
        expected_cadence_days=raw.get("expected_cadence_days", 1),
    )


def load_reports(path: Path) -> tuple[ReportDef, ...]:
    """Load and validate every [[report]] in a TOML file."""
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    reports = tuple(_parse_report(r) for r in raw.get("report", []))
    _require(bool(reports), f"{path}: no [[report]] definitions found")

    codes = [r.code for r in reports]
    dupes = {c for c in codes if codes.count(c) > 1}
    _require(not dupes, f"{path}: duplicate report codes {sorted(dupes)}")
    return reports
```

### Parsing

#### `pipeline/vabudget/parsers.py`

```python
"""Turn raw report files into typed rows.

Two shapes are supported, because those are the two the VA budget reports
actually arrive in:

* ``delimited`` -- CSV/TSV exports, whether produced by a Reflection macro or
  by a real system export.
* ``fixed`` -- a captured roll-and-scroll screen or spooled print file, where
  fields live at fixed column offsets and the payload is interrupted by page
  headers, form feeds and rule lines.

Amounts are normalised to integer cents. Accounting notations that show up in
VistA and FMS output all mean "negative": parentheses, a trailing CR, or a
leading minus.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .config import Column, ReportDef

_AMOUNT_CLEAN = re.compile(r"[$,\s]")
_DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y%m%d", "%d-%b-%Y", "%b %d, %Y",
)


class ParseError(ValueError):
    """Raised when a file cannot be parsed at all (not for per-row problems)."""


@dataclass
class ParsedFile:
    """The outcome of parsing one file: rows plus everything needed to judge them."""

    rows: list[dict] = field(default_factory=list)
    as_of_date: date | None = None
    control_total_cents: int | None = None
    row_errors: list[str] = field(default_factory=list)
    skipped_lines: int = 0

    @property
    def row_count(self) -> int:
        return len(self.rows)


def parse_amount(text: str | None) -> int | None:
    """Parse an accounting amount into integer cents.

    Handles ``$1,234.56``, ``(1,234.56)``, ``1234.56-``, ``1,234.56CR`` and
    bare integers. Returns None for blanks and placeholder dashes.
    """
    if text is None:
        return None
    raw = text.strip()
    if raw in {"", "-", "--", ".", "N/A", "NA"}:
        return None

    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative, raw = True, raw[1:-1]
    upper = raw.upper()
    for suffix in ("CR", "DR"):
        if upper.endswith(suffix):
            negative = negative or suffix == "CR"
            raw = raw[: -len(suffix)]
            break
    raw = raw.strip()
    if raw.endswith("-"):
        negative, raw = True, raw[:-1]
    if raw.startswith("-"):
        negative, raw = True, raw[1:]

    cleaned = _AMOUNT_CLEAN.sub("", raw)
    if not cleaned:
        return None
    if not re.fullmatch(r"\d*\.?\d*", cleaned):
        raise ValueError(f"not an amount: {text!r}")

    if "." in cleaned:
        whole, _, frac = cleaned.partition(".")
        frac = (frac + "00")[:2]
    else:
        whole, frac = cleaned, "00"
    cents = int(whole or "0") * 100 + int(frac or "0")
    return -cents if negative else cents


def parse_date(text: str | None, fmt: str | None = None) -> str | None:
    """Parse a date into an ISO string, trying the common VA report formats."""
    if text is None:
        return None
    raw = text.strip()
    if raw in {"", "-", "--", "N/A", "NA", "00/00/00", "00000000"}:
        return None

    formats = (fmt,) if fmt else _DATE_FORMATS
    for f in formats:
        try:
            return datetime.strptime(raw, f).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"not a date: {text!r}")


def coerce(column: Column, text: str | None) -> object:
    if column.type == "amount":
        return parse_amount(text)
    if column.type == "date":
        return parse_date(text, column.date_format)
    if column.type == "integer":
        raw = (text or "").strip()
        if not raw:
            return None
        return int(raw.replace(",", ""))
    value = (text or "").strip()
    return value or None


def _resolve_as_of(report: ReportDef, path: Path, text: str) -> date | None:
    if report.as_of_from == "mtime":
        return date.fromtimestamp(path.stat().st_mtime)

    haystack = path.name if report.as_of_from == "filename" else text
    match = re.search(report.as_of_pattern, haystack, re.MULTILINE)
    if not match:
        where = "filename" if report.as_of_from == "filename" else "file content"
        raise ParseError(
            f"{path.name}: could not find the as-of date in the {where} using "
            f"pattern {report.as_of_pattern!r}"
        )
    captured = match.group(1)
    try:
        return datetime.strptime(captured, report.as_of_format).date()
    except ValueError as exc:
        raise ParseError(
            f"{path.name}: matched as-of text {captured!r} but it does not fit "
            f"format {report.as_of_format!r}"
        ) from exc


def _find_control_total(report: ReportDef, text: str) -> int | None:
    if report.control_total is None:
        return None
    match = re.search(report.control_total.pattern, text, re.MULTILINE)
    if not match:
        return None
    return parse_amount(match.group(1))


def _parse_fixed(report: ReportDef, text: str, result: ParsedFile) -> None:
    skips = [re.compile(p) for p in report.skip_patterns]
    row_re = re.compile(report.row_pattern) if report.row_pattern else None

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip("\r\n")
        if not stripped.strip():
            result.skipped_lines += 1
            continue
        if row_re is not None:
            if not row_re.search(stripped):
                result.skipped_lines += 1
                continue
        elif any(s.search(stripped) for s in skips):
            result.skipped_lines += 1
            continue

        padded = stripped.ljust(max(c.start + c.length - 1 for c in report.columns))
        row: dict = {}
        try:
            for col in report.columns:
                chunk = padded[col.start - 1 : col.start - 1 + col.length]
                row[col.name] = coerce(col, chunk)
        except ValueError as exc:
            result.row_errors.append(f"line {lineno}: {exc}")
            continue
        result.rows.append(row)


def _parse_delimited(report: ReportDef, text: str, result: ParsedFile) -> None:
    handle = io.StringIO(text)
    if report.has_header:
        reader = csv.DictReader(handle, delimiter=report.delimiter)
        if reader.fieldnames is None:
            raise ParseError("file is empty; expected a header row")
        headers = {(h or "").strip(): (h or "") for h in reader.fieldnames}
        missing = [
            c.source for c in report.columns
            if c.source is not None and c.source not in headers
        ]
        if missing:
            raise ParseError(
                f"missing expected column(s) {missing}; file has "
                f"{sorted(headers)}. If the export changed shape, update the "
                f"report definition for '{report.code}'."
            )
        records = ({k: v for k, v in r.items()} for r in reader)
    else:
        rows = csv.reader(handle, delimiter=report.delimiter)
        records = ({str(i): v for i, v in enumerate(r)} for r in rows)
        headers = {}

    skips = [re.compile(p) for p in report.skip_patterns]
    for lineno, record in enumerate(records, start=2 if report.has_header else 1):
        joined = report.delimiter.join(str(v or "") for v in record.values())
        if not joined.strip(report.delimiter).strip():
            result.skipped_lines += 1
            continue
        if any(s.search(joined) for s in skips):
            result.skipped_lines += 1
            continue

        row: dict = {}
        try:
            for col in report.columns:
                key = headers.get(col.source, col.source) if col.source else str(col.index)
                row[col.name] = coerce(col, record.get(key))
        except ValueError as exc:
            result.row_errors.append(f"line {lineno}: {exc}")
            continue
        result.rows.append(row)


def parse_file(report: ReportDef, path: Path) -> ParsedFile:
    """Parse one file against its report definition."""
    text = path.read_text(encoding=report.encoding, errors="replace")
    text = text.replace("\f", "\n")

    result = ParsedFile()
    result.as_of_date = _resolve_as_of(report, path, text)
    result.control_total_cents = _find_control_total(report, text)

    if report.format == "fixed":
        _parse_fixed(report, text, result)
    else:
        _parse_delimited(report, text, result)
    return result
```

### Database and schema

#### `pipeline/vabudget/db.py`

```python
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
```

### Ingest orchestration

#### `pipeline/vabudget/loader.py`

```python
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
```

### Data quality

#### `pipeline/vabudget/quality.py`

```python
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
```

### Sample data generator

#### `pipeline/vabudget/samples.py`

```python
"""Synthetic sample data.

This generates files shaped like the real reports -- fixed-width captures with
page furniture and printed totals, delimited exports with headers -- so the
pipeline can be run, tested and demonstrated without any VA data ever being
present. Nothing here is real; the control point names and vendors are made up.

The generated set is internally consistent on purpose: balances reconcile,
IFCAP totals agree with the general ledger extract, invoice dates run in the
right order. A clean generation therefore passes every data-quality check, and
``--inject-faults`` breaks specific things so you can watch the checks catch
them.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

STATION = "999"
FUND = "0160A1"

FCPS: tuple[tuple[str, str, int, str], ...] = (
    # fcp,  name,                        allocation cents, cost centre
    ("0101", "PROSTHETICS",                 1_250_000_00, "821000"),
    ("0102", "MEDICAL SUPPLIES",              875_000_00, "822000"),
    ("0103", "PHARMACY NON-FORMULARY",        640_000_00, "823000"),
    ("0104", "ENGINEERING SERVICE",           980_000_00, "831000"),
    ("0105", "ENVIRONMENTAL MGMT",            410_000_00, "832000"),
    ("0106", "LABORATORY",                    525_000_00, "824000"),
    ("0107", "IMAGING SERVICE",               760_000_00, "825000"),
    ("0108", "NUTRITION AND FOOD SVC",        315_000_00, "833000"),
)

BOCS = ("2631", "2632", "2660", "2579", "3110", "2534")
VENDORS = (
    "ACME MEDICAL SUPPLY CO",
    "NORTHSTAR SURGICAL LLC",
    "BLUE RIDGE DIAGNOSTICS",
    "CAPITOL FACILITY SERVICES",
    "GREATLAKES LABORATORY INC",
    "PIONEER IMAGING PARTNERS",
)
DOC_TYPES = ("PO", "1358", "ADJ")


def money(cents: int) -> str:
    """Format integer cents the way an accounting report does."""
    sign = "-" if cents < 0 else ""
    value = abs(cents)
    return f"{sign}{value // 100:,}.{value % 100:02d}"


def fiscal_year_of(day: date) -> int:
    return day.year + 1 if day.month >= 10 else day.year


def fiscal_period_of(day: date) -> int:
    return ((day.month - 10) % 12) + 1


def business_days(start: date, end: date) -> list[date]:
    days, day = [], start
    while day <= end:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


@dataclass
class Txn:
    txn_date: date
    doc_number: str
    doc_type: str
    fcp: str
    boc: str
    vendor: str
    description: str
    amount_cents: int
    # Invoice lifecycle, only populated for purchase orders.
    invoice_number: str | None = None
    invoice_date: date | None = None
    received_date: date | None = None
    certified_date: date | None = None
    paid_date: date | None = None


def build_ledger(days: list[date], rng: random.Random) -> list[Txn]:
    """Create a transaction ledger for the whole window, then derive files from it.

    Deriving every report from one ledger is what makes the sample set
    reconcile: the general ledger extract and the control point activity report
    are two projections of the same facts, exactly as they should be in life.
    """
    ledger: list[Txn] = []
    seq = 1
    budget_used = {fcp: 0 for fcp, _, _, _ in FCPS}
    ceiling = {fcp: int(alloc * 0.62) for fcp, _, alloc, _ in FCPS}

    # Size transactions relative to each control point's allocation so that
    # spending runs at a steady rate across the whole window. Fixed-size
    # transactions would let the smaller control points hit their ceiling early
    # and flatline, which would make the burn-rate views look broken when they
    # are in fact reporting a genuine absence of activity.
    expected_txns = max(1, int(len(days) * 0.8))
    mean_amount = {
        fcp: max(50_00, ceiling[fcp] // expected_txns) for fcp, _, _, _ in FCPS
    }

    for day in days:
        for fcp, name, _alloc, _cc in FCPS:
            for _ in range(rng.choice((0, 0, 1, 1, 2))):
                mean = mean_amount[fcp]
                amount = rng.randrange(int(mean * 0.35), int(mean * 1.65))
                if budget_used[fcp] + amount > ceiling[fcp]:
                    continue
                budget_used[fcp] += amount

                doc_type = rng.choices(DOC_TYPES, weights=(70, 22, 8))[0]
                doc_number = f"{STATION}-{seq:06d}"
                seq += 1
                vendor = rng.choice(VENDORS)
                txn = Txn(
                    txn_date=day,
                    doc_number=doc_number,
                    doc_type=doc_type,
                    fcp=fcp,
                    boc=rng.choice(BOCS),
                    vendor=vendor,
                    description=f"{name.title()} order {doc_number[-4:]}",
                    amount_cents=amount,
                )
                if doc_type == "PO":
                    inv = day + timedelta(days=rng.randrange(6, 15))
                    txn.invoice_number = f"INV{seq:07d}"
                    txn.invoice_date = inv
                    txn.received_date = inv + timedelta(days=rng.randrange(1, 4))
                    txn.certified_date = txn.received_date + timedelta(days=rng.randrange(2, 8))
                    txn.paid_date = txn.certified_date + timedelta(days=rng.randrange(3, 12))
                ledger.append(txn)
    return ledger


def _write_sof(path: Path, day: date, ledger: list[Txn], rng: random.Random) -> None:
    fy = fiscal_year_of(day)
    obligations: dict[str, int] = {}
    expenditures: dict[str, int] = {}
    for txn in ledger:
        if txn.txn_date > day or fiscal_year_of(txn.txn_date) != fy:
            continue
        obligations[txn.fcp] = obligations.get(txn.fcp, 0) + txn.amount_cents
        if txn.paid_date is not None and txn.paid_date <= day:
            expenditures[txn.fcp] = expenditures.get(txn.fcp, 0) + txn.amount_cents

    lines = [
        "".center(108),
        "STATUS OF FUNDS BY CONTROL POINT".center(108),
        f"STATION: {STATION} - EXAMPLE VAMC".ljust(60) + f"RUN DATE: {day:%m/%d/%Y}",
        f"AS OF: {day:%m/%d/%Y}".ljust(60) + "PAGE 1",
        "-" * 108,
        "FCP      CONTROL POINT NAME                 ALLOCATION   COMMITMENTS"
        "  OBLIGATIONS EXPENDITURES        BALANCE",
        "-" * 108,
    ]

    total_obligations = 0
    for index, (fcp, name, allocation, _cc) in enumerate(FCPS):
        if index == 4:
            # A page break part way down, because the real capture has one and
            # the parser has to survive it.
            lines += ["", f"AS OF: {day:%m/%d/%Y}".ljust(60) + "PAGE 2", "-" * 108]

        obligated = obligations.get(fcp, 0)
        expended = expenditures.get(fcp, 0)
        committed = rng.randrange(0, 60_000_00)
        balance = allocation - committed - obligated
        total_obligations += obligated

        lines.append(
            f"{fcp:<8} {name[:30]:<30}"
            f"{money(allocation):>15}{money(committed):>14}{money(obligated):>13}"
            f"{money(expended):>13}{money(balance):>14}"
        )

    lines += [
        "-" * 108,
        " " * 41 + f"TOTAL OBLIGATIONS:   {money(total_obligations)}",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_cpa(path: Path, day: date, ledger: list[Txn]) -> None:
    fy = fiscal_year_of(day)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "Transaction Date", "Document Number", "Type", "Control Point",
            "BOC", "Vendor", "Description", "Amount", "Status",
        ])
        for txn in ledger:
            if txn.txn_date > day or fiscal_year_of(txn.txn_date) != fy:
                continue
            if txn.paid_date is not None and txn.paid_date <= day:
                status = "PAID"
            elif txn.certified_date is not None and txn.certified_date <= day:
                status = "CERTIFIED"
            else:
                status = "OBLIGATED"
            writer.writerow([
                txn.txn_date.strftime("%m/%d/%Y"), txn.doc_number, txn.doc_type,
                txn.fcp, txn.boc, txn.vendor, txn.description,
                money(txn.amount_cents), status,
            ])


def _write_obl1358(path: Path, day: date, ledger: list[Txn]) -> None:
    fy = fiscal_year_of(day)
    rows = []
    for txn in ledger:
        if txn.doc_type != "1358" or txn.txn_date > day:
            continue
        if fiscal_year_of(txn.txn_date) != fy:
            continue
        authorized = txn.amount_cents
        obligated = txn.amount_cents
        elapsed = (day - txn.txn_date).days
        liquidated = min(obligated, int(obligated * min(elapsed / 60.0, 1.0)))
        rows.append((
            f"{STATION}-C{txn.doc_number[-5:]}", txn.fcp, txn.description[:32],
            authorized, obligated, liquidated, obligated - liquidated,
        ))

    lines = [
        "1358 OBLIGATION BALANCES".center(110),
        f"AS OF {day:%m/%d/%Y}".center(110),
        "-" * 110,
        "OBL NUMBER    FCP    DESCRIPTION                         AUTHORIZED"
        "     OBLIGATED    LIQUIDATED       REMAINING",
        "-" * 110,
    ]
    for obl, fcp, desc, auth, oblig, liq, rem in rows:
        lines.append(
            f"{obl:<14}{fcp:<7}{desc:<32}"
            f"{money(auth):>14}{money(oblig):>14}{money(liq):>14}{money(rem):>15}"
        )
    lines += ["-" * 110, f"RECORDS PRINTED: {len(rows)}", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ipps(path: Path, day: date, ledger: list[Txn]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "Invoice Number", "PO Number", "Vendor", "Invoice Date",
            "Received Date", "Certified Date", "Paid Date", "Amount", "Status",
        ])
        for txn in ledger:
            if txn.invoice_number is None or txn.invoice_date is None:
                continue
            if txn.invoice_date > day:
                continue

            def visible(value: date | None) -> str:
                return value.strftime("%m/%d/%Y") if value and value <= day else ""

            if txn.paid_date and txn.paid_date <= day:
                status = "PAID"
            elif txn.certified_date and txn.certified_date <= day:
                status = "CERTIFIED"
            elif txn.received_date and txn.received_date <= day:
                status = "RECEIVED"
            else:
                status = "PENDING"

            writer.writerow([
                txn.invoice_number, txn.doc_number, txn.vendor,
                visible(txn.invoice_date), visible(txn.received_date),
                visible(txn.certified_date), visible(txn.paid_date),
                money(txn.amount_cents), status,
            ])


def _write_fmsact(path: Path, day: date, ledger: list[Txn]) -> None:
    fy = fiscal_year_of(day)
    cost_centre = {fcp: cc for fcp, _n, _a, cc in FCPS}
    totals: dict[tuple, list[int]] = {}
    for txn in ledger:
        if txn.txn_date > day or fiscal_year_of(txn.txn_date) != fy:
            continue
        key = (fy, fiscal_period_of(txn.txn_date), FUND, cost_centre[txn.fcp], txn.boc)
        bucket = totals.setdefault(key, [0, 0])
        bucket[0] += txn.amount_cents
        if txn.paid_date is not None and txn.paid_date <= day:
            bucket[1] += txn.amount_cents

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "Fiscal Year", "Accounting Period", "Fund", "Cost Center", "BOC",
            "Obligations", "Expenditures",
        ])
        for (year, period, fund, cc, boc), (oblig, expend) in sorted(totals.items()):
            writer.writerow([year, period, fund, cc, boc, money(oblig), money(expend)])


def generate(
    outdir: Path,
    start: date,
    end: date,
    seed: int = 20260817,
    inject_faults: bool = False,
) -> list[Path]:
    """Write a full set of sample reports for every business day in the window."""
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    days = business_days(start, end)
    if not days:
        raise ValueError(f"no business days between {start} and {end}")

    ledger = build_ledger(days, rng)

    if inject_faults and len(days) > 6:
        # A missing day, as when a scheduled pull silently fails.
        days = [d for i, d in enumerate(days) if i != len(days) // 2]

    written: list[Path] = []
    for day in days:
        stamp = day.strftime("%Y%m%d")
        targets = [
            (outdir / f"SOF_{stamp}.txt", _write_sof, True),
            (outdir / f"CPA_{stamp}.csv", _write_cpa, False),
            (outdir / f"OBL1358_{stamp}.txt", _write_obl1358, False),
            (outdir / f"IPPS_{stamp}.csv", _write_ipps, False),
            (outdir / f"FMSACT_{stamp}.csv", _write_fmsact, False),
        ]
        for path, writer, needs_rng in targets:
            if needs_rng:
                writer(path, day, ledger, random.Random(seed + day.toordinal()))
            else:
                writer(path, day, ledger)
            written.append(path)

    if inject_faults:
        # Truncate the newest Status of Funds capture but leave its printed
        # total intact -- the signature of a screen scrape that stopped early.
        newest = outdir / f"SOF_{days[-1]:%Y%m%d}.txt"
        text = newest.read_text(encoding="utf-8").splitlines()
        kept = [line for line in text if not line.startswith(("0106", "0107", "0108"))]
        newest.write_text("\n".join(kept) + "\n", encoding="utf-8")

    return written
```

### Command line interface

#### `pipeline/vabudget/cli.py`

```python
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
```

### SQL — core schema

#### `pipeline/sql/010_core.sql`

```sql
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
```

### SQL — conformed mart

#### `pipeline/sql/200_marts.sql`

```sql
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
```

### Configuration — report catalogue

#### `pipeline/config/reports.toml`

```toml

# Report catalogue.
#
# One [[report]] block per recurring extract that lands in the inbox. These five
# are modelled on the shapes VA budget reports actually arrive in, and they are
# wired to the synthetic sample generator so the pipeline runs end to end with
# no VA data present. Replace the column offsets with the real ones measured off
# your own files -- that is the main onboarding task for each report.
#
# Fixed-width columns use `start` (1-based, count it off the printed report) and
# `length`. Delimited columns use `source` (the header text) or `index`.
#
# Amount columns are stored as integer cents and must be named `*_cents`.

# ---------------------------------------------------------------------------
# IFCAP / VistA -- Status of Funds by Control Point.
# A captured roll-and-scroll screen: page headers, rule lines, a printed total.
# ---------------------------------------------------------------------------
[[report]]
code = "SOF"
name = "Status of Funds by Control Point"
source_system = "IFCAP"
format = "fixed"
filename_glob = "SOF_*.txt"
as_of_from = "filename"
as_of_pattern = 'SOF_(\d{8})\.txt'
as_of_format = "%Y%m%d"
grain = ["fcp"]
expected_cadence_days = 4          # daily, with slack for weekends and holidays
row_pattern = '^\d{4}\s'           # data lines begin with a 4-digit control point

  [report.control_total]
  pattern = 'TOTAL OBLIGATIONS:\s+([\d,]+\.\d{2})'
  column = "obligations_cents"

  [[report.column]]
  name = "fcp"
  start = 1
  length = 8

  [[report.column]]
  name = "fcp_name"
  start = 10
  length = 30

  [[report.column]]
  name = "allocation_cents"
  type = "amount"
  start = 40
  length = 15

  [[report.column]]
  name = "commitments_cents"
  type = "amount"
  start = 55
  length = 14

  [[report.column]]
  name = "obligations_cents"
  type = "amount"
  start = 69
  length = 13

  [[report.column]]
  name = "expenditures_cents"
  type = "amount"
  start = 82
  length = 13

  [[report.column]]
  name = "balance_cents"
  type = "amount"
  start = 95
  length = 14


# ---------------------------------------------------------------------------
# IFCAP / VistA -- Control Point Activity, fiscal-year-to-date transactions.
# Delivered as a delimited export (today, whatever the Reflection macro writes).
# ---------------------------------------------------------------------------
[[report]]
code = "CPA"
name = "Control Point Activity (FYTD transactions)"
source_system = "IFCAP"
format = "delimited"
filename_glob = "CPA_*.csv"
as_of_from = "filename"
as_of_pattern = 'CPA_(\d{8})\.csv'
as_of_format = "%Y%m%d"
grain = ["doc_number"]
expected_cadence_days = 4

  [[report.column]]
  name = "txn_date"
  type = "date"
  source = "Transaction Date"

  [[report.column]]
  name = "doc_number"
  source = "Document Number"

  [[report.column]]
  name = "doc_type"
  source = "Type"

  [[report.column]]
  name = "fcp"
  source = "Control Point"

  [[report.column]]
  name = "boc"
  source = "BOC"

  [[report.column]]
  name = "vendor_name"
  source = "Vendor"

  [[report.column]]
  name = "description"
  source = "Description"

  [[report.column]]
  name = "amount_cents"
  type = "amount"
  source = "Amount"

  [[report.column]]
  name = "status"
  source = "Status"


# ---------------------------------------------------------------------------
# IFCAP / VistA -- 1358 obligation balances.
# ---------------------------------------------------------------------------
[[report]]
code = "OBL1358"
name = "1358 Obligation Balances"
source_system = "IFCAP"
format = "fixed"
filename_glob = "OBL1358_*.txt"
as_of_from = "filename"
as_of_pattern = 'OBL1358_(\d{8})\.txt'
as_of_format = "%Y%m%d"
grain = ["obligation_number"]
expected_cadence_days = 4
row_pattern = '^\d{3}-C\d'

  [[report.column]]
  name = "obligation_number"
  start = 1
  length = 14

  [[report.column]]
  name = "fcp"
  start = 15
  length = 7

  [[report.column]]
  name = "description"
  start = 22
  length = 32

  [[report.column]]
  name = "authorized_cents"
  type = "amount"
  start = 54
  length = 14

  [[report.column]]
  name = "obligated_cents"
  type = "amount"
  start = 68
  length = 14

  [[report.column]]
  name = "liquidated_cents"
  type = "amount"
  start = 82
  length = 14

  [[report.column]]
  name = "remaining_cents"
  type = "amount"
  start = 96
  length = 15


# ---------------------------------------------------------------------------
# IPPS -- invoice status and payment history.
# ---------------------------------------------------------------------------
[[report]]
code = "IPPS"
name = "Invoice Payment Status"
source_system = "IPPS"
format = "delimited"
filename_glob = "IPPS_*.csv"
as_of_from = "filename"
as_of_pattern = 'IPPS_(\d{8})\.csv'
as_of_format = "%Y%m%d"
grain = ["invoice_number"]
expected_cadence_days = 4

  [[report.column]]
  name = "invoice_number"
  source = "Invoice Number"

  [[report.column]]
  name = "po_number"
  source = "PO Number"

  [[report.column]]
  name = "vendor_name"
  source = "Vendor"

  [[report.column]]
  name = "invoice_date"
  type = "date"
  source = "Invoice Date"

  [[report.column]]
  name = "received_date"
  type = "date"
  source = "Received Date"

  [[report.column]]
  name = "certified_date"
  type = "date"
  source = "Certified Date"

  [[report.column]]
  name = "paid_date"
  type = "date"
  source = "Paid Date"

  [[report.column]]
  name = "amount_cents"
  type = "amount"
  source = "Amount"

  [[report.column]]
  name = "status"
  source = "Status"


# ---------------------------------------------------------------------------
# FMS (and, after cutover, iFAMS) -- general ledger actuals by accounting period.
# The authoritative side of every reconciliation.
# ---------------------------------------------------------------------------
[[report]]
code = "FMSACT"
name = "General Ledger Actuals by Period"
source_system = "FMS"
format = "delimited"
filename_glob = "FMSACT_*.csv"
as_of_from = "filename"
as_of_pattern = 'FMSACT_(\d{8})\.csv'
as_of_format = "%Y%m%d"
grain = ["fiscal_year", "accounting_period", "fund", "cost_center", "boc"]
expected_cadence_days = 10         # monthly close, refreshed through the month

  [[report.column]]
  name = "fiscal_year"
  type = "integer"
  source = "Fiscal Year"

  [[report.column]]
  name = "accounting_period"
  type = "integer"
  source = "Accounting Period"

  [[report.column]]
  name = "fund"
  source = "Fund"

  [[report.column]]
  name = "cost_center"
  source = "Cost Center"

  [[report.column]]
  name = "boc"
  source = "BOC"

  [[report.column]]
  name = "obligations_cents"
  type = "amount"
  source = "Obligations"

  [[report.column]]
  name = "expenditures_cents"
  type = "amount"
  source = "Expenditures"
```

### Configuration — data-quality rulebook

#### `pipeline/config/checks.toml`

```toml

# Data-quality rules.
#
# Each check is a query that selects violations, plus the severity of finding
# any. `expect = "zero_rows"` is the default and means "this query should come
# back empty". The point of keeping them here rather than in code is that the
# whole rulebook can be read, reviewed and extended by anyone who knows the
# budget domain and a little SQL.
#
# Severity drives the exit code: `error` fails the run, `warn` and `info` do not.

# --- Did the load itself work? -------------------------------------------

[[check]]
name = "something_loaded"
severity = "error"
expect = "nonzero_rows"
message = "The most recent run loaded no files at all."
sql = """
SELECT f.file_id
FROM ingest_file f
WHERE f.run_id = (SELECT MAX(run_id) FROM ingest_run)
  AND f.status = 'loaded'
"""

[[check]]
name = "no_failed_files"
severity = "error"
message = "One or more files could not be parsed."
sql = """
SELECT filename, report_code, message
FROM ingest_file
WHERE run_id = (SELECT MAX(run_id) FROM ingest_run)
  AND status = 'failed'
"""

# The single most valuable check in the whole set. A screen-scraped report that
# stops early looks completely normal -- correct format, plausible numbers, just
# fewer rows. Comparing against the total the report printed on itself is the
# only cheap way to notice.
[[check]]
name = "control_total_match"
severity = "error"
message = "A report's printed total disagrees with the rows parsed from it, which usually means a truncated capture."
sql = """
SELECT filename,
       report_code,
       as_of_date,
       control_total_cents / 100.0 AS printed_total,
       parsed_total_cents  / 100.0 AS parsed_total
FROM ingest_file
WHERE status = 'loaded'
  AND control_total_cents IS NOT NULL
  AND control_total_cents <> parsed_total_cents
"""

[[check]]
name = "report_freshness"
severity = "error"
message = "A report has not arrived within its expected cadence, so the dashboard would be showing stale figures as though they were current."
sql = """
SELECT report_code, latest_as_of, days_stale, freshness_status
FROM v_report_freshness
WHERE freshness_status <> 'current'
"""

# Enumerate the weekdays that should have a snapshot and find the ones that do
# not, rather than measuring the gap between consecutive snapshots. A single
# missing Tuesday only widens the gap from one day to two, which no threshold on
# consecutive dates can distinguish from a normal weekend -- and a quietly
# missing day is the whole failure this rule exists to catch.
#
# Federal holidays will show up here. Either accept them as known warnings or
# add a holiday table and exclude it in the NOT EXISTS below.
[[check]]
name = "snapshot_gaps"
severity = "warn"
message = "Status of Funds snapshots are missing for business days inside the loaded window, so trend lines interpolate across a hole."
sql = """
SELECT d.date_key AS missing_business_day
FROM dim_date d
WHERE d.date_key BETWEEN (SELECT MIN(as_of_date) FROM fact_fcp_daily_balance)
                     AND (SELECT MAX(as_of_date) FROM fact_fcp_daily_balance)
  AND CAST(strftime('%w', d.date_key) AS INTEGER) BETWEEN 1 AND 5
  AND NOT EXISTS (
      SELECT 1 FROM fact_fcp_daily_balance f WHERE f.as_of_date = d.date_key
  )
"""

# --- Does the arithmetic hold? -------------------------------------------

# Verify this identity against a real Status of Funds report before trusting it.
# Whether expenditures sit inside obligations or beside them varies by report,
# and getting it wrong silently shifts every balance.
[[check]]
name = "sof_balance_identity"
severity = "error"
message = "Status of Funds rows where allocation - commitments - obligations does not equal the printed balance."
sql = """
SELECT as_of_date,
       fcp,
       (allocation_cents - commitments_cents - obligations_cents) / 100.0 AS computed,
       balance_cents / 100.0 AS reported
FROM fact_fcp_daily_balance
WHERE allocation_cents - commitments_cents - obligations_cents <> balance_cents
"""

[[check]]
name = "expenditures_within_obligations"
severity = "warn"
message = "Expenditures exceed obligations on a control point, which normally indicates a mapping error rather than a real overspend."
sql = """
SELECT as_of_date, fcp,
       expenditures_cents / 100.0 AS expenditures,
       obligations_cents  / 100.0 AS obligations
FROM fact_fcp_daily_balance
WHERE expenditures_cents > obligations_cents
"""

[[check]]
name = "negative_balance"
severity = "warn"
message = "A control point shows a negative available balance."
sql = """
SELECT as_of_date, fcp, balance_cents / 100.0 AS balance
FROM fact_fcp_daily_balance
WHERE balance_cents < 0
"""

# --- Do the sources agree with each other? --------------------------------

[[check]]
name = "cpa_orphan_control_point"
severity = "warn"
message = "Transactions reference a control point that never appears on a Status of Funds report."
sql = """
SELECT DISTINCT t.fcp
FROM fact_cp_transaction t
LEFT JOIN fact_fcp_daily_balance b ON b.fcp = t.fcp
WHERE b.fcp IS NULL
"""

[[check]]
name = "ifcap_fms_variance"
severity = "warn"
message = "IFCAP obligations and FMS actuals differ by more than one percent for an accounting period."
sql = """
SELECT fiscal_year, fiscal_period, ifcap_obligations, fms_obligations, variance_pct
FROM v_ifcap_vs_fms_monthly
WHERE variance_pct IS NOT NULL
  AND ABS(variance_pct) > 1.0
"""

[[check]]
name = "invoice_paid_before_invoiced"
severity = "warn"
message = "An invoice has a payment date earlier than its invoice date."
sql = """
SELECT invoice_number, invoice_date, paid_date
FROM fact_invoice
WHERE paid_date IS NOT NULL
  AND julianday(paid_date) < julianday(invoice_date)
"""

[[check]]
name = "duplicate_control_point_in_snapshot"
severity = "error"
message = "The same control point appears more than once in a single Status of Funds snapshot."
sql = """
SELECT s.as_of_date, s.fcp, COUNT(*) AS occurrences
FROM stg_sof s
JOIN v_current_file c ON c.file_id = s.file_id
GROUP BY s.as_of_date, s.fcp
HAVING COUNT(*) > 1
"""
```

### Tests

#### `pipeline/tests/__init__.py`

```python
# (intentionally empty - marks tests/ as a package)
```

#### `pipeline/tests/test_parsers.py`

```python
"""Parsing tests.

The amount cases are drawn from the notations that actually turn up in VistA
and FMS output. Getting any of them wrong flips the sign on a real number, so
they are pinned here rather than trusted to look right.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from vabudget.config import ConfigError, load_reports
from vabudget.parsers import ParseError, parse_amount, parse_date, parse_file

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = Path(__file__).parent.parent / "config" / "reports.toml"


class TestParseAmount(unittest.TestCase):
    def test_plain_and_grouped(self):
        self.assertEqual(parse_amount("1234.56"), 123456)
        self.assertEqual(parse_amount("1,234.56"), 123456)
        self.assertEqual(parse_amount("$1,234.56"), 123456)
        self.assertEqual(parse_amount("  1,250,000.00  "), 125000000)

    def test_every_negative_notation_agrees(self):
        for text in ("(1,234.56)", "-1,234.56", "1,234.56-", "1,234.56CR"):
            with self.subTest(text=text):
                self.assertEqual(parse_amount(text), -123456)

    def test_credit_debit_suffixes(self):
        self.assertEqual(parse_amount("500.00DR"), 50000)
        self.assertEqual(parse_amount("500.00CR"), -50000)

    def test_integers_and_partial_decimals(self):
        self.assertEqual(parse_amount("42"), 4200)
        self.assertEqual(parse_amount("42.5"), 4250)
        self.assertEqual(parse_amount(".75"), 75)

    def test_blanks_and_placeholders_are_null(self):
        for text in ("", "   ", "-", "--", "N/A", None):
            with self.subTest(text=text):
                self.assertIsNone(parse_amount(text))

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_amount("TOTAL")


class TestParseDate(unittest.TestCase):
    def test_common_formats(self):
        self.assertEqual(parse_date("10/15/2025"), "2025-10-15")
        self.assertEqual(parse_date("2025-10-15"), "2025-10-15")
        self.assertEqual(parse_date("20251015"), "2025-10-15")

    def test_null_placeholders(self):
        for text in ("", "00/00/00", "N/A", None):
            with self.subTest(text=text):
                self.assertIsNone(parse_date(text))

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_date("sometime last week")


class TestFixedWidthParsing(unittest.TestCase):
    """The fixed-width path has to survive real report furniture."""

    def setUp(self):
        self.reports = {r.code: r for r in load_reports(CONFIG)}
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_sof(self, body_lines, total="1,000.00", name="SOF_20251015.txt"):
        header = [
            "STATUS OF FUNDS BY CONTROL POINT".center(108),
            "AS OF: 10/15/2025".ljust(60) + "PAGE 1",
            "-" * 108,
            "FCP      CONTROL POINT NAME  ALLOCATION",
            "-" * 108,
        ]
        footer = ["-" * 108, " " * 41 + f"TOTAL OBLIGATIONS:   {total}", ""]
        path = self.dir / name
        path.write_text("\n".join(header + body_lines + footer) + "\n", encoding="utf-8")
        return path

    def test_parses_row_and_ignores_page_furniture(self):
        row = (
            f"{'0101':<8} {'PROSTHETICS':<30}"
            f"{'1,250,000.00':>15}{'45,200.00':>14}{'820,455.10':>13}"
            f"{'790,100.00':>13}{'384,344.90':>14}"
        )
        path = self._write_sof([row], total="820,455.10")
        parsed = parse_file(self.reports["SOF"], path)

        self.assertEqual(parsed.row_count, 1)
        self.assertEqual(parsed.as_of_date, date(2025, 10, 15))
        self.assertEqual(parsed.control_total_cents, 82045510)

        record = parsed.rows[0]
        self.assertEqual(record["fcp"], "0101")
        self.assertEqual(record["fcp_name"], "PROSTHETICS")
        self.assertEqual(record["allocation_cents"], 125000000)
        self.assertEqual(record["obligations_cents"], 82045510)
        self.assertEqual(record["balance_cents"], 38434490)

    def test_form_feed_and_repeated_headers_do_not_become_rows(self):
        row = (
            f"{'0101':<8} {'PROSTHETICS':<30}"
            f"{'1,250,000.00':>15}{'0.00':>14}{'100.00':>13}{'0.00':>13}{'0.00':>14}"
        )
        body = [row, "\f", "AS OF: 10/15/2025".ljust(60) + "PAGE 2", "-" * 108, row]
        parsed = parse_file(self.reports["SOF"], self._write_sof(body, total="200.00"))
        self.assertEqual(parsed.row_count, 2)

    def test_missing_as_of_in_filename_is_a_clear_error(self):
        path = self._write_sof([], name="SOF_notadate.txt")
        with self.assertRaises(ParseError) as ctx:
            parse_file(self.reports["SOF"], path)
        self.assertIn("as-of date", str(ctx.exception))

    def test_short_line_is_padded_not_crashed(self):
        parsed = parse_file(
            self.reports["SOF"], self._write_sof(["0101     PROSTHETICS"])
        )
        self.assertEqual(parsed.row_count, 1)
        self.assertIsNone(parsed.rows[0]["allocation_cents"])


class TestDelimitedParsing(unittest.TestCase):
    def setUp(self):
        self.reports = {r.code: r for r in load_reports(CONFIG)}
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parses_by_header_name(self):
        path = self.dir / "CPA_20251015.csv"
        path.write_text(
            "Transaction Date,Document Number,Type,Control Point,BOC,Vendor,"
            "Description,Amount,Status\n"
            "10/14/2025,999-000001,PO,0101,2631,ACME,Widget order,\"1,234.56\",PAID\n",
            encoding="utf-8",
        )
        parsed = parse_file(self.reports["CPA"], path)

        self.assertEqual(parsed.row_count, 1)
        record = parsed.rows[0]
        self.assertEqual(record["txn_date"], "2025-10-14")
        self.assertEqual(record["amount_cents"], 123456)
        self.assertEqual(record["fcp"], "0101")

    def test_renamed_export_column_names_the_problem(self):
        """A silently changed export is the most likely real-world breakage."""
        path = self.dir / "CPA_20251015.csv"
        path.write_text("Txn Date,Document Number\n10/14/2025,999-000001\n", encoding="utf-8")
        with self.assertRaises(ParseError) as ctx:
            parse_file(self.reports["CPA"], path)
        message = str(ctx.exception)
        self.assertIn("Transaction Date", message)
        self.assertIn("CPA", message)


class TestConfigValidation(unittest.TestCase):
    """Configuration mistakes should fail loudly at load time, not silently."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "reports.toml"

    def tearDown(self):
        self.tmp.cleanup()

    def _load(self, text):
        self.path.write_text(text, encoding="utf-8")
        return load_reports(self.path)

    def test_amount_column_must_be_named_cents(self):
        with self.assertRaises(ConfigError) as ctx:
            self._load(
                '[[report]]\ncode="X"\nformat="delimited"\nas_of_from="mtime"\n'
                '[[report.column]]\nname="amount"\ntype="amount"\nsource="Amount"\n'
            )
        self.assertIn("_cents", str(ctx.exception))

    def test_fixed_column_needs_offsets(self):
        with self.assertRaises(ConfigError) as ctx:
            self._load(
                '[[report]]\ncode="X"\nformat="fixed"\nas_of_from="mtime"\n'
                '[[report.column]]\nname="fcp"\n'
            )
        self.assertIn("start", str(ctx.exception))

    def test_duplicate_report_codes_rejected(self):
        with self.assertRaises(ConfigError) as ctx:
            self._load(
                '[[report]]\ncode="X"\nformat="delimited"\nas_of_from="mtime"\n'
                '[[report.column]]\nname="a"\nsource="A"\n'
                '[[report]]\ncode="X"\nformat="delimited"\nas_of_from="mtime"\n'
                '[[report.column]]\nname="a"\nsource="A"\n'
            )
        self.assertIn("duplicate report codes", str(ctx.exception))

    def test_shipped_config_is_valid(self):
        reports = load_reports(CONFIG)
        self.assertEqual(
            {r.code for r in reports},
            {"SOF", "CPA", "OBL1358", "IPPS", "FMSACT"},
        )


if __name__ == "__main__":
    unittest.main()
```

#### `pipeline/tests/test_loader.py`

```python
"""Loader semantics.

These tests pin the three behaviours that decide whether the numbers can be
trusted: a file is never counted twice, a genuinely new day is never mistaken
for a duplicate, and a corrected report supersedes the one it replaces without
anybody deleting anything.
"""

import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from vabudget.config import load_reports
from vabudget.db import connect, ensure_schema, fiscal_attributes
from vabudget.loader import discover, ingest

CONFIG = Path(__file__).parent.parent / "config" / "reports.toml"

HEADER = (
    "STATUS OF FUNDS BY CONTROL POINT\n"
    "AS OF: 10/15/2025                                           PAGE 1\n"
    + "-" * 108 + "\n"
)


def sof_row(fcp="0101", name="PROSTHETICS", allocation="1,000.00",
            commitments="0.00", obligations="100.00", expenditures="0.00",
            balance="900.00"):
    return (
        f"{fcp:<8} {name:<30}{allocation:>15}{commitments:>14}"
        f"{obligations:>13}{expenditures:>13}{balance:>14}"
    )


def write_sof(directory: Path, stamp: str, rows, total="100.00") -> Path:
    path = directory / f"SOF_{stamp}.txt"
    body = "\n".join(rows)
    footer = "\n" + "-" * 108 + "\n" + " " * 41 + f"TOTAL OBLIGATIONS:   {total}\n"
    path.write_text(HEADER + body + footer, encoding="utf-8")
    return path


class LoaderTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.inbox = self.dir / "inbox"
        self.inbox.mkdir()
        self.reports = load_reports(CONFIG)
        self.conn = connect(self.dir / "test.db")
        ensure_schema(self.conn, self.reports)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def load(self, **kwargs):
        return ingest(self.conn, self.reports, self.inbox, **kwargs)

    def scalar(self, sql):
        return self.conn.execute(sql).fetchone()[0]


class TestIdempotency(LoaderTestCase):
    def test_second_run_over_same_inbox_loads_nothing(self):
        write_sof(self.inbox, "20251015", [sof_row()])
        first = self.load()
        second = self.load()

        self.assertEqual(first.loaded, 1)
        self.assertEqual(second.loaded, 0)
        self.assertEqual(second.skipped, 1)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM stg_sof"), 1)

    def test_identical_content_on_a_different_day_is_a_real_snapshot(self):
        """A quiet day produces a byte-identical report. It is still a day."""
        rows = [sof_row()]
        write_sof(self.inbox, "20251015", rows)
        write_sof(self.inbox, "20251016", rows)
        summary = self.load()

        self.assertEqual(summary.loaded, 2)
        self.assertEqual(
            self.scalar("SELECT COUNT(DISTINCT as_of_date) FROM fact_fcp_daily_balance"),
            2,
        )

    def test_force_reloads_without_duplicating(self):
        write_sof(self.inbox, "20251015", [sof_row()])
        self.load()
        summary = self.load(force=True)

        self.assertEqual(summary.loaded, 1)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM stg_sof"), 1)


class TestCorrections(LoaderTestCase):
    def test_later_file_for_the_same_day_wins(self):
        write_sof(self.inbox, "20251015", [sof_row(obligations="100.00")], total="100.00")
        self.load()

        # A corrected report arrives for the same date with a different figure.
        write_sof(
            self.inbox, "20251015",
            [sof_row(obligations="250.00", balance="750.00")],
            total="250.00",
        )
        self.load()

        # Both files are retained for audit, but only the correction is in the mart.
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM ingest_file"), 2)
        self.assertEqual(
            self.scalar("SELECT obligations_cents FROM fact_fcp_daily_balance"), 25000
        )
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM fact_fcp_daily_balance"), 1)


class TestFailureHandling(LoaderTestCase):
    def test_one_bad_file_does_not_stop_the_others(self):
        write_sof(self.inbox, "20251015", [sof_row()])
        (self.inbox / "SOF_notadate.txt").write_text("garbage\n", encoding="utf-8")

        summary = self.load()
        self.assertEqual(summary.loaded, 1)
        self.assertEqual(summary.failed, 1)

    def test_failed_file_is_retried_on_the_next_run(self):
        bad = self.inbox / "SOF_notadate.txt"
        bad.write_text("garbage\n", encoding="utf-8")
        self.assertEqual(self.load().failed, 1)

        # Renaming so the as-of date is discoverable is the realistic fix.
        bad.unlink()
        write_sof(self.inbox, "20251015", [sof_row()])
        summary = self.load()
        self.assertEqual(summary.loaded, 1)
        self.assertEqual(summary.failed, 0)


class TestDiscovery(LoaderTestCase):
    def test_overlapping_globs_are_rejected_rather_than_guessed(self):
        write_sof(self.inbox, "20251015", [sof_row()])
        overlapping = tuple(
            replace(report, filename_glob="*") for report in self.reports
        )
        with self.assertRaises(ValueError) as ctx:
            discover(self.inbox, overlapping)
        self.assertIn("overlap", str(ctx.exception))

    def test_unrecognised_files_are_ignored(self):
        (self.inbox / "notes.docx").write_text("unrelated", encoding="utf-8")
        write_sof(self.inbox, "20251015", [sof_row()])
        self.assertEqual(self.load().loaded, 1)


class TestFiscalCalendar(unittest.TestCase):
    def test_october_starts_the_next_fiscal_year(self):
        self.assertEqual(fiscal_attributes(date(2025, 10, 1))["fiscal_year"], 2026)
        self.assertEqual(fiscal_attributes(date(2025, 10, 1))["fiscal_period"], 1)
        self.assertEqual(fiscal_attributes(date(2025, 10, 1))["fiscal_quarter"], 1)

    def test_september_ends_the_fiscal_year(self):
        attributes = fiscal_attributes(date(2026, 9, 30))
        self.assertEqual(attributes["fiscal_year"], 2026)
        self.assertEqual(attributes["fiscal_period"], 12)
        self.assertEqual(attributes["fiscal_quarter"], 4)
        self.assertEqual(attributes["is_fiscal_year_end"], 1)

    def test_calendar_new_year_stays_in_the_same_fiscal_year(self):
        self.assertEqual(fiscal_attributes(date(2026, 1, 15))["fiscal_year"], 2026)
        self.assertEqual(fiscal_attributes(date(2026, 1, 15))["fiscal_period"], 4)


if __name__ == "__main__":
    unittest.main()
```

#### `pipeline/tests/test_end_to_end.py`

```python
"""Whole-pipeline tests over generated sample data.

The clean case asserts that a full generation passes every data-quality rule,
which is what makes the rulebook meaningful: if clean data failed checks, the
warnings would be noise and would be ignored within a week. The fault case
asserts that the two failures most likely to happen in real life -- a truncated
capture and a silently missing day -- are actually detected.
"""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from vabudget.config import load_reports
from vabudget.db import connect, ensure_schema
from vabudget.loader import ingest
from vabudget.quality import load_checks, run_checks, worst_severity
from vabudget.samples import generate

PIPELINE = Path(__file__).parent.parent
CONFIG = PIPELINE / "config" / "reports.toml"
CHECKS = PIPELINE / "config" / "checks.toml"

START = date(2025, 10, 1)
END = date(2025, 12, 19)


class EndToEndTestCase(unittest.TestCase):
    inject_faults = False

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        inbox = root / "inbox"

        generate(inbox, START, END, inject_faults=cls.inject_faults)
        cls.reports = load_reports(CONFIG)
        cls.conn = connect(root / "e2e.db")
        ensure_schema(cls.conn, cls.reports)
        cls.summary = ingest(cls.conn, cls.reports, inbox)
        cls.results = run_checks(cls.conn, load_checks(CHECKS), cls.summary.run_id)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def failing(self):
        return {r.check.name for r in self.results if not r.passed}

    def scalar(self, sql):
        return self.conn.execute(sql).fetchone()[0]


class TestCleanData(EndToEndTestCase):
    inject_faults = False

    def test_everything_loaded(self):
        self.assertGreater(self.summary.loaded, 0)
        self.assertEqual(self.summary.failed, 0)

    def test_all_checks_pass_on_clean_data(self):
        self.assertEqual(self.failing(), set())
        self.assertIsNone(worst_severity(self.results))

    def test_ifcap_and_general_ledger_reconcile_exactly(self):
        """Both are projections of one ledger, so any variance is a pipeline bug."""
        worst = self.scalar(
            "SELECT COALESCE(MAX(ABS(variance)), 0) FROM v_ifcap_vs_fms_monthly"
        )
        self.assertEqual(worst, 0)

    def test_every_business_day_has_a_snapshot(self):
        expected = sum(
            1 for offset in range((END - START).days + 1)
            if (START + timedelta(days=offset)).weekday() < 5
        )
        self.assertEqual(
            self.scalar("SELECT COUNT(DISTINCT as_of_date) FROM fact_fcp_daily_balance"),
            expected,
        )

    def test_control_totals_all_match(self):
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM v_ingest_audit WHERE control_total_check = 'MISMATCH'"
            ),
            0,
        )

    def test_burn_rate_projects_a_date_for_every_control_point(self):
        missing = self.scalar(
            "SELECT COUNT(*) FROM v_fcp_burn_rate"
            " WHERE as_of_date = (SELECT MAX(as_of_date) FROM v_fcp_burn_rate)"
            "   AND projected_exhaustion_date IS NULL"
        )
        self.assertEqual(missing, 0)

    def test_transactions_are_not_multiplied_by_snapshot_count(self):
        """The FYTD extract repeats every transaction daily; only one copy should land."""
        staged = self.scalar("SELECT COUNT(*) FROM stg_cpa")
        fact = self.scalar("SELECT COUNT(*) FROM fact_cp_transaction")
        distinct = self.scalar("SELECT COUNT(DISTINCT doc_number) FROM stg_cpa")
        self.assertEqual(fact, distinct)
        self.assertLess(fact, staged)

    def test_money_survives_the_round_trip(self):
        """Report text -> cents -> view dollars, with no float drift."""
        cents = self.scalar("SELECT SUM(obligations_cents) FROM fact_fcp_daily_balance")
        dollars = self.scalar("SELECT SUM(obligations) FROM v_fcp_daily_balance")
        self.assertAlmostEqual(dollars, cents / 100.0, places=2)


class TestInjectedFaults(EndToEndTestCase):
    inject_faults = True

    def test_truncated_capture_is_caught_by_its_own_printed_total(self):
        self.assertIn("control_total_match", self.failing())

    def test_missing_business_day_is_caught(self):
        self.assertIn("snapshot_gaps", self.failing())

    def test_an_error_severity_failure_is_reported(self):
        self.assertEqual(worst_severity(self.results), "error")

    def test_faults_are_localised_rather_than_breaking_everything(self):
        self.assertLessEqual(len(self.failing()), 3)
        self.assertEqual(self.summary.failed, 0)


if __name__ == "__main__":
    unittest.main()
```

### Repository hygiene

#### `pipeline/.gitignore`

```text
# Generated at runtime -- never commit budget data or databases.
inbox/
faulty/
curated/
*.db
*.db-wal
*.db-shm
__pycache__/
*.pyc
```

### Project README

#### `README.md`

````markdown
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
````


---

## Part 5 — Rebuilding the working tree from this document

### 5.1 If the receiving account has repository access

```bash
git clone <repo-url>
git checkout claude/va-budget-reporting-discovery-6bst1o
cd va-budget-reporting/pipeline
python3 -m unittest discover -s tests -t .
```

### 5.2 If it does not — rebuild from Part 4

Create this tree and save each fenced block from Part 4 to the path in its
heading. Nothing else is needed: no dependencies, no build step, no packaging.

```
va-budget-reporting/
├── README.md
├── HANDOFF.md                     <- this document
├── discovery/
│   ├── discovery-report.md        <- Part 1
│   └── open-questions.md          <- Part 2
└── pipeline/
    ├── .gitignore
    ├── README.md                  <- Part 3.1
    ├── config/
    │   ├── reports.toml
    │   └── checks.toml
    ├── powerbi/
    │   └── CONNECTING.md          <- Part 3.2
    ├── sql/
    │   ├── 010_core.sql
    │   └── 200_marts.sql
    ├── tests/
    │   ├── __init__.py
    │   ├── test_parsers.py
    │   ├── test_loader.py
    │   └── test_end_to_end.py
    └── vabudget/
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        ├── config.py
        ├── db.py
        ├── loader.py
        ├── parsers.py
        ├── quality.py
        └── samples.py
```

The four documentation files marked above are **rendered inline** in Parts 1–3
rather than fenced, so they read as part of this document. To restore them as
standalone files, copy the relevant section and shift every heading back up by
two levels (Parts 1 and 2) or three levels (Part 3). `README.md` and every code
file appear fenced in Part 4 and can be copied verbatim.

Three details that matter when reconstructing by hand:

- `pipeline/tests/__init__.py` **must exist and must be empty**. Without it
  `unittest discover` fails with *"Start directory is not importable"*.
- Paths are resolved relative to the package, so `sql/` and `config/` must sit
  beside `vabudget/` exactly as shown.
- Run commands from inside `pipeline/`.

### 5.3 Verifying the rebuild

```bash
cd pipeline
python3 -m unittest discover -s tests -t .
```

Expect `Ran 42 tests ... OK`. Then the full round trip:

```bash
python3 -m vabudget sample --out ./inbox --start 2025-10-01 --end 2025-12-19
python3 -m vabudget ingest --inbox ./inbox
```

Expect `290 loaded, 0 already present, 0 failed, 24,226 rows staged` followed by
`All 12 checks passed.` Anything else means a file did not transfer intact.

If tests pass but counts differ, check that `config/reports.toml` and
`config/checks.toml` copied completely — a truncated TOML file often parses
without error and simply defines fewer reports or checks.

---

## Appendix — provenance and reading order

**Suggested reading order for a newcomer:** Part 0 (context and constraints) →
Part 1 §1 (what is actually wrong today) → Part 1 §3 (the ranked options) →
Part 2 (what to go and ask) → Part 3.1 (how the pipeline works) → Part 4 only
when changing code.

**How this was produced.** Public web research only; the VA intranet was not
reachable and no VA systems were accessed. Every external source is listed at
the end of Part 1. All data in the reference implementation is synthetic.
Confidence levels are recorded in §0.4 — that table is the honest summary of
what is solid and what still needs a local check.

**Anything not covered here is not known.** If a question arises that this
document does not answer, treat it as unresolved and add it to Part 2 rather
than inferring an answer from the surrounding material.
