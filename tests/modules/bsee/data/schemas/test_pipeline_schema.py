from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldenergydata.modules.bsee.data.schemas.deepwater_structure import (
    DeepwaterStructureSchema,
)
from worldenergydata.modules.bsee.data.schemas.pipeline import (
    PipelineLocationSchema,
    PipelinePermitSchema,
)


class TestPipelinePermitSchema:
    """Tests for PipelinePermitSchema pydantic model."""

    def test_valid_pipeline_permit_record(self):
        """All fields populated correctly produces a valid schema instance."""
        data = {
            "SEGMENT_NUM": "001",
            "PPL_SIZE_CODE": "12.750",
            "MAOP_PRSS": 1480.0,
            "RECV_MAOP_PRSS": 1440.0,
            "SEG_LENGTH": 12.5,
            "MAX_WTR_DPTH": 2200.0,
            "MIN_WTR_DPTH": 150.0,
            "PROD_CODE": "OIL",
            "STATUS_CODE": "ACT",
            "PPL_CONST_DATE": "2005-03-20",
            "ABAN_DATE": None,
            "AREA_CODE": "GC",
            "BLOCK_NUMBER": "640",
            "LEASE_NUMBER": "G34567",
        }
        schema = PipelinePermitSchema(**data)

        assert schema.SEGMENT_NUM == "001"
        assert schema.PPL_SIZE_CODE == "12.750"
        assert schema.MAOP_PRSS == 1480.0
        assert schema.RECV_MAOP_PRSS == 1440.0
        assert schema.SEG_LENGTH == 12.5
        assert schema.MAX_WTR_DPTH == 2200.0
        assert schema.MIN_WTR_DPTH == 150.0
        assert schema.PROD_CODE == "OIL"
        assert schema.STATUS_CODE == "ACT"
        assert schema.PPL_CONST_DATE == "2005-03-20"
        assert schema.ABAN_DATE is None
        assert schema.AREA_CODE == "GC"
        assert schema.BLOCK_NUMBER == "640"
        assert schema.LEASE_NUMBER == "G34567"

    def test_maop_bounds_validation(self):
        """MAOP must be non-negative when provided."""
        with pytest.raises(ValidationError, match="MAOP_PRSS"):
            PipelinePermitSchema(MAOP_PRSS=-100.0)

    def test_maop_zero_valid(self):
        """MAOP of zero is valid."""
        schema = PipelinePermitSchema(MAOP_PRSS=0.0)
        assert schema.MAOP_PRSS == 0.0

    def test_od_code_parsing(self):
        """Pipeline OD codes are accepted as strings."""
        od_codes = ["12.750", "8.625", "6.625", "4.500", "24.000"]
        for code in od_codes:
            schema = PipelinePermitSchema(PPL_SIZE_CODE=code)
            assert schema.PPL_SIZE_CODE == code

    def test_status_code_values(self):
        """Common status codes are accepted."""
        status_codes = ["ACT", "ABN", "OUT", "RMV", "PRO"]
        for code in status_codes:
            schema = PipelinePermitSchema(STATUS_CODE=code)
            assert schema.STATUS_CODE == code

    def test_optional_fields_default_none(self):
        """All fields are optional and default to None."""
        schema = PipelinePermitSchema()
        assert schema.SEGMENT_NUM is None
        assert schema.PPL_SIZE_CODE is None
        assert schema.MAOP_PRSS is None
        assert schema.RECV_MAOP_PRSS is None
        assert schema.SEG_LENGTH is None
        assert schema.MAX_WTR_DPTH is None
        assert schema.MIN_WTR_DPTH is None
        assert schema.PROD_CODE is None
        assert schema.STATUS_CODE is None
        assert schema.PPL_CONST_DATE is None
        assert schema.ABAN_DATE is None
        assert schema.AREA_CODE is None
        assert schema.BLOCK_NUMBER is None
        assert schema.LEASE_NUMBER is None

    def test_maop_coercion_from_string(self):
        """MAOP provided as string is coerced to float."""
        schema = PipelinePermitSchema(MAOP_PRSS="1480.0")
        assert schema.MAOP_PRSS == 1480.0

    def test_empty_string_coerced_to_none(self):
        """Empty strings for optional fields are coerced to None."""
        schema = PipelinePermitSchema(
            SEGMENT_NUM="",
            PPL_SIZE_CODE="",
            PROD_CODE="",
        )
        assert schema.SEGMENT_NUM is None
        assert schema.PPL_SIZE_CODE is None
        assert schema.PROD_CODE is None


