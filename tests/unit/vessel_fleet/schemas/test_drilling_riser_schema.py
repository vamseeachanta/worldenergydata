"""Tests for drilling riser component schemas."""

import pytest

from worldenergydata.vessel_fleet.schemas.drilling_riser import (
    BOPSchema,
    FlexJointSchema,
    LMRPSchema,
    RiserJointSchema,
    TelescopicJointSchema,
)


class TestRiserJointSchema:
    def test_valid_riser_joint(self):
        rj = RiserJointSchema(
            COMPONENT_ID="RJ-21-75",
            OD_IN=21.0, ID_IN=19.5, WALL_THICKNESS_IN=0.75,
            LENGTH_FT=75.0, WEIGHT_AIR_KIPS=22.5,
        )
        assert rj.OD_IN == 21.0
        assert rj.COMPONENT_TYPE == "riser_joint"

    def test_empty_string_coerced_to_none(self):
        rj = RiserJointSchema(COMPONENT_ID="RJ-1", MANUFACTURER="  ")
        assert rj.MANUFACTURER is None

    def test_string_float_coercion(self):
        rj = RiserJointSchema(COMPONENT_ID="RJ-1", OD_IN="21.0")
        assert rj.OD_IN == 21.0

    def test_negative_od_rejected(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            RiserJointSchema(COMPONENT_ID="RJ-1", OD_IN=-1.0)

    def test_empty_string_float_coerced_to_none(self):
        rj = RiserJointSchema(COMPONENT_ID="RJ-1", LENGTH_FT="")
        assert rj.LENGTH_FT is None


class TestBOPSchema:
    def test_valid_subsea_bop(self):
        bop = BOPSchema(
            COMPONENT_ID="BOP-1",
            BOP_TYPE="subsea",
            BORE_SIZE_IN=18.75,
            PRESSURE_RATING_PSI=15000.0,
            ANNULAR_COUNT=1,
            SHEAR_RAM_COUNT=1,
            PIPE_RAM_COUNT=3,
        )
        assert bop.BORE_SIZE_IN == 18.75
        assert bop.ANNULAR_COUNT == 1

    def test_int_coercion_from_float(self):
        bop = BOPSchema(COMPONENT_ID="BOP-1", ANNULAR_COUNT=2.0)
        assert bop.ANNULAR_COUNT == 2

    def test_int_coercion_from_string(self):
        bop = BOPSchema(COMPONENT_ID="BOP-1", PIPE_RAM_COUNT="3")
        assert bop.PIPE_RAM_COUNT == 3


class TestLMRPSchema:
    def test_valid_lmrp(self):
        lmrp = LMRPSchema(
            COMPONENT_ID="LMRP-1",
            BORE_SIZE_IN=18.75,
            CONNECTOR_TYPE="H-4 collet",
        )
        assert lmrp.BORE_SIZE_IN == 18.75
        assert lmrp.COMPONENT_TYPE == "lmrp"


class TestFlexJointSchema:
    def test_valid_flex_joint(self):
        fj = FlexJointSchema(
            COMPONENT_ID="FJ-1",
            POSITION="upper",
            MAX_ANGLE_DEG=10.0,
            STIFFNESS_FT_KIP_PER_DEG=15.0,
        )
        assert fj.POSITION == "upper"
        assert fj.MAX_ANGLE_DEG == 10.0

    def test_negative_angle_rejected(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            FlexJointSchema(COMPONENT_ID="FJ-1", MAX_ANGLE_DEG=-5.0)


class TestTelescopicJointSchema:
    def test_valid_telescopic_joint(self):
        tj = TelescopicJointSchema(
            COMPONENT_ID="TJ-1",
            OD_IN=21.0,
            STROKE_FT=50.0,
            OUTER_BARREL_LENGTH_FT=65.0,
            INNER_BARREL_LENGTH_FT=45.0,
        )
        assert tj.STROKE_FT == 50.0
        assert tj.COMPONENT_TYPE == "telescopic_joint"

    def test_negative_stroke_rejected(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            TelescopicJointSchema(COMPONENT_ID="TJ-1", STROKE_FT=-10.0)
