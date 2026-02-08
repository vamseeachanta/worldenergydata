"""Tests for safety analysis constants and enums."""

from worldenergydata.safety_analysis.constants import (
    SEVERITY_LABEL_MAP,
    ClassifierType,
    FeatureType,
    IncidentType,
    ObservationType,
    SeverityLevel,
)


class TestSeverityLevel:
    def test_all_levels_exist(self):
        assert len(SeverityLevel) == 6

    def test_numeric_values(self):
        assert SeverityLevel.NO_HURT.numeric_value == 0
        assert SeverityLevel.MINOR.numeric_value == 1
        assert SeverityLevel.MODERATE.numeric_value == 2
        assert SeverityLevel.SEVERE.numeric_value == 3
        assert SeverityLevel.FATALITY.numeric_value == 4
        assert SeverityLevel.MULTIPLE_FATALITIES.numeric_value == 5

    def test_string_values(self):
        assert SeverityLevel.NO_HURT.value == "no_hurt"
        assert SeverityLevel.MINOR.value == "minor"

    def test_label_map_covers_all(self):
        for level in SeverityLevel:
            assert level.value in SEVERITY_LABEL_MAP


class TestObservationType:
    def test_all_types_exist(self):
        expected = {"safe", "at_risk", "near_miss", "positive", "corrective", "unknown"}
        actual = {t.value for t in ObservationType}
        assert actual == expected


class TestIncidentType:
    def test_all_types_exist(self):
        assert len(IncidentType) >= 8
        assert IncidentType.INJURY.value == "injury"
        assert IncidentType.OTHER.value == "other"


class TestClassifierType:
    def test_all_types(self):
        assert ClassifierType.RANDOM_FOREST.value == "random_forest"
        assert ClassifierType.XGBOOST.value == "xgboost"
        assert ClassifierType.LOGISTIC_REGRESSION.value == "logistic_regression"


class TestFeatureType:
    def test_all_types(self):
        assert FeatureType.TFIDF.value == "tfidf"
        assert FeatureType.BERT.value == "bert"
        assert FeatureType.STATISTICAL.value == "statistical"
