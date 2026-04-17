"""Tests for construction vessel domain model."""

from worldenergydata.vessel_fleet.models.construction_vessel import (
    ConstructionVesselEntry,
)


class TestConstructionVesselEntry:
    def test_required(self):
        v = ConstructionVesselEntry(vessel_name="Thialf")
        assert v.vessel_name == "Thialf"

    def test_defaults(self):
        v = ConstructionVesselEntry(vessel_name="T")
        assert v.main_crane_capacity_t is None
        assert v.pipelay_capacity_in is None
        assert v.water_depth_rating_m is None

    def test_is_heavy_lift_crane(self):
        v = ConstructionVesselEntry(
            vessel_name="Thialf",
            main_crane_capacity_t=14200.0,
        )
        assert v.is_heavy_lift is True

    def test_is_heavy_lift_capacity(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            heavy_lift_capacity_t=6000.0,
        )
        assert v.is_heavy_lift is True

    def test_is_heavy_lift_below_threshold(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            main_crane_capacity_t=4000.0,
        )
        assert v.is_heavy_lift is False

    def test_is_heavy_lift_none(self):
        v = ConstructionVesselEntry(vessel_name="T")
        assert v.is_heavy_lift is False

    def test_is_heavy_lift_boundary(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            main_crane_capacity_t=5000.0,
        )
        assert v.is_heavy_lift is True

    def test_is_deepwater_capable_true(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            water_depth_rating_m=3000.0,
        )
        assert v.is_deepwater_capable is True

    def test_is_deepwater_capable_false(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            water_depth_rating_m=1500.0,
        )
        assert v.is_deepwater_capable is False

    def test_is_deepwater_capable_none(self):
        v = ConstructionVesselEntry(vessel_name="T")
        assert v.is_deepwater_capable is False

    def test_is_deepwater_capable_boundary(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            water_depth_rating_m=2000.0,
        )
        assert v.is_deepwater_capable is True

    def test_is_pipelay_capacity(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            pipelay_capacity_in=48.0,
        )
        assert v.is_pipelay is True

    def test_is_pipelay_tension(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            pipelay_tension_t=600.0,
        )
        assert v.is_pipelay is True

    def test_is_pipelay_false(self):
        v = ConstructionVesselEntry(vessel_name="T")
        assert v.is_pipelay is False

    def test_is_crane_vessel(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            main_crane_capacity_t=5000.0,
        )
        assert v.is_crane_vessel is True

    def test_is_crane_vessel_false(self):
        v = ConstructionVesselEntry(vessel_name="T")
        assert v.is_crane_vessel is False

    def test_total_crane_capacity(self):
        v = ConstructionVesselEntry(
            vessel_name="Thialf",
            main_crane_capacity_t=14200.0,
            aux_crane_capacity_t=1500.0,
        )
        assert v.total_crane_capacity_t == 15700.0

    def test_total_crane_capacity_main_only(self):
        v = ConstructionVesselEntry(
            vessel_name="T",
            main_crane_capacity_t=5000.0,
        )
        assert v.total_crane_capacity_t == 5000.0

    def test_total_crane_capacity_none(self):
        v = ConstructionVesselEntry(vessel_name="T")
        assert v.total_crane_capacity_t == 0.0

    def test_inherits_base_properties(self):
        v = ConstructionVesselEntry(
            vessel_name="Thialf",
            status="active",
        )
        assert v.is_active is True
        assert v.vessel_key == "thialf"
