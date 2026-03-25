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


class TestDrillingRigSchemaHullGeometry:
    """Hull geometry fields for RAO / diffraction analysis mapping."""

    def test_hull_form_type(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            HULL_FORM_TYPE="semi_sub",
        )
        assert schema.HULL_FORM_TYPE == "semi_sub"

    def test_hull_form_type_empty_to_none(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", HULL_FORM_TYPE="")
        assert schema.HULL_FORM_TYPE is None

    def test_semisub_pontoon_column_fields(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            HULL_FORM_TYPE="semi_sub",
            PONTOON_LENGTH_M=114.0,
            PONTOON_WIDTH_M=17.7,
            PONTOON_HEIGHT_M=10.4,
            COLUMN_DIAMETER_M=17.7,
            COLUMN_SPACING_M=58.6,
            COLUMN_COUNT=4,
        )
        assert schema.PONTOON_LENGTH_M == 114.0
        assert schema.PONTOON_WIDTH_M == 17.7
        assert schema.PONTOON_HEIGHT_M == 10.4
        assert schema.COLUMN_DIAMETER_M == 17.7
        assert schema.COLUMN_SPACING_M == 58.6
        assert schema.COLUMN_COUNT == 4

    def test_stability_parameters(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            GM_M=3.5,
            VCG_M=18.2,
        )
        assert schema.GM_M == 3.5
        assert schema.VCG_M == 18.2

    def test_hull_library_ref(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            HULL_LIBRARY_REF="semi_sub_gvA7500",
        )
        assert schema.HULL_LIBRARY_REF == "semi_sub_gvA7500"

    def test_pontoon_float_from_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", PONTOON_LENGTH_M="114.0")
        assert schema.PONTOON_LENGTH_M == 114.0

    def test_column_count_from_float_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", COLUMN_COUNT="4.0")
        assert schema.COLUMN_COUNT == 4

    def test_negative_pontoon_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", PONTOON_LENGTH_M=-10)

    def test_negative_gm_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", GM_M=-1)

    def test_drillship_hull_form(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER PROTEUS",
            HULL_FORM_TYPE="drillship",
            LOA_M=238.0,
            BEAM_M=42.0,
            DRAFT_M=12.0,
            DISPLACEMENT_TONNES=96000.0,
        )
        assert schema.HULL_FORM_TYPE == "drillship"
        assert schema.LOA_M == 238.0


class TestDrillingRigSchemaValidation:
    def test_negative_water_depth_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", WATER_DEPTH_RATING_FT=-100)

    def test_negative_hookload_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", HOOKLOAD_RATING_KIPS=-1)
