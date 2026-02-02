"""
Safety Analysis Domain Models

Pydantic models for safety observations, incidents,
classification results, and correlation results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from worldenergydata.modules.safety_analysis.constants import (
    IncidentType,
    ObservationType,
    SeverityLevel,
)


class SafetyObservation(BaseModel):
    """A single safety observation record (observation card)."""

    asset_id: str = Field(..., description="Asset/facility/rig identifier")
    observed_at: datetime = Field(..., description="When the observation occurred")
    description: str = Field(..., description="Observation description text")
    observation_type: ObservationType = Field(
        default=ObservationType.UNKNOWN,
        description="Classification of the observation",
    )
    action_taken: Optional[str] = Field(
        default=None, description="Action taken in response"
    )
    observer_id: Optional[str] = Field(default=None, description="Observer identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be empty")
        return v


class SafetyIncident(BaseModel):
    """A single safety incident record."""

    asset_id: str = Field(..., description="Asset/facility/rig identifier")
    occurred_at: datetime = Field(..., description="When the incident occurred")
    incident_type: IncidentType = Field(
        default=IncidentType.OTHER, description="Type of incident"
    )
    actual_severity: SeverityLevel = Field(
        default=SeverityLevel.NO_HURT, description="Actual severity level"
    )
    potential_severity: SeverityLevel = Field(
        default=SeverityLevel.NO_HURT, description="Potential severity level"
    )
    description: Optional[str] = Field(default=None, description="Incident description")
    work_activity: Optional[str] = Field(
        default=None, description="Work activity during incident"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """Result of a text classification operation."""

    text: str = Field(..., description="Input text that was classified")
    predicted_label: str = Field(..., description="Predicted classification label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    model_name: str = Field(..., description="Name of the model used")
    feature_type: str = Field(default="tfidf", description="Feature extraction method")
    probabilities: Optional[Dict[str, float]] = Field(
        default=None, description="Class probabilities"
    )


class CorrelationResult(BaseModel):
    """Result of a lag correlation analysis."""

    asset_id: str = Field(..., description="Asset identifier")
    lag_values: List[int] = Field(..., description="Lag values tested")
    correlation_values: List[float] = Field(..., description="Correlation at each lag")
    peak_correlation: float = Field(
        ..., description="Maximum absolute correlation found"
    )
    peak_lag: int = Field(..., description="Lag at peak correlation")
    observation_column: str = Field(
        default="obs_count", description="Observation series name"
    )
    incident_column: str = Field(
        default="inc_count", description="Incident series name"
    )
