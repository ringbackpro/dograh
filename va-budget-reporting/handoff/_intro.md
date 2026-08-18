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
