"""Tests for compliance data models.

Incidence-rate source: Cal/OSHA, Brief Guide to Recordkeeping Requirements,
2021 PDF revision, p. 5, Calculating Injury and Illness Incidence Rates:
https://www.dir.ca.gov/dosh/dosh_publications/RecKeepOverview.pdf
Additional rate examples use synthetic inputs with hand calculations below.
"""

from datetime import date

import numpy as np
import pytest

from worldenergydata.bsee.reports.comprehensive.templates.compliance_models import (
    ComplianceMetrics,
    EnvironmentalMetrics,
    ProductionQuota,
    RegulatoryMilestone,
    SafetyMetrics,
)


class TestComplianceMetrics:
    def test_defaults(self):
        c = ComplianceMetrics()
        assert c.permitted_production_bbls == 0.0
        assert c.actual_production_bbls == 0.0
        assert c.regulatory_violations == 0
        assert c.permit_status == "active"

    def test_production_compliance_percentage(self):
        c = ComplianceMetrics(
            permitted_production_bbls=10000.0,
            actual_production_bbls=8000.0,
        )
        assert c.production_compliance_percentage() == pytest.approx(80.0)

    def test_production_compliance_zero_permitted(self):
        c = ComplianceMetrics(permitted_production_bbls=0.0)
        assert c.production_compliance_percentage() == 0.0

    def test_gas_compliance_percentage(self):
        c = ComplianceMetrics(
            permitted_gas_mcf=1000.0,
            actual_gas_mcf=900.0,
        )
        assert c.gas_compliance_percentage() == pytest.approx(90.0)

    def test_is_over_production_true(self):
        c = ComplianceMetrics(
            permitted_production_bbls=1000.0,
            actual_production_bbls=1200.0,
        )
        assert c.is_over_production() is True

    def test_is_over_production_false(self):
        c = ComplianceMetrics(
            permitted_production_bbls=1000.0,
            actual_production_bbls=800.0,
        )
        assert c.is_over_production() is False

    def test_over_production_amount(self):
        c = ComplianceMetrics(
            permitted_production_bbls=1000.0,
            actual_production_bbls=1200.0,
        )
        assert c.over_production_amount() == pytest.approx(200.0)

    def test_over_production_amount_under(self):
        c = ComplianceMetrics(
            permitted_production_bbls=1000.0,
            actual_production_bbls=800.0,
        )
        assert c.over_production_amount() == 0.0

    def test_overall_compliance_status_compliant(self):
        c = ComplianceMetrics(
            permitted_production_bbls=1000.0,
            actual_production_bbls=900.0,
            regulatory_violations=0,
        )
        assert c.overall_compliance_status() == "Compliant"

    def test_overall_compliance_status_non_compliant_violations(self):
        c = ComplianceMetrics(regulatory_violations=2)
        assert c.overall_compliance_status() == "Non-Compliant"

    def test_overall_compliance_status_non_compliant_over_production(self):
        c = ComplianceMetrics(
            permitted_production_bbls=1000.0,
            actual_production_bbls=1500.0,
        )
        assert c.overall_compliance_status() == "Non-Compliant"


class TestEnvironmentalMetrics:
    def test_defaults(self):
        e = EnvironmentalMetrics()
        assert e.spill_incidents == 0
        assert e.air_emissions_tons == 0.0

    def test_calculate_environmental_score_perfect(self):
        e = EnvironmentalMetrics()
        assert e.calculate_environmental_score() == pytest.approx(1.0)

    def test_calculate_environmental_score_with_spills(self):
        e = EnvironmentalMetrics(spill_incidents=2)
        assert e.calculate_environmental_score() == pytest.approx(0.8)

    def test_calculate_environmental_score_capped_at_zero(self):
        e = EnvironmentalMetrics(
            spill_incidents=20,
            environmental_violations=10,
        )
        assert e.calculate_environmental_score() == 0.0

    def test_calculate_environmental_score_high_emissions(self):
        e = EnvironmentalMetrics(air_emissions_tons=200)
        score = e.calculate_environmental_score()
        assert score < 1.0

    def test_spill_rate_per_bbl(self):
        e = EnvironmentalMetrics(total_spill_volume_bbls=10.0)
        assert e.spill_rate_per_bbl_produced(1000.0) == pytest.approx(0.01)

    def test_spill_rate_zero_production(self):
        e = EnvironmentalMetrics(total_spill_volume_bbls=10.0)
        assert e.spill_rate_per_bbl_produced(0.0) == 0.0

    def test_environmental_status_excellent(self):
        e = EnvironmentalMetrics()
        assert e.environmental_status() == "Excellent"

    def test_environmental_status_poor(self):
        e = EnvironmentalMetrics(spill_incidents=5, environmental_violations=3)
        assert e.environmental_status() == "Poor"


