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
