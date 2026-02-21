"""
Tests for CrossDatabaseAnalyzer live importer integration.

Verifies:
- data_freshness field on CrossDatabaseResult
- Live MAIB and TSB importer paths using fixture CSVs
- Graceful fallback to synthetic when importer fails
- Schema column preservation for live data
- Mixed live + synthetic source sets
- Per-source normalizer helpers
"""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.marine_safety.cross_database import (
    CrossDatabaseAnalyzer,
    CrossDatabaseQuery,
    CrossDatabaseResult,
    _calc_severity,
    _normalize_incident_type,
    _normalize_region_maib,
    _normalize_region_tsb,
    _normalize_vessel_type,
)

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent / "fixtures" / "marine_safety"
)


@pytest.fixture
def maib_fixture() -> Path:
    """Path to the MAIB sample occurrences CSV fixture."""
    p = FIXTURES_DIR / "maib_occurrences_sample.csv"
    assert p.exists(), f"MAIB fixture not found: {p}"
    return p


@pytest.fixture
def tsb_fixture() -> Path:
    """Path to the TSB sample occurrence CSV fixture."""
    p = FIXTURES_DIR / "tsb_occurrence_sample.csv"
    assert p.exists(), f"TSB fixture not found: {p}"
    return p


# ---------------------------------------------------------------------------
# data_freshness field — default (synthetic)
# ---------------------------------------------------------------------------


class TestDataFreshnessSynthetic:
    def test_data_freshness_field_exists_on_result(self):
        analyzer = CrossDatabaseAnalyzer()
        result = analyzer.query(CrossDatabaseQuery())
        assert hasattr(result, "data_freshness")

    def test_data_freshness_synthetic_by_default(self):
        analyzer = CrossDatabaseAnalyzer()
        result = analyzer.query(CrossDatabaseQuery())
        assert result.data_freshness == "synthetic"

    def test_data_freshness_synthetic_when_no_importer_config(self):
        analyzer = CrossDatabaseAnalyzer(importer_config={})
        result = analyzer.query(CrossDatabaseQuery())
        assert result.data_freshness == "synthetic"

    def test_synthetic_result_has_at_least_200_incidents(self):
        analyzer = CrossDatabaseAnalyzer()
        result = analyzer.query(CrossDatabaseQuery())
        assert result.total_incidents >= 200


# ---------------------------------------------------------------------------
# Live MAIB importer
# ---------------------------------------------------------------------------


