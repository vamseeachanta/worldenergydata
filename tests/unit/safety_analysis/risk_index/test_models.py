"""Tests for safety analysis risk index models."""

import pytest
from pydantic import ValidationError

from worldenergydata.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    DimensionScore,
    RiskCategory,
)


class TestRiskCategory:
    def test_low(self):
        assert RiskCategory.from_score(1.0) == RiskCategory.LOW
        assert RiskCategory.from_score(3.0) == RiskCategory.LOW

    def test_medium(self):
        assert RiskCategory.from_score(3.1) == RiskCategory.MEDIUM
        assert RiskCategory.from_score(5.0) == RiskCategory.MEDIUM

    def test_high(self):
        assert RiskCategory.from_score(5.1) == RiskCategory.HIGH
        assert RiskCategory.from_score(7.0) == RiskCategory.HIGH

    def test_critical(self):
        assert RiskCategory.from_score(7.1) == RiskCategory.CRITICAL
        assert RiskCategory.from_score(10.0) == RiskCategory.CRITICAL

    def test_below_range(self):
        with pytest.raises(ValueError, match="between 1.0 and 10.0"):
            RiskCategory.from_score(0.5)

    def test_above_range(self):
        with pytest.raises(ValueError, match="between 1.0 and 10.0"):
            RiskCategory.from_score(10.5)


class TestDimensionScore:
    def test_valid(self):
        d = DimensionScore(
            dimension="acute",
            raw_metrics={"incident_rate": 0.05},
            score=3.5,
        )
        assert d.dimension == "acute"
        assert d.score == 3.5
        assert d.subscores == {}

    def test_with_subscores(self):
        d = DimensionScore(
            dimension="chronic",
            raw_metrics={"fatigue_hours": 120},
            score=6.0,
            subscores={"fatigue": 7.0, "exposure": 5.0},
        )
        assert d.subscores["fatigue"] == 7.0

    def test_score_too_low(self):
        with pytest.raises(ValidationError):
            DimensionScore(
                dimension="acute",
                raw_metrics={},
                score=0.5,
            )

    def test_score_too_high(self):
        with pytest.raises(ValidationError):
            DimensionScore(
                dimension="acute",
                raw_metrics={},
                score=10.5,
            )


def _make_dimension(dim_name: str, score: float) -> DimensionScore:
    return DimensionScore(
        dimension=dim_name,
        raw_metrics={"m": 1},
        score=score,
    )


class TestActivityRiskScore:
    def test_auto_category_low(self):
        a = ActivityRiskScore(
            activity_code="DRILL",
            activity_name="Drilling",
            acute=_make_dimension("acute", 2.0),
            chronic=_make_dimension("chronic", 1.5),
            compliance=_make_dimension("compliance", 1.0),
            composite_score=2.0,
            incident_count=5,
            confidence="high",
        )
        assert a.category == RiskCategory.LOW

    def test_auto_category_critical(self):
        a = ActivityRiskScore(
            activity_code="HOT",
            activity_name="Hot Work",
            acute=_make_dimension("acute", 9.0),
            chronic=_make_dimension("chronic", 8.0),
            compliance=_make_dimension("compliance", 7.5),
            composite_score=8.5,
            incident_count=42,
            confidence="high",
        )
        assert a.category == RiskCategory.CRITICAL

    def test_confidence_validation(self):
        with pytest.raises(ValidationError, match="confidence"):
            ActivityRiskScore(
                activity_code="X",
                activity_name="X",
                acute=_make_dimension("acute", 5.0),
                chronic=_make_dimension("chronic", 5.0),
                compliance=_make_dimension("compliance", 5.0),
                composite_score=5.0,
                incident_count=0,
                confidence="very_high",
            )

    def test_sources(self):
        a = ActivityRiskScore(
            activity_code="LIFT",
            activity_name="Lifting",
            acute=_make_dimension("acute", 4.0),
            chronic=_make_dimension("chronic", 3.0),
            compliance=_make_dimension("compliance", 3.5),
            composite_score=3.5,
            incident_count=10,
            confidence="medium",
            sources=["bsee", "internal"],
        )
        assert a.sources == ["bsee", "internal"]

    def test_negative_incident_count(self):
        with pytest.raises(ValidationError):
            ActivityRiskScore(
                activity_code="X",
                activity_name="X",
                acute=_make_dimension("acute", 5.0),
                chronic=_make_dimension("chronic", 5.0),
                compliance=_make_dimension("compliance", 5.0),
                composite_score=5.0,
                incident_count=-1,
                confidence="low",
            )


class TestCompositeScore:
    def test_defaults(self):
        c = CompositeScore()
        assert c.scores == []
        assert c.metadata == {}
        assert c.generated_at is not None

    def test_with_scores(self):
        score = ActivityRiskScore(
            activity_code="DRILL",
            activity_name="Drilling",
            acute=_make_dimension("acute", 5.0),
            chronic=_make_dimension("chronic", 4.0),
            compliance=_make_dimension("compliance", 3.0),
            composite_score=4.0,
            incident_count=20,
            confidence="medium",
        )
        c = CompositeScore(
            scores=[score],
            metadata={"version": "1.0"},
        )
        assert len(c.scores) == 1
        assert c.scores[0].category == RiskCategory.MEDIUM
        assert c.metadata["version"] == "1.0"
