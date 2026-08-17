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
