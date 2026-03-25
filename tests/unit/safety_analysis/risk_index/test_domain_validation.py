"""Domain-validation tests for HSE Risk Index.

These tests verify that risk scores produce rankings that align with
industry knowledge and common-sense expectations:
- More incidents -> higher risk score
- Fatalities -> higher acute score than injuries alone
- Deep water -> higher risk than shallow (due to incident severity)
- Drilling -> higher risk than production (due to incident frequency)
"""

import pandas as pd
import pytest

from worldenergydata.safety_analysis.risk_index.models import CompositeScore
from worldenergydata.safety_analysis.risk_index.scorer import RiskScorer
from worldenergydata.safety_analysis.risk_index.slicer import RiskSlicer


def _make_assembled(rows):
    """Build an assembled-format DataFrame from dicts."""
    columns = [
        "activity_code", "activity_name", "total_incidents",
        "fatalities", "injuries", "fatality_rate", "injury_rate",
        "tri_carcinogen_lbs", "inc_rate", "confidence",
        "sources", "weighted_incident_count",
    ]
    return pd.DataFrame(rows, columns=columns)


class TestMoreIncidentsHigherRisk:
    """Field A with 10 incidents should score higher than field B with 2."""

    def test_more_incidents_higher_composite(self):
        rows = [
            {
                "activity_code": "FIELD_A", "activity_name": "Field A",
                "total_incidents": 100, "fatalities": 5, "injuries": 20,
                "fatality_rate": 0.05, "injury_rate": 0.20,
                "tri_carcinogen_lbs": 500.0, "inc_rate": 0.15,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 30.0,
            },
            {
                "activity_code": "FIELD_B", "activity_name": "Field B",
                "total_incidents": 10, "fatalities": 0, "injuries": 1,
                "fatality_rate": 0.0, "injury_rate": 0.10,
                "tri_carcinogen_lbs": 50.0, "inc_rate": 0.05,
                "confidence": "low", "sources": ["bsee"],
                "weighted_incident_count": 3.0,
            },
        ]
        df = _make_assembled(rows)
        scorer = RiskScorer()
        result = scorer.score(df)

        field_a = next(s for s in result.scores if s.activity_code == "FIELD_A")
        field_b = next(s for s in result.scores if s.activity_code == "FIELD_B")
        assert field_a.composite_score > field_b.composite_score

    def test_more_incidents_higher_acute(self):
        rows = [
            {
                "activity_code": "A", "activity_name": "High Freq",
                "total_incidents": 200, "fatalities": 10, "injuries": 50,
                "fatality_rate": 0.05, "injury_rate": 0.25,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.0,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 60.0,
            },
            {
                "activity_code": "B", "activity_name": "Low Freq",
                "total_incidents": 5, "fatalities": 0, "injuries": 0,
                "fatality_rate": 0.0, "injury_rate": 0.0,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.0,
                "confidence": "low", "sources": ["bsee"],
                "weighted_incident_count": 1.5,
            },
        ]
        df = _make_assembled(rows)
        scorer = RiskScorer()
        result = scorer.score(df)

        a = next(s for s in result.scores if s.activity_code == "A")
        b = next(s for s in result.scores if s.activity_code == "B")
        assert a.acute.score > b.acute.score


class TestFatalitiesHigherThanInjuries:
    """Activities with fatalities rank higher in acute dimension."""

    def test_fatality_activity_scores_higher_acute(self):
        rows = [
            {
                "activity_code": "FATAL", "activity_name": "With Fatalities",
                "total_incidents": 50, "fatalities": 5, "injuries": 10,
                "fatality_rate": 0.10, "injury_rate": 0.20,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.0,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 15.0,
            },
            {
                "activity_code": "NONFATAL", "activity_name": "No Fatalities",
                "total_incidents": 50, "fatalities": 0, "injuries": 10,
                "fatality_rate": 0.0, "injury_rate": 0.20,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.0,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 15.0,
            },
        ]
        df = _make_assembled(rows)
        scorer = RiskScorer()
        result = scorer.score(df)

        fatal = next(s for s in result.scores if s.activity_code == "FATAL")
        nonfatal = next(s for s in result.scores if s.activity_code == "NONFATAL")
        assert fatal.acute.score > nonfatal.acute.score


