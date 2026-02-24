"""
Tests for WRK-320: incident taxonomy, USCG client, and cross-database correlator.

Covers:
- RootCauseType enum completeness
- IncidentTaxonomyClassifier keyword classification
- IncidentDataFrameNormaliser column mapping for each source
- TaxonomyRecord construction
- build_taxonomy_summary aggregation
- load_dataframe_as_uscg in-memory path
- IncidentCorrelator matching logic
- build_correlation_summary DataFrame structure
- build_pattern_report aggregation
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.marine_safety.analysis.incidents.incident_correlator import (
    CorrelationConfig,
    CorrelationMatch,
    IncidentCorrelator,
    _days_apart,
    _extract_year,
    _haversine,
    _jaccard_similarity,
    build_correlation_summary,
    build_pattern_report,
)
from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    IncidentDataFrameNormaliser,
    IncidentTaxonomyClassifier,
    RootCauseType,
    TaxonomyRecord,
    _safe_float,
    _safe_str,
    build_taxonomy_summary,
)
from worldenergydata.marine_safety.analysis.incidents.uscg_client import (
    describe_uscg_dataset,
    load_dataframe_as_uscg,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def classifier() -> IncidentTaxonomyClassifier:
    return IncidentTaxonomyClassifier()


@pytest.fixture()
def normaliser() -> IncidentDataFrameNormaliser:
    return IncidentDataFrameNormaliser()


@pytest.fixture()
def sample_uscg_df() -> pd.DataFrame:
    """Minimal USCG-style DataFrame with raw column names."""
    return pd.DataFrame(
        [
            {
                "REPORT_NUM": "USCG-2021-001",
                "VESSEL_NAME": "MV Atlantic Ranger",
                "EVENT_DATE": "2021-03-15",
                "CASUALTY_TYPE": "COLLISION",
                "PRIMARY_CAUSE": "operator error during bridge watch",
                "NARRATIVE": "Vessel collided with pier due to crew inattention.",
                "LATITUDE": 29.5,
                "LONGITUDE": -94.2,
                "INJURY_COUNT": 2,
                "FATALITY_COUNT": 0,
                "VESSEL_TYPE": "cargo",
            },
            {
                "REPORT_NUM": "USCG-2021-002",
                "VESSEL_NAME": "F/V Blue Horizon",
                "EVENT_DATE": "2021-07-04",
                "CASUALTY_TYPE": "SINKING",
                "PRIMARY_CAUSE": "machinery failure in engine room",
                "NARRATIVE": "Flooding caused by failed pump.",
                "LATITUDE": 27.1,
                "LONGITUDE": -97.0,
                "INJURY_COUNT": 0,
                "FATALITY_COUNT": 1,
                "VESSEL_TYPE": "fishing",
            },
        ]
    )


@pytest.fixture()
def sample_maib_df() -> pd.DataFrame:
    """Minimal MAIB-style DataFrame."""
    return pd.DataFrame(
        [
            {
                "Occurrence_Id": "MAIB-2021-999",
                "Date": "2021-03-16",
                "Vessel_Name": "MV ATLANTIC RANGER",
                "Vessel_Type": "cargo",
                "Main_Event": "collision",
                "Abstract": "Vessel struck jetty; crew inattention cited.",
                "Latitude": 29.55,
                "Longitude": -94.1,
                "Deaths": 0,
                "Injuries": 2,
            },
        ]
    )


@pytest.fixture()
def sample_ntsb_df() -> pd.DataFrame:
    """Minimal NTSB-style DataFrame."""
    return pd.DataFrame(
        [
            {
                "EventId": "NTSB-MAR-2020-001",
                "EventDate": "2020-06-01",
                "VesselName": "SS GULF PROVIDER",
                "VesselType": "tanker",
                "ProbableCause": "inadequate safety management system procedures",
                "Narrative": "Grounding attributed to non-compliance with watchkeeping procedure.",
                "Latitude": 28.0,
                "Longitude": -90.0,
                "FatalCount": 0,
                "InjuryCount": 3,
            },
        ]
    )


def _make_record(
    report_id: str = "R1",
    source: str = "uscg",
    incident_date: str = "2021-01-01",
    vessel_name: str = "TEST VESSEL",
    vessel_type: str = "cargo",
    root_cause: RootCauseType = RootCauseType.HUMAN_ERROR,
    latitude: float = 29.5,
    longitude: float = -94.0,
    fatality_count: int = 0,
    injury_count: int = 0,
) -> TaxonomyRecord:
    return TaxonomyRecord(
        report_id=report_id,
        source=source,
        incident_date=incident_date,
        vessel_name=vessel_name,
        vessel_type=vessel_type,
        incident_type="collision",
        root_cause=root_cause,
        raw_cause=None,
        narrative=None,
        latitude=latitude,
        longitude=longitude,
        fatality_count=fatality_count,
        injury_count=injury_count,
    )


# ---------------------------------------------------------------------------
# RootCauseType enum
# ---------------------------------------------------------------------------


class TestRootCauseType:
    def test_has_human_error(self):
        assert RootCauseType.HUMAN_ERROR == "human_error"

    def test_has_equipment_failure(self):
        assert RootCauseType.EQUIPMENT_FAILURE == "equipment_failure"

    def test_has_environmental(self):
        assert RootCauseType.ENVIRONMENTAL == "environmental"

    def test_has_procedure(self):
        assert RootCauseType.PROCEDURE == "procedure"

    def test_has_design_defect(self):
        assert RootCauseType.DESIGN_DEFECT == "design_defect"

    def test_has_management(self):
        assert RootCauseType.MANAGEMENT == "management"

    def test_has_unknown(self):
        assert RootCauseType.UNKNOWN == "unknown"

    def test_all_seven_types_present(self):
        types = {e.value for e in RootCauseType}
        assert types == {
            "human_error",
            "equipment_failure",
            "environmental",
            "procedure",
            "design_defect",
            "management",
            "unknown",
        }


# ---------------------------------------------------------------------------
# IncidentTaxonomyClassifier
# ---------------------------------------------------------------------------


class TestIncidentTaxonomyClassifier:
    def test_classify_operator_error_returns_human_error(self, classifier):
        result = classifier.classify(primary_cause="operator error during navigation")
        assert result == RootCauseType.HUMAN_ERROR

    def test_classify_crew_fatigue_returns_human_error(self, classifier):
        result = classifier.classify(primary_cause="crew fatigue identified as factor")
        assert result == RootCauseType.HUMAN_ERROR

    def test_classify_watchkeeping_returns_human_error(self, classifier):
        result = classifier.classify(
            narrative="failure of watchkeeping led to grounding"
        )
        assert result == RootCauseType.HUMAN_ERROR

    def test_classify_machinery_failure_returns_equipment_failure(self, classifier):
        result = classifier.classify(primary_cause="machinery failure in engine room")
        assert result == RootCauseType.EQUIPMENT_FAILURE

    def test_classify_steering_failure_returns_equipment_failure(self, classifier):
        result = classifier.classify(primary_cause="steering failure at sea")
        assert result == RootCauseType.EQUIPMENT_FAILURE

    def test_classify_adverse_weather_returns_environmental(self, classifier):
        result = classifier.classify(primary_cause="adverse weather conditions")
        assert result == RootCauseType.ENVIRONMENTAL

    def test_classify_heavy_seas_returns_environmental(self, classifier):
        result = classifier.classify(
            narrative="vessel lost power in heavy seas with high winds"
        )
        assert result == RootCauseType.ENVIRONMENTAL

    def test_classify_sms_deficiency_returns_procedure(self, classifier):
        result = classifier.classify(primary_cause="SMS deficiency identified")
        assert result == RootCauseType.PROCEDURE

    def test_classify_procedure_not_followed_returns_procedure(self, classifier):
        result = classifier.classify(primary_cause="procedure not followed by officer")
        assert result == RootCauseType.PROCEDURE

    def test_classify_design_defect_returns_design_defect(self, classifier):
        result = classifier.classify(primary_cause="design defect in hatch cover")
        assert result == RootCauseType.DESIGN_DEFECT

    def test_classify_safety_culture_returns_management(self, classifier):
        result = classifier.classify(
            primary_cause="safety culture failure at company level"
        )
        assert result == RootCauseType.MANAGEMENT

    def test_classify_management_failure_returns_management(self, classifier):
        result = classifier.classify(
            narrative="management failure contributed to the accident"
        )
        assert result == RootCauseType.MANAGEMENT

    def test_classify_empty_string_returns_unknown(self, classifier):
        result = classifier.classify(primary_cause="")
        assert result == RootCauseType.UNKNOWN

    def test_classify_none_inputs_returns_unknown(self, classifier):
        result = classifier.classify(primary_cause=None, narrative=None)
        assert result == RootCauseType.UNKNOWN

    def test_classify_narrative_takes_precedence_over_empty_cause(self, classifier):
        result = classifier.classify(
            primary_cause=None, narrative="operator fatigue noted"
        )
        assert result == RootCauseType.HUMAN_ERROR

    def test_classify_dataframe_assigns_correct_types(self, classifier):
        df = pd.DataFrame(
            [
                {"primary_cause": "operator error", "narrative": ""},
                {"primary_cause": "engine failure", "narrative": ""},
                {"primary_cause": "", "narrative": "heavy seas"},
            ]
        )
        series = classifier.classify_dataframe(df)
        assert list(series) == [
            RootCauseType.HUMAN_ERROR,
            RootCauseType.EQUIPMENT_FAILURE,
            RootCauseType.ENVIRONMENTAL,
        ]

    def test_classify_dataframe_empty_input_returns_empty_series(self, classifier):
        result = classifier.classify_dataframe(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# IncidentDataFrameNormaliser
# ---------------------------------------------------------------------------


class TestIncidentDataFrameNormaliser:
    def test_normalise_uscg_renames_report_num(self, normaliser, sample_uscg_df):
        result = normaliser.normalise(sample_uscg_df, source="uscg")
        assert "report_id" in result.columns

    def test_normalise_uscg_renames_event_date(self, normaliser, sample_uscg_df):
        result = normaliser.normalise(sample_uscg_df, source="uscg")
        assert "incident_date" in result.columns

    def test_normalise_uscg_adds_source_column(self, normaliser, sample_uscg_df):
        result = normaliser.normalise(sample_uscg_df, source="uscg")
        assert (result["source"] == "uscg").all()

    def test_normalise_uscg_coerces_fatality_count(self, normaliser, sample_uscg_df):
        result = normaliser.normalise(sample_uscg_df, source="uscg")
        assert result["fatality_count"].dtype in (int, "int64", "int32")

    def test_normalise_maib_renames_occurrence_id(self, normaliser, sample_maib_df):
        result = normaliser.normalise(sample_maib_df, source="maib")
        assert "report_id" in result.columns
        assert result.iloc[0]["report_id"] == "MAIB-2021-999"

    def test_normalise_ntsb_renames_event_id(self, normaliser, sample_ntsb_df):
        result = normaliser.normalise(sample_ntsb_df, source="ntsb")
        assert "report_id" in result.columns
        assert result.iloc[0]["report_id"] == "NTSB-MAR-2020-001"

    def test_normalise_empty_df_returns_empty(self, normaliser):
        result = normaliser.normalise(pd.DataFrame(), source="uscg")
        assert result.empty

    def test_to_taxonomy_records_produces_correct_count(
        self, normaliser, sample_uscg_df
    ):
        df = normaliser.normalise(sample_uscg_df, source="uscg")
        records = normaliser.to_taxonomy_records(df, source="uscg")
        assert len(records) == 2

    def test_to_taxonomy_records_classify_human_error(self, normaliser, sample_uscg_df):
        df = normaliser.normalise(sample_uscg_df, source="uscg")
        records = normaliser.to_taxonomy_records(df, source="uscg")
        # First record: "operator error during bridge watch"
        assert records[0].root_cause == RootCauseType.HUMAN_ERROR

    def test_to_taxonomy_records_classify_equipment_failure(
        self, normaliser, sample_uscg_df
    ):
        df = normaliser.normalise(sample_uscg_df, source="uscg")
        records = normaliser.to_taxonomy_records(df, source="uscg")
        # Second record: "machinery failure in engine room"
        assert records[1].root_cause == RootCauseType.EQUIPMENT_FAILURE

    def test_to_taxonomy_records_fatality_count(self, normaliser, sample_uscg_df):
        df = normaliser.normalise(sample_uscg_df, source="uscg")
        records = normaliser.to_taxonomy_records(df, source="uscg")
        assert records[1].fatality_count == 1


# ---------------------------------------------------------------------------
# build_taxonomy_summary
# ---------------------------------------------------------------------------


class TestBuildTaxonomySummary:
    def test_empty_list_returns_empty_df(self):
        result = build_taxonomy_summary([])
        assert result.empty

    def test_single_record_produces_one_row(self):
        r = _make_record(root_cause=RootCauseType.HUMAN_ERROR, source="uscg")
        result = build_taxonomy_summary([r])
        assert len(result) == 1
        assert result.iloc[0]["count"] == 1

    def test_aggregates_multiple_records_same_cause_source(self):
        records = [
            _make_record(
                report_id="A", root_cause=RootCauseType.HUMAN_ERROR, source="uscg"
            ),
            _make_record(
                report_id="B", root_cause=RootCauseType.HUMAN_ERROR, source="uscg"
            ),
        ]
        result = build_taxonomy_summary(records)
        assert result.iloc[0]["count"] == 2

    def test_separates_different_sources(self):
        records = [
            _make_record(
                report_id="A", source="uscg", root_cause=RootCauseType.HUMAN_ERROR
            ),
            _make_record(
                report_id="B", source="maib", root_cause=RootCauseType.HUMAN_ERROR
            ),
        ]
        result = build_taxonomy_summary(records)
        assert len(result) == 2

    def test_sums_fatalities(self):
        records = [
            _make_record(
                report_id="A",
                source="uscg",
                root_cause=RootCauseType.EQUIPMENT_FAILURE,
                fatality_count=2,
            ),
            _make_record(
                report_id="B",
                source="uscg",
                root_cause=RootCauseType.EQUIPMENT_FAILURE,
                fatality_count=1,
            ),
        ]
        result = build_taxonomy_summary(records)
        assert result.iloc[0]["fatalities"] == 3


# ---------------------------------------------------------------------------
# load_dataframe_as_uscg (in-memory USCG client path)
# ---------------------------------------------------------------------------


class TestLoadDataframeAsUSCG:
    def test_returns_taxonomy_records(self, sample_uscg_df):
        records = load_dataframe_as_uscg(sample_uscg_df)
        assert isinstance(records, list)
        assert all(isinstance(r, TaxonomyRecord) for r in records)

    def test_record_source_is_uscg(self, sample_uscg_df):
        records = load_dataframe_as_uscg(sample_uscg_df)
        assert all(r.source == "uscg" for r in records)

    def test_empty_df_returns_empty_list(self):
        records = load_dataframe_as_uscg(pd.DataFrame())
        assert records == []


class TestDescribeUSCGDataset:
    def test_empty_df_returns_zero_records(self):
        result = describe_uscg_dataset(pd.DataFrame())
        assert result["total_records"] == 0

    def test_populated_df_returns_correct_count(self, sample_uscg_df):
        from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
            IncidentDataFrameNormaliser,
        )

        normalised = IncidentDataFrameNormaliser().normalise(
            sample_uscg_df, source="uscg"
        )
        result = describe_uscg_dataset(normalised)
        assert result["total_records"] == 2

    def test_vessel_types_extracted(self, sample_uscg_df):
        from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
            IncidentDataFrameNormaliser,
        )

        normalised = IncidentDataFrameNormaliser().normalise(
            sample_uscg_df, source="uscg"
        )
        result = describe_uscg_dataset(normalised)
        assert "cargo" in result["vessel_types"]


# ---------------------------------------------------------------------------
# IncidentCorrelator
# ---------------------------------------------------------------------------


class TestIncidentCorrelator:
    def test_same_source_records_never_matched(self):
        corr = IncidentCorrelator()
        a = _make_record("A", source="uscg")
        b = _make_record("B", source="uscg")
        matches = corr.correlate([a], [b])
        assert matches == []

    def test_matching_records_different_sources_produce_match(self):
        corr = IncidentCorrelator(config=CorrelationConfig(date_window_days=3))
        a = _make_record(
            "A",
            source="uscg",
            incident_date="2021-03-15",
            vessel_name="MV ATLANTIC RANGER",
            latitude=29.5,
            longitude=-94.2,
        )
        b = _make_record(
            "B",
            source="maib",
            incident_date="2021-03-16",
            vessel_name="MV ATLANTIC RANGER",
            latitude=29.55,
            longitude=-94.1,
        )
        matches = corr.correlate([a], [b])
        assert len(matches) == 1

    def test_match_confidence_between_zero_and_one(self):
        corr = IncidentCorrelator(config=CorrelationConfig(date_window_days=3))
        a = _make_record(
            "A",
            source="uscg",
            incident_date="2021-03-15",
            vessel_name="ATLANTIC RANGER",
        )
        b = _make_record(
            "B",
            source="maib",
            incident_date="2021-03-16",
            vessel_name="ATLANTIC RANGER",
        )
        matches = corr.correlate([a], [b])
        assert 0.0 <= matches[0].confidence <= 1.0

    def test_date_too_far_apart_no_match(self):
        corr = IncidentCorrelator(config=CorrelationConfig(date_window_days=2))
        a = _make_record("A", source="uscg", incident_date="2021-01-01")
        b = _make_record("B", source="ntsb", incident_date="2021-06-01")
        matches = corr.correlate([a], [b])
        assert matches == []

    def test_location_too_far_no_match(self):
        corr = IncidentCorrelator(
            config=CorrelationConfig(date_window_days=10, location_threshold_km=10.0)
        )
        a = _make_record(
            "A",
            source="uscg",
            incident_date="2021-01-01",
            latitude=29.0,
            longitude=-90.0,
        )
        b = _make_record(
            "B", source="maib", incident_date="2021-01-02", latitude=51.5, longitude=0.1
        )  # London vs Gulf of Mexico
        matches = corr.correlate([a], [b])
        assert matches == []

    def test_correlate_multi_three_sources(self):
        corr = IncidentCorrelator(config=CorrelationConfig(date_window_days=5))
        a = _make_record(
            "A", source="uscg", incident_date="2021-03-15", vessel_name="TEST SHIP"
        )
        b = _make_record(
            "B", source="maib", incident_date="2021-03-16", vessel_name="TEST SHIP"
        )
        c = _make_record(
            "C", source="ntsb", incident_date="2021-03-17", vessel_name="TEST SHIP"
        )
        matches = corr.correlate_multi([a], [b], [c])
        assert len(matches) >= 2  # A-B and A-C and B-C all possible

    def test_correlate_multi_deduplicates(self):
        corr = IncidentCorrelator(config=CorrelationConfig(date_window_days=5))
        a = _make_record(
            "A", source="uscg", incident_date="2021-01-10", vessel_name="SHARED"
        )
        b = _make_record(
            "B", source="maib", incident_date="2021-01-11", vessel_name="SHARED"
        )
        # Pass same sets twice — should deduplicate by (report_id_a, report_id_b)
        matches = corr.correlate_multi([a], [b], [b])
        ids = [(m.record_a.report_id, m.record_b.report_id) for m in matches]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# build_correlation_summary
# ---------------------------------------------------------------------------


class TestBuildCorrelationSummary:
    def test_empty_list_returns_empty_df(self):
        result = build_correlation_summary([])
        assert result.empty

    def test_columns_present(self):
        a = _make_record("A", source="uscg", incident_date="2021-01-01")
        b = _make_record("B", source="maib", incident_date="2021-01-02")
        match = CorrelationMatch(
            record_a=a,
            record_b=b,
            date_diff_days=1,
            distance_km=15.0,
            name_similarity=0.9,
            confidence=0.85,
            match_reasons=["date_diff=1d"],
        )
        df = build_correlation_summary([match])
        for col in ("report_id_a", "source_a", "report_id_b", "source_b", "confidence"):
            assert col in df.columns

    def test_one_match_one_row(self):
        a = _make_record("A", source="uscg")
        b = _make_record("B", source="maib")
        match = CorrelationMatch(
            record_a=a,
            record_b=b,
            date_diff_days=0,
            distance_km=0.0,
            name_similarity=1.0,
            confidence=1.0,
        )
        df = build_correlation_summary([match])
        assert len(df) == 1


# ---------------------------------------------------------------------------
# build_pattern_report
# ---------------------------------------------------------------------------


class TestBuildPatternReport:
    def test_empty_list_returns_empty_df(self):
        result = build_pattern_report([])
        assert result.empty

    def test_expected_columns_present(self):
        r = _make_record(incident_date="2021-01-01", vessel_type="tanker")
        result = build_pattern_report([r])
        for col in ("year", "vessel_type", "root_cause", "source", "count"):
            assert col in result.columns

    def test_year_extracted_correctly(self):
        r = _make_record(incident_date="2021-06-15")
        result = build_pattern_report([r])
        assert result.iloc[0]["year"] == 2021

    def test_aggregates_same_group(self):
        records = [
            _make_record(
                "A",
                incident_date="2021-01-01",
                vessel_type="cargo",
                root_cause=RootCauseType.HUMAN_ERROR,
                source="uscg",
            ),
            _make_record(
                "B",
                incident_date="2021-06-01",
                vessel_type="cargo",
                root_cause=RootCauseType.HUMAN_ERROR,
                source="uscg",
            ),
        ]
        result = build_pattern_report(records)
        row = result[
            (result["vessel_type"] == "cargo") & (result["root_cause"] == "human_error")
        ]
        assert row["count"].sum() == 2

    def test_handles_none_dates(self):
        r = _make_record(incident_date=None)
        result = build_pattern_report([r])
        assert not result.empty
        # None dates become NaN in the groupby result
        assert pd.isna(result.iloc[0]["year"])


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


class TestDaysApart:
    def test_same_date_returns_zero(self):
        assert _days_apart("2021-01-01", "2021-01-01") == 0

    def test_one_day_apart(self):
        assert _days_apart("2021-01-01", "2021-01-02") == 1

    def test_missing_date_returns_none(self):
        assert _days_apart(None, "2021-01-01") is None
        assert _days_apart("2021-01-01", None) is None

    def test_us_format_date(self):
        result = _days_apart("03/15/2021", "2021-03-16")
        assert result == 1


class TestJaccardSimilarity:
    def test_identical_names_score_one(self):
        assert _jaccard_similarity("ATLANTIC RANGER", "ATLANTIC RANGER") == 1.0

    def test_no_overlap_score_zero(self):
        assert _jaccard_similarity("ATLANTIC RANGER", "PACIFIC STAR") == 0.0

    def test_partial_overlap(self):
        score = _jaccard_similarity("ATLANTIC RANGER", "ATLANTIC EXPLORER")
        assert 0.0 < score < 1.0

    def test_none_input_returns_zero(self):
        assert _jaccard_similarity(None, "VESSEL") == 0.0

    def test_empty_string_returns_zero(self):
        assert _jaccard_similarity("", "VESSEL") == 0.0


class TestHaversine:
    def test_same_point_returns_zero(self):
        assert _haversine(29.5, -94.0, 29.5, -94.0) == pytest.approx(0.0, abs=0.001)

    def test_known_distance(self):
        # Approximate distance: Houston area (29.5, -94) to New Orleans (29.95, -90.07) ≈ 375 km
        dist = _haversine(29.5, -94.0, 29.95, -90.07)
        assert 350 < dist < 420

    def test_missing_longitude_returns_inf(self):
        assert _haversine(29.5, None, 29.6, -94.0) == float("inf")


class TestExtractYear:
    def test_standard_iso_date(self):
        assert _extract_year("2021-06-15") == 2021

    def test_none_returns_none(self):
        assert _extract_year(None) is None

    def test_invalid_string_returns_none(self):
        assert _extract_year("not-a-date") is None


class TestSafeHelpers:
    def test_safe_str_none_returns_none(self):
        assert _safe_str(None) is None

    def test_safe_str_nan_returns_none(self):
        assert _safe_str(float("nan")) is None

    def test_safe_str_strips_whitespace(self):
        assert _safe_str("  hello  ") == "hello"

    def test_safe_float_none_returns_none(self):
        assert _safe_float(None) is None

    def test_safe_float_valid_value(self):
        assert _safe_float("29.5") == pytest.approx(29.5)

    def test_safe_float_invalid_string_returns_none(self):
        assert _safe_float("not-a-number") is None


# ---------------------------------------------------------------------------
# CorrelationConfig validation
# ---------------------------------------------------------------------------


class TestCorrelationConfig:
    def test_negative_date_window_raises(self):
        with pytest.raises(ValueError, match="date_window_days"):
            CorrelationConfig(date_window_days=-1)

    def test_zero_location_raises(self):
        with pytest.raises(ValueError, match="location_threshold_km"):
            CorrelationConfig(location_threshold_km=0)

    def test_name_similarity_out_of_range_raises(self):
        with pytest.raises(ValueError, match="name_similarity_threshold"):
            CorrelationConfig(name_similarity_threshold=1.5)

    def test_defaults_are_valid(self):
        cfg = CorrelationConfig()
        assert cfg.date_window_days == 5
        assert cfg.location_threshold_km == 100.0
