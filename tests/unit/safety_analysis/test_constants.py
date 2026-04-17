"""Tests for safety analysis constants."""

from worldenergydata.safety_analysis.constants import (
    DEFAULT_FREQUENCY,
    DEFAULT_LAG_MAX,
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_STEP_SIZE,
    DEFAULT_WINDOW_SIZE,
    MONTHLY_FREQUENCY,
    SEVERITY_LABEL_MAP,
    WEEKLY_FREQUENCY,
    ClassifierType,
    FeatureType,
    IncidentType,
    ObservationType,
    SeverityLevel,
)


class TestSeverityLevel:
    def test_all_members(self):
        expected = {
            "NO_HURT",
            "MINOR",
            "MODERATE",
            "SEVERE",
            "FATALITY",
            "MULTIPLE_FATALITIES",
        }
        assert {m.name for m in SeverityLevel} == expected

    def test_numeric_values(self):
        assert SeverityLevel.NO_HURT.numeric_value == 0
        assert SeverityLevel.MINOR.numeric_value == 1
        assert SeverityLevel.MODERATE.numeric_value == 2
        assert SeverityLevel.SEVERE.numeric_value == 3
        assert SeverityLevel.FATALITY.numeric_value == 4
        assert SeverityLevel.MULTIPLE_FATALITIES.numeric_value == 5

    def test_ordering(self):
        assert (
            SeverityLevel.NO_HURT.numeric_value < SeverityLevel.FATALITY.numeric_value
        )

    def test_string_enum(self):
        assert isinstance(SeverityLevel.MINOR, str)
        assert SeverityLevel.MINOR == "minor"


class TestSeverityLabelMap:
    def test_text_labels(self):
        assert SEVERITY_LABEL_MAP["0 - No Hurt"] == SeverityLevel.NO_HURT
        assert SEVERITY_LABEL_MAP["4 - Fatality"] == SeverityLevel.FATALITY

    def test_value_labels(self):
        assert SEVERITY_LABEL_MAP["no_hurt"] == SeverityLevel.NO_HURT
        assert SEVERITY_LABEL_MAP["moderate"] == SeverityLevel.MODERATE

    def test_all_severity_levels_mapped(self):
        mapped_values = set(SEVERITY_LABEL_MAP.values())
        all_levels = set(SeverityLevel)
        assert all_levels == mapped_values


class TestObservationType:
    def test_all_members(self):
        expected = {
            "SAFE",
            "AT_RISK",
            "NEAR_MISS",
            "POSITIVE",
            "CORRECTIVE",
            "UNKNOWN",
        }
        assert {m.name for m in ObservationType} == expected


class TestIncidentType:
    def test_all_members(self):
        expected = {
            "INJURY",
            "SPILL",
            "EQUIPMENT_FAILURE",
            "NEAR_MISS",
            "PROPERTY_DAMAGE",
            "ENVIRONMENTAL",
            "FIRE",
            "VIOLATION",
            "OTHER",
        }
        assert {m.name for m in IncidentType} == expected


class TestClassifierType:
    def test_all_members(self):
        expected = {"RANDOM_FOREST", "XGBOOST", "LOGISTIC_REGRESSION"}
        assert {m.name for m in ClassifierType} == expected


class TestFeatureType:
    def test_all_members(self):
        expected = {"TFIDF", "BERT", "STATISTICAL"}
        assert {m.name for m in FeatureType} == expected


class TestFrequencyConstants:
    def test_default_frequency(self):
        assert DEFAULT_FREQUENCY == "D"

    def test_weekly_frequency(self):
        assert WEEKLY_FREQUENCY == "W-SUN"

    def test_monthly_frequency(self):
        assert MONTHLY_FREQUENCY == "MS"


class TestAnalysisParameters:
    def test_window_size(self):
        assert DEFAULT_WINDOW_SIZE == 10

    def test_step_size(self):
        assert DEFAULT_STEP_SIZE == 1

    def test_lag_max(self):
        assert DEFAULT_LAG_MAX == 30

    def test_rolling_window(self):
        assert DEFAULT_ROLLING_WINDOW == 7
