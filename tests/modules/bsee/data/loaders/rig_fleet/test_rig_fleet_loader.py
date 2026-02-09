"""Tests for RigFleetLoader - TDD Red phase.

Tests cover:
- Binary file loading and caching
- WAR data aggregation into fleet inventory
- Override CSV application
- Rig well history queries
- New aggregation fields (FIRST_WAR_DATE, MAX_WATER_DEPTH_FT)
- DATA_SOURCE and IS_OFFSHORE auto-set
- .local/ fallback loading
- Offshore status filtering
"""

from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.data.loaders.rig_fleet.rig_fleet_loader import (
    RigFleetLoader,
)


# ---------------------------------------------------------------------------
# _load_data tests
# ---------------------------------------------------------------------------


class TestLoadData:
    """Tests for binary file loading and caching."""

    def test_load_data_returns_none_when_no_bin_files(self, tmp_path: Path):
        """Empty directory produces None."""
        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)
        result = loader._load_data()
        assert result is None

    def test_load_data_caches_result(self, tmp_path: Path):
        """Second call returns cached data without re-reading files."""
        # Arrange - write a bin file
        df = pd.DataFrame({"RIG_NAME": ["RIG_A"], "RIG_TYPE": ["drillship"]})
        bin_file = tmp_path / "fleet.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(df, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)

        # Act - load twice
        first = loader._load_data()
        # Remove the bin file so second load must use cache
        bin_file.unlink()
        second = loader._load_data()

        # Assert - both return the same object
        assert first is second
        assert len(first) == 1

    def test_load_data_from_bin_file(self, tmp_path: Path):
        """Correctly loads a pickled DataFrame from .bin file."""
        expected = pd.DataFrame({
            "RIG_NAME": ["DEEPWATER TITAN", "ROWAN GORILLA"],
            "RIG_TYPE": ["drillship", "jack_up"],
        })
        bin_file = tmp_path / "rigs.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(expected, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)
        result = loader._load_data()

        assert result is not None
        assert len(result) == 2
        assert list(result["RIG_NAME"]) == ["DEEPWATER TITAN", "ROWAN GORILLA"]

    def test_load_data_uses_custom_path_from_cfg(self, tmp_path: Path):
        """Config override for bin path is respected."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        df = pd.DataFrame({"RIG_NAME": ["STENA DRILLMAX"]})
        with open(custom_dir / "custom.bin", "wb") as f:
            pickle.dump(df, f)

        loader = RigFleetLoader()
        cfg = {
            "parameters": {
                "filepath": {
                    "rig_fleet": {"bin": str(custom_dir)}
                }
            }
        }
        result = loader._load_data(cfg)

        assert result is not None
        assert result["RIG_NAME"].iloc[0] == "STENA DRILLMAX"

    def test_load_data_prefers_local_dir(self, tmp_path: Path):
        """Data from .local/ directory takes precedence over bin/."""
        # Create bin directory with sample data
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        df_bin = pd.DataFrame({"RIG_NAME": ["SAMPLE_RIG"]})
        with open(bin_dir / "fleet.bin", "wb") as f:
            pickle.dump(df_bin, f)

        # Create .local directory with full data
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        df_local = pd.DataFrame({"RIG_NAME": ["FULL_RIG_A", "FULL_RIG_B"]})
        with open(local_dir / "rig_fleet_full.bin", "wb") as f:
            pickle.dump(df_local, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(bin_dir)
        loader._local_dir = str(local_dir)
        result = loader._load_data()

        assert result is not None
        assert len(result) == 2
        assert "FULL_RIG_A" in result["RIG_NAME"].values

    def test_load_data_falls_back_to_bin_when_no_local(self, tmp_path: Path):
        """Falls back to bin/ when .local/ doesn't exist."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        df_bin = pd.DataFrame({"RIG_NAME": ["SAMPLE_RIG"]})
        with open(bin_dir / "fleet.bin", "wb") as f:
            pickle.dump(df_bin, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(bin_dir)
        loader._local_dir = str(tmp_path / "nonexistent")
        result = loader._load_data()

        assert result is not None
        assert result["RIG_NAME"].iloc[0] == "SAMPLE_RIG"


# ---------------------------------------------------------------------------
# build_fleet_from_war tests
# ---------------------------------------------------------------------------


class TestBuildFleetFromWar:
    """Tests for WAR data aggregation into fleet inventory."""

    def test_build_fleet_from_war_basic(self):
        """Three unique rigs from five WAR records produces 3 rows."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B", "RIG_A", "RIG_C", "RIG_B"],
            "API_WELL_NUMBER": ["001", "002", "003", "004", "005"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert len(result) == 3
        assert set(result["RIG_NAME"]) == {"RIG_A", "RIG_B", "RIG_C"}

    def test_build_fleet_from_war_filters_non_rig(self):
        """Rows with 'NON RIG UNIT OPERATION' are excluded."""
        war_df = pd.DataFrame({
            "RIG_NAME": [
                "DEEPWATER TITAN",
                "NON RIG UNIT OPERATION",
                "NON RIG SPECIAL",
            ],
            "API_WELL_NUMBER": ["001", "002", "003"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert len(result) == 1
        assert result["RIG_NAME"].iloc[0] == "DEEPWATER TITAN"

    def test_build_fleet_from_war_filters_empty_names(self):
        """Rows with empty or null RIG_NAME are excluded."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["VALID_RIG", "", None, "   "],
            "API_WELL_NUMBER": ["001", "002", "003", "004"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert len(result) == 1
        assert result["RIG_NAME"].iloc[0] == "VALID_RIG"

    def test_build_fleet_from_war_classifies_types(self):
        """Rig type classification is applied to fleet entries."""
        war_df = pd.DataFrame({
            "RIG_NAME": [
                "T.O. DEEPWATER TITAN",
                "ROWAN GORILLA V",
                "GENERIC RIG",
            ],
            "API_WELL_NUMBER": ["001", "002", "003"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        type_map = dict(zip(result["RIG_NAME"], result["RIG_TYPE"]))
        assert type_map["T.O. DEEPWATER TITAN"] == "drillship"
        assert type_map["ROWAN GORILLA V"] == "jack_up"
        assert type_map["GENERIC RIG"] == "unknown"

    def test_build_fleet_from_war_aggregates_wells(self):
        """Rig with 3 distinct API numbers gets WELLS_DRILLED_COUNT=3."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["RIG_X", "RIG_X", "RIG_X"],
            "API_WELL_NUMBER": ["API_1", "API_2", "API_3"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert len(result) == 1
        assert result["WELLS_DRILLED_COUNT"].iloc[0] == 3

    def test_build_fleet_from_war_no_rig_name_column(self):
        """DataFrame without RIG_NAME column returns empty DataFrame."""
        war_df = pd.DataFrame({
            "WELL_NAME": ["WELL_A"],
            "API_WELL_NUMBER": ["001"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert result.empty

    def test_build_fleet_from_war_tracks_last_war_date(self):
        """LAST_WAR_DATE is the max WAR_END_DT per rig."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["RIG_Y", "RIG_Y", "RIG_Y"],
            "WAR_END_DT": ["2023-01-01", "2024-06-15", "2023-07-01"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert result["LAST_WAR_DATE"].iloc[0] == "2024-06-15"

    def test_build_fleet_from_war_tracks_first_war_date(self):
        """FIRST_WAR_DATE is the min WAR_START_DT per rig."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["RIG_Z", "RIG_Z", "RIG_Z"],
            "WAR_START_DT": ["2020-03-15", "2018-01-01", "2019-06-01"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert result["FIRST_WAR_DATE"].iloc[0] == "2018-01-01"

    def test_build_fleet_from_war_tracks_max_water_depth(self):
        """MAX_WATER_DEPTH_FT is the max WATER_DEPTH per rig."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["RIG_W", "RIG_W", "RIG_W"],
            "WATER_DEPTH": [500.0, 8500.0, 3200.0],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert result["MAX_WATER_DEPTH_FT"].iloc[0] == 8500.0

    def test_build_fleet_from_war_sets_data_source(self):
        """DATA_SOURCE is set to 'bsee_war' for all rows."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B"],
            "API_WELL_NUMBER": ["001", "002"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert (result["DATA_SOURCE"] == "bsee_war").all()

    def test_build_fleet_from_war_sets_is_offshore(self):
        """IS_OFFSHORE is set to True for all BSEE WAR rows."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B"],
            "API_WELL_NUMBER": ["001", "002"],
        })
        loader = RigFleetLoader()
        result = loader.build_fleet_from_war(war_df)

        assert (result["IS_OFFSHORE"] == True).all()  # noqa: E712


# ---------------------------------------------------------------------------
# load_overrides tests
# ---------------------------------------------------------------------------


class TestLoadOverrides:
    """Tests for CSV override application."""

    def test_load_overrides_applies_corrections(self, tmp_path: Path):
        """Override CSV changes rig type for matching rig name."""
        fleet_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B"],
            "RIG_TYPE": ["unknown", "unknown"],
        })
        overrides_path = tmp_path / "overrides.csv"
        overrides_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A"],
            "RIG_TYPE": ["drillship"],
        })
        overrides_df.to_csv(overrides_path, index=False)

        loader = RigFleetLoader()
        result = loader.load_overrides(overrides_path, fleet_df)

        type_map = dict(zip(result["RIG_NAME"], result["RIG_TYPE"]))
        assert type_map["RIG_A"] == "drillship"
        assert type_map["RIG_B"] == "unknown"

    def test_load_overrides_missing_file(self, tmp_path: Path):
        """Nonexistent overrides file returns original DataFrame."""
        fleet_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A"],
            "RIG_TYPE": ["unknown"],
        })
        missing_path = tmp_path / "does_not_exist.csv"

        loader = RigFleetLoader()
        result = loader.load_overrides(missing_path, fleet_df)

        pd.testing.assert_frame_equal(result, fleet_df)

    def test_load_overrides_adds_new_columns(self, tmp_path: Path):
        """Override CSV with extra columns adds them to fleet DataFrame."""
        fleet_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A"],
            "RIG_TYPE": ["drillship"],
        })
        overrides_path = tmp_path / "overrides.csv"
        overrides_df = pd.DataFrame({
            "RIG_NAME": ["RIG_A"],
            "OWNER": ["Company X"],
        })
        overrides_df.to_csv(overrides_path, index=False)

        loader = RigFleetLoader()
        result = loader.load_overrides(overrides_path, fleet_df)

        assert "OWNER" in result.columns
        assert result.loc[result["RIG_NAME"] == "RIG_A", "OWNER"].iloc[0] == "Company X"


