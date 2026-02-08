"""
HSE Risk Index Models

Pydantic v2 models for the three-dimensional risk scoring framework:
acute, chronic, and compliance dimensions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator, model_validator


class RiskCategory(str, Enum):
    """Risk category derived from composite score.

    Ranges:
        LOW:      1.0 - 3.0
        MEDIUM:   3.1 - 5.0
        HIGH:     5.1 - 7.0
        CRITICAL: 7.1 - 10.0
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: float) -> "RiskCategory":
        """Determine risk category from a numeric score (1.0-10.0)."""
        if score < 1.0 or score > 10.0:
            raise ValueError(f"Score must be between 1.0 and 10.0, got {score}")
        if score <= 3.0:
            return cls.LOW
        if score <= 5.0:
            return cls.MEDIUM
        if score <= 7.0:
            return cls.HIGH
        return cls.CRITICAL


class DimensionScore(BaseModel):
    """Score for a single risk dimension (acute, chronic, or compliance).

    Attributes:
        dimension: Name of the dimension (e.g. "acute", "chronic", "compliance").
        raw_metrics: Dictionary of raw metric values used to compute the score.
        score: Normalized score on a 1-10 scale.
        subscores: Optional breakdown of sub-component scores.
    """

    dimension: str = Field(..., description="Dimension name")
    raw_metrics: Dict[str, Any] = Field(..., description="Raw metric values")
    score: float = Field(..., ge=1.0, le=10.0, description="Normalized score (1-10)")
    subscores: Dict[str, float] = Field(
        default_factory=dict, description="Sub-component score breakdown"
    )


class ActivityRiskScore(BaseModel):
    """Risk score for a single activity type.

    The category is automatically computed from the composite_score
    using a model_validator.

    Attributes:
        activity_code: Short identifier for the activity.
        activity_name: Human-readable activity name.
        acute: Acute risk dimension score.
        chronic: Chronic risk dimension score.
        compliance: Compliance risk dimension score.
        composite_score: Overall score (1-10) combining all dimensions.
        category: Auto-computed RiskCategory from composite_score.
        incident_count: Number of incidents associated with this activity.
        confidence: Confidence level of the score ("high", "medium", "low").
        sources: List of data source identifiers.
    """

    activity_code: str = Field(..., description="Activity identifier")
    activity_name: str = Field(..., description="Human-readable activity name")
    acute: DimensionScore = Field(..., description="Acute risk dimension")
    chronic: DimensionScore = Field(..., description="Chronic risk dimension")
    compliance: DimensionScore = Field(..., description="Compliance risk dimension")
    composite_score: float = Field(
        ..., ge=1.0, le=10.0, description="Overall composite score (1-10)"
    )
    category: RiskCategory = Field(
        default=RiskCategory.LOW, description="Auto-computed risk category"
    )
    incident_count: int = Field(..., ge=0, description="Number of associated incidents")
    confidence: str = Field(..., description="Score confidence level (high/medium/low)")
    sources: List[str] = Field(
        default_factory=list, description="Data source identifiers"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        allowed = {"high", "medium", "low"}
        if v not in allowed:
            raise ValueError(f"confidence must be one of {allowed}, got '{v}'")
        return v

    @model_validator(mode="after")
    def compute_category(self) -> "ActivityRiskScore":
        """Auto-compute category from composite_score."""
        self.category = RiskCategory.from_score(self.composite_score)
        return self


class CompositeScore(BaseModel):
    """Container for a collection of activity risk scores.

    Attributes:
        scores: List of ActivityRiskScore instances.
        metadata: Arbitrary metadata about the scoring run.
        generated_at: Timestamp of when the scores were generated.
    """

    scores: List[ActivityRiskScore] = Field(
        default_factory=list, description="Activity risk scores"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Scoring run metadata"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of score generation",
    )
