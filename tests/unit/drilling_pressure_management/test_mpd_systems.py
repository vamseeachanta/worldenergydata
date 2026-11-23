"""Tests for MPD system catalog — mpd_systems module."""

import pandas as pd
import pytest

from worldenergydata.drilling_pressure_management.mpd_systems import (
    MPD_SYSTEMS,
    MPDSystemEntry,
    get_system,
    get_systems_by_rig_type,
    get_systems_by_type,
    systems_summary,
)


class TestMPDSystemsCatalog:
    def test_catalog_has_at_least_five_entries(self):
        assert len(MPD_SYSTEMS) >= 5

    def test_all_entries_are_mpd_system_entry_instances(self):
        for entry in MPD_SYSTEMS:
            assert isinstance(entry, MPDSystemEntry)

    def test_all_system_ids_are_non_empty(self):
        for entry in MPD_SYSTEMS:
            assert entry.system_id and isinstance(entry.system_id, str)

    def test_all_manufacturers_are_non_empty(self):
        for entry in MPD_SYSTEMS:
            assert entry.manufacturer and isinstance(entry.manufacturer, str)

    def test_all_product_names_are_non_empty(self):
        for entry in MPD_SYSTEMS:
            assert entry.product_name and isinstance(entry.product_name, str)

    def test_all_mpd_types_are_valid(self):
        valid_types = {"CBHP", "PMCD", "dual_gradient", "RFC", "multi_mode"}
        for entry in MPD_SYSTEMS:
            assert (
                entry.mpd_type in valid_types
            ), f"{entry.system_id} has unknown mpd_type={entry.mpd_type!r}"

    def test_all_max_pressure_ratings_positive(self):
        for entry in MPD_SYSTEMS:
            assert (
                entry.max_pressure_rating_psi > 0
            ), f"{entry.system_id} has non-positive pressure rating"

    def test_all_max_flow_rates_positive(self):
        for entry in MPD_SYSTEMS:
            assert (
                entry.max_flow_rate_gpm > 0
            ), f"{entry.system_id} has non-positive flow rate"

    def test_all_key_features_non_empty(self):
        for entry in MPD_SYSTEMS:
            assert entry.key_features, f"{entry.system_id} has empty key_features"

    def test_all_key_features_have_at_least_three_items(self):
        for entry in MPD_SYSTEMS:
            assert (
                len(entry.key_features) >= 3
            ), f"{entry.system_id} has fewer than 3 key_features"

    def test_all_compatible_rig_types_non_empty(self):
        for entry in MPD_SYSTEMS:
            assert (
                entry.compatible_rig_types
            ), f"{entry.system_id} has empty compatible_rig_types"

    def test_all_suitable_water_depths_non_empty(self):
        for entry in MPD_SYSTEMS:
            assert (
                entry.suitable_water_depths
            ), f"{entry.system_id} has empty suitable_water_depths"

    def test_system_ids_are_unique(self):
        ids = [s.system_id for s in MPD_SYSTEMS]
        assert len(ids) == len(set(ids)), "Duplicate system_id values found"


class TestGetSystem:
    def test_get_safekick_returns_correct_entry(self):
        entry = get_system("safekick_mpd")
        assert entry.system_id == "safekick_mpd"
        assert entry.manufacturer == "Safekick (Halliburton)"

    def test_get_ec_drill_returns_correct_entry(self):
        entry = get_system("ec_drill")
        assert entry.system_id == "ec_drill"
        assert entry.mpd_type == "PMCD"

    def test_get_unknown_system_raises_key_error(self):
        with pytest.raises(KeyError, match="unknown_system"):
            get_system("unknown_system")

    def test_get_onesubsea_has_highest_pressure_rating(self):
        entry = get_system("onesubsea_mpd")
        assert entry.max_pressure_rating_psi == 20000.0

    def test_get_microflux_compatible_with_land_rigs(self):
        entry = get_system("microflux_weatherford")
        assert "land" in entry.compatible_rig_types


class TestGetSystemsByType:
    def test_cbhp_returns_non_empty_list(self):
        result = get_systems_by_type("CBHP")
        assert len(result) >= 1

    def test_pmcd_returns_non_empty_list(self):
        result = get_systems_by_type("PMCD")
        assert len(result) >= 1

    def test_dual_gradient_returns_non_empty_list(self):
        result = get_systems_by_type("dual_gradient")
        assert len(result) >= 1

    def test_unknown_type_returns_empty_list(self):
        result = get_systems_by_type("nonexistent_type")
        assert result == []

    def test_cbhp_entries_all_have_correct_type(self):
        for entry in get_systems_by_type("CBHP"):
            assert entry.mpd_type == "CBHP"


class TestGetSystemsByRigType:
    def test_drillship_returns_non_empty_list(self):
        result = get_systems_by_rig_type("drillship")
        assert len(result) >= 1

    def test_semisubmersible_returns_non_empty_list(self):
        result = get_systems_by_rig_type("semisubmersible")
        assert len(result) >= 1

    def test_unknown_rig_type_returns_empty_list(self):
        result = get_systems_by_rig_type("submarine")
        assert result == []

    def test_jackup_compatible_entries_include_jackup(self):
        for entry in get_systems_by_rig_type("jackup"):
            assert "jackup" in entry.compatible_rig_types


class TestSystemsSummary:
    def test_returns_dataframe(self):
        df = systems_summary()
        assert isinstance(df, pd.DataFrame)

    def test_dataframe_has_expected_columns(self):
        df = systems_summary()
        expected = {
            "system_id",
            "manufacturer",
            "product_name",
            "mpd_type",
            "max_pressure_rating_psi",
            "max_flow_rate_gpm",
        }
        assert expected.issubset(set(df.columns))

    def test_dataframe_row_count_matches_catalog(self):
        df = systems_summary()
        assert len(df) == len(MPD_SYSTEMS)

    def test_dataframe_pressure_ratings_all_positive(self):
        df = systems_summary()
        assert (df["max_pressure_rating_psi"] > 0).all()
