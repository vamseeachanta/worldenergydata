"""
Safety Analysis Constants

Enumerations and constants for safety observation types,
severity levels, incident types, and hurt indices.
"""

from enum import Enum


class SeverityLevel(str, Enum):
    """Severity levels for safety incidents (0-5 scale)."""

    NO_HURT = "no_hurt"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    FATALITY = "fatality"
    MULTIPLE_FATALITIES = "multiple_fatalities"

    @property
    def numeric_value(self) -> int:
        """Return numeric severity value (0-5)."""
        return _SEVERITY_VALUES[self]


_SEVERITY_VALUES = {
    SeverityLevel.NO_HURT: 0,
    SeverityLevel.MINOR: 1,
    SeverityLevel.MODERATE: 2,
    SeverityLevel.SEVERE: 3,
    SeverityLevel.FATALITY: 4,
    SeverityLevel.MULTIPLE_FATALITIES: 5,
}

# Mapping from common text representations to SeverityLevel
SEVERITY_LABEL_MAP = {
    "0 - No Hurt": SeverityLevel.NO_HURT,
    "1 - Minor Hurt": SeverityLevel.MINOR,
    "2 - Moderate Hurt": SeverityLevel.MODERATE,
    "3 - Severe Hurt": SeverityLevel.SEVERE,
    "4 - Fatality": SeverityLevel.FATALITY,
    "5 - Multiple Fatalities": SeverityLevel.MULTIPLE_FATALITIES,
    "no_hurt": SeverityLevel.NO_HURT,
    "minor": SeverityLevel.MINOR,
    "moderate": SeverityLevel.MODERATE,
    "severe": SeverityLevel.SEVERE,
    "fatality": SeverityLevel.FATALITY,
    "multiple_fatalities": SeverityLevel.MULTIPLE_FATALITIES,
}


class ObservationType(str, Enum):
    """Types of safety observations (observation card categories)."""

    SAFE = "safe"
    AT_RISK = "at_risk"
    NEAR_MISS = "near_miss"
    POSITIVE = "positive"
    CORRECTIVE = "corrective"
    UNKNOWN = "unknown"


class IncidentType(str, Enum):
    """Types of safety incidents."""

    INJURY = "injury"
    SPILL = "spill"
    EQUIPMENT_FAILURE = "equipment_failure"
    NEAR_MISS = "near_miss"
    PROPERTY_DAMAGE = "property_damage"
    ENVIRONMENTAL = "environmental"
    FIRE = "fire"
    VIOLATION = "violation"
    OTHER = "other"


class ClassifierType(str, Enum):
    """Supported classifier types for NLP pipeline."""

    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LOGISTIC_REGRESSION = "logistic_regression"


class FeatureType(str, Enum):
    """Feature extraction methods."""

    TFIDF = "tfidf"
    BERT = "bert"
    STATISTICAL = "statistical"


# Default time series frequencies
DEFAULT_FREQUENCY = "D"  # Daily
WEEKLY_FREQUENCY = "W-SUN"
MONTHLY_FREQUENCY = "MS"

# Default analysis parameters
DEFAULT_WINDOW_SIZE = 10
DEFAULT_STEP_SIZE = 1
DEFAULT_LAG_MAX = 30
DEFAULT_ROLLING_WINDOW = 7
