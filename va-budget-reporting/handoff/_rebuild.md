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