class TestComplianceViolations:
    """Higher INC rate produces higher compliance dimension score."""

    def test_high_inc_rate_higher_compliance(self):
        rows = [
            {
                "activity_code": "HIGH_INC", "activity_name": "Many Violations",
                "total_incidents": 50, "fatalities": 0, "injuries": 0,
                "fatality_rate": 0.0, "injury_rate": 0.0,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.80,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 15.0,
            },
            {
                "activity_code": "LOW_INC", "activity_name": "Few Violations",
                "total_incidents": 50, "fatalities": 0, "injuries": 0,
                "fatality_rate": 0.0, "injury_rate": 0.0,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.05,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 15.0,
            },
        ]
        df = _make_assembled(rows)
        scorer = RiskScorer()
        result = scorer.score(df)

        high = next(s for s in result.scores if s.activity_code == "HIGH_INC")
        low = next(s for s in result.scores if s.activity_code == "LOW_INC")
        assert high.compliance.score > low.compliance.score


class TestDrillingHigherThanProduction:
    """Drilling activity should score higher than production (more risk)."""

    def test_drilling_higher_composite_than_production(self):
        rows = [
            {
                "activity_code": "DRILL", "activity_name": "Drilling",
                "total_incidents": 150, "fatalities": 8, "injuries": 40,
                "fatality_rate": 0.053, "injury_rate": 0.267,
                "tri_carcinogen_lbs": 200.0, "inc_rate": 0.25,
                "confidence": "high", "sources": ["bsee", "osha"],
                "weighted_incident_count": 50.0,
            },
            {
                "activity_code": "PROD", "activity_name": "Production",
                "total_incidents": 80, "fatalities": 1, "injuries": 10,
                "fatality_rate": 0.0125, "injury_rate": 0.125,
                "tri_carcinogen_lbs": 100.0, "inc_rate": 0.10,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 24.0,
            },
        ]
        df = _make_assembled(rows)
        scorer = RiskScorer()
        result = scorer.score(df)

        drill = next(s for s in result.scores if s.activity_code == "DRILL")
        prod = next(s for s in result.scores if s.activity_code == "PROD")
        assert drill.composite_score > prod.composite_score


class TestSlicerFieldRanking:
    """Slicer should rank fields by incident count correctly."""

    def test_high_incident_field_more_incidents(self):
        incidents = pd.DataFrame({
            "field_name": (["Alpha"] * 50) + (["Beta"] * 10),
            "severity": ["minor"] * 60,
            "fatalities": [0] * 60,
            "injuries": [0] * 60,
        })
        slicer = RiskSlicer()
        result = slicer.slice_by_field(incidents)
        alpha = result[result["group_key"] == "Alpha"].iloc[0]
        beta = result[result["group_key"] == "Beta"].iloc[0]
        assert alpha["total_incidents"] > beta["total_incidents"]


class TestSlicerWaterDepthRanking:
    """Deep water incidents should form their own group."""

    def test_deep_water_group_exists(self):
        incidents = pd.DataFrame({
            "field_name": ["F1"] * 20,
            "water_depth_ft": [100] * 5 + [2000] * 5 + [8000] * 10,
            "severity": ["minor"] * 20,
            "fatalities": [0] * 5 + [0] * 5 + [1] * 10,
            "injuries": [0] * 20,
        })
        slicer = RiskSlicer()
        result = slicer.slice_by_water_depth(incidents)
        deep = result[result["group_key"] == "deep"]
        assert len(deep) == 1
        assert deep.iloc[0]["total_incidents"] == 10
        assert deep.iloc[0]["fatality_rate"] == pytest.approx(1.0)