class TestSafetyMetrics:
    def test_defaults(self):
        s = SafetyMetrics()
        assert s.incident_count == 0
        assert s.man_hours_worked == 0.0

    def test_calculate_trir(self):
        s = SafetyMetrics(total_recordables=5, man_hours_worked=1000000.0)
        assert s.calculate_trir() == pytest.approx(1.0)

    def test_calculate_trir_zero_hours(self):
        s = SafetyMetrics(total_recordables=5)
        with pytest.raises(ValueError, match="hours_worked"):
            s.calculate_trir()

    def test_calculate_ltir(self):
        s = SafetyMetrics(lost_time_incidents=2, man_hours_worked=1000000.0)
        assert s.calculate_ltir() == pytest.approx(0.4)

    @pytest.mark.parametrize("method", ["calculate_trir", "calculate_ltir"])
    @pytest.mark.parametrize(
        "hours", [0, -1, None, float("nan"), float("inf"), -float("inf")]
    )
    @pytest.mark.parametrize("count", [0, 7])
    def test_invalid_exposure_raises(self, method, hours, count):
        """Undefined exposure stays undefined even with no recorded cases."""
        metrics = SafetyMetrics(
            total_recordables=count, lost_time_incidents=count, man_hours_worked=hours
        )
        with pytest.raises(ValueError, match="hours_worked"):
            getattr(metrics, method)()

    @pytest.mark.parametrize("method", ["calculate_trir", "calculate_ltir"])
    @pytest.mark.parametrize(
        "count", [-1, np.int64(-1), True, False, np.bool_(True), 1.5]
    )
    def test_invalid_counts_raise(self, method, count):
        """Case counts obey the shared nonnegative-integral contract."""
        metrics = SafetyMetrics(
            total_recordables=count, lost_time_incidents=count, man_hours_worked=400_000
        )
        with pytest.raises(ValueError, match="incident_count"):
            getattr(metrics, method)()

    def test_qualified_counts_and_numpy_aggregation(self):
        """Synthetic hand calculation using the cited Cal/OSHA formula:

        7 recordables * 200,000 / 400,000 = 3.5; the chosen lost-time
        subset is 2 * 200,000 / 400,000 = 1.0. All inputs represent the
        same population and period. The unrelated incident total is 99.
        """
        from worldenergydata.hse.incidence_rate import incidence_rate

        metrics = SafetyMetrics(
            incident_count=99,
            total_recordables=np.array([4, 3], dtype=np.int64).sum(),
            lost_time_incidents=np.int64(2),
            man_hours_worked=400_000,
        )
        assert metrics.calculate_trir() == 3.5
        assert metrics.calculate_ltir() == 1.0
        assert metrics.calculate_trir() == incidence_rate(7, 400_000)
        assert metrics.calculate_ltir() == incidence_rate(2, 400_000)

    def test_zero_counts_with_positive_exposure(self):
        """Cited formula, synthetic: 0 * 200,000 / 400,000 = 0.0."""
        metrics = SafetyMetrics(man_hours_worked=400_000)
        assert metrics.calculate_trir() == 0.0
        assert metrics.calculate_ltir() == 0.0

    def test_calculate_safety_score_perfect(self):
        s = SafetyMetrics(
            safety_inspections=5,
            safety_training_hours=20.0,
        )
        score = s.calculate_safety_score()
        assert score > 0.95

    def test_calculate_safety_score_degraded(self):
        s = SafetyMetrics(incident_count=3, lost_time_incidents=1)
        score = s.calculate_safety_score()
        assert score < 0.6

    def test_safety_status_excellent(self):
        s = SafetyMetrics()
        assert s.safety_status() == "Excellent"

    def test_safety_status_poor(self):
        s = SafetyMetrics(incident_count=5, safety_violations=3)
        assert s.safety_status() == "Poor"


