"""Tests for safety analysis core domain models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from worldenergydata.safety_analysis.constants import (
    IncidentType,
    ObservationType,
    SeverityLevel,
)
from worldenergydata.safety_analysis.core.models import (
    ClassificationResult,
    CorrelationResult,
    SafetyIncident,
    SafetyObservation,
)


class TestSafetyObservation:
    def test_required_fields(self):
        obs = SafetyObservation(
            asset_id="RIG-001",
            observed_at=datetime(2024, 1, 15, 10, 30),
            description="Loose handrail on stairway B",
        )
        assert obs.asset_id == "RIG-001"
        assert obs.observation_type == ObservationType.UNKNOWN

    def test_defaults(self):
        obs = SafetyObservation(
            asset_id="RIG-001",
            observed_at=datetime(2024, 1, 15),
            description="Test",
        )
        assert obs.action_taken is None
        assert obs.observer_id is None
        assert obs.metadata == {}

    def test_custom_type(self):
        obs = SafetyObservation(
            asset_id="RIG-001",
            observed_at=datetime(2024, 1, 15),
            description="Near miss event",
            observation_type=ObservationType.NEAR_MISS,
        )
        assert obs.observation_type == ObservationType.NEAR_MISS

    def test_empty_description_raises(self):
        with pytest.raises(ValidationError, match="description must not be empty"):
            SafetyObservation(
                asset_id="RIG-001",
                observed_at=datetime(2024, 1, 15),
                description="   ",
            )

    def test_metadata(self):
        obs = SafetyObservation(
            asset_id="RIG-001",
            observed_at=datetime(2024, 1, 15),
            description="Test obs",
            metadata={"location": "drill floor", "shift": "night"},
        )
        assert obs.metadata["location"] == "drill floor"


class TestSafetyIncident:
    def test_required_fields(self):
        inc = SafetyIncident(
            asset_id="PLT-002",
            occurred_at=datetime(2024, 3, 10, 14, 0),
        )
        assert inc.asset_id == "PLT-002"
        assert inc.incident_type == IncidentType.OTHER
        assert inc.actual_severity == SeverityLevel.NO_HURT
        assert inc.potential_severity == SeverityLevel.NO_HURT

    def test_severity_levels(self):
        inc = SafetyIncident(
            asset_id="PLT-002",
            occurred_at=datetime(2024, 3, 10),
            actual_severity=SeverityLevel.MINOR,
            potential_severity=SeverityLevel.SEVERE,
        )
        assert inc.actual_severity == SeverityLevel.MINOR
        assert inc.potential_severity == SeverityLevel.SEVERE

    def test_with_description(self):
        inc = SafetyIncident(
            asset_id="PLT-002",
            occurred_at=datetime(2024, 3, 10),
            incident_type=IncidentType.SPILL,
            description="Small hydraulic fluid spill",
            work_activity="crane operations",
        )
        assert inc.incident_type == IncidentType.SPILL
        assert inc.work_activity == "crane operations"


class TestClassificationResult:
    def test_required_fields(self):
        r = ClassificationResult(
            text="Test observation",
            predicted_label="safe",
            confidence=0.95,
            model_name="random_forest_v1",
        )
        assert r.predicted_label == "safe"
        assert r.confidence == 0.95
        assert r.feature_type == "tfidf"

    def test_with_probabilities(self):
        r = ClassificationResult(
            text="Test text",
            predicted_label="at_risk",
            confidence=0.82,
            model_name="xgboost_v2",
            feature_type="bert",
            probabilities={"safe": 0.18, "at_risk": 0.82},
        )
        assert r.probabilities["at_risk"] == 0.82

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                text="T", predicted_label="x",
                confidence=1.5, model_name="m",
            )

    def test_confidence_negative(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                text="T", predicted_label="x",
                confidence=-0.1, model_name="m",
            )


class TestCorrelationResult:
    def test_required_fields(self):
        r = CorrelationResult(
            asset_id="RIG-001",
            lag_values=[-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5],
            correlation_values=[0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.7, 0.5, 0.3, 0.2, 0.1],
            peak_correlation=0.9,
            peak_lag=0,
        )
        assert r.peak_correlation == 0.9
        assert r.peak_lag == 0

    def test_defaults(self):
        r = CorrelationResult(
            asset_id="RIG-001",
            lag_values=[0],
            correlation_values=[0.5],
            peak_correlation=0.5,
            peak_lag=0,
        )
        assert r.observation_column == "obs_count"
        assert r.incident_column == "inc_count"

    def test_custom_columns(self):
        r = CorrelationResult(
            asset_id="RIG-001",
            lag_values=[0],
            correlation_values=[0.5],
            peak_correlation=0.5,
            peak_lag=0,
            observation_column="observations",
            incident_column="incidents",
        )
        assert r.observation_column == "observations"
        assert r.incident_column == "incidents"
