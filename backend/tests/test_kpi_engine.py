import unittest
from datetime import datetime
from types import SimpleNamespace

from services.kpi_engine import KPIEngine


def assignment(
    *,
    quality_status: str = "PASS",
    major_error_count: int = 0,
    late_count: int = 0,
    submitted_at: datetime | None = None,
    deadline: datetime | None = None,
    quality_exception: bool = False,
    delay_exception: bool = False,
    weight: float = 1.0,
    verified: bool = True,
    ai_relevance_score: float | None = None,
):
    """Build one verified assignment for deterministic formula tests."""

    return SimpleNamespace(
        quality_status=quality_status,
        major_error_count=major_error_count,
        late_count=late_count,
        submitted_at=submitted_at,
        objective_quality_exception=quality_exception,
        objective_delay_exception=delay_exception,
        verified=verified,
        ai_relevance_score=ai_relevance_score,
        task=SimpleNamespace(
            conversion_factor_snapshot=weight,
            weight=999.0,
            deadline=deadline,
        ),
    )


class KPIEngineFormulaTest(unittest.TestCase):
    """Verify that human inputs, not AI output, determine task ratios."""

    def setUp(self):
        """Create an engine with database-dependent helpers isolated."""

        self.engine = object.__new__(KPIEngine)
        self.engine._assignment_weight = lambda item: 1.0
        self.engine._is_verified_output = lambda item: True

    def test_major_error_deducts_twenty_five_percent(self):
        """Apply one fixed quality deduction after a human PASS decision."""

        item = assignment(major_error_count=1)
        self.assertEqual(self.engine._quality_ratio([item], 1.0), 0.75)

    def test_documented_quality_exception_avoids_deduction(self):
        """Honor a previously confirmed objective quality exception."""

        item = assignment(major_error_count=2, quality_exception=True)
        self.assertEqual(self.engine._quality_ratio([item], 1.0), 1.0)

    def test_late_submission_deducts_twenty_five_percent(self):
        """Derive one late occurrence from the submitted and deadline times."""

        item = assignment(
            submitted_at=datetime(2026, 8, 2, 9),
            deadline=datetime(2026, 8, 1, 17),
        )
        self.assertEqual(self.engine._timeliness_ratio([item], 1.0), 0.75)

    def test_documented_delay_exception_avoids_deduction(self):
        """Honor a previously confirmed objective delay exception."""

        item = assignment(late_count=3, delay_exception=True)
        self.assertEqual(self.engine._timeliness_ratio([item], 1.0), 1.0)

    def test_catalog_factor_overrides_legacy_manual_weight(self):
        """Use the immutable catalog snapshot instead of the legacy task weight."""

        item = assignment(weight=12.0)
        self.assertEqual(KPIEngine._assignment_weight(self.engine, item), 12.0)

    def test_quantity_uses_converted_workload(self):
        """Count one verified factor against the total converted workload."""

        completed = assignment(weight=1.0, verified=True)
        pending = assignment(weight=9.0, verified=False)
        self.engine._assignment_weight = lambda item: item.task.conversion_factor_snapshot
        self.engine._is_verified_output = lambda item: item.verified
        result = self.engine._task_result(
            SimpleNamespace(organization_role="SPECIALIST"),
            [completed, pending],
            None,
            "2026-08",
        )
        quantity = result["breakdown"]["metrics"][0]["ratio"]
        self.assertEqual(quantity, 0.1)

    def test_quality_credit_never_becomes_negative(self):
        """Clamp repeated major-error deductions at zero."""

        item = assignment(major_error_count=10)
        self.assertEqual(self.engine._quality_ratio([item], 1.0), 0.0)

    def test_ai_relevance_does_not_change_official_quality(self):
        """Ignore AI relevance when the human verification inputs are unchanged."""

        low_ai = assignment(ai_relevance_score=20)
        high_ai = assignment(ai_relevance_score=99)
        self.assertEqual(
            self.engine._quality_ratio([low_ai], 1.0),
            self.engine._quality_ratio([high_ai], 1.0),
        )

    def test_management_result_uses_fixed_fifty_percent_rule(self):
        """Map any confirmed score below 50 to the management ratio of 50%."""

        self.assertEqual(self.engine._management_result_ratio([70, 50, 90]), 1.0)
        self.assertEqual(self.engine._management_result_ratio([70, 49.99, 90]), 0.5)

    def test_reference_thresholds_are_tracking_bands(self):
        """Preserve the approved 90/70/50 thresholds as reference levels."""

        expected = {
            90: "Mức tham chiếu 90-100",
            89.99: "Mức tham chiếu 70-89",
            70: "Mức tham chiếu 70-89",
            69.99: "Mức tham chiếu 50-69",
            50: "Mức tham chiếu 50-69",
            49.99: "Mức tham chiếu dưới 50",
        }
        for score, label in expected.items():
            self.assertEqual(self.engine.reference_level(score), label)

    def test_month_and_quarter_period_bounds(self):
        """Resolve both supported tracking period formats."""

        self.assertEqual(
            self.engine._period_bounds("2026-08"),
            (datetime(2026, 8, 1), datetime(2026, 9, 1)),
        )
        self.assertEqual(
            self.engine._period_bounds("2026-Q4"),
            (datetime(2026, 10, 1), datetime(2027, 1, 1)),
        )


if __name__ == "__main__":
    unittest.main()
