"""Tests for the construction vessel schema."""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.schemas.construction_vessel import (
    ConstructionVesselSchema,
)


class TestConstructionVesselSchemaInheritance:
    def test_inherits_base_fields(self):
        schema = ConstructionVesselSchema(VESSEL_NAME="SLEIPNIR")
        assert schema.VESSEL_NAME == "SLEIPNIR"
        assert schema.OWNER is None

    def test_construction_specific_fields(self):
        schema = ConstructionVesselSchema(
            VESSEL_NAME="SLEIPNIR",
            MAIN_CRANE_CAPACITY_T=10000.0,
            MAIN_CRANE_REACH_M=48.0,
            DECK_AREA_M2=11000.0,
        )
        assert schema.MAIN_CRANE_CAPACITY_T == 10000.0
        assert schema.MAIN_CRANE_REACH_M == 48.0
        assert schema.DECK_AREA_M2 == 11000.0


class TestConstructionVesselSchemaCoercion:
    def test_float_from_string(self):
        schema = ConstructionVesselSchema(
            VESSEL_NAME="T",
            MAIN_CRANE_CAPACITY_T="14200",
        )
        assert schema.MAIN_CRANE_CAPACITY_T == 14200.0

    def test_float_empty_to_none(self):
        schema = ConstructionVesselSchema(
            VESSEL_NAME="T",
            PIPELAY_TENSION_T="",
        )
        assert schema.PIPELAY_TENSION_T is None

    def test_string_empty_to_none(self):
        schema = ConstructionVesselSchema(
            VESSEL_NAME="T",
            PIPELAY_METHOD="",
        )
        assert schema.PIPELAY_METHOD is None

    def test_int_from_float_string(self):
        schema = ConstructionVesselSchema(VESSEL_NAME="T", ROV_SYSTEMS="2.0")
        assert schema.ROV_SYSTEMS == 2


class TestConstructionVesselSchemaValidation:
    def test_negative_crane_capacity_raises(self):
        with pytest.raises(Exception):
            ConstructionVesselSchema(
                VESSEL_NAME="T",
                MAIN_CRANE_CAPACITY_T=-100,
            )

    def test_negative_deck_area_raises(self):
        with pytest.raises(Exception):
            ConstructionVesselSchema(VESSEL_NAME="T", DECK_AREA_M2=-1)


class TestPipelayBurialFields:
    """#701 — pipelay firing-line + burial capability fields."""

    PIPELAY_BURIAL_KWARGS = {
        "WELDING_STATIONS_COUNT": 5,
        "TOTAL_STATIONS_COUNT": 9,
        "NDT_STATIONS_COUNT": 2,
        "WELDING_METHOD": "manual+automatic",
        "TENSIONER_COUNT": 3,
        "PIPELAY_MIN_DIAMETER_IN": 4.0,
        "SLAY_CENTER_CAPABLE": True,
        "SLAY_SIDE_CAPABLE": False,
        "JLAY_CAPABLE": True,
        "REEL_PERMANENT_CAPABLE": False,
        "REEL_REMOVABLE_CAPABLE": True,
        "CAROUSEL_CAPABLE": False,
        "TOW_INSTALL_CAPABLE": True,
        "TOW_METHODS": "surface,mid-depth,on-bottom",
        "BURIAL_CAPABLE": True,
        "SIMULTANEOUS_LAY_BURY_CAPABLE": False,
        "BURIAL_MIN_DIAMETER_IN": 4.0,
        "BURIAL_MAX_DIAMETER_IN": 60.0,
        "BURIAL_MAX_WATER_DEPTH_M": 243.8,
        "PIPELAY_MIN_WATER_DEPTH_M": 6.1,
        "PIPELAY_MAX_WATER_DEPTH_M": 3048.0,
        "EXPERIENCE_WATER_DEPTH_M": 2286.0,
        "PIPE_JOINT_LENGTH_MAX_M": 12.8,
        "DAVITS_COUNT": 4,
    }

    def test_all_new_fields_default_to_none(self):
        schema = ConstructionVesselSchema(VESSEL_NAME="T")
        for field in self.PIPELAY_BURIAL_KWARGS:
            assert getattr(schema, field) is None, field

    def test_round_trip_with_new_columns(self):
        """model_dump -> re-validate keeps every new field intact."""
        schema = ConstructionVesselSchema(
            VESSEL_NAME="CASTORO 10",
            **self.PIPELAY_BURIAL_KWARGS,
        )
        dumped = schema.model_dump()
        rebuilt = ConstructionVesselSchema(**dumped)
        for field, expected in self.PIPELAY_BURIAL_KWARGS.items():
            assert getattr(rebuilt, field) == expected, field

    def test_count_fields_coerce_from_float_strings(self):
        schema = ConstructionVesselSchema(
            VESSEL_NAME="T",
            WELDING_STATIONS_COUNT="5.0",
            TOTAL_STATIONS_COUNT="9.0",
            TENSIONER_COUNT="3.0",
            DAVITS_COUNT="4.0",
        )
        assert schema.WELDING_STATIONS_COUNT == 5
        assert schema.TOTAL_STATIONS_COUNT == 9
        assert schema.TENSIONER_COUNT == 3
        assert schema.DAVITS_COUNT == 4

    def test_empty_strings_coerce_to_none(self):
        """CSV empty cells must load as nulls for every new field."""
        schema = ConstructionVesselSchema(
            VESSEL_NAME="T",
            **{field: "" for field in self.PIPELAY_BURIAL_KWARGS},
        )
        for field in self.PIPELAY_BURIAL_KWARGS:
            assert getattr(schema, field) is None, field

    def test_negative_new_floats_raise(self):
        with pytest.raises(Exception):
            ConstructionVesselSchema(
                VESSEL_NAME="T",
                PIPELAY_MIN_DIAMETER_IN=-2.0,
            )
        with pytest.raises(Exception):
            ConstructionVesselSchema(
                VESSEL_NAME="T",
                BURIAL_MAX_WATER_DEPTH_M=-1.0,
            )
