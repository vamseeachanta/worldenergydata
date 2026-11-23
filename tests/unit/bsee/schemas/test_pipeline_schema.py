"""Tests for BSEE pipeline schemas."""

import json

import pytest
from pydantic import ValidationError

from worldenergydata.bsee.data.schemas.pipeline import (
    PipelineLocationSchema,
    PipelinePermitSchema,
)


class TestPipelinePermitSchema:
    """Tests for PipelinePermitSchema."""

    def test_create_with_all_fields(self):
        schema = PipelinePermitSchema(
            SEGMENT_NUM="001",
            PPL_SIZE_CODE="12",
            MAOP_PRSS=1200.0,
            RECV_MAOP_PRSS=1100.0,
            SEG_LENGTH=5.5,
            MAX_WTR_DPTH=3000.0,
            MIN_WTR_DPTH=500.0,
            PROD_CODE="OIL",
            STATUS_CODE="ACT",
            PPL_CONST_DATE="2020-01-01",
            ABAN_DATE=None,
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            LEASE_NUMBER="OCS-G 12345",
        )
        assert schema.SEGMENT_NUM == "001"
        assert schema.MAOP_PRSS == 1200.0
        assert schema.AREA_CODE == "GC"

    def test_create_with_minimal_fields(self):
        schema = PipelinePermitSchema()
        assert schema.SEGMENT_NUM is None
        assert schema.MAOP_PRSS is None

    def test_empty_string_coerced_to_none(self):
        schema = PipelinePermitSchema(
            SEGMENT_NUM="  ",
            PROD_CODE="",
            STATUS_CODE="   ",
        )
        assert schema.SEGMENT_NUM is None
        assert schema.PROD_CODE is None
        assert schema.STATUS_CODE is None

    def test_float_string_coercion(self):
        schema = PipelinePermitSchema(
            MAOP_PRSS="1200.5",
            SEG_LENGTH="  10.2  ",
        )
        assert schema.MAOP_PRSS == 1200.5
        assert schema.SEG_LENGTH == 10.2

    def test_empty_float_string_coerced_to_none(self):
        schema = PipelinePermitSchema(
            MAOP_PRSS="",
            SEG_LENGTH="  ",
        )
        assert schema.MAOP_PRSS is None
        assert schema.SEG_LENGTH is None

    def test_none_float_stays_none(self):
        schema = PipelinePermitSchema(MAOP_PRSS=None)
        assert schema.MAOP_PRSS is None

    def test_negative_maop_raises_error(self):
        with pytest.raises(ValidationError, match="MAOP_PRSS must be >= 0"):
            PipelinePermitSchema(MAOP_PRSS=-1.0)

    def test_zero_maop_is_valid(self):
        schema = PipelinePermitSchema(MAOP_PRSS=0.0)
        assert schema.MAOP_PRSS == 0.0

    # Issue #13 truth table: all numbers below are synthetic literals.
    # Omitted/None/blank -> null; numeric/text zero -> 0.0;
    # "1200.5"/"987.25" -> 1200.5/987.25; segment "000123" stays text.
    # These expectations assign no units or design/test-pressure meaning.
    @pytest.mark.parametrize(
        ("pressure_record", "expected_pressures"),
        [
            pytest.param(
                {},
                {"MAOP_PRSS": None, "RECV_MAOP_PRSS": None},
                id="omitted",
            ),
            pytest.param(
                {"MAOP_PRSS": None, "RECV_MAOP_PRSS": None},
                {"MAOP_PRSS": None, "RECV_MAOP_PRSS": None},
                id="none",
            ),
            pytest.param(
                {"MAOP_PRSS": "", "RECV_MAOP_PRSS": ""},
                {"MAOP_PRSS": None, "RECV_MAOP_PRSS": None},
                id="empty",
            ),
            pytest.param(
                {"MAOP_PRSS": "  ", "RECV_MAOP_PRSS": " \t "},
                {"MAOP_PRSS": None, "RECV_MAOP_PRSS": None},
                id="whitespace",
            ),
            pytest.param(
                {"MAOP_PRSS": 0, "RECV_MAOP_PRSS": 0.0},
                {"MAOP_PRSS": 0.0, "RECV_MAOP_PRSS": 0.0},
                id="numeric-zero",
            ),
            pytest.param(
                {"MAOP_PRSS": "0", "RECV_MAOP_PRSS": " 0.0 "},
                {"MAOP_PRSS": 0.0, "RECV_MAOP_PRSS": 0.0},
                id="text-zero",
            ),
            pytest.param(
                {"RECV_MAOP_PRSS": "0"},
                {"MAOP_PRSS": None, "RECV_MAOP_PRSS": 0.0},
                id="missing-sending-zero-receiving",
            ),
            pytest.param(
                {"MAOP_PRSS": "0"},
                {"MAOP_PRSS": 0.0, "RECV_MAOP_PRSS": None},
                id="zero-sending-missing-receiving",
            ),
            pytest.param(
                {"MAOP_PRSS": " 1200.5 ", "RECV_MAOP_PRSS": "987.25"},
                {"MAOP_PRSS": 1200.5, "RECV_MAOP_PRSS": 987.25},
                id="distinct-positive",
            ),
        ],
    )
    def test_pressure_record_json_round_trip(self, pressure_record, expected_pressures):
        record = {"SEGMENT_NUM": "000123", **pressure_record}
        expected = {"SEGMENT_NUM": "000123", **expected_pressures}
        fields = set(expected)

        schema = PipelinePermitSchema.model_validate(record)
        assert schema.model_dump(include=fields) == expected

        payload = json.loads(schema.model_dump_json())
        assert {field: payload[field] for field in fields} == expected

        restored = PipelinePermitSchema.model_validate(payload)
        assert restored.model_dump(include=fields) == expected

    def test_whitespace_stripping(self):
        schema = PipelinePermitSchema(
            AREA_CODE="  GC  ",
            BLOCK_NUMBER=" 640 ",
        )
        assert schema.AREA_CODE == "GC"
        assert schema.BLOCK_NUMBER == "640"