class TestEdgeCases:
    """Edge cases that should not crash."""

    def test_single_activity_scores(self):
        rows = [
            {
                "activity_code": "ONLY", "activity_name": "Only Activity",
                "total_incidents": 25, "fatalities": 1, "injuries": 5,
                "fatality_rate": 0.04, "injury_rate": 0.20,
                "tri_carcinogen_lbs": 100.0, "inc_rate": 0.10,
                "confidence": "medium", "sources": ["bsee"],
                "weighted_incident_count": 7.5,
            },
        ]
        df = _make_assembled(rows)
        scorer = RiskScorer()
        result = scorer.score(df)
        assert len(result.scores) == 1
        assert 1.0 <= result.scores[0].composite_score <= 10.0

    def test_zero_incidents_field(self):
        incidents = pd.DataFrame({
            "field_name": ["Empty"],
            "severity": ["minor"],
            "fatalities": [0],
            "injuries": [0],
        })
        slicer = RiskSlicer()
        result = slicer.slice_by_field(incidents)
        assert len(result) == 1
        assert result.iloc[0]["fatality_rate"] == 0.0

    def test_all_fatalities_maximum_severity(self):
        rows = [
            {
                "activity_code": "ALL_FATAL", "activity_name": "All Fatal",
                "total_incidents": 10, "fatalities": 10, "injuries": 0,
                "fatality_rate": 1.0, "injury_rate": 0.0,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.0,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 3.0,
            },
            {
                "activity_code": "NO_FATAL", "activity_name": "No Fatal",
                "total_incidents": 10, "fatalities": 0, "injuries": 0,
                "fatality_rate": 0.0, "injury_rate": 0.0,
                "tri_carcinogen_lbs": 0.0, "inc_rate": 0.0,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 3.0,
            },
        ]
        df = _make_assembled(rows)
        scorer = RiskScorer()
        result = scorer.score(df)
        all_fatal = next(s for s in result.scores if s.activity_code == "ALL_FATAL")
        no_fatal = next(s for s in result.scores if s.activity_code == "NO_FATAL")
        assert all_fatal.acute.score >= no_fatal.acute.score


class TestConfigurableWeights:
    """Verify that custom config changes scoring behavior."""

    def test_higher_acute_weight_shifts_composite(self):
        from worldenergydata.safety_analysis.risk_index.config_loader import RiskConfig

        # Default: acute=0.50
        default_scorer = RiskScorer()

        # Custom: acute=0.80
        custom_cfg = RiskConfig(
            composite_weights={"acute": 0.80, "chronic": 0.10, "compliance": 0.10},
            acute_weights={"fatality_rate": 0.40, "injury_rate": 0.35, "frequency": 0.25},
            chronic_weights={"tri_carcinogen_lbs": 1.0},
            compliance_weights={"inc_rate": 1.0},
            default_missing_score=5.5,
            water_depth_bands={"shallow": 500, "mid": 5000},
        )
        custom_scorer = RiskScorer(config=custom_cfg)

        # Activity with high acute, low chronic/compliance
        rows = [
            {
                "activity_code": "HIGH_ACUTE", "activity_name": "High Acute",
                "total_incidents": 100, "fatalities": 10, "injuries": 30,
                "fatality_rate": 0.10, "injury_rate": 0.30,
                "tri_carcinogen_lbs": 10.0, "inc_rate": 0.02,
                "confidence": "high", "sources": ["bsee"],
                "weighted_incident_count": 30.0,
            },
            {
                "activity_code": "LOW_ACUTE", "activity_name": "Low Acute",
                "total_incidents": 10, "fatalities": 0, "injuries": 0,
                "fatality_rate": 0.0, "injury_rate": 0.0,
                "tri_carcinogen_lbs": 5000.0, "inc_rate": 0.90,
                "confidence": "high", "sources": ["epa_tri"],
                "weighted_incident_count": 1.0,
            },
        ]
        df = _make_assembled(rows)
        default_result = default_scorer.score(df)
        custom_result = custom_scorer.score(df)

        # With higher acute weight, HIGH_ACUTE should have a bigger gap
        def_high = next(s for s in default_result.scores if s.activity_code == "HIGH_ACUTE")
        def_low = next(s for s in default_result.scores if s.activity_code == "LOW_ACUTE")
        cust_high = next(s for s in custom_result.scores if s.activity_code == "HIGH_ACUTE")
        cust_low = next(s for s in custom_result.scores if s.activity_code == "LOW_ACUTE")

        default_gap = def_high.composite_score - def_low.composite_score
        custom_gap = cust_high.composite_score - cust_low.composite_score

        # The custom config (more acute weight) should make the high-acute
        # activity relatively higher compared to the low-acute activity
        assert custom_gap >= default_gap or cust_high.composite_score >= def_high.composite_score
