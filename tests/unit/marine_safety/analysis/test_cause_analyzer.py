"""Tests for marine_safety.analysis.cause_analyzer module."""

import pandas as pd
import pytest

from worldenergydata.marine_safety.analysis.cause_analyzer import (
    CauseNormalizer,
    IncidentCauseExtractor,
    clean_cause_data,
    detect_hatch_opening_maloperation,
    extract_causes_from_narrative,
    map_to_cause_category,
)
from worldenergydata.marine_safety.constants import CauseCategory


class TestMapToCauseCategory:
    def test_human_error_operator(self):
        assert map_to_cause_category("operator error") == CauseCategory.HUMAN_ERROR

    def test_human_error_crew(self):
        assert map_to_cause_category("crew fatigue") == CauseCategory.HUMAN_ERROR

    def test_equipment_failure(self):
        assert map_to_cause_category("equipment malfunction") == CauseCategory.EQUIPMENT_FAILURE

    def test_maintenance_issue(self):
        assert map_to_cause_category("inadequate maintenance") == CauseCategory.MAINTENANCE_ISSUE

    def test_weather(self):
        assert map_to_cause_category("severe storm conditions") == CauseCategory.WEATHER

    def test_design_flaw(self):
        assert map_to_cause_category("design deficiency") == CauseCategory.DESIGN_FLAW

    def test_procedural(self):
        assert map_to_cause_category("procedure violation") == CauseCategory.PROCEDURAL

    def test_training(self):
        assert map_to_cause_category("training deficiency") == CauseCategory.TRAINING

    def test_communication(self):
        assert map_to_cause_category("communication breakdown") == CauseCategory.COMMUNICATION

    def test_management(self):
        assert map_to_cause_category("management oversight") == CauseCategory.MANAGEMENT

    def test_environmental(self):
        assert map_to_cause_category("environmental current") == CauseCategory.ENVIRONMENTAL

    def test_external(self):
        assert map_to_cause_category("external collision") == CauseCategory.EXTERNAL

    def test_multiple_causes(self):
        assert map_to_cause_category("multiple equipment and human factors") == CauseCategory.MULTIPLE

    def test_unknown(self):
        assert map_to_cause_category("some random text") == CauseCategory.UNKNOWN

    def test_none_input(self):
        assert map_to_cause_category(None) == CauseCategory.UNKNOWN

    def test_nan_input(self):
        assert map_to_cause_category(float("nan")) == CauseCategory.UNKNOWN


class TestDetectHatchOpeningMaloperation:
    def test_hatch_failure(self):
        assert detect_hatch_opening_maloperation("hatch cover failure") is True

    def test_door_not_secured(self):
        assert detect_hatch_opening_maloperation("watertight door not secured") is True

    def test_opening_left_open(self):
        assert detect_hatch_opening_maloperation("access opening left open") is True

    def test_no_hatch_keywords(self):
        assert detect_hatch_opening_maloperation("engine room fire") is False

    def test_hatch_without_malfunction(self):
        assert detect_hatch_opening_maloperation("hatch was inspected") is False

    def test_none_input(self):
        assert detect_hatch_opening_maloperation(None) is False

    def test_nan_input(self):
        assert detect_hatch_opening_maloperation(float("nan")) is False


class TestExtractCausesFromNarrative:
    def test_caused_by_pattern(self):
        result = extract_causes_from_narrative("The incident was caused by engine failure")
        assert len(result) >= 1
        assert any("engine failure" in c.lower() for c in result)

    def test_due_to_pattern(self):
        result = extract_causes_from_narrative("Sinking due to hull breach")
        assert len(result) >= 1

    def test_failure_of_pattern(self):
        result = extract_causes_from_narrative("failure of the steering mechanism led to grounding")
        assert len(result) >= 1

    def test_empty_narrative(self):
        assert extract_causes_from_narrative("") == []

    def test_none_narrative(self):
        assert extract_causes_from_narrative(None) == []

    def test_nan_narrative(self):
        assert extract_causes_from_narrative(float("nan")) == []

    def test_no_cause_patterns_with_keywords(self):
        result = extract_causes_from_narrative(
            "The vessel experienced hatch problems during the voyage"
        )
        assert isinstance(result, list)

    def test_deduplicates_results(self):
        result = extract_causes_from_narrative(
            "caused by engine failure. Also attributed to engine failure"
        )
        lower_results = [c.lower() for c in result]
        assert len(lower_results) == len(set(lower_results))


