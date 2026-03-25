"""Tests for WellPlanningRisk dataclass and supporting enums — risk_model module."""

import pytest

from worldenergydata.well_planning.risk_model import (
    RiskAuthority,
    RiskCategory,
    RiskSeverity,
    WellPlanningRisk,
)


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def sample_risk() -> WellPlanningRisk:
    return WellPlanningRisk(
        risk_id="TEST-001",
        title="Sample risk",
        description="A test risk for unit tests.",
        category=RiskCategory.PRESSURE_MANAGEMENT,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.HIGH,
        probability=0.6,
        risk_score=3 * 0.6,
        mitigation_owner="Drilling Engineer",
        mitigation_action="Take corrective action.",
        mpd_mitigation=True,
        escalation_template="ACTION REQUIRED: resolve this risk.",
        related_wrk=["WRK-163"],
    )


# ------------------------------------------------------------------ #
# RiskAuthority enum                                                  #
# ------------------------------------------------------------------ #

class TestRiskAuthority:
    def test_has_operational(self):
        assert RiskAuthority.OPERATIONAL.value == "operational"

    def test_has_tactical(self):
        assert RiskAuthority.TACTICAL.value == "tactical"

    def test_has_strategic(self):
        assert RiskAuthority.STRATEGIC.value == "strategic"

    def test_three_members(self):
        assert len(RiskAuthority) == 3


# ------------------------------------------------------------------ #
# RiskSeverity enum                                                   #
# ------------------------------------------------------------------ #

class TestRiskSeverity:
    def test_low_is_1(self):
        assert RiskSeverity.LOW.value == 1

    def test_medium_is_2(self):
        assert RiskSeverity.MEDIUM.value == 2

    def test_high_is_3(self):
        assert RiskSeverity.HIGH.value == 3

    def test_critical_is_4(self):
        assert RiskSeverity.CRITICAL.value == 4

    def test_four_members(self):
        assert len(RiskSeverity) == 4

    def test_severity_ordering(self):
        assert RiskSeverity.LOW.value < RiskSeverity.MEDIUM.value
        assert RiskSeverity.MEDIUM.value < RiskSeverity.HIGH.value
        assert RiskSeverity.HIGH.value < RiskSeverity.CRITICAL.value


# ------------------------------------------------------------------ #
# RiskCategory enum                                                   #
# ------------------------------------------------------------------ #

class TestRiskCategory:
    def test_has_wellbore_integrity(self):
        assert RiskCategory.WELLBORE_INTEGRITY.value == "wellbore_integrity"

    def test_has_pressure_management(self):
        assert RiskCategory.PRESSURE_MANAGEMENT.value == "pressure_management"

    def test_has_hole_cleaning(self):
        assert RiskCategory.HOLE_CLEANING.value == "hole_cleaning"

    def test_has_rig_capability(self):
        assert RiskCategory.RIG_CAPABILITY.value == "rig_capability"

    def test_has_regulatory(self):
        assert RiskCategory.REGULATORY.value == "regulatory"

    def test_has_formation_evaluation(self):
        assert RiskCategory.FORMATION_EVALUATION.value == "formation_evaluation"

    def test_has_completion(self):
        assert RiskCategory.COMPLETION.value == "completion"


# ------------------------------------------------------------------ #
# WellPlanningRisk dataclass                                          #
# ------------------------------------------------------------------ #

class TestWellPlanningRisk:
    def test_risk_id_stored(self, sample_risk):
        assert sample_risk.risk_id == "TEST-001"

    def test_title_stored(self, sample_risk):
        assert sample_risk.title == "Sample risk"

    def test_description_stored(self, sample_risk):
        assert "test risk" in sample_risk.description

    def test_category_is_enum(self, sample_risk):
        assert isinstance(sample_risk.category, RiskCategory)

    def test_authority_is_enum(self, sample_risk):
        assert isinstance(sample_risk.authority, RiskAuthority)

    def test_severity_is_enum(self, sample_risk):
        assert isinstance(sample_risk.severity, RiskSeverity)

    def test_probability_range(self, sample_risk):
        assert 0.0 <= sample_risk.probability <= 1.0

    def test_risk_score_equals_severity_times_probability(self, sample_risk):
        expected = sample_risk.severity.value * sample_risk.probability
        assert abs(sample_risk.risk_score - expected) < 1e-9

    def test_mpd_mitigation_is_bool(self, sample_risk):
        assert isinstance(sample_risk.mpd_mitigation, bool)

    def test_mpd_mitigation_true(self, sample_risk):
        assert sample_risk.mpd_mitigation is True

    def test_escalation_template_non_empty(self, sample_risk):
        assert len(sample_risk.escalation_template) > 0

    def test_mitigation_owner_stored(self, sample_risk):
        assert sample_risk.mitigation_owner == "Drilling Engineer"

    def test_mitigation_action_stored(self, sample_risk):
        assert "corrective" in sample_risk.mitigation_action

    def test_related_wrk_default_is_empty_list(self):
        risk = WellPlanningRisk(
            risk_id="X-001",
            title="No WRK risk",
            description="desc",
            category=RiskCategory.REGULATORY,
            authority=RiskAuthority.STRATEGIC,
            severity=RiskSeverity.LOW,
            probability=0.1,
            risk_score=0.1,
            mitigation_owner="Manager",
            mitigation_action="action",
            mpd_mitigation=False,
            escalation_template="template",
        )
        assert risk.related_wrk == []

    def test_related_wrk_populated(self, sample_risk):
        assert "WRK-163" in sample_risk.related_wrk

    def test_risk_score_positive(self, sample_risk):
        assert sample_risk.risk_score > 0

    def test_two_risks_with_independent_related_wrk_lists(self):
        r1 = WellPlanningRisk(
            risk_id="A-001",
            title="risk 1",
            description="d",
            category=RiskCategory.COMPLETION,
            authority=RiskAuthority.TACTICAL,
            severity=RiskSeverity.MEDIUM,
            probability=0.5,
            risk_score=1.0,
            mitigation_owner="Owner",
            mitigation_action="Act",
            mpd_mitigation=False,
            escalation_template="tmpl",
        )
        r2 = WellPlanningRisk(
            risk_id="B-001",
            title="risk 2",
            description="d",
            category=RiskCategory.COMPLETION,
            authority=RiskAuthority.TACTICAL,
            severity=RiskSeverity.MEDIUM,
            probability=0.5,
            risk_score=1.0,
            mitigation_owner="Owner",
            mitigation_action="Act",
            mpd_mitigation=False,
            escalation_template="tmpl",
        )
        r1.related_wrk.append("WRK-100")
        assert r2.related_wrk == []
