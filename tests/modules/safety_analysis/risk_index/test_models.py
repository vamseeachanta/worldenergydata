"""Tests for HSE Risk Index models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from worldenergydata.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    DimensionScore,
    RiskCategory,
)


class TestRiskCategory:
    """Tests for RiskCategory enum and from_score classmethod."""

    def test_low_range(self):
        assert RiskCategory.from_score(1.0) == RiskCategory.LOW
        assert RiskCategory.from_score(2.5) == RiskCategory.LOW
        assert RiskCategory.from_score(3.0) == RiskCategory.LOW

    def test_medium_range(self):
        assert RiskCategory.from_score(3.1) == RiskCategory.MEDIUM
        assert RiskCategory.from_score(4.0) == RiskCategory.MEDIUM
        assert RiskCategory.from_score(5.0) == RiskCategory.MEDIUM

    def test_high_range(self):
        assert RiskCategory.from_score(5.1) == RiskCategory.HIGH
        assert RiskCategory.from_score(6.0) == RiskCategory.HIGH
        assert RiskCategory.from_score(7.0) == RiskCategory.HIGH

    def test_critical_range(self):
        assert RiskCategory.from_score(7.1) == RiskCategory.CRITICAL
        assert RiskCategory.from_score(8.0) == RiskCategory.CRITICAL
        assert RiskCategory.from_score(9.5) == RiskCategory.CRITICAL
        assert RiskCategory.from_score(10.0) == RiskCategory.CRITICAL

    def test_boundary_low_medium(self):
        """3.0 is LOW, 3.1 is MEDIUM."""
        assert RiskCategory.from_score(3.0) == RiskCategory.LOW
        assert RiskCategory.from_score(3.1) == RiskCategory.MEDIUM

    def test_boundary_medium_high(self):
        """5.0 is MEDIUM, 5.1 is HIGH."""
        assert RiskCategory.from_score(5.0) == RiskCategory.MEDIUM
        assert RiskCategory.from_score(5.1) == RiskCategory.HIGH

    def test_boundary_high_critical(self):
        """7.0 is HIGH, 7.1 is CRITICAL."""
        assert RiskCategory.from_score(7.0) == RiskCategory.HIGH
        assert RiskCategory.from_score(7.1) == RiskCategory.CRITICAL

    def test_exact_boundaries(self):
        """Exact integer boundaries."""
        assert RiskCategory.from_score(1.0) == RiskCategory.LOW
        assert RiskCategory.from_score(10.0) == RiskCategory.CRITICAL

    def test_score_below_range_raises(self):
        with pytest.raises(ValueError, match="Score must be between 1.0 and 10.0"):
            RiskCategory.from_score(0.5)

    def test_score_above_range_raises(self):
        with pytest.raises(ValueError, match="Score must be between 1.0 and 10.0"):
            RiskCategory.from_score(10.5)

    def test_enum_values(self):
        assert RiskCategory.LOW.value == "low"
        assert RiskCategory.MEDIUM.value == "medium"
        assert RiskCategory.HIGH.value == "high"
        assert RiskCategory.CRITICAL.value == "critical"


class TestDimensionScore:
    """Tests for DimensionScore Pydantic model."""

    def test_create_minimal(self):
        ds = DimensionScore(
            dimension="acute",
            raw_metrics={"fatality_rate": 0.05},
            score=5.0,
        )
        assert ds.dimension == "acute"
        assert ds.score == 5.0
        assert ds.subscores == {}

    def test_create_full(self):
        ds = DimensionScore(
            dimension="chronic",
            raw_metrics={"injury_rate": 12.3, "dart_rate": 4.1},
            score=7.5,
            subscores={"injury_sub": 8.0, "dart_sub": 7.0},
        )
        assert ds.raw_metrics["injury_rate"] == 12.3
        assert ds.subscores["injury_sub"] == 8.0

    def test_score_minimum_boundary(self):
        ds = DimensionScore(
            dimension="compliance",
            raw_metrics={},
            score=1.0,
        )
        assert ds.score == 1.0

    def test_score_maximum_boundary(self):
        ds = DimensionScore(
            dimension="compliance",
            raw_metrics={},
            score=10.0,
        )
        assert ds.score == 10.0

    def test_score_below_minimum_fails(self):
        with pytest.raises(ValidationError, match="score"):
            DimensionScore(
                dimension="acute",
                raw_metrics={},
                score=0.5,
            )

    def test_score_above_maximum_fails(self):
        with pytest.raises(ValidationError, match="score"):
            DimensionScore(
                dimension="acute",
                raw_metrics={},
                score=10.5,
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            DimensionScore(score=5.0)

    def test_empty_raw_metrics_allowed(self):
        ds = DimensionScore(
            dimension="acute",
            raw_metrics={},
            score=5.0,
        )
        assert ds.raw_metrics == {}


class TestActivityRiskScore:
    """Tests for ActivityRiskScore Pydantic model."""

    @pytest.fixture()
    def sample_dimension(self):
        return DimensionScore(
            dimension="acute",
            raw_metrics={"fatality_rate": 0.05},
            score=5.0,
        )

    @pytest.fixture()
    def low_dimension(self):
        return DimensionScore(
            dimension="test",
            raw_metrics={},
            score=2.0,
        )

    @pytest.fixture()
    def critical_dimension(self):
        return DimensionScore(
            dimension="test",
            raw_metrics={},
            score=9.0,
        )

    def test_create_with_auto_category(self, sample_dimension):
        ars = ActivityRiskScore(
            activity_code="DRILL",
            activity_name="Drilling Operations",
            acute=sample_dimension,
            chronic=sample_dimension,
            compliance=sample_dimension,
            composite_score=5.0,
            incident_count=42,
            confidence="high",
            sources=["phmsa", "osha"],
        )
        assert ars.category == RiskCategory.MEDIUM
        assert ars.incident_count == 42
        assert ars.confidence == "high"
        assert "phmsa" in ars.sources

    def test_category_auto_computed_low(self, low_dimension):
        ars = ActivityRiskScore(
            activity_code="OFFICE",
            activity_name="Office Work",
            acute=low_dimension,
            chronic=low_dimension,
            compliance=low_dimension,
            composite_score=2.0,
            incident_count=1,
            confidence="low",
            sources=["internal"],
        )
        assert ars.category == RiskCategory.LOW

    def test_category_auto_computed_critical(self, critical_dimension):
        ars = ActivityRiskScore(
            activity_code="DECOM",
            activity_name="Decommissioning",
            acute=critical_dimension,
            chronic=critical_dimension,
            compliance=critical_dimension,
            composite_score=9.0,
            incident_count=200,
            confidence="high",
            sources=["phmsa", "osha", "ntsb"],
        )
        assert ars.category == RiskCategory.CRITICAL

    def test_composite_score_below_range_fails(self, sample_dimension):
        with pytest.raises(ValidationError, match="composite_score"):
            ActivityRiskScore(
                activity_code="TEST",
                activity_name="Test",
                acute=sample_dimension,
                chronic=sample_dimension,
                compliance=sample_dimension,
                composite_score=0.5,
                incident_count=0,
                confidence="low",
                sources=[],
            )

    def test_composite_score_above_range_fails(self, sample_dimension):
        with pytest.raises(ValidationError, match="composite_score"):
            ActivityRiskScore(
                activity_code="TEST",
                activity_name="Test",
                acute=sample_dimension,
                chronic=sample_dimension,
                compliance=sample_dimension,
                composite_score=11.0,
                incident_count=0,
                confidence="low",
                sources=[],
            )

    def test_invalid_confidence_fails(self, sample_dimension):
        with pytest.raises(ValidationError, match="confidence"):
            ActivityRiskScore(
                activity_code="TEST",
                activity_name="Test",
                acute=sample_dimension,
                chronic=sample_dimension,
                compliance=sample_dimension,
                composite_score=5.0,
                incident_count=0,
                confidence="very_high",
                sources=[],
            )

    def test_valid_confidence_values(self, sample_dimension):
        for conf in ("high", "medium", "low"):
            ars = ActivityRiskScore(
                activity_code="TEST",
                activity_name="Test",
                acute=sample_dimension,
                chronic=sample_dimension,
                compliance=sample_dimension,
                composite_score=5.0,
                incident_count=0,
                confidence=conf,
                sources=[],
            )
            assert ars.confidence == conf

    def test_empty_sources_allowed(self, sample_dimension):
        ars = ActivityRiskScore(
            activity_code="TEST",
            activity_name="Test",
            acute=sample_dimension,
            chronic=sample_dimension,
            compliance=sample_dimension,
            composite_score=5.0,
            incident_count=0,
            confidence="low",
            sources=[],
        )
        assert ars.sources == []

    def test_negative_incident_count_fails(self, sample_dimension):
        with pytest.raises(ValidationError, match="incident_count"):
            ActivityRiskScore(
                activity_code="TEST",
                activity_name="Test",
                acute=sample_dimension,
                chronic=sample_dimension,
                compliance=sample_dimension,
                composite_score=5.0,
                incident_count=-1,
                confidence="low",
                sources=[],
            )

    def test_category_boundary_3_0(self, sample_dimension):
        """composite_score=3.0 should be LOW."""
        ars = ActivityRiskScore(
            activity_code="TEST",
            activity_name="Test",
            acute=sample_dimension,
            chronic=sample_dimension,
            compliance=sample_dimension,
            composite_score=3.0,
            incident_count=0,
            confidence="low",
            sources=[],
        )
        assert ars.category == RiskCategory.LOW

    def test_category_boundary_3_1(self, sample_dimension):
        """composite_score=3.1 should be MEDIUM."""
        ars = ActivityRiskScore(
            activity_code="TEST",
            activity_name="Test",
            acute=sample_dimension,
            chronic=sample_dimension,
            compliance=sample_dimension,
            composite_score=3.1,
            incident_count=0,
            confidence="low",
            sources=[],
        )
        assert ars.category == RiskCategory.MEDIUM

    def test_category_boundary_7_0(self, sample_dimension):
        """composite_score=7.0 should be HIGH."""
        ars = ActivityRiskScore(
            activity_code="TEST",
            activity_name="Test",
            acute=sample_dimension,
            chronic=sample_dimension,
            compliance=sample_dimension,
            composite_score=7.0,
            incident_count=0,
            confidence="low",
            sources=[],
        )
        assert ars.category == RiskCategory.HIGH

    def test_category_boundary_7_1(self, sample_dimension):
        """composite_score=7.1 should be CRITICAL."""
        ars = ActivityRiskScore(
            activity_code="TEST",
            activity_name="Test",
            acute=sample_dimension,
            chronic=sample_dimension,
            compliance=sample_dimension,
            composite_score=7.1,
            incident_count=0,
            confidence="low",
            sources=[],
        )
        assert ars.category == RiskCategory.CRITICAL


class TestCompositeScore:
    """Tests for CompositeScore container model."""

    def test_create_empty(self):
        cs = CompositeScore(
            scores=[],
            metadata={"version": "1.0"},
        )
        assert cs.scores == []
        assert cs.metadata["version"] == "1.0"
        assert cs.generated_at is not None

    def test_create_with_scores(self):
        dim = DimensionScore(
            dimension="acute",
            raw_metrics={},
            score=5.0,
        )
        score = ActivityRiskScore(
            activity_code="DRILL",
            activity_name="Drilling",
            acute=dim,
            chronic=dim,
            compliance=dim,
            composite_score=5.0,
            incident_count=10,
            confidence="medium",
            sources=["phmsa"],
        )
        cs = CompositeScore(
            scores=[score],
            metadata={"method": "percentile_rank"},
        )
        assert len(cs.scores) == 1
        assert cs.scores[0].activity_code == "DRILL"

    def test_generated_at_default(self):
        cs = CompositeScore(scores=[], metadata={})
        assert isinstance(cs.generated_at, datetime)

    def test_generated_at_custom(self):
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        cs = CompositeScore(scores=[], metadata={}, generated_at=ts)
        assert cs.generated_at == ts

    def test_metadata_empty_allowed(self):
        cs = CompositeScore(scores=[], metadata={})
        assert cs.metadata == {}