class TestProductionQuota:
    def test_defaults(self):
        p = ProductionQuota()
        assert p.quota_type == "monthly"
        assert p.oil_quota_bbls == 0.0

    def test_oil_compliance_percentage(self):
        p = ProductionQuota(oil_quota_bbls=10000.0, actual_oil_bbls=9000.0)
        assert p.oil_compliance_percentage() == pytest.approx(90.0)

    def test_gas_compliance_percentage(self):
        p = ProductionQuota(gas_quota_mcf=50000.0, actual_gas_mcf=40000.0)
        assert p.gas_compliance_percentage() == pytest.approx(80.0)

    def test_overall_compliance_score(self):
        p = ProductionQuota(
            oil_quota_bbls=10000.0,
            actual_oil_bbls=9000.0,
            gas_quota_mcf=50000.0,
            actual_gas_mcf=40000.0,
        )
        score = p.overall_compliance_score()
        assert 0.0 <= score <= 1.0

    def test_overall_compliance_score_zero_volumes(self):
        p = ProductionQuota(
            oil_quota_bbls=10000.0,
            gas_quota_mcf=50000.0,
        )
        score = p.overall_compliance_score()
        assert score == 0.0

    def test_is_quota_exceeded_oil(self):
        p = ProductionQuota(oil_quota_bbls=1000.0, actual_oil_bbls=1500.0)
        assert p.is_quota_exceeded() is True

    def test_is_quota_exceeded_gas(self):
        p = ProductionQuota(gas_quota_mcf=5000.0, actual_gas_mcf=6000.0)
        assert p.is_quota_exceeded() is True

    def test_is_quota_not_exceeded(self):
        p = ProductionQuota(
            oil_quota_bbls=1000.0,
            actual_oil_bbls=900.0,
            gas_quota_mcf=5000.0,
            actual_gas_mcf=4000.0,
        )
        assert p.is_quota_exceeded() is False


class TestRegulatoryMilestone:
    def test_required(self):
        m = RegulatoryMilestone(milestone_id="M-001")
        assert m.status == "pending"
        assert m.priority == "medium"

    def test_is_completed(self):
        m = RegulatoryMilestone(
            milestone_id="M-001",
            status="completed",
            completion_date=date(2024, 6, 15),
        )
        assert m.is_completed() is True

    def test_is_not_completed(self):
        m = RegulatoryMilestone(milestone_id="M-001", status="pending")
        assert m.is_completed() is False

    def test_is_overdue(self):
        m = RegulatoryMilestone(
            milestone_id="M-001",
            due_date=date(2020, 1, 1),
            status="pending",
        )
        assert m.is_overdue() is True

    def test_is_not_overdue_completed(self):
        m = RegulatoryMilestone(
            milestone_id="M-001",
            due_date=date(2020, 1, 1),
            status="completed",
            completion_date=date(2019, 12, 31),
        )
        assert m.is_overdue() is False

    def test_days_until_due(self):
        m = RegulatoryMilestone(
            milestone_id="M-001",
            due_date=date(2030, 12, 31),
        )
        assert m.days_until_due() > 0

    def test_days_until_due_no_date(self):
        m = RegulatoryMilestone(milestone_id="M-001")
        assert m.days_until_due() == 0

    def test_completion_status_completed(self):
        m = RegulatoryMilestone(
            milestone_id="M-001",
            status="completed",
            completion_date=date(2024, 1, 1),
        )
        assert m.completion_status() == "Completed"

    def test_completion_status_overdue(self):
        m = RegulatoryMilestone(
            milestone_id="M-001",
            due_date=date(2020, 1, 1),
        )
        assert m.completion_status() == "Overdue"

    def test_completion_status_pending(self):
        m = RegulatoryMilestone(
            milestone_id="M-001",
            due_date=date(2030, 12, 31),
        )
        assert m.completion_status() == "Pending"
