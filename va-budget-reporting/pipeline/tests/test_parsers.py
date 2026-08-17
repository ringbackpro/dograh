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
