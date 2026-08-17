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
