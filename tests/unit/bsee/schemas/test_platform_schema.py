"""Tests for BSEE platform structure schema."""

import pytest
from pydantic import ValidationError

from worldenergydata.bsee.data.schemas.platform import PlatformStructureSchema


class TestPlatformStructureSchema:
    """Tests for PlatformStructureSchema."""

    def test_create_with_required_fields(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
        )
        assert schema.AREA_CODE == "EI"
        assert schema.BLOCK_NUMBER == "330"

    def test_create_with_all_fields(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            COMPLEX_ID_NUM="C001",
            STRUCTURE_NAME="Platform Alpha",
            STRUC_TYPE_CODE="FP",
            MAJ_STRUC_FLAG="Y",
            FIELD_NAME_CODE="MARS",
            WATER_DEPTH=500.0,
            INSTALL_DATE="1990-01-01",
            REMOVAL_DATE=None,
            DECK_COUNT=2,
            SLOT_COUNT=12,
            LATITUDE=29.0,
            LONGITUDE=-88.5,
            LEASE_NUMBER="OCS-G 54321",
            DISTRICT_CODE="4",
        )
        assert schema.STRUCTURE_NAME == "Platform Alpha"
        assert schema.WATER_DEPTH == 500.0

    def test_empty_string_coerced_to_none(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            COMPLEX_ID_NUM="",
            STRUCTURE_NAME="  ",
            INSTALL_DATE="",
            LEASE_NUMBER="   ",
        )
        assert schema.COMPLEX_ID_NUM is None
        assert schema.STRUCTURE_NAME is None
        assert schema.INSTALL_DATE is None
        assert schema.LEASE_NUMBER is None

    def test_water_depth_string_coercion(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH="500.5",
        )
        assert schema.WATER_DEPTH == 500.5

    def test_water_depth_empty_to_none(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH="",
        )
        assert schema.WATER_DEPTH is None

    def test_negative_water_depth_raises(self):
        with pytest.raises(ValidationError, match="WATER_DEPTH must be >= 0"):
            PlatformStructureSchema(
                AREA_CODE="EI",
                BLOCK_NUMBER="330",
                STRUCTURE_NUMBER="A001",
                WATER_DEPTH=-1.0,
            )

    def test_int_string_coercion(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            DECK_COUNT="2",
            SLOT_COUNT=" 12 ",
        )
        assert schema.DECK_COUNT == 2
        assert schema.SLOT_COUNT == 12

    def test_int_empty_to_none(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            DECK_COUNT="",
        )
        assert schema.DECK_COUNT is None

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError, match="LATITUDE"):
            PlatformStructureSchema(
                AREA_CODE="EI",
                BLOCK_NUMBER="330",
                STRUCTURE_NUMBER="A001",
                LATITUDE=95.0,
            )

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError, match="LONGITUDE"):
            PlatformStructureSchema(
                AREA_CODE="EI",
                BLOCK_NUMBER="330",
                STRUCTURE_NUMBER="A001",
                LONGITUDE=-200.0,
            )

    def test_valid_boundary_coordinates(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            LATITUDE=90.0,
            LONGITUDE=-180.0,
        )
        assert schema.LATITUDE == 90.0
        assert schema.LONGITUDE == -180.0

    def test_zero_water_depth_is_valid(self):
        schema = PlatformStructureSchema(
            AREA_CODE="EI",
            BLOCK_NUMBER="330",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH=0.0,
        )
        assert schema.WATER_DEPTH == 0.0
