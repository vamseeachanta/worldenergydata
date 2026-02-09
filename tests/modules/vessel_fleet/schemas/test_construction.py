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
            VESSEL_NAME="T", MAIN_CRANE_CAPACITY_T="14200",
        )
        assert schema.MAIN_CRANE_CAPACITY_T == 14200.0

    def test_float_empty_to_none(self):
        schema = ConstructionVesselSchema(
            VESSEL_NAME="T", PIPELAY_TENSION_T="",
        )
        assert schema.PIPELAY_TENSION_T is None

    def test_string_empty_to_none(self):
        schema = ConstructionVesselSchema(
            VESSEL_NAME="T", PIPELAY_METHOD="",
        )
        assert schema.PIPELAY_METHOD is None

    def test_int_from_float_string(self):
        schema = ConstructionVesselSchema(VESSEL_NAME="T", ROV_SYSTEMS="2.0")
        assert schema.ROV_SYSTEMS == 2


class TestConstructionVesselSchemaValidation:
    def test_negative_crane_capacity_raises(self):
        with pytest.raises(Exception):
            ConstructionVesselSchema(
                VESSEL_NAME="T", MAIN_CRANE_CAPACITY_T=-100,
            )

    def test_negative_deck_area_raises(self):
        with pytest.raises(Exception):
            ConstructionVesselSchema(VESSEL_NAME="T", DECK_AREA_M2=-1)
