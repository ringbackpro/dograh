"""Assemble ../HANDOFF.md, the standalone export of this whole directory.

The handoff document embeds copies of the discovery write-ups and every source
file. Generating it rather than maintaining it by hand is the point: edit the
real files, re-run this, and the export cannot drift from what it describes.

    python3 handoff/build.py

Section text that exists only in the export -- the instructions for a receiving
account, and the rebuild guide -- lives in _intro.md and _rebuild.md beside this
script.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRATCH = HERE
OUT = ROOT / "HANDOFF.md"

FENCE_LANG = {".py": "python", ".sql": "sql", ".toml": "toml", ".md": "markdown"}


def demote(text: str, levels: int = 1) -> str:
    """Add `levels` to every markdown heading, skipping fenced code blocks."""
    out, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("#"):
            line = "#" * levels + line
        out.append(line)
    return "\n".join(out)


def embed_doc(path: Path, levels: int = 1) -> str:
    """Inline a markdown file as flowing content, with its headings demoted."""
    return demote(path.read_text(encoding="utf-8").rstrip(), levels)


def embed_code(path: Path) -> str:
    """Inline a source file inside a fence, labelled with its repo-relative path."""
    rel = path.relative_to(ROOT)
    body = path.read_text(encoding="utf-8").rstrip("\n")
    lang = FENCE_LANG.get(path.suffix, "text")
    if not body:
        body = "# (intentionally empty - marks tests/ as a package)"
    # Markdown contains its own 3-backtick fences, so wrap it in four.
    fence = "````" if path.suffix == ".md" else "```"
    return f"#### `{rel}`\n\n{fence}{lang}\n{body}\n{fence}"


# Order matters: it is the reading order of the finished document.
CODE_FILES = [
    ("Package", ["pipeline/vabudget/__init__.py", "pipeline/vabudget/__main__.py"]),
    ("Configuration loading", ["pipeline/vabudget/config.py"]),
    ("Parsing", ["pipeline/vabudget/parsers.py"]),
    ("Database and schema", ["pipeline/vabudget/db.py"]),
    ("Ingest orchestration", ["pipeline/vabudget/loader.py"]),
    ("Data quality", ["pipeline/vabudget/quality.py"]),
    ("Sample data generator", ["pipeline/vabudget/samples.py"]),
    ("Command line interface", ["pipeline/vabudget/cli.py"]),
    ("SQL — core schema", ["pipeline/sql/010_core.sql"]),
    ("SQL — conformed mart", ["pipeline/sql/200_marts.sql"]),
    ("Configuration — report catalogue", ["pipeline/config/reports.toml"]),
    ("Configuration — data-quality rulebook", ["pipeline/config/checks.toml"]),
    ("Tests", [
        "pipeline/tests/__init__.py",
        "pipeline/tests/test_parsers.py",
        "pipeline/tests/test_loader.py",
        "pipeline/tests/test_end_to_end.py",
    ]),
    ("Repository hygiene", ["pipeline/.gitignore"]),
    ("Project README", ["README.md"]),
]

parts = [SCRATCH.joinpath("_intro.md").read_text(encoding="utf-8").rstrip()]

parts.append("## Part 1 — Discovery report\n\n" + embed_doc(ROOT / "discovery/discovery-report.md", 2))
parts.append("---\n\n## Part 2 — Open questions\n\n" + embed_doc(ROOT / "discovery/open-questions.md", 2))

parts.append(
    "---\n\n## Part 3 — Reference pipeline documentation\n\n"
    "### 3.1 Pipeline README\n\n" + embed_doc(ROOT / "pipeline/README.md", 3)
    + "\n\n---\n\n### 3.2 Connecting Power BI\n\n"
    + embed_doc(ROOT / "pipeline/powerbi/CONNECTING.md", 3)
)

code_sections = ["---\n\n## Part 4 — Complete source code\n"]
code_sections.append(
    "Every file of the reference implementation, in reading order. Each block is\n"
    "headed by its path relative to the project root. Part 5 explains how to turn\n"
    "these back into a working tree.\n"
)
for heading, files in CODE_FILES:
    code_sections.append(f"### {heading}\n")
    for rel in files:
        code_sections.append(embed_code(ROOT / rel) + "\n")
parts.append("\n".join(code_sections))

parts.append((SCRATCH / "_rebuild.md").read_text(encoding="utf-8").rstrip())

OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT.parent)} "
      f"({len(OUT.read_text(encoding='utf-8').splitlines()):,} lines)")
