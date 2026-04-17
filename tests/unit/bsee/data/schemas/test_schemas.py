"""Tests for BSEE Pydantic schemas (pipeline, platform, deepwater, rig fleet)."""

import pytest
from pydantic import ValidationError

from worldenergydata.bsee.data.schemas.deepwater_structure import (
    DeepwaterStructureSchema,
)
from worldenergydata.bsee.data.schemas.pipeline import (
    PipelineLocationSchema,
    PipelinePermitSchema,
)
from worldenergydata.bsee.data.schemas.platform import PlatformStructureSchema
from worldenergydata.bsee.data.schemas.rig_fleet import RigFleetSchema


class TestPipelinePermitSchema:
    def test_minimal(self):
        s = PipelinePermitSchema()
        assert s.SEGMENT_NUM is None
        assert s.MAOP_PRSS is None

    def test_all_fields(self):
        s = PipelinePermitSchema(
            SEGMENT_NUM="SEG001",
            PPL_SIZE_CODE="12",
            MAOP_PRSS=1200.0,
            RECV_MAOP_PRSS=1100.0,
            SEG_LENGTH=5.5,
            MAX_WTR_DPTH=500.0,
            MIN_WTR_DPTH=100.0,
            PROD_CODE="OIL",
            STATUS_CODE="ACT",
            PPL_CONST_DATE="2020-01-15",
            ABAN_DATE=None,
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
            LEASE_NUMBER="G12345",
        )
        assert s.SEGMENT_NUM == "SEG001"
        assert s.MAOP_PRSS == 1200.0
        assert s.PROD_CODE == "OIL"

    def test_empty_str_to_none(self):
        s = PipelinePermitSchema(SEGMENT_NUM="  ", PROD_CODE="", STATUS_CODE="  ")
        assert s.SEGMENT_NUM is None
        assert s.PROD_CODE is None
        assert s.STATUS_CODE is None

    def test_float_from_string(self):
        s = PipelinePermitSchema(MAOP_PRSS="1200.5", SEG_LENGTH="  5.5 ")
        assert s.MAOP_PRSS == 1200.5
        assert s.SEG_LENGTH == 5.5

    def test_float_empty_string_to_none(self):
        s = PipelinePermitSchema(MAOP_PRSS="", SEG_LENGTH="  ")
        assert s.MAOP_PRSS is None
        assert s.SEG_LENGTH is None

    def test_negative_maop_raises(self):
        with pytest.raises(ValidationError, match="MAOP_PRSS must be >= 0"):
            PipelinePermitSchema(MAOP_PRSS=-100)

    def test_str_strip(self):
        s = PipelinePermitSchema(AREA_CODE="  MC  ")
        assert s.AREA_CODE == "MC"


class TestPipelineLocationSchema:
    def test_minimal(self):
        s = PipelineLocationSchema()
        assert s.SEGMENT_NUM is None
        assert s.LATITUDE is None

    def test_all_fields(self):
        s = PipelineLocationSchema(
            SEGMENT_NUM="SEG001",
            POINT_NUM=1,
            LATITUDE=29.5,
            LONGITUDE=-90.0,
            WATER_DEPTH=500.0,
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
        )
        assert s.POINT_NUM == 1
        assert s.LATITUDE == 29.5

    def test_empty_str_to_none(self):
        s = PipelineLocationSchema(SEGMENT_NUM="  ", AREA_CODE="")
        assert s.SEGMENT_NUM is None
        assert s.AREA_CODE is None

    def test_point_num_from_string(self):
        s = PipelineLocationSchema(POINT_NUM=" 42 ")
        assert s.POINT_NUM == 42

    def test_point_num_empty_to_none(self):
        s = PipelineLocationSchema(POINT_NUM="")
        assert s.POINT_NUM is None

    def test_float_from_string(self):
        s = PipelineLocationSchema(LATITUDE="29.5", LONGITUDE="-90.0")
        assert s.LATITUDE == 29.5
        assert s.LONGITUDE == -90.0

    def test_latitude_out_of_range(self):
        with pytest.raises(
            ValidationError, match="LATITUDE must be between -90 and 90"
        ):
            PipelineLocationSchema(LATITUDE=91.0)

    def test_latitude_negative_out_of_range(self):
        with pytest.raises(ValidationError, match="LATITUDE"):
            PipelineLocationSchema(LATITUDE=-91.0)

    def test_longitude_out_of_range(self):
        with pytest.raises(
            ValidationError, match="LONGITUDE must be between -180 and 180"
        ):
            PipelineLocationSchema(LONGITUDE=181.0)

    def test_longitude_boundary(self):
        s = PipelineLocationSchema(LONGITUDE=180.0)
        assert s.LONGITUDE == 180.0
        s2 = PipelineLocationSchema(LONGITUDE=-180.0)
        assert s2.LONGITUDE == -180.0


