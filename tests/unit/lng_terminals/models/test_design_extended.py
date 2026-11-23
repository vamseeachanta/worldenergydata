"""Extended tests for LNG terminal design models."""

import pytest
from pydantic import ValidationError

from worldenergydata.lng_terminals.constants import PipelineType
from worldenergydata.lng_terminals.models.design import (
    HullDesign,
    MarineInfrastructure,
    PipelineSpec,
    ProcessEquipment,
    StorageSpec,
)


class TestHullDesign:
    def test_required(self):
        h = HullDesign(hull_type="ship-shaped")
        assert h.hull_type == "ship-shaped"

    def test_optional_defaults(self):
        h = HullDesign(hull_type="ship-shaped")
        assert h.loa_m is None
        assert h.beam_m is None
        assert h.year_built is None

    def test_with_dimensions(self):
        h = HullDesign(
            hull_type="ship-shaped",
            loa_m=350.0,
            beam_m=55.0,
            depth_m=30.0,
            draft_m=12.0,
            displacement_tonnes=120000.0,
        )
        assert h.loa_m == 350.0
        assert h.displacement_tonnes == 120000.0

    def test_loa_too_large(self):
        with pytest.raises(ValidationError):
            HullDesign(hull_type="ship-shaped", loa_m=600.0)

    def test_negative_loa(self):
        with pytest.raises(ValidationError):
            HullDesign(hull_type="ship-shaped", loa_m=-10.0)

    def test_year_built_valid(self):
        h = HullDesign(hull_type="barge", year_built=2010)
        assert h.year_built == 2010

    def test_year_built_too_old(self):
        with pytest.raises(ValidationError):
            HullDesign(hull_type="barge", year_built=1940)

    def test_mooring_type(self):
        h = HullDesign(
            hull_type="ship-shaped",
            mooring_type="internal_turret",
        )
        assert h.mooring_type == "internal_turret"


class TestPipelineSpec:
    def test_required(self):
        p = PipelineSpec(pipeline_type=PipelineType.FEED_GAS)
        assert p.pipeline_type == PipelineType.FEED_GAS

    def test_optional_defaults(self):
        p = PipelineSpec(pipeline_type=PipelineType.FEED_GAS)
        assert p.diameter_inches is None
        assert p.offshore_segment is False

    def test_with_all_fields(self):
        p = PipelineSpec(
            pipeline_type=PipelineType.LNG_TRANSFER,
            diameter_inches=36.0,
            length_km=15.0,
            wall_thickness_mm=25.0,
            material="9% Ni",
            design_pressure_barg=100.0,
            design_temperature_c=-163.0,
            offshore_segment=True,
        )
        assert p.diameter_inches == 36.0
        assert p.offshore_segment is True

    def test_diameter_too_large(self):
        with pytest.raises(ValidationError):
            PipelineSpec(
                pipeline_type=PipelineType.FEED_GAS,
                diameter_inches=65.0,
            )

    def test_negative_length(self):
        with pytest.raises(ValidationError):
            PipelineSpec(
                pipeline_type=PipelineType.FEED_GAS,
                length_km=-10.0,
            )


class TestProcessEquipment:
    def test_defaults(self):
        p = ProcessEquipment()
        assert p.liquefaction_process is None
        assert p.number_of_trains is None

    def test_liquefaction_plant(self):
        p = ProcessEquipment(
            liquefaction_process="C3MR",
            number_of_trains=4,
            capacity_per_train_mtpa=5.0,
        )
        assert p.liquefaction_process == "C3MR"
        assert p.number_of_trains == 4

    def test_regasification(self):
        p = ProcessEquipment(
            regasification_capacity_mmscfd=1500.0,
            regasification_type="ORV",
        )
        assert p.regasification_capacity_mmscfd == 1500.0

    def test_boil_off_rate_too_high(self):
        with pytest.raises(ValidationError):
            ProcessEquipment(boil_off_rate_percent=1.5)

    def test_negative_trains(self):
        with pytest.raises(ValidationError):
            ProcessEquipment(number_of_trains=-1)

    def test_capacity_too_high(self):
        with pytest.raises(ValidationError):
            ProcessEquipment(capacity_per_train_mtpa=20.0)


class TestStorageSpec:
    def test_required(self):
        s = StorageSpec(tank_type="full_containment")
        assert s.tank_type == "full_containment"

    def test_auto_compute_total(self):
        s = StorageSpec(
            tank_type="membrane_mark_iii",
            number_of_tanks=4,
            capacity_per_tank_m3=180000.0,
        )
        assert s.total_capacity_m3 == pytest.approx(720000.0)

    def test_total_not_overridden(self):
        s = StorageSpec(
            tank_type="full_containment",
            number_of_tanks=4,
            capacity_per_tank_m3=180000.0,
            total_capacity_m3=500000.0,
        )
        assert s.total_capacity_m3 == 500000.0  # explicit not overwritten

    def test_partial_fields_no_compute(self):
        s = StorageSpec(
            tank_type="moss",
            number_of_tanks=4,
        )
        assert s.total_capacity_m3 is None

    def test_negative_tanks(self):
        with pytest.raises(ValidationError):
            StorageSpec(tank_type="full_containment", number_of_tanks=-1)


class TestMarineInfrastructure:
    def test_defaults(self):
        m = MarineInfrastructure()
        assert m.water_depth_m is None
        assert m.jetty_count is None
        assert m.breakwater is None

    def test_all_fields(self):
        m = MarineInfrastructure(
            water_depth_m=15.0,
            jetty_count=2,
            berth_count=3,
            max_vessel_size_m3=266000.0,
            loading_arms_count=5,
            loading_arm_size_inches=16.0,
            loading_rate_m3_per_hr=12000.0,
            breakwater=True,
            approach_channel_depth_m=14.0,
        )
        assert m.jetty_count == 2
        assert m.breakwater is True

    def test_water_depth_too_large(self):
        with pytest.raises(ValidationError):
            MarineInfrastructure(water_depth_m=6000.0)

    def test_negative_water_depth(self):
        with pytest.raises(ValidationError):
            MarineInfrastructure(water_depth_m=-10.0)
