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
