"""Tests for WellPlanningRiskAnalyzer — risk_analyzer module."""

import pytest
import pandas as pd

from worldenergydata.well_planning.risk_model import (
    RiskAuthority,
    RiskCategory,
    RiskSeverity,
    WellPlanningRisk,
)
from worldenergydata.well_planning.risk_analyzer import WellPlanningRiskAnalyzer
from worldenergydata.well_planning.risk_registry import WELL_PLANNING_RISKS


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

def _make_risk(
    risk_id: str,
    authority: RiskAuthority,
    category: RiskCategory,
    severity: RiskSeverity,
    probability: float,
    mpd_mitigation: bool = False,
) -> WellPlanningRisk:
    return WellPlanningRisk(
        risk_id=risk_id,
        title=f"Risk {risk_id}",
        description="desc",
        category=category,
        authority=authority,
        severity=severity,
        probability=probability,
        risk_score=severity.value * probability,
        mitigation_owner="Engineer",
        mitigation_action="action",
        mpd_mitigation=mpd_mitigation,
        escalation_template=f"Template for {risk_id}",
    )


@pytest.fixture
def custom_risks() -> list[WellPlanningRisk]:
    return [
        _make_risk("C-001", RiskAuthority.OPERATIONAL, RiskCategory.PRESSURE_MANAGEMENT,
                   RiskSeverity.HIGH, 0.8, mpd_mitigation=True),
        _make_risk("C-002", RiskAuthority.TACTICAL, RiskCategory.WELLBORE_INTEGRITY,
                   RiskSeverity.MEDIUM, 0.5),
        _make_risk("C-003", RiskAuthority.STRATEGIC, RiskCategory.RIG_CAPABILITY,
                   RiskSeverity.CRITICAL, 0.4, mpd_mitigation=True),
        _make_risk("C-004", RiskAuthority.OPERATIONAL, RiskCategory.HOLE_CLEANING,
                   RiskSeverity.LOW, 0.3),
        _make_risk("C-005", RiskAuthority.STRATEGIC, RiskCategory.REGULATORY,
                   RiskSeverity.MEDIUM, 0.6, mpd_mitigation=True),
    ]


@pytest.fixture
def default_analyzer() -> WellPlanningRiskAnalyzer:
    return WellPlanningRiskAnalyzer()


@pytest.fixture
def custom_analyzer(custom_risks) -> WellPlanningRiskAnalyzer:
    return WellPlanningRiskAnalyzer(risks=custom_risks)


# ------------------------------------------------------------------ #
# Constructor                                                         #
# ------------------------------------------------------------------ #

class TestConstructor:
    def test_default_uses_registry(self, default_analyzer):
        assert len(default_analyzer._risks) == len(WELL_PLANNING_RISKS)

    def test_custom_risks_list_used_when_provided(self, custom_analyzer, custom_risks):
        assert len(custom_analyzer._risks) == len(custom_risks)

    def test_empty_list_accepted(self):
        analyzer = WellPlanningRiskAnalyzer(risks=[])
        assert analyzer._risks == []


# ------------------------------------------------------------------ #
# get_by_authority                                                    #
# ------------------------------------------------------------------ #

class TestGetByAuthority:
    def test_strategic_returns_non_empty_from_default(self, default_analyzer):
        result = default_analyzer.get_by_authority(RiskAuthority.STRATEGIC)
        assert len(result) > 0

    def test_operational_returns_non_empty_from_default(self, default_analyzer):
        result = default_analyzer.get_by_authority(RiskAuthority.OPERATIONAL)
        assert len(result) > 0

    def test_tactical_returns_non_empty_from_default(self, default_analyzer):
        result = default_analyzer.get_by_authority(RiskAuthority.TACTICAL)
        assert len(result) > 0

    def test_all_returned_have_correct_authority(self, custom_analyzer):
        result = custom_analyzer.get_by_authority(RiskAuthority.STRATEGIC)
        for risk in result:
            assert risk.authority == RiskAuthority.STRATEGIC

    def test_count_matches_custom_fixture(self, custom_analyzer):
        strategic = custom_analyzer.get_by_authority(RiskAuthority.STRATEGIC)
        assert len(strategic) == 2


# ------------------------------------------------------------------ #
# get_by_category                                                     #
# ------------------------------------------------------------------ #

class TestGetByCategory:
    def test_pressure_management_non_empty_from_default(self, default_analyzer):
        result = default_analyzer.get_by_category(RiskCategory.PRESSURE_MANAGEMENT)
        assert len(result) > 0

    def test_rig_capability_non_empty_from_default(self, default_analyzer):
        result = default_analyzer.get_by_category(RiskCategory.RIG_CAPABILITY)
        assert len(result) > 0

    def test_all_returned_have_correct_category(self, custom_analyzer):
        result = custom_analyzer.get_by_category(RiskCategory.WELLBORE_INTEGRITY)
        for risk in result:
            assert risk.category == RiskCategory.WELLBORE_INTEGRITY

    def test_count_for_custom_fixture(self, custom_analyzer):
        result = custom_analyzer.get_by_category(RiskCategory.PRESSURE_MANAGEMENT)
        assert len(result) == 1


# ------------------------------------------------------------------ #
# get_by_severity                                                     #
# ------------------------------------------------------------------ #

