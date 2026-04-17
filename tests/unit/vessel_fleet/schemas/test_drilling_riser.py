"""Tests for drilling riser component schemas."""

import pytest
from pydantic import ValidationError

from worldenergydata.vessel_fleet.schemas.drilling_riser import (
    BOPSchema,
    FlexJointSchema,
    LMRPSchema,
    RiserJointSchema,
    TelescopicJointSchema,
)


class TestRiserJointSchema:
    def test_required(self):
        s = RiserJointSchema(COMPONENT_ID="RJ-001")
        assert s.COMPONENT_ID == "RJ-001"
        assert s.COMPONENT_TYPE == "riser_joint"

    def test_optional_defaults(self):
        s = RiserJointSchema(COMPONENT_ID="RJ-001")
        assert s.OD_IN is None
        assert s.LENGTH_FT is None

    def test_float_coercion(self):
        s = RiserJointSchema(
            COMPONENT_ID="RJ-001",
            OD_IN="21.0",
            LENGTH_FT=" 75.0 ",
        )
        assert s.OD_IN == 21.0
        assert s.LENGTH_FT == 75.0

    def test_float_empty_to_none(self):
        s = RiserJointSchema(COMPONENT_ID="RJ-001", OD_IN="")
        assert s.OD_IN is None

    def test_negative_raises(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            RiserJointSchema(COMPONENT_ID="RJ-001", OD_IN=-1.0)

    def test_empty_str_to_none(self):
        s = RiserJointSchema(
            COMPONENT_ID="RJ-001",
            MANUFACTURER="  ",
            GRADE="",
        )
        assert s.MANUFACTURER is None
        assert s.GRADE is None

    def test_all_fields(self):
        s = RiserJointSchema(
            COMPONENT_ID="RJ-001",
            OD_IN=21.0,
            ID_IN=19.5,
            WALL_THICKNESS_IN=0.75,
            LENGTH_FT=75.0,
            WEIGHT_AIR_KIPS=24.5,
            BUOYANCY_COVERAGE_PCT=90.0,
            PRESSURE_RATING_PSI=15000,
        )
        assert s.WALL_THICKNESS_IN == 0.75


class TestBOPSchema:
    def test_required(self):
        s = BOPSchema(COMPONENT_ID="BOP-001")
        assert s.COMPONENT_TYPE == "bop"

    def test_float_coercion(self):
        s = BOPSchema(
            COMPONENT_ID="BOP-001",
            BORE_SIZE_IN="18.75",
            PRESSURE_RATING_PSI="15000",
        )
        assert s.BORE_SIZE_IN == 18.75
        assert s.PRESSURE_RATING_PSI == 15000.0

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            BOPSchema(COMPONENT_ID="BOP-001", BORE_SIZE_IN=-5.0)

    def test_int_coercion(self):
        s = BOPSchema(
            COMPONENT_ID="BOP-001",
            ANNULAR_COUNT="2",
            SHEAR_RAM_COUNT=3.0,
        )
        assert s.ANNULAR_COUNT == 2
        assert s.SHEAR_RAM_COUNT == 3

    def test_empty_str_to_none(self):
        s = BOPSchema(
            COMPONENT_ID="BOP-001",
            BOP_TYPE="  ",
            MANUFACTURER="",
        )
        assert s.BOP_TYPE is None
        assert s.MANUFACTURER is None


class TestLMRPSchema:
    def test_required(self):
        s = LMRPSchema(COMPONENT_ID="LMRP-001")
        assert s.COMPONENT_TYPE == "lmrp"

    def test_float_coercion(self):
        s = LMRPSchema(
            COMPONENT_ID="LMRP-001",
            BORE_SIZE_IN="18.75",
        )
        assert s.BORE_SIZE_IN == 18.75

    def test_int_coercion(self):
        s = LMRPSchema(COMPONENT_ID="LMRP-001", ANNULAR_COUNT="1")
        assert s.ANNULAR_COUNT == 1

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            LMRPSchema(COMPONENT_ID="LMRP-001", HEIGHT_FT=-10.0)


class TestFlexJointSchema:
    def test_required(self):
        s = FlexJointSchema(COMPONENT_ID="FJ-001")
        assert s.COMPONENT_TYPE == "flex_joint"

    def test_float_coercion(self):
        s = FlexJointSchema(
            COMPONENT_ID="FJ-001",
            MAX_ANGLE_DEG="10.0",
            BORE_SIZE_IN="21",
        )
        assert s.MAX_ANGLE_DEG == 10.0
        assert s.BORE_SIZE_IN == 21.0

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            FlexJointSchema(COMPONENT_ID="FJ-001", BORE_SIZE_IN=-5.0)

    def test_empty_str_to_none(self):
        s = FlexJointSchema(
            COMPONENT_ID="FJ-001",
            POSITION="  ",
            MANUFACTURER="",
        )
        assert s.POSITION is None


class TestTelescopicJointSchema:
    def test_required(self):
        s = TelescopicJointSchema(COMPONENT_ID="TJ-001")
        assert s.COMPONENT_TYPE == "telescopic_joint"

    def test_float_coercion(self):
        s = TelescopicJointSchema(
            COMPONENT_ID="TJ-001",
            STROKE_FT="50.0",
            OD_IN="24",
        )
        assert s.STROKE_FT == 50.0
        assert s.OD_IN == 24.0

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            TelescopicJointSchema(COMPONENT_ID="TJ-001", STROKE_FT=-10.0)

    def test_empty_str_to_none(self):
        s = TelescopicJointSchema(
            COMPONENT_ID="TJ-001",
            MANUFACTURER="  ",
        )
        assert s.MANUFACTURER is None