class TestPlatformStructureSchema:
    def test_required_fields(self):
        s = PlatformStructureSchema(
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
            STRUCTURE_NUMBER="A001",
        )
        assert s.AREA_CODE == "MC"
        assert s.BLOCK_NUMBER == "100"
        assert s.STRUCTURE_NUMBER == "A001"

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            PlatformStructureSchema(AREA_CODE="MC")

    def test_optional_defaults(self):
        s = PlatformStructureSchema(
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
            STRUCTURE_NUMBER="A001",
        )
        assert s.WATER_DEPTH is None
        assert s.DECK_COUNT is None
        assert s.LATITUDE is None

    def test_empty_str_to_none(self):
        s = PlatformStructureSchema(
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
            STRUCTURE_NUMBER="A001",
            STRUCTURE_NAME="  ",
            LEASE_NUMBER="",
        )
        assert s.STRUCTURE_NAME is None
        assert s.LEASE_NUMBER is None

    def test_water_depth_from_string(self):
        s = PlatformStructureSchema(
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH="500.0",
        )
        assert s.WATER_DEPTH == 500.0

    def test_water_depth_negative_raises(self):
        with pytest.raises(ValidationError, match="WATER_DEPTH must be >= 0"):
            PlatformStructureSchema(
                AREA_CODE="MC",
                BLOCK_NUMBER="100",
                STRUCTURE_NUMBER="A001",
                WATER_DEPTH=-10.0,
            )

    def test_int_from_string(self):
        s = PlatformStructureSchema(
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
            STRUCTURE_NUMBER="A001",
            DECK_COUNT=" 3 ",
            SLOT_COUNT="24",
        )
        assert s.DECK_COUNT == 3
        assert s.SLOT_COUNT == 24

    def test_int_empty_to_none(self):
        s = PlatformStructureSchema(
            AREA_CODE="MC",
            BLOCK_NUMBER="100",
            STRUCTURE_NUMBER="A001",
            DECK_COUNT="",
        )
        assert s.DECK_COUNT is None

    def test_latitude_validation(self):
        with pytest.raises(ValidationError, match="LATITUDE"):
            PlatformStructureSchema(
                AREA_CODE="MC",
                BLOCK_NUMBER="100",
                STRUCTURE_NUMBER="A001",
                LATITUDE=100.0,
            )

    def test_longitude_validation(self):
        with pytest.raises(ValidationError, match="LONGITUDE"):
            PlatformStructureSchema(
                AREA_CODE="MC",
                BLOCK_NUMBER="100",
                STRUCTURE_NUMBER="A001",
                LONGITUDE=-200.0,
            )


class TestDeepwaterStructureSchema:
    def test_required_fields(self):
        s = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="200",
            STRUCTURE_NUMBER="B002",
        )
        assert s.AREA_CODE == "GC"

    def test_permit_fields(self):
        s = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="200",
            STRUCTURE_NUMBER="B002",
            PERMIT_NUMBER="P12345",
            BUS_ASC_NAME="Shell",
        )
        assert s.PERMIT_NUMBER == "P12345"
        assert s.BUS_ASC_NAME == "Shell"

    def test_empty_permit_to_none(self):
        s = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="200",
            STRUCTURE_NUMBER="B002",
            PERMIT_NUMBER="  ",
            BUS_ASC_NAME="",
        )
        assert s.PERMIT_NUMBER is None
        assert s.BUS_ASC_NAME is None

    def test_water_depth_negative(self):
        with pytest.raises(ValidationError, match="WATER_DEPTH must be >= 0"):
            DeepwaterStructureSchema(
                AREA_CODE="GC",
                BLOCK_NUMBER="200",
                STRUCTURE_NUMBER="B002",
                WATER_DEPTH=-500.0,
            )

    def test_lat_lon_validation(self):
        with pytest.raises(ValidationError):
            DeepwaterStructureSchema(
                AREA_CODE="GC",
                BLOCK_NUMBER="200",
                STRUCTURE_NUMBER="B002",
                LATITUDE=95.0,
            )

    def test_int_coercion(self):
        s = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="200",
            STRUCTURE_NUMBER="B002",
            DECK_COUNT="5",
            SLOT_COUNT=" 30 ",
        )
        assert s.DECK_COUNT == 5
        assert s.SLOT_COUNT == 30


