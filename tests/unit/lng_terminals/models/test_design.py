"""Tests for LNG terminal design models."""

import pytest

from worldenergydata.lng_terminals.constants import PipelineType
from worldenergydata.lng_terminals.models.design import (
    HullDesign,
    MarineInfrastructure,
    PipelineSpec,
    ProcessEquipment,
    StorageSpec,
)


class TestHullDesign:
    def test_minimal(self):
        hull = HullDesign(hull_type="ship-shaped")
        assert hull.hull_type == "ship-shaped"
        assert hull.loa_m is None
        assert hull.beam_m is None

    def test_full(self):
        hull = HullDesign(
            hull_type="barge",
            loa_m=300.0,
            beam_m=60.0,
            depth_m=30.0,
            draft_m=12.0,
            displacement_tonnes=250000,
            mooring_type="internal_turret",
            riser_count=8,
            year_built=2015,
        )
        assert hull.loa_m == 300.0
        assert hull.riser_count == 8
        assert hull.year_built == 2015


class TestPipelineSpec:
    def test_minimal(self):
        pipe = PipelineSpec(pipeline_type=PipelineType.FEED_GAS)
        assert pipe.pipeline_type == PipelineType.FEED_GAS
        assert pipe.offshore_segment is False

    def test_full(self):
        pipe = PipelineSpec(
            pipeline_type=PipelineType.LNG_LOADING,
            diameter_inches=16.0,
            length_km=5.0,
            wall_thickness_mm=25.4,
            material="duplex SS",
            design_pressure_barg=150,
            design_temperature_c=-162,
            insulation_type="PUF",
            offshore_segment=True,
        )
        assert pipe.diameter_inches == 16.0
        assert pipe.offshore_segment is True


class TestProcessEquipment:
    def test_defaults(self):
        proc = ProcessEquipment()
        assert proc.liquefaction_process is None
        assert proc.number_of_trains is None
        assert proc.regasification_capacity_mmscfd is None

    def test_full(self):
        proc = ProcessEquipment(
            liquefaction_process="C3MR",
            number_of_trains=4,
            capacity_per_train_mtpa=5.0,
            compressor_type="centrifugal",
            compressor_driver="gas turbine",
            compressor_power_mw=80.0,
        )
        assert proc.liquefaction_process == "C3MR"
        assert proc.number_of_trains == 4


class TestStorageSpec:
    def test_minimal(self):
        storage = StorageSpec(tank_type="full_containment")
        assert storage.tank_type == "full_containment"
        assert storage.number_of_tanks is None

    def test_auto_compute_total_capacity(self):
        storage = StorageSpec(
            tank_type="membrane_mark_iii",
            number_of_tanks=4,
            capacity_per_tank_m3=160000,
        )
        assert storage.total_capacity_m3 == 640000

    def test_no_override_when_total_provided(self):
        storage = StorageSpec(
            tank_type="full_containment",
            number_of_tanks=2,
            capacity_per_tank_m3=100000,
            total_capacity_m3=250000,
        )
        assert storage.total_capacity_m3 == 250000

    def test_no_compute_when_missing_fields(self):
        storage = StorageSpec(
            tank_type="spb",
            number_of_tanks=3,
        )
        assert storage.total_capacity_m3 is None


class TestMarineInfrastructure:
    def test_defaults(self):
        marine = MarineInfrastructure()
        assert marine.water_depth_m is None
        assert marine.jetty_count is None
        assert marine.breakwater is None

    def test_full(self):
        marine = MarineInfrastructure(
            water_depth_m=15.0,
            jetty_count=2,
            berth_count=3,
            max_vessel_size_m3=266000,
            loading_arms_count=4,
            loading_arm_size_inches=16.0,
            loading_rate_m3_per_hr=12000,
            breakwater=True,
        )
        assert marine.water_depth_m == 15.0
        assert marine.loading_arms_count == 4
        assert marine.breakwater is True
