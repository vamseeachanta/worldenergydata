"""Tests for rig-selection queries over the real spec database (#998)."""

import pytest

from worldenergydata.vessel_fleet import selection


@pytest.fixture(scope="module")
def fleet():
    return selection.load_spec_fleet()


class TestLoadSpecFleet:
    def test_six_contractors_loaded(self, fleet):
        assert fleet["OWNER"].nunique() >= 6

    def test_fleet_size(self, fleet):
        assert len(fleet) >= 180

    def test_rig_types(self, fleet):
        types = set(fleet["RIG_TYPE"].dropna())
        assert {"drillship", "semi_submersible", "jack_up"} <= types

    def test_all_rows_have_provenance(self, fleet):
        assert fleet["DATA_SOURCE_URL"].notna().all()


class TestFilterRigs:
    def test_deepwater_drillship_shortlist(self, fleet):
        result = selection.filter_rigs(
            fleet,
            rig_type="drillship",
            min_water_depth_ft=12_000,
            min_hookload_kips=2_500,
        )
        names = set(result["VESSEL_NAME"])
        assert "Deepwater Titan" in names  # 3,400 kips — 20k rig
        assert "Noble Valiant" in names  # 2,500 kips
        assert (result["RIG_TYPE"] == "drillship").all()

    def test_missing_field_is_not_qualified(self, fleet):
        # Rigs whose sheet omits hookload must not pass a hookload floor.
        result = selection.filter_rigs(fleet, min_hookload_kips=1)
        assert result["HOOKLOAD_RATING_KIPS"].notna().all()

    def test_moonpool_envelope(self, fleet):
        result = selection.filter_rigs(fleet, min_moonpool_length_m=30)
        names = set(result["VESSEL_NAME"])
        assert "Noble Stanley Lafosse" in names  # 35.1 m extended moonpool
        assert "Noble Valiant" not in names  # 25.6 m

    def test_jackup_leg_length(self, fleet):
        result = selection.filter_rigs(fleet, rig_type="jack_up", min_leg_length_ft=540)
        assert len(result) > 0
        assert (result["LEG_LENGTH_FT"] >= 540).all()
        assert "West Elara" in set(result["VESSEL_NAME"])  # 673 ft CJ70

    def test_unknown_criterion_raises(self, fleet):
        with pytest.raises(TypeError, match="min_torque"):
            selection.filter_rigs(fleet, min_torque=1)

    def test_owner_and_design_contains(self, fleet):
        result = selection.filter_rigs(
            fleet, owner_contains="transocean", design_contains="espadon"
        )
        assert set(result["VESSEL_NAME"]) >= {"Deepwater Titan", "Deepwater Atlas"}


class TestCompareRigs:
    def test_side_by_side(self, fleet):
        table = selection.compare_rigs(
            fleet, ["Deepwater Titan", "Noble Valiant", "VALARIS DS-18"]
        )
        assert list(table.columns.sort_values()) == [
            "Deepwater Titan",
            "Noble Valiant",
            "VALARIS DS-18",
        ]
        assert table.loc["MOONPOOL_LENGTH_M", "Deepwater Titan"] == 28.0
        assert table.loc["MOONPOOL_LENGTH_M", "Noble Valiant"] == 25.6

    def test_unknown_rig_raises(self, fleet):
        with pytest.raises(KeyError, match="NO SUCH RIG"):
            selection.compare_rigs(fleet, ["No Such Rig"])


class TestLandRigs:
    def test_land_classes_loaded(self, fleet):
        land = fleet[fleet["RIG_TYPE"] == "land_rig"]
        assert len(land) >= 10
        assert not land["IS_OFFSHORE"].any()

    def test_super_spec_hookload_floor(self, fleet):
        result = selection.filter_rigs(
            fleet, rig_type="land_rig", min_hookload_kips=1000
        )
        names = set(result["VESSEL_NAME"])
        assert "H&P FlexRig3W Arabia" in names  # 1,000,000 lb mast
        assert "Nabors PACE-X800" not in names  # 600 kip lower-bound variant

    def test_walking_rigs_have_field(self, fleet):
        land = fleet[fleet["RIG_TYPE"] == "land_rig"]
        assert land["WALKING_SYSTEM"].notna().all()


class TestFleetSummary:
    def test_summary_totals(self, fleet):
        summary = selection.fleet_summary(fleet)
        assert summary["rigs"].sum() == len(fleet)
        assert (
            summary[["drillships", "semis", "jackups"]].sum(axis=1) <= summary["rigs"]
        ).all()
