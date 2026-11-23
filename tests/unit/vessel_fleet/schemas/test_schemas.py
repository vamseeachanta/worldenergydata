"""Tests for vessel fleet Pydantic schemas."""

import pytest
from pydantic import ValidationError

from worldenergydata.vessel_fleet.schemas.base import BaseVesselSchema
from worldenergydata.vessel_fleet.schemas.construction_vessel import (
    ConstructionVesselSchema,
)
from worldenergydata.vessel_fleet.schemas.drilling_rig import DrillingRigSchema


class TestBaseVesselSchema:
    def test_required(self):
        s = BaseVesselSchema(VESSEL_NAME="Test Vessel")
        assert s.VESSEL_NAME == "Test Vessel"

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            BaseVesselSchema()

    def test_strip_quotes(self):
        s = BaseVesselSchema(VESSEL_NAME='"Thialf"')
        assert s.VESSEL_NAME == "Thialf"

    def test_strip_single_quotes(self):
        s = BaseVesselSchema(VESSEL_NAME="'Thialf'")
        assert s.VESSEL_NAME == "Thialf"

    def test_empty_str_to_none(self):
        s = BaseVesselSchema(
            VESSEL_NAME="T",
            OWNER="  ",
            OPERATOR="",
            FLAG_STATE=" ",
        )
        assert s.OWNER is None
        assert s.OPERATOR is None
        assert s.FLAG_STATE is None

    def test_float_coercion(self):
        s = BaseVesselSchema(
            VESSEL_NAME="T",
            LOA_M="201.5",
            BEAM_M=" 36.0 ",
        )
        assert s.LOA_M == 201.5
        assert s.BEAM_M == 36.0

    def test_float_empty_to_none(self):
        s = BaseVesselSchema(VESSEL_NAME="T", LOA_M="")
        assert s.LOA_M is None

    def test_negative_float_raises(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            BaseVesselSchema(VESSEL_NAME="T", LOA_M=-10.0)

    def test_int_coercion_from_string(self):
        s = BaseVesselSchema(VESSEL_NAME="T", DP_CLASS="3", YEAR_BUILT="2010")
        assert s.DP_CLASS == 3
        assert s.YEAR_BUILT == 2010

    def test_int_coercion_from_float(self):
        s = BaseVesselSchema(VESSEL_NAME="T", DP_CLASS=3.0)
        assert s.DP_CLASS == 3

    def test_int_from_float_string(self):
        s = BaseVesselSchema(VESSEL_NAME="T", DP_CLASS="3.0")
        assert s.DP_CLASS == 3

    def test_int_empty_to_none(self):
        s = BaseVesselSchema(VESSEL_NAME="T", DP_CLASS="")
        assert s.DP_CLASS is None

    def test_year_built_valid(self):
        s = BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT=2020)
        assert s.YEAR_BUILT == 2020

    def test_year_built_too_old(self):
        with pytest.raises(ValidationError, match="YEAR_BUILT"):
            BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT=1800)

    def test_year_built_too_future(self):
        with pytest.raises(ValidationError, match="YEAR_BUILT"):
            BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT=2036)

    def test_imo_valid(self):
        s = BaseVesselSchema(VESSEL_NAME="T", IMO_NUMBER="1234567")
        assert s.IMO_NUMBER == "1234567"

    def test_imo_too_short(self):
        with pytest.raises(
            ValidationError, match="IMO_NUMBER must be exactly 7 digits"
        ):
            BaseVesselSchema(VESSEL_NAME="T", IMO_NUMBER="12345")

    def test_imo_non_digit(self):
        with pytest.raises(ValidationError, match="IMO_NUMBER"):
            BaseVesselSchema(VESSEL_NAME="T", IMO_NUMBER="ABC1234")


