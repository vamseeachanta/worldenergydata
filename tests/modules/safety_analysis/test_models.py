"""Tests for safety analysis domain models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from worldenergydata.modules.safety_analysis.constants import (
    IncidentType,
    ObservationType,
    SeverityLevel,
)
from worldenergydata.modules.safety_analysis.core.models import (
    ClassificationResult,
    CorrelationResult,
    SafetyIncident,
    SafetyObservation,
)


class TestSafetyObservation:
    def test_create_minimal(self):
        obs = SafetyObservation(
            asset_id="RIG-001",
            observed_at=datetime(2024, 1, 1),
            description="Test observation",
        )
        assert obs.asset_id == "RIG-001"
        assert obs.observation_type == ObservationType.UNKNOWN
        assert obs.metadata == {}

    def test_create_full(self):
        obs = SafetyObservation(
            asset_id="RIG-001",
            observed_at=datetime(2024, 1, 1),
            description="Worker wearing PPE",
            observation_type=ObservationType.SAFE,
            action_taken="Positive feedback given",
            observer_id="OBS-42",
            metadata={"contractor": "ACME"},
        )
        assert obs.observation_type == ObservationType.SAFE
        assert obs.action_taken == "Positive feedback given"

    def test_empty_description_fails(self):
        with pytest.raises(ValidationError, match="description must not be empty"):
            SafetyObservation(
                asset_id="RIG-001",
                observed_at=datetime(2024, 1, 1),
                description="   ",
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            SafetyObservation(
                asset_id="RIG-001",
                description="test",
            )


class TestSafetyIncident:
    def test_create_minimal(self):
        inc = SafetyIncident(
            asset_id="RIG-001",
            occurred_at=datetime(2024, 1, 1),
        )
        assert inc.actual_severity == SeverityLevel.NO_HURT
        assert inc.potential_severity == SeverityLevel.NO_HURT
        assert inc.incident_type == IncidentType.OTHER

    def test_create_full(self):
        inc = SafetyIncident(
            asset_id="RIG-002",
            occurred_at=datetime(2024, 1, 15),
            incident_type=IncidentType.INJURY,
            actual_severity=SeverityLevel.MINOR,
            potential_severity=SeverityLevel.MODERATE,
            description="Slip and fall",
            work_activity="Drilling",
            metadata={"location": "drill floor"},
        )
        assert inc.actual_severity == SeverityLevel.MINOR
        assert inc.work_activity == "Drilling"


class TestClassificationResult:
    def test_create(self):
        result = ClassificationResult(
            text="Worker not wearing gloves",
            predicted_label="at_risk",
            confidence=0.87,
            model_name="rf_tfidf_v1",
        )
        assert result.predicted_label == "at_risk"
        assert result.confidence == 0.87
        assert result.feature_type == "tfidf"

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                text="test",
                predicted_label="safe",
                confidence=1.5,
                model_name="test",
            )

    def test_with_probabilities(self):
        result = ClassificationResult(
            text="test obs",
            predicted_label="safe",
            confidence=0.9,
            model_name="rf_v1",
            probabilities={"safe": 0.9, "at_risk": 0.1},
        )
        assert result.probabilities["safe"] == 0.9


class TestCorrelationResult:
    def test_create(self):
        result = CorrelationResult(
            asset_id="RIG-001",
            lag_values=[-2, -1, 0, 1, 2],
            correlation_values=[0.1, 0.3, 0.5, 0.3, 0.1],
            peak_correlation=0.5,
            peak_lag=0,
        )
        assert result.peak_correlation == 0.5
        assert len(result.lag_values) == 5