class TestPipelineLocationSchema:
    """Tests for PipelineLocationSchema pydantic model."""

    def test_valid_pipeline_location_record(self):
        """All fields populated correctly produces a valid schema instance."""
        data = {
            "SEGMENT_NUM": "001",
            "POINT_NUM": 1,
            "LATITUDE": 28.123,
            "LONGITUDE": -89.456,
            "WATER_DEPTH": 500.0,
            "AREA_CODE": "GC",
            "BLOCK_NUMBER": "640",
        }
        schema = PipelineLocationSchema(**data)

        assert schema.SEGMENT_NUM == "001"
        assert schema.POINT_NUM == 1
        assert schema.LATITUDE == 28.123
        assert schema.LONGITUDE == -89.456
        assert schema.WATER_DEPTH == 500.0
        assert schema.AREA_CODE == "GC"
        assert schema.BLOCK_NUMBER == "640"

    def test_optional_fields_default_none(self):
        """All fields are optional and default to None."""
        schema = PipelineLocationSchema()
        assert schema.SEGMENT_NUM is None
        assert schema.POINT_NUM is None
        assert schema.LATITUDE is None
        assert schema.LONGITUDE is None
        assert schema.WATER_DEPTH is None
        assert schema.AREA_CODE is None
        assert schema.BLOCK_NUMBER is None

    def test_latitude_longitude_bounds(self):
        """Latitude must be -90..90 and longitude -180..180."""
        with pytest.raises(ValidationError, match="LATITUDE"):
            PipelineLocationSchema(LATITUDE=91.0)

        with pytest.raises(ValidationError, match="LONGITUDE"):
            PipelineLocationSchema(LONGITUDE=181.0)

    def test_point_num_coercion_from_string(self):
        """Point number provided as string is coerced to int."""
        schema = PipelineLocationSchema(POINT_NUM="5")
        assert schema.POINT_NUM == 5


class TestDeepwaterStructureSchema:
    """Tests for DeepwaterStructureSchema pydantic model."""

    def test_valid_deepwater_structure_record(self):
        """All fields populated correctly produces a valid schema instance."""
        data = {
            "AREA_CODE": "GC",
            "BLOCK_NUMBER": "640",
            "STRUCTURE_NUMBER": "B001",
            "STRUCTURE_NAME": "Thunder Horse",
            "STRUC_TYPE_CODE": "FPS",
            "WATER_DEPTH": 6050.0,
            "INSTALL_DATE": "2008-06-01",
            "LATITUDE": 28.195,
            "LONGITUDE": -88.497,
            "PERMIT_NUMBER": "P00123",
            "BUS_ASC_NAME": "BP Exploration & Production Inc.",
            "LEASE_NUMBER": "G98765",
            "DISTRICT_CODE": "4",
        }
        schema = DeepwaterStructureSchema(**data)

        assert schema.AREA_CODE == "GC"
        assert schema.BLOCK_NUMBER == "640"
        assert schema.STRUCTURE_NUMBER == "B001"
        assert schema.STRUCTURE_NAME == "Thunder Horse"
        assert schema.STRUC_TYPE_CODE == "FPS"
        assert schema.WATER_DEPTH == 6050.0
        assert schema.INSTALL_DATE == "2008-06-01"
        assert schema.LATITUDE == 28.195
        assert schema.LONGITUDE == -88.497
        assert schema.PERMIT_NUMBER == "P00123"
        assert schema.BUS_ASC_NAME == "BP Exploration & Production Inc."
        assert schema.LEASE_NUMBER == "G98765"
        assert schema.DISTRICT_CODE == "4"

    def test_permit_and_business_fields(self):
        """Permit number and business associate name are optional."""
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="B001",
        )
        assert schema.PERMIT_NUMBER is None
        assert schema.BUS_ASC_NAME is None

    def test_invalid_water_depth_negative(self):
        """Negative water depth raises ValidationError."""
        with pytest.raises(ValidationError, match="WATER_DEPTH"):
            DeepwaterStructureSchema(
                AREA_CODE="GC",
                BLOCK_NUMBER="640",
                STRUCTURE_NUMBER="B001",
                WATER_DEPTH=-100.0,
            )