class TestLiveMAIBImporter:
    def test_data_freshness_live_when_maib_configured(self, maib_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery())
        assert result.data_freshness == "live"

    def test_live_maib_data_present_in_results(self, maib_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        assert len(result.data) > 0

    def test_live_maib_source_column_correct(self, maib_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        assert set(result.data["source"].unique()) == {"maib"}

    def test_live_maib_schema_columns_all_present(self, maib_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        for col in CrossDatabaseAnalyzer.SCHEMA_COLUMNS:
            assert col in result.data.columns, f"Missing column: {col}"

    def test_live_maib_no_null_incident_ids(self, maib_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        assert result.data["incident_id"].notna().all()

    def test_live_maib_fatalities_integer(self, maib_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        assert pd.api.types.is_integer_dtype(result.data["fatalities"])

    def test_live_maib_injuries_integer(self, maib_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        assert pd.api.types.is_integer_dtype(result.data["injuries"])

    def test_live_maib_severity_values_valid(self, maib_fixture):
        valid_severities = {"minor", "moderate", "serious", "very_serious", "fatal"}
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        actual = set(result.data["severity"].unique())
        assert actual.issubset(valid_severities), (
            f"Unexpected severity values: {actual - valid_severities}"
        )


# ---------------------------------------------------------------------------
# Live TSB importer
# ---------------------------------------------------------------------------


class TestLiveTSBImporter:
    def test_data_freshness_live_when_tsb_configured(self, tsb_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"tsb": {"occurrence_file": tsb_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery())
        assert result.data_freshness == "live"

    def test_live_tsb_data_present_in_results(self, tsb_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"tsb": {"occurrence_file": tsb_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["tsb"]))
        assert len(result.data) > 0

    def test_live_tsb_source_column_correct(self, tsb_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"tsb": {"occurrence_file": tsb_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["tsb"]))
        assert set(result.data["source"].unique()) == {"tsb"}

    def test_live_tsb_schema_columns_all_present(self, tsb_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"tsb": {"occurrence_file": tsb_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["tsb"]))
        for col in CrossDatabaseAnalyzer.SCHEMA_COLUMNS:
            assert col in result.data.columns, f"Missing column: {col}"

    def test_live_tsb_no_null_incident_ids(self, tsb_fixture):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"tsb": {"occurrence_file": tsb_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["tsb"]))
        assert result.data["incident_id"].notna().all()


# ---------------------------------------------------------------------------
# Fallback to synthetic on bad file path
# ---------------------------------------------------------------------------


class TestGracefulFallback:
    def test_fallback_to_synthetic_on_missing_maib_file(self):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={
                "maib": {"occurrences_file": Path("/nonexistent_maib.csv")}
            }
        )
        result = analyzer.query(CrossDatabaseQuery())
        assert result.data_freshness == "synthetic"

    def test_fallback_synthetic_dataset_intact(self):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={
                "maib": {"occurrences_file": Path("/nonexistent_maib.csv")}
            }
        )
        result = analyzer.query(CrossDatabaseQuery())
        assert result.total_incidents >= 200

    def test_fallback_to_synthetic_on_missing_tsb_file(self):
        analyzer = CrossDatabaseAnalyzer(
            importer_config={
                "tsb": {"occurrence_file": Path("/nonexistent_tsb.csv")}
            }
        )
        result = analyzer.query(CrossDatabaseQuery())
        assert result.data_freshness == "synthetic"

    def test_partial_fallback_single_bad_source(self, maib_fixture):
        """Good MAIB + bad TSB path → freshness still 'live' from MAIB."""
        analyzer = CrossDatabaseAnalyzer(
            importer_config={
                "maib": {"occurrences_file": maib_fixture},
                "tsb": {"occurrence_file": Path("/nonexistent_tsb.csv")},
            }
        )
        result = analyzer.query(CrossDatabaseQuery())
        # MAIB loaded live, so freshness is 'live' even though TSB fell back
        assert result.data_freshness == "live"


# ---------------------------------------------------------------------------
# Mixed live + synthetic sources
# ---------------------------------------------------------------------------


class TestMixedLiveAndSynthetic:
    def test_mixed_all_four_sources_present(self, maib_fixture):
        """MAIB live, others synthetic — all four sources still in result."""
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery())
        sources = set(result.data["source"].unique())
        assert "maib" in sources
        assert "imo" in sources
        assert "emsa" in sources
        assert "tsb" in sources

    def test_mixed_maib_live_tsb_live(self, maib_fixture, tsb_fixture):
        """Both MAIB and TSB live, IMO and EMSA synthetic."""
        analyzer = CrossDatabaseAnalyzer(
            importer_config={
                "maib": {"occurrences_file": maib_fixture},
                "tsb": {"occurrence_file": tsb_fixture},
            }
        )
        result = analyzer.query(CrossDatabaseQuery())
        sources = set(result.data["source"].unique())
        assert {"maib", "tsb", "imo", "emsa"}.issubset(sources)
        assert result.data_freshness == "live"

    def test_emsa_always_synthetic_even_with_importer_config(self, maib_fixture):
        """EMSA should always come from synthetic data."""
        analyzer = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        result = analyzer.query(CrossDatabaseQuery(sources=["emsa"]))
        assert len(result.data) > 0
        assert set(result.data["source"].unique()) == {"emsa"}

    def test_live_maib_replaces_synthetic_maib(self, maib_fixture):
        """When MAIB is live, live records replace the synthetic MAIB set."""
        analyzer_live = CrossDatabaseAnalyzer(
            importer_config={"maib": {"occurrences_file": maib_fixture}}
        )
        analyzer_syn = CrossDatabaseAnalyzer()

        result_live = analyzer_live.query(CrossDatabaseQuery(sources=["maib"]))
        result_syn = analyzer_syn.query(CrossDatabaseQuery(sources=["maib"]))

        # Live MAIB fixture has 7 records; synthetic has 50+
        # They should differ in count
        assert result_live.total_incidents != result_syn.total_incidents


# ---------------------------------------------------------------------------
# Normalizer unit tests
# ---------------------------------------------------------------------------


class TestNormalizeIncidentType:
    def test_collision_maps_to_collision(self):
        assert _normalize_incident_type("collision") == "collision"

    def test_contact_maps_to_collision(self):
        assert _normalize_incident_type("contact") == "collision"

    def test_grounding_maps_to_grounding(self):
        assert _normalize_incident_type("grounding") == "grounding"

    def test_fire_maps_to_fire(self):
        assert _normalize_incident_type("fire") == "fire"

    def test_flooding_maps_to_flooding(self):
        assert _normalize_incident_type("flooding") == "flooding"

    def test_capsizing_maps_to_capsizing(self):
        assert _normalize_incident_type("capsizing") == "capsizing"

    def test_personnel_injury_maps_to_man_overboard(self):
        assert _normalize_incident_type("personnel_injury") == "man_overboard"

    def test_equipment_failure_maps_to_machinery_failure(self):
        assert _normalize_incident_type("equipment_failure") == "machinery_failure"

    def test_empty_string_maps_to_other(self):
        assert _normalize_incident_type("") == "other"

    def test_unknown_maps_to_other(self):
        assert _normalize_incident_type("xyz_unknown_type") == "other"


class TestNormalizeVesselType:
    def test_tanker_maps_to_tanker(self):
        assert _normalize_vessel_type("tanker") == "tanker"

    def test_fishing_maps_to_fishing(self):
        assert _normalize_vessel_type("fishing") == "fishing"

    def test_bulk_carrier_maps_to_bulk_carrier(self):
        assert _normalize_vessel_type("bulk_carrier") == "bulk_carrier"

    def test_cargo_vessel_maps_to_general_cargo(self):
        assert _normalize_vessel_type("cargo_vessel") == "general_cargo"

    def test_tug_maps_to_tug(self):
        assert _normalize_vessel_type("tug") == "tug"

    def test_empty_maps_to_other(self):
        assert _normalize_vessel_type("") == "other"

    def test_unknown_maps_to_other(self):
        assert _normalize_vessel_type("hovercraft") == "other"


class TestNormalizeRegionMAIB:
    def test_united_kingdom_maps_to_north_sea(self):
        assert _normalize_region_maib("United Kingdom") == "north_sea"

    def test_north_sea_string_maps_to_north_sea(self):
        assert _normalize_region_maib("North Sea") == "north_sea"

    def test_empty_defaults_to_north_sea(self):
        assert _normalize_region_maib("") == "north_sea"

    def test_ireland_maps_to_atlantic(self):
        assert _normalize_region_maib("Ireland") == "atlantic"


class TestNormalizeRegionTSB:
    def test_bc_maps_to_pacific(self):
        assert _normalize_region_tsb("BRITISH COLUMBIA (BC)") == "pacific"

    def test_nova_scotia_maps_to_atlantic(self):
        assert _normalize_region_tsb("NOVA SCOTIA (NS)") == "atlantic"

    def test_nunavut_maps_to_arctic(self):
        assert _normalize_region_tsb("NUNAVUT (NU)") == "arctic"

    def test_empty_defaults_to_atlantic(self):
        assert _normalize_region_tsb("") == "atlantic"


class TestCalcSeverity:
    def test_one_fatality_returns_fatal(self):
        assert _calc_severity(1, 0) == "fatal"

    def test_three_injuries_returns_very_serious(self):
        assert _calc_severity(0, 3) == "very_serious"

    def test_one_injury_returns_serious(self):
        assert _calc_severity(0, 1) == "serious"

    def test_zero_casualties_returns_moderate(self):
        assert _calc_severity(0, 0) == "moderate"

    def test_none_casualties_returns_moderate(self):
        assert _calc_severity(None, None) == "moderate"
