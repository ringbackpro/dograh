# Open questions

Everything here needs someone with VA intranet access and the right local
contacts. They are ordered so that the answers which could most change the plan
come first — question 1 could make most of the build unnecessary, and question 4
could invalidate an assumption the whole design rests on.

Each entry states why it matters and what changes depending on the answer,
because a question whose answer changes nothing is not worth an office's time.

---

## Priority 1 — could remove most of the work

### 1. Does FSC's Data Analytics Service already publish what you need?

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

### 2. What financial content is in CDW, and can a budget office get at it?

**Ask:** VHA Data Portal (intranet) and National Data Systems; access runs
through the **Data Access Request Tracker (DART)**.

**Specifically:** is there an IFCAP or financial domain in CDW at facility
grain? Is DART access available for operational budget management, or is it
scoped to research? What is the realistic approval timeline?

**Changes what:** a CDW route would be more durable than local extracts and
would survive the iFAMS migration better. Note that CDW is VHA-oriented and
strongest on clinical and MCA cost data — the financial-detail answer is
genuinely uncertain and worth asking rather than assuming either way.

### 3. What is the iFAMS wave date for your station?

**Ask:** FMBT programme office; your Fiscal Service chief will know the local
readiness activity.

**Specifically:** when does your facility cut over? What happens to IFCAP
locally at that point? What does budget reporting look like afterwards, and does
the FMBT Data Estate serve field users directly?

**Changes what:** everything about how much to invest in IFCAP-specific work. A
cutover 18 months out justifies Option C; a cutover in two quarters means do
Option B only and wait.

---

## Priority 2 — needed before building

### 4. Is the Status of Funds balance identity what the pipeline assumes?

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

### 5. Can the IFCAP report options be scheduled through TaskMan?

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

### 6. Where may the database live, and what does the ISSO expect?

**Ask:** local ISSO and OIT.

**Specifically:** approved storage for a database holding procurement and vendor
detail; whether a locally-managed analytic database needs any review or
registration; whether row-level security by control point or service is
expected; retention requirements.

**Changes what:** where the file goes, whether SQLite is acceptable or a managed
SQL Server is required, and how much governance overhead Phase 1 carries.

### 7. What Power BI hosting do you actually have?

**Ask:** VISN or facility Power BI/BI support.

**Specifically:** is there a workspace your office can publish to? Power BI
Service in the VA tenant, or Report Server on-prem? Is an on-premises data
gateway available for a local database? Who administers it? Are Pro licences
available for the intended readers?

**Changes what:** whether dashboards are published centrally with scheduled
refresh, or distributed as files against a shared database. Note that PBRS is
carried in the TRM as **unauthorized pending POA&M**, so do not plan on it.

---

## Priority 3 — completeness

### 8. Where do labour and payroll actuals come from?

Salary is typically the largest line in a facility budget. A dashboard without
it answers a fraction of the question. Ask Fiscal where facility-level labour
actuals now come from and at what grain and cadence.

### 9. Should MCA cost data be in scope?

Managerial Cost Accounting supports cost-per-workload views. Ask whether that is
part of the audience's question or a later phase — it is a meaningful scope
expansion, not a free addition.

### 10. Who are the readers, and what decision does each make?

Not a technical question, but the one that determines whether the dashboards get
used. Four dashboards on four cadences serve different people making different
decisions. Identify the decision each is meant to support before designing it,
or you will build a report that is admired and ignored.

### 11. Who is the second maintainer?

Name them in Phase 1, not Phase 4. The current system's core failure is that
only a few people can operate it. Rebuilding that property in a new technology
would be the most disappointing possible outcome of this work.

---

## Answers log

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