class TestPipelineLocationSchema:
    """Tests for PipelineLocationSchema."""

    def test_create_with_all_fields(self):
        schema = PipelineLocationSchema(
            SEGMENT_NUM="001",
            POINT_NUM=1,
            LATITUDE=28.5,
            LONGITUDE=-89.2,
            WATER_DEPTH=3000.0,
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
        )
        assert schema.LATITUDE == 28.5
        assert schema.LONGITUDE == -89.2
        assert schema.POINT_NUM == 1

    def test_create_with_minimal_fields(self):
        schema = PipelineLocationSchema()
        assert schema.SEGMENT_NUM is None
        assert schema.LATITUDE is None

    def test_point_num_string_coercion(self):
        schema = PipelineLocationSchema(POINT_NUM="5")
        assert schema.POINT_NUM == 5

    def test_point_num_empty_string_to_none(self):
        schema = PipelineLocationSchema(POINT_NUM="")
        assert schema.POINT_NUM is None

    def test_point_num_none_stays_none(self):
        schema = PipelineLocationSchema(POINT_NUM=None)
        assert schema.POINT_NUM is None

    def test_float_string_coercion(self):
        schema = PipelineLocationSchema(
            LATITUDE="28.5",
            LONGITUDE=" -89.2 ",
            WATER_DEPTH="3000",
        )
        assert schema.LATITUDE == 28.5
        assert schema.LONGITUDE == -89.2
        assert schema.WATER_DEPTH == 3000.0

    def test_latitude_out_of_range_raises(self):
        with pytest.raises(
            ValidationError, match="LATITUDE must be between -90 and 90"
        ):
            PipelineLocationSchema(LATITUDE=91.0)

    def test_latitude_negative_boundary(self):
        with pytest.raises(
            ValidationError, match="LATITUDE must be between -90 and 90"
        ):
            PipelineLocationSchema(LATITUDE=-91.0)

    def test_longitude_out_of_range_raises(self):
        with pytest.raises(
            ValidationError, match="LONGITUDE must be between -180 and 180"
        ):
            PipelineLocationSchema(LONGITUDE=181.0)

    def test_longitude_negative_boundary(self):
        with pytest.raises(
            ValidationError, match="LONGITUDE must be between -180 and 180"
        ):
            PipelineLocationSchema(LONGITUDE=-181.0)

    def test_valid_boundary_coordinates(self):
        schema = PipelineLocationSchema(LATITUDE=90.0, LONGITUDE=-180.0)
        assert schema.LATITUDE == 90.0
        assert schema.LONGITUDE == -180.0

    def test_empty_string_fields_coerced_to_none(self):
        schema = PipelineLocationSchema(
            SEGMENT_NUM="",
            AREA_CODE="   ",
            BLOCK_NUMBER=" ",
        )
        assert schema.SEGMENT_NUM is None
        assert schema.AREA_CODE is None
        assert schema.BLOCK_NUMBER is None