class TestGetBySeverity:
    def test_returns_all_for_low_threshold(self, custom_analyzer):
        result = custom_analyzer.get_by_severity(RiskSeverity.LOW)
        assert len(result) == 5

    def test_filters_correctly_for_high_threshold(self, custom_analyzer):
        result = custom_analyzer.get_by_severity(RiskSeverity.HIGH)
        for risk in result:
            assert risk.severity.value >= RiskSeverity.HIGH.value

    def test_critical_only_includes_critical(self, custom_analyzer):
        result = custom_analyzer.get_by_severity(RiskSeverity.CRITICAL)
        assert all(r.severity == RiskSeverity.CRITICAL for r in result)
        assert len(result) == 1


# ------------------------------------------------------------------ #
# high_priority_risks                                                 #
# ------------------------------------------------------------------ #

class TestHighPriorityRisks:
    def test_default_threshold_filters_correctly(self, custom_analyzer):
        result = custom_analyzer.high_priority_risks(threshold=2.0)
        for risk in result:
            assert risk.risk_score >= 2.0

    def test_results_sorted_descending(self, custom_analyzer):
        result = custom_analyzer.high_priority_risks(threshold=0.0)
        scores = [r.risk_score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_high_threshold_returns_fewer_risks(self, default_analyzer):
        low = default_analyzer.high_priority_risks(threshold=0.5)
        high = default_analyzer.high_priority_risks(threshold=3.0)
        assert len(high) <= len(low)

    def test_threshold_2_from_custom(self, custom_analyzer):
        # C-001: 3*0.8=2.4, C-003: 4*0.4=1.6, C-005: 2*0.6=1.2
        # Only C-001 (2.4) and nothing else >= 2.0 ... C-003=1.6 < 2.0
        result = custom_analyzer.high_priority_risks(threshold=2.0)
        ids = {r.risk_id for r in result}
        assert "C-001" in ids
        assert "C-004" not in ids


# ------------------------------------------------------------------ #
# mpd_mitigable_risks                                                 #
# ------------------------------------------------------------------ #

class TestMPDMitigableRisks:
    def test_returns_at_least_three_from_default(self, default_analyzer):
        result = default_analyzer.mpd_mitigable_risks()
        assert len(result) >= 3

    def test_all_returned_have_mpd_mitigation_true(self, default_analyzer):
        result = default_analyzer.mpd_mitigable_risks()
        for risk in result:
            assert risk.mpd_mitigation is True

    def test_count_from_custom_fixture(self, custom_analyzer):
        result = custom_analyzer.mpd_mitigable_risks()
        assert len(result) == 3


# ------------------------------------------------------------------ #
# risk_matrix                                                         #
# ------------------------------------------------------------------ #

class TestRiskMatrix:
    def test_returns_dataframe(self, default_analyzer):
        result = default_analyzer.risk_matrix()
        assert isinstance(result, pd.DataFrame)

    def test_index_contains_authority_values(self, default_analyzer):
        result = default_analyzer.risk_matrix()
        for auth in RiskAuthority:
            assert auth.value in result.index

    def test_columns_contain_category_values(self, default_analyzer):
        result = default_analyzer.risk_matrix()
        for cat in RiskCategory:
            assert cat.value in result.columns

    def test_cell_values_are_non_negative(self, default_analyzer):
        result = default_analyzer.risk_matrix()
        assert (result >= 0).all().all()

    def test_total_count_equals_registry_size(self, default_analyzer):
        result = default_analyzer.risk_matrix()
        assert result.values.sum() == len(WELL_PLANNING_RISKS)


# ------------------------------------------------------------------ #
# escalation_report                                                   #
# ------------------------------------------------------------------ #

class TestEscalationReport:
    def test_strategic_returns_non_empty_string(self, default_analyzer):
        result = default_analyzer.escalation_report(RiskAuthority.STRATEGIC)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_report_contains_authority_label(self, default_analyzer):
        result = default_analyzer.escalation_report(RiskAuthority.STRATEGIC)
        assert "STRATEGIC" in result.upper()

    def test_report_contains_risk_ids(self, default_analyzer):
        result = default_analyzer.escalation_report(RiskAuthority.STRATEGIC)
        strategic = default_analyzer.get_by_authority(RiskAuthority.STRATEGIC)
        for risk in strategic:
            assert risk.risk_id in result

    def test_empty_analyzer_returns_empty_string(self):
        analyzer = WellPlanningRiskAnalyzer(risks=[])
        result = analyzer.escalation_report(RiskAuthority.OPERATIONAL)
        assert result == ""

    def test_operational_report_non_empty(self, default_analyzer):
        result = default_analyzer.escalation_report(RiskAuthority.OPERATIONAL)
        assert len(result) > 0


# ------------------------------------------------------------------ #
# summary                                                             #
# ------------------------------------------------------------------ #

class TestSummary:
    def test_returns_dataframe(self, default_analyzer):
        result = default_analyzer.summary()
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, default_analyzer):
        result = default_analyzer.summary()
        required = {"risk_id", "title", "authority", "severity", "risk_score",
                    "mitigation_owner"}
        assert required.issubset(set(result.columns))

    def test_sorted_by_risk_score_descending(self, default_analyzer):
        result = default_analyzer.summary()
        scores = result["risk_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_row_count_matches_registry(self, default_analyzer):
        result = default_analyzer.summary()
        assert len(result) == len(WELL_PLANNING_RISKS)

    def test_empty_risks_returns_empty_dataframe(self):
        analyzer = WellPlanningRiskAnalyzer(risks=[])
        result = analyzer.summary()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_authority_column_contains_string_values(self, default_analyzer):
        result = default_analyzer.summary()
        assert result["authority"].dtype == object
