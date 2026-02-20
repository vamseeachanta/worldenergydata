"""Tests for BSEE deepwater structure schema."""

import pytest
from pydantic import ValidationError

from worldenergydata.bsee.data.schemas.deepwater_structure import (
    DeepwaterStructureSchema,
)


class TestDeepwaterStructureSchema:
    """Tests for DeepwaterStructureSchema."""

    def test_create_with_required_fields(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
        )
        assert schema.AREA_CODE == "GC"
        assert schema.BLOCK_NUMBER == "640"
        assert schema.STRUCTURE_NUMBER == "A001"

    def test_create_with_all_fields(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
            COMPLEX_ID_NUM="C001",
            STRUCTURE_NAME="Test Platform",
            STRUC_TYPE_CODE="FP",
            MAJ_STRUC_FLAG="Y",
            FIELD_NAME_CODE="MARS",
            WATER_DEPTH=3000.0,
            INSTALL_DATE="2005-01-01",
            REMOVAL_DATE=None,
            DECK_COUNT=3,
            SLOT_COUNT=24,
            LATITUDE=28.5,
            LONGITUDE=-89.2,
            LEASE_NUMBER="OCS-G 12345",
            DISTRICT_CODE="3",
            PERMIT_NUMBER="P-001",
            BUS_ASC_NAME="Energy Co",
        )
        assert schema.STRUCTURE_NAME == "Test Platform"
        assert schema.WATER_DEPTH == 3000.0
        assert schema.PERMIT_NUMBER == "P-001"

    def test_empty_string_coerced_to_none(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
            COMPLEX_ID_NUM="",
            STRUCTURE_NAME="   ",
            PERMIT_NUMBER="  ",
            BUS_ASC_NAME="",
        )
        assert schema.COMPLEX_ID_NUM is None
        assert schema.STRUCTURE_NAME is None
        assert schema.PERMIT_NUMBER is None
        assert schema.BUS_ASC_NAME is None

    def test_water_depth_string_coercion(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH="3000.5",
        )
        assert schema.WATER_DEPTH == 3000.5

    def test_water_depth_empty_string_to_none(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH="",
        )
        assert schema.WATER_DEPTH is None

    def test_negative_water_depth_raises_error(self):
        with pytest.raises(ValidationError, match="WATER_DEPTH must be >= 0"):
            DeepwaterStructureSchema(
                AREA_CODE="GC",
                BLOCK_NUMBER="640",
                STRUCTURE_NUMBER="A001",
                WATER_DEPTH=-100.0,
            )

    def test_int_string_coercion(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
            DECK_COUNT="3",
            SLOT_COUNT=" 24 ",
        )
        assert schema.DECK_COUNT == 3
        assert schema.SLOT_COUNT == 24

    def test_int_empty_string_to_none(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
            DECK_COUNT="",
            SLOT_COUNT="  ",
        )
        assert schema.DECK_COUNT is None
        assert schema.SLOT_COUNT is None

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError, match="LATITUDE must be between -90 and 90"):
            DeepwaterStructureSchema(
                AREA_CODE="GC",
                BLOCK_NUMBER="640",
                STRUCTURE_NUMBER="A001",
                LATITUDE=91.0,
            )

    def test_longitude_out_of_range(self):
        with pytest.raises(
            ValidationError, match="LONGITUDE must be between -180 and 180"
        ):
            DeepwaterStructureSchema(
                AREA_CODE="GC",
                BLOCK_NUMBER="640",
                STRUCTURE_NUMBER="A001",
                LONGITUDE=181.0,
            )

    def test_valid_boundary_coordinates(self):
        schema = DeepwaterStructureSchema(
            AREA_CODE="GC",
            BLOCK_NUMBER="640",
            STRUCTURE_NUMBER="A001",
            LATITUDE=-90.0,
            LONGITUDE=180.0,
        )
        assert schema.LATITUDE == -90.0
        assert schema.LONGITUDE == 180.0