class TestRigFleetSchema:
    def test_required_rig_name(self):
        s = RigFleetSchema(RIG_NAME="DEEPWATER NAUTILUS")
        assert s.RIG_NAME == "DEEPWATER NAUTILUS"

    def test_missing_rig_name(self):
        with pytest.raises(ValidationError):
            RigFleetSchema()

    def test_rig_name_strip_quotes(self):
        s = RigFleetSchema(RIG_NAME='"DEEPWATER NAUTILUS"')
        assert s.RIG_NAME == "DEEPWATER NAUTILUS"

    def test_rig_name_strip_single_quotes(self):
        s = RigFleetSchema(RIG_NAME="'NAUTILUS'")
        assert s.RIG_NAME == "NAUTILUS"

    def test_empty_str_to_none(self):
        s = RigFleetSchema(RIG_NAME="TEST", RIG_TYPE="  ", OWNER="", FLAG_STATE=" ")
        assert s.RIG_TYPE is None
        assert s.OWNER is None
        assert s.FLAG_STATE is None

    def test_float_from_string(self):
        s = RigFleetSchema(
            RIG_NAME="TEST",
            WATER_DEPTH_RATING_FT="10000.0",
            LOA_M=" 230.5 ",
        )
        assert s.WATER_DEPTH_RATING_FT == 10000.0
        assert s.LOA_M == 230.5

    def test_float_empty_to_none(self):
        s = RigFleetSchema(RIG_NAME="TEST", WATER_DEPTH_RATING_FT="")
        assert s.WATER_DEPTH_RATING_FT is None

    def test_negative_float_raises(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            RigFleetSchema(RIG_NAME="TEST", WATER_DEPTH_RATING_FT=-100.0)

    def test_negative_loa_raises(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            RigFleetSchema(RIG_NAME="TEST", LOA_M=-50.0)

    def test_int_from_string(self):
        s = RigFleetSchema(RIG_NAME="TEST", DP_CLASS=" 3 ", YEAR_BUILT="2010")
        assert s.DP_CLASS == 3
        assert s.YEAR_BUILT == 2010

    def test_int_empty_to_none(self):
        s = RigFleetSchema(RIG_NAME="TEST", DP_CLASS="")
        assert s.DP_CLASS is None

    def test_year_built_valid(self):
        s = RigFleetSchema(RIG_NAME="TEST", YEAR_BUILT=2020)
        assert s.YEAR_BUILT == 2020

    def test_year_built_too_old(self):
        with pytest.raises(
            ValidationError, match="YEAR_BUILT must be between 1900 and 2035"
        ):
            RigFleetSchema(RIG_NAME="TEST", YEAR_BUILT=1800)

    def test_year_built_too_future(self):
        with pytest.raises(ValidationError, match="YEAR_BUILT"):
            RigFleetSchema(RIG_NAME="TEST", YEAR_BUILT=2036)

    def test_float_field_none_passthrough(self):
        """Line 102: _coerce_float_fields returns None for None input."""
        s = RigFleetSchema(RIG_NAME="TEST", WATER_DEPTH_RATING_FT=None)
        assert s.WATER_DEPTH_RATING_FT is None

    def test_int_field_none_passthrough(self):
        """Line 133: _coerce_int_fields returns None for None input."""
        s = RigFleetSchema(RIG_NAME="TEST", DP_CLASS=None)
        assert s.DP_CLASS is None

    def test_all_optional_fields(self):
        s = RigFleetSchema(
            RIG_NAME="DEEPWATER HORIZON",
            RIG_TYPE="drillship",
            RIG_STATUS="active",
            OWNER="Transocean",
            OPERATOR="BP",
            WATER_DEPTH_RATING_FT=10000.0,
            DRILLING_DEPTH_RATING_FT=30000.0,
            LOA_M=230.0,
            BEAM_M=36.0,
            DISPLACEMENT_TONNES=52587.0,
            DP_CLASS=3,
            YEAR_BUILT=2001,
            IMO_NUMBER="1234567",
            FLAG_STATE="MHL",
            IS_OFFSHORE=True,
            WELLS_DRILLED_COUNT=15,
        )
        assert s.OPERATOR == "BP"
        assert s.IS_OFFSHORE is True
        assert s.WELLS_DRILLED_COUNT == 15
