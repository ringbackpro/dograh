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
