"""Tests for the drilling rig schema."""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.schemas.drilling_rig import DrillingRigSchema


class TestDrillingRigSchemaInheritance:
    def test_inherits_base_fields(self):
        schema = DrillingRigSchema(VESSEL_NAME="DEEPWATER TITAN")
        assert schema.VESSEL_NAME == "DEEPWATER TITAN"
        assert schema.OWNER is None

    def test_rig_specific_fields(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER TITAN",
            WATER_DEPTH_RATING_FT=12000.0,
            DRILLING_DEPTH_RATING_FT=40000.0,
            BOP_PRESSURE_PSI=15000.0,
        )
        assert schema.WATER_DEPTH_RATING_FT == 12000.0
        assert schema.DRILLING_DEPTH_RATING_FT == 40000.0
        assert schema.BOP_PRESSURE_PSI == 15000.0


class TestDrillingRigSchemaCoercion:
    def test_float_from_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", WATER_DEPTH_RATING_FT="12000")
        assert schema.WATER_DEPTH_RATING_FT == 12000.0

    def test_float_empty_to_none(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", WATER_DEPTH_RATING_FT="")
        assert schema.WATER_DEPTH_RATING_FT is None

    def test_string_empty_to_none(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", RIG_TYPE="")
        assert schema.RIG_TYPE is None

    def test_int_from_float_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", MUD_PUMP_COUNT="4.0")
        assert schema.MUD_PUMP_COUNT == 4

    def test_jackup_fields(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="VALARIS 105",
            LEG_LENGTH_FT="500",
            CANTILEVER_REACH_FT="75",
            PRELOAD_CAPACITY_ST="16000",
        )
        assert schema.LEG_LENGTH_FT == 500.0
        assert schema.CANTILEVER_REACH_FT == 75.0


class TestDrillingRigSchemaValidation:
    def test_negative_water_depth_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", WATER_DEPTH_RATING_FT=-100)

    def test_negative_hookload_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", HOOKLOAD_RATING_KIPS=-1)
