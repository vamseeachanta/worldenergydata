"""Tests for vessel_fleet bridge to legacy BSEE rig_fleet format.

TDD Red phase: tests written before implementation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.bridge.rig_fleet_bridge import (
    LEGACY_COLUMNS,
    convert_curated_to_rig_fleet,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CURATED_PARQUET = Path(
    "data/modules/vessel_fleet/curated/drilling_rigs.parquet"
)


def _make_curated_df(**overrides: object) -> pd.DataFrame:
    """Build a minimal curated DataFrame with sensible defaults."""
    defaults = {
        "RIG_NAME": ["DEEPWATER ATLAS", "VALARIS DS-16", None],
        "VESSEL_NAME": ["DEEPWATER ATLAS", "VALARIS DS-16", "Stena IceMAX"],
        "RIG_TYPE": ["drillship", "drillship", "drillship"],
        "RIG_STATUS": ["active", "active", None],
        "OWNER": ["Transocean", "Valaris", "Stena"],
        "OPERATOR": [None, None, None],
        "IMO_NUMBER": ["9618888", None, "9529130"],
        "FLAG_STATE": ["Marshall Islands", None, "Bahamas"],
        "WATER_DEPTH_RATING_FT": [12000.0, 10000.0, 10000.0],
        "DRILLING_DEPTH_RATING_FT": [40000.0, None, 35000.0],
        "MAX_WATER_DEPTH_FT": [9800.0, 8000.0, None],
        "LOA_M": [228.0, None, 228.0],
        "BEAM_M": [42.0, None, 41.0],
        "DISPLACEMENT_TONNES": [96000.0, None, None],
        "MOONPOOL_DIAMETER_M": [12.0, None, None],
        "DP_CLASS": [3.0, None, 3.0],
        "YEAR_BUILT": [2021.0, None, 2012.0],
        "WELLS_DRILLED_COUNT": [15.0, 200.0, None],
        "LAST_WAR_DATE": ["2025-12-01", "2024-06-15", None],
        "FIRST_WAR_DATE": ["2022-01-15", "2010-03-01", None],
        "LAST_AREA_CODE": ["GC", "MC", None],
        "LAST_BLOCK_NUMBER": ["738", "252", None],
        "DATA_SOURCE": ["bsee_war", "bsee_war", "contractor_fleet_page"],
        "IS_OFFSHORE": [True, True, True],
        # Extra columns that should NOT appear in output
        "VESSEL_CATEGORY": ["drilling_rig", "drilling_rig", "drilling_rig"],
        "RIG_DESIGN": ["GustoMSC", None, "Samsung 10000"],
        "DATA_SOURCE_URL": [None, None, "https://example.com"],
        "NOTES": [None, None, "Added from scrape"],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


# ---------------------------------------------------------------------------
# Test: RIG_NAME populated from VESSEL_NAME
# ---------------------------------------------------------------------------


class TestRigNamePopulation:
    """Verify RIG_NAME fallback from VESSEL_NAME."""

    def test_rig_name_populated_from_vessel_name(self) -> None:
        """Rows with null RIG_NAME get VESSEL_NAME as fallback."""
        df = _make_curated_df()
        result = convert_curated_to_rig_fleet(df)

        # Third row had null RIG_NAME, should now be "Stena IceMAX"
        stena = result[result["RIG_NAME"] == "Stena IceMAX"]
        assert len(stena) == 1

    def test_rig_name_preserved_when_present(self) -> None:
        """Rows with existing RIG_NAME keep their original value."""
        df = _make_curated_df()
        result = convert_curated_to_rig_fleet(df)

        atlas = result[result["RIG_NAME"] == "DEEPWATER ATLAS"]
        assert len(atlas) == 1


# ---------------------------------------------------------------------------
# Test: rows without any name are dropped
# ---------------------------------------------------------------------------


class TestDropNullNames:
    """Verify rows with both null RIG_NAME and VESSEL_NAME are dropped."""

    def test_rows_without_any_name_dropped(self) -> None:
        """Rows where both RIG_NAME and VESSEL_NAME are null are removed."""
        df = _make_curated_df(
            RIG_NAME=[None, "VALID_RIG", None],
            VESSEL_NAME=[None, "VALID_RIG", "FALLBACK"],
        )
        result = convert_curated_to_rig_fleet(df)

        # First row has both null -> dropped; third has VESSEL_NAME fallback
        assert len(result) == 2
        assert "VALID_RIG" in result["RIG_NAME"].values
        assert "FALLBACK" in result["RIG_NAME"].values


# ---------------------------------------------------------------------------
# Test: output columns are legacy-only
# ---------------------------------------------------------------------------


class TestOutputColumns:
    """Verify only legacy RigFleetSchema columns are present."""

    def test_output_columns_are_legacy_only(self) -> None:
        """No VESSEL_NAME, DATA_SOURCE_URL, RIG_DESIGN in output."""
        df = _make_curated_df()
        result = convert_curated_to_rig_fleet(df)

        assert "VESSEL_NAME" not in result.columns
        assert "DATA_SOURCE_URL" not in result.columns
        assert "RIG_DESIGN" not in result.columns
        assert "VESSEL_CATEGORY" not in result.columns
        assert "NOTES" not in result.columns

    def test_all_legacy_columns_present(self) -> None:
        """All columns from LEGACY_COLUMNS are in the output."""
        df = _make_curated_df()
        result = convert_curated_to_rig_fleet(df)

        for col in LEGACY_COLUMNS:
            assert col in result.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# Test: all RIG_NAMEs are non-null
# ---------------------------------------------------------------------------


class TestAllRigNamesNonNull:
    """Verify every output row has a non-null RIG_NAME."""

    def test_all_rig_names_non_null(self) -> None:
        """Every output row has a non-null RIG_NAME."""
        df = _make_curated_df()
        result = convert_curated_to_rig_fleet(df)

        assert result["RIG_NAME"].notna().all()
        assert (result["RIG_NAME"].str.strip() != "").all()


# ---------------------------------------------------------------------------
# Test: DATA_SOURCE preserved
# ---------------------------------------------------------------------------


class TestDataSourcePreserved:
    """Verify DATA_SOURCE values are unchanged through conversion."""

    def test_data_source_preserved(self) -> None:
        """DATA_SOURCE values unchanged from input."""
        df = _make_curated_df()
        result = convert_curated_to_rig_fleet(df)

        sources = result["DATA_SOURCE"].tolist()
        assert "bsee_war" in sources
        assert "contractor_fleet_page" in sources


# ---------------------------------------------------------------------------
# Test: RIG_TYPE values are valid
# ---------------------------------------------------------------------------


class TestRigTypeValidation:
    """Verify RIG_TYPE values are valid enum strings."""

    VALID_RIG_TYPES = {
        "drillship",
        "semi_submersible",
        "jack_up",
        "platform_rig",
        "tender_assisted",
        "inland_barge",
        "submersible",
        "land_rig",
        "wireline_unit",
        "coil_tubing_unit",
        "lift_boat",
        "snubbing_unit",
        "workover_rig",
        "support_vessel",
        "pumping_unit",
        "unknown",
    }

    def test_rig_type_values_valid(self) -> None:
        """All non-null RIG_TYPE values are valid enum strings."""
        df = _make_curated_df()
        result = convert_curated_to_rig_fleet(df)

        non_null_types = result["RIG_TYPE"].dropna().unique()
        for rt in non_null_types:
            assert rt in self.VALID_RIG_TYPES, f"Invalid RIG_TYPE: {rt}"


# ---------------------------------------------------------------------------
# Integration tests with real curated data
# ---------------------------------------------------------------------------


class TestRealCuratedData:
    """Integration tests reading actual curated parquet file."""

    @pytest.mark.skipif(
        not CURATED_PARQUET.exists(),
        reason="Curated parquet not found on disk",
    )
    def test_real_curated_data_converts(self) -> None:
        """Real curated data converts without error."""
        df = pd.read_parquet(CURATED_PARQUET)
        result = convert_curated_to_rig_fleet(df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    @pytest.mark.skipif(
        not CURATED_PARQUET.exists(),
        reason="Curated parquet not found on disk",
    )
    def test_real_curated_data_row_count(self) -> None:
        """Converted output has >= 2000 rows."""
        df = pd.read_parquet(CURATED_PARQUET)
        result = convert_curated_to_rig_fleet(df)

        assert len(result) >= 2000, (
            f"Expected >= 2000 rows, got {len(result)}"
        )

    @pytest.mark.skipif(
        not CURATED_PARQUET.exists(),
        reason="Curated parquet not found on disk",
    )
    def test_real_all_rig_names_non_null(self) -> None:
        """Every row in real converted data has a non-null RIG_NAME."""
        df = pd.read_parquet(CURATED_PARQUET)
        result = convert_curated_to_rig_fleet(df)

        assert result["RIG_NAME"].notna().all()

    @pytest.mark.skipif(
        not CURATED_PARQUET.exists(),
        reason="Curated parquet not found on disk",
    )
    def test_real_data_source_preserved(self) -> None:
        """DATA_SOURCE values in real data are unchanged."""
        df = pd.read_parquet(CURATED_PARQUET)
        original_sources = set(df["DATA_SOURCE"].dropna().unique())
        result = convert_curated_to_rig_fleet(df)
        result_sources = set(result["DATA_SOURCE"].dropna().unique())

        assert result_sources == original_sources

    @pytest.mark.skipif(
        not CURATED_PARQUET.exists(),
        reason="Curated parquet not found on disk",
    )
    def test_real_rig_type_values_valid(self) -> None:
        """All non-null RIG_TYPE values in real data are valid enums."""
        valid = TestRigTypeValidation.VALID_RIG_TYPES
        df = pd.read_parquet(CURATED_PARQUET)
        result = convert_curated_to_rig_fleet(df)

        non_null_types = result["RIG_TYPE"].dropna().unique()
        for rt in non_null_types:
            assert rt in valid, f"Invalid RIG_TYPE: {rt}"