class TestCauseNormalizer:
    def test_normalize_basic(self):
        normalizer = CauseNormalizer()
        result = normalizer.normalize("  Equipment Failure  ")
        assert result == "equipment failure"

    def test_normalize_extra_whitespace(self):
        normalizer = CauseNormalizer()
        result = normalizer.normalize("multiple   spaces\tand\ttabs")
        assert result == "multiple spaces and tabs"

    def test_normalize_none(self):
        normalizer = CauseNormalizer()
        assert normalizer.normalize(None) is None

    def test_normalize_empty(self):
        normalizer = CauseNormalizer()
        assert normalizer.normalize("") is None

    def test_normalize_nan(self):
        normalizer = CauseNormalizer()
        assert normalizer.normalize(float("nan")) is None

    def test_cause_mappings_exist(self):
        normalizer = CauseNormalizer()
        assert "operator" in normalizer.cause_mappings
        assert "equipment" in normalizer.cause_mappings
        assert "weather" in normalizer.cause_mappings


class TestIncidentCauseExtractor:
    def test_extract_empty_dataframe(self):
        extractor = IncidentCauseExtractor()
        df = pd.DataFrame()
        result = extractor.extract_from_dataframe(df)
        assert result.empty

    def test_extract_with_primary_cause(self):
        extractor = IncidentCauseExtractor()
        df = pd.DataFrame({
            "incident_id": [1],
            "primary_cause": ["equipment failure"],
        })
        result = extractor.extract_from_dataframe(df)
        assert "primary_cause_category" in result.columns
        assert result.iloc[0]["primary_cause_category"] == CauseCategory.EQUIPMENT_FAILURE

    def test_extract_without_primary_cause(self):
        extractor = IncidentCauseExtractor()
        df = pd.DataFrame({"incident_id": [1]})
        result = extractor.extract_from_dataframe(df)
        assert result.iloc[0]["primary_cause_category"] == CauseCategory.UNKNOWN

    def test_extract_with_contributing_factors(self):
        extractor = IncidentCauseExtractor()
        df = pd.DataFrame({
            "incident_id": [1],
            "contributing_factors": ["fatigue, poor visibility"],
        })
        result = extractor.extract_from_dataframe(df)
        assert "contributing_causes" in result.columns
        causes = result.iloc[0]["contributing_causes"]
        assert isinstance(causes, list)
        assert len(causes) >= 2

    def test_extract_with_narrative(self):
        extractor = IncidentCauseExtractor()
        df = pd.DataFrame({
            "incident_id": [1],
            "narrative": ["The incident was caused by equipment failure"],
        })
        result = extractor.extract_from_dataframe(df)
        assert "narrative_causes" in result.columns

    def test_parse_contributing_factors_none(self):
        extractor = IncidentCauseExtractor()
        assert extractor._parse_contributing_factors(None) == []

    def test_parse_contributing_factors_empty(self):
        extractor = IncidentCauseExtractor()
        assert extractor._parse_contributing_factors("") == []

    def test_parse_contributing_factors_semicolon_separated(self):
        extractor = IncidentCauseExtractor()
        result = extractor._parse_contributing_factors("fatigue; poor visibility")
        assert len(result) >= 2


class TestCleanCauseData:
    def test_clean_normalizes(self):
        df = pd.DataFrame({"cause": ["  EQUIPMENT Failure  ", "STORM  damage"]})
        result = clean_cause_data(df, "cause")
        assert result.iloc[0]["cause"] == "equipment failure"
        assert result.iloc[1]["cause"] == "storm damage"

    def test_clean_empty_df(self):
        df = pd.DataFrame()
        result = clean_cause_data(df, "cause")
        assert result.empty

    def test_clean_missing_column(self):
        df = pd.DataFrame({"other": [1]})
        result = clean_cause_data(df, "cause")
        assert "other" in result.columns

    def test_clean_remove_duplicates(self):
        df = pd.DataFrame({"cause": ["equipment failure", "equipment failure", "storm"]})
        result = clean_cause_data(df, "cause", remove_duplicates=True)
        assert len(result) == 2

    def test_clean_validate_categories(self):
        df = pd.DataFrame({"cause": ["equipment failure", "random text"]})
        result = clean_cause_data(df, "cause", validate_categories=True)
        assert "validation_status" in result.columns
        assert result.iloc[0]["validation_status"] == "valid"
        assert result.iloc[1]["validation_status"] == "unknown"