class TestConstructionVesselSchema:
    def test_inherits_base(self):
        s = ConstructionVesselSchema(VESSEL_NAME="Thialf")
        assert s.VESSEL_NAME == "Thialf"
        assert s.LOA_M is None

    def test_crane_fields(self):
        s = ConstructionVesselSchema(
            VESSEL_NAME="Thialf",
            MAIN_CRANE_CAPACITY_T=14200.0,
            MAIN_CRANE_REACH_M=50.0,
        )
        assert s.MAIN_CRANE_CAPACITY_T == 14200.0
        assert s.MAIN_CRANE_REACH_M == 50.0

    def test_float_coercion(self):
        s = ConstructionVesselSchema(
            VESSEL_NAME="T",
            MAIN_CRANE_CAPACITY_T="5000",
            DECK_AREA_M2=" 4500.5 ",
        )
        assert s.MAIN_CRANE_CAPACITY_T == 5000.0
        assert s.DECK_AREA_M2 == 4500.5

    def test_float_empty_to_none(self):
        s = ConstructionVesselSchema(
            VESSEL_NAME="T",
            MAIN_CRANE_CAPACITY_T="",
        )
        assert s.MAIN_CRANE_CAPACITY_T is None

    def test_negative_crane_raises(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            ConstructionVesselSchema(
                VESSEL_NAME="T",
                MAIN_CRANE_CAPACITY_T=-100.0,
            )

    def test_empty_method_to_none(self):
        s = ConstructionVesselSchema(
            VESSEL_NAME="T",
            PIPELAY_METHOD="  ",
            FOUNDATION_TYPE="",
        )
        assert s.PIPELAY_METHOD is None
        assert s.FOUNDATION_TYPE is None

    def test_rov_int_coercion(self):
        s = ConstructionVesselSchema(VESSEL_NAME="T", ROV_SYSTEMS="2")
        assert s.ROV_SYSTEMS == 2

    def test_rov_empty_to_none(self):
        s = ConstructionVesselSchema(VESSEL_NAME="T", ROV_SYSTEMS="")
        assert s.ROV_SYSTEMS is None

    def test_rov_from_float(self):
        s = ConstructionVesselSchema(VESSEL_NAME="T", ROV_SYSTEMS=2.0)
        assert s.ROV_SYSTEMS == 2


class TestDrillingRigSchema:
    def test_inherits_base(self):
        s = DrillingRigSchema(VESSEL_NAME="Deepwater Nautilus")
        assert s.VESSEL_NAME == "Deepwater Nautilus"

    def test_rig_specific_fields(self):
        s = DrillingRigSchema(
            VESSEL_NAME="DN",
            RIG_TYPE="drillship",
            WATER_DEPTH_RATING_FT=10000.0,
            DRILLING_DEPTH_RATING_FT=30000.0,
            BOP_PRESSURE_PSI=15000.0,
        )
        assert s.RIG_TYPE == "drillship"
        assert s.WATER_DEPTH_RATING_FT == 10000.0

    def test_empty_rig_strings_to_none(self):
        s = DrillingRigSchema(
            VESSEL_NAME="T",
            RIG_TYPE="  ",
            RIG_STATUS="",
            BOP_MANUFACTURER=" ",
        )
        assert s.RIG_TYPE is None
        assert s.RIG_STATUS is None
        assert s.BOP_MANUFACTURER is None

    def test_float_coercion(self):
        s = DrillingRigSchema(
            VESSEL_NAME="T",
            WATER_DEPTH_RATING_FT="10000",
            DERRICK_HEIGHT_FT=" 200.5 ",
        )
        assert s.WATER_DEPTH_RATING_FT == 10000.0
        assert s.DERRICK_HEIGHT_FT == 200.5

    def test_negative_float_raises(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            DrillingRigSchema(
                VESSEL_NAME="T",
                WATER_DEPTH_RATING_FT=-100.0,
            )

    def test_int_coercion(self):
        s = DrillingRigSchema(
            VESSEL_NAME="T",
            MUD_PUMP_COUNT="4",
            WELLS_DRILLED_COUNT="250",
        )
        assert s.MUD_PUMP_COUNT == 4
        assert s.WELLS_DRILLED_COUNT == 250

    def test_int_from_float(self):
        s = DrillingRigSchema(VESSEL_NAME="T", COLUMN_COUNT=4.0)
        assert s.COLUMN_COUNT == 4

    def test_jackup_fields(self):
        s = DrillingRigSchema(
            VESSEL_NAME="Rowan",
            LEG_LENGTH_FT=500.0,
            CANTILEVER_REACH_FT=75.0,
            PRELOAD_CAPACITY_ST=18000.0,
        )
        assert s.LEG_LENGTH_FT == 500.0

    def test_hull_geometry_fields(self):
        s = DrillingRigSchema(
            VESSEL_NAME="T",
            HULL_FORM_TYPE="semi_sub",
            PONTOON_LENGTH_M=100.0,
            COLUMN_DIAMETER_M=15.0,
            GM_M=3.5,
        )
        assert s.HULL_FORM_TYPE == "semi_sub"
        assert s.GM_M == 3.5

    def test_onshore_fields(self):
        s = DrillingRigSchema(
            VESSEL_NAME="Land Rig 1",
            MAST_HEIGHT_FT=147.0,
            WALKING_SYSTEM=True,
            SUPER_SPEC=True,
        )
        assert s.MAST_HEIGHT_FT == 147.0
        assert s.WALKING_SYSTEM is True
        assert s.SUPER_SPEC is True
