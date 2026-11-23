"""Tests for the built-in well planning risk registry — risk_registry module."""

import pytest

from worldenergydata.well_planning.risk_model import (
    RiskAuthority,
    RiskCategory,
    RiskSeverity,
    WellPlanningRisk,
)
from worldenergydata.well_planning.risk_registry import WELL_PLANNING_RISKS


class TestRegistrySize:
    def test_registry_has_at_least_20_entries(self):
        assert len(WELL_PLANNING_RISKS) >= 20

    def test_all_entries_are_well_planning_risk_instances(self):
        for risk in WELL_PLANNING_RISKS:
            assert isinstance(risk, WellPlanningRisk)


class TestAuthorityRepresentation:
    def test_operational_risks_present(self):
        authorities = {r.authority for r in WELL_PLANNING_RISKS}
        assert RiskAuthority.OPERATIONAL in authorities

    def test_tactical_risks_present(self):
        authorities = {r.authority for r in WELL_PLANNING_RISKS}
        assert RiskAuthority.TACTICAL in authorities

    def test_strategic_risks_present(self):
        authorities = {r.authority for r in WELL_PLANNING_RISKS}
        assert RiskAuthority.STRATEGIC in authorities

    def test_all_three_authority_levels_present(self):
        authorities = {r.authority for r in WELL_PLANNING_RISKS}
        assert authorities == set(RiskAuthority)


class TestRiskIdFormat:
    def test_all_risk_ids_start_with_a_letter(self):
        for risk in WELL_PLANNING_RISKS:
            assert risk.risk_id[
                0
            ].isalpha(), f"risk_id '{risk.risk_id}' does not start with a letter"

    def test_all_risk_ids_are_non_empty(self):
        for risk in WELL_PLANNING_RISKS:
            assert len(risk.risk_id) > 0

    def test_all_risk_ids_are_unique(self):
        ids = [r.risk_id for r in WELL_PLANNING_RISKS]
        assert len(ids) == len(set(ids))


class TestMPDMitigation:
    def test_at_least_three_mpd_mitigable_risks(self):
        mpd_risks = [r for r in WELL_PLANNING_RISKS if r.mpd_mitigation]
        assert len(mpd_risks) >= 3

    def test_mpd_mitigation_is_bool_for_all(self):
        for risk in WELL_PLANNING_RISKS:
            assert isinstance(risk.mpd_mitigation, bool)


class TestStrategicRisks:
    def test_strategic_risks_include_rig_capability(self):
        strategic = [
            r for r in WELL_PLANNING_RISKS if r.authority == RiskAuthority.STRATEGIC
        ]
        categories = {r.category for r in strategic}
        assert RiskCategory.RIG_CAPABILITY in categories

    def test_strategic_risks_include_regulatory(self):
        strategic = [
            r for r in WELL_PLANNING_RISKS if r.authority == RiskAuthority.STRATEGIC
        ]
        categories = {r.category for r in strategic}
        assert RiskCategory.REGULATORY in categories


class TestRiskScores:
    def test_all_risk_scores_are_positive(self):
        for risk in WELL_PLANNING_RISKS:
            assert (
                risk.risk_score > 0
            ), f"risk {risk.risk_id} has non-positive score {risk.risk_score}"

    def test_risk_scores_match_severity_times_probability(self):
        for risk in WELL_PLANNING_RISKS:
            expected = risk.severity.value * risk.probability
            assert abs(risk.risk_score - expected) < 1e-9, (
                f"risk {risk.risk_id}: score {risk.risk_score} "
                f"!= {risk.severity.value} * {risk.probability}"
            )

    def test_probabilities_in_valid_range(self):
        for risk in WELL_PLANNING_RISKS:
            assert (
                0.0 <= risk.probability <= 1.0
            ), f"risk {risk.risk_id} probability {risk.probability} out of range"


class TestEscalationTemplates:
    def test_all_escalation_templates_non_empty(self):
        for risk in WELL_PLANNING_RISKS:
            assert (
                len(risk.escalation_template) > 0
            ), f"risk {risk.risk_id} has empty escalation_template"

    def test_strategic_escalation_templates_mention_escalation(self):
        strategic = [
            r for r in WELL_PLANNING_RISKS if r.authority == RiskAuthority.STRATEGIC
        ]
        for risk in strategic:
            assert (
                "ESCALATION" in risk.escalation_template.upper()
            ), f"strategic risk {risk.risk_id} template lacks ESCALATION keyword"


class TestMitigationOwners:
    def test_all_mitigation_owners_non_empty(self):
        for risk in WELL_PLANNING_RISKS:
            assert len(risk.mitigation_owner) > 0


class TestCategoryPresence:
    def test_pressure_management_risks_present(self):
        cats = {r.category for r in WELL_PLANNING_RISKS}
        assert RiskCategory.PRESSURE_MANAGEMENT in cats

    def test_wellbore_integrity_risks_present(self):
        cats = {r.category for r in WELL_PLANNING_RISKS}
        assert RiskCategory.WELLBORE_INTEGRITY in cats