# ---------------------------------------------------------------------------
# get_rig_well_history tests
# ---------------------------------------------------------------------------


class TestGetRigWellHistory:
    """Tests for rig well history retrieval."""

    def test_get_rig_well_history(self):
        """Filter WAR by rig name, case insensitive."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["Rig Alpha", "RIG ALPHA", "Rig Beta"],
            "API_WELL_NUMBER": ["001", "002", "003"],
        })
        loader = RigFleetLoader()
        result = loader.get_rig_well_history("rig alpha", war_df)

        assert result is not None
        assert len(result) == 2

    def test_get_rig_well_history_not_found(self):
        """Rig name not in WAR returns None."""
        war_df = pd.DataFrame({
            "RIG_NAME": ["Rig Alpha"],
            "API_WELL_NUMBER": ["001"],
        })
        loader = RigFleetLoader()
        result = loader.get_rig_well_history("NONEXISTENT RIG", war_df)

        assert result is None


# ---------------------------------------------------------------------------
# get_rigs_by_type tests
# ---------------------------------------------------------------------------


class TestGetRigsByType:
    """Tests for rig type filtering."""

    def test_get_rigs_by_type_found(self, tmp_path: Path):
        """Filters loaded data by RIG_TYPE correctly."""
        df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B", "RIG_C"],
            "RIG_TYPE": ["drillship", "jack_up", "drillship"],
        })
        bin_file = tmp_path / "fleet.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(df, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)
        result = loader.get_rigs_by_type("drillship")

        assert result is not None
        assert len(result) == 2

    def test_get_rigs_by_type_none_found(self, tmp_path: Path):
        """Returns None when no rigs match the requested type."""
        df = pd.DataFrame({
            "RIG_NAME": ["RIG_A"],
            "RIG_TYPE": ["jack_up"],
        })
        bin_file = tmp_path / "fleet.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(df, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)
        result = loader.get_rigs_by_type("drillship")

        assert result is None


# ---------------------------------------------------------------------------
# get_rigs_by_offshore_status tests
# ---------------------------------------------------------------------------


class TestGetRigsByOffshoreStatus:
    """Tests for offshore status filtering."""

    def test_filter_offshore_rigs(self, tmp_path: Path):
        """Filters loaded data by IS_OFFSHORE == True."""
        df = pd.DataFrame({
            "RIG_NAME": ["OFFSHORE_A", "LAND_B", "OFFSHORE_C"],
            "IS_OFFSHORE": [True, False, True],
        })
        bin_file = tmp_path / "fleet.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(df, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)
        result = loader.get_rigs_by_offshore_status(True)

        assert result is not None
        assert len(result) == 2

    def test_filter_onshore_rigs(self, tmp_path: Path):
        """Filters loaded data by IS_OFFSHORE == False."""
        df = pd.DataFrame({
            "RIG_NAME": ["OFFSHORE_A", "LAND_B"],
            "IS_OFFSHORE": [True, False],
        })
        bin_file = tmp_path / "fleet.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(df, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)
        result = loader.get_rigs_by_offshore_status(False)

        assert result is not None
        assert len(result) == 1
        assert result["RIG_NAME"].iloc[0] == "LAND_B"

    def test_filter_returns_none_when_no_column(self, tmp_path: Path):
        """Returns None when IS_OFFSHORE column is missing."""
        df = pd.DataFrame({
            "RIG_NAME": ["RIG_A"],
            "RIG_TYPE": ["drillship"],
        })
        bin_file = tmp_path / "fleet.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(df, f)

        loader = RigFleetLoader()
        loader._bin_dir = str(tmp_path)
        result = loader.get_rigs_by_offshore_status(True)

        assert result is None
