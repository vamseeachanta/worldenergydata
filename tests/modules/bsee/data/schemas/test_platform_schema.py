from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldenergydata.bsee.data.schemas.platform import PlatformStructureSchema


class TestPlatformStructureSchema:
    """Tests for PlatformStructureSchema pydantic model."""

    def test_valid_platform_record(self):
        """All fields populated correctly produces a valid schema instance."""
        data = {
            "AREA_CODE": "WC",
            "BLOCK_NUMBER": "168",
            "COMPLEX_ID_NUM": "26830",
            "STRUCTURE_NUMBER": "A001",
            "STRUCTURE_NAME": "Platform Alpha",
            "STRUC_TYPE_CODE": "FP",
            "MAJ_STRUC_FLAG": "Y",
            "FIELD_NAME_CODE": "OCS-G 12345",
            "WATER_DEPTH": 150.5,
            "INSTALL_DATE": "1990-05-15",
            "REMOVAL_DATE": None,
            "DECK_COUNT": 3,
            "SLOT_COUNT": 24,
            "LATITUDE": 28.945,
            "LONGITUDE": -89.456,
            "LEASE_NUMBER": "G12345",
            "DISTRICT_CODE": "3",
        }
        schema = PlatformStructureSchema(**data)

        assert schema.AREA_CODE == "WC"
        assert schema.BLOCK_NUMBER == "168"
        assert schema.COMPLEX_ID_NUM == "26830"
        assert schema.STRUCTURE_NUMBER == "A001"
        assert schema.STRUCTURE_NAME == "Platform Alpha"
        assert schema.STRUC_TYPE_CODE == "FP"
        assert schema.MAJ_STRUC_FLAG == "Y"
        assert schema.FIELD_NAME_CODE == "OCS-G 12345"
        assert schema.WATER_DEPTH == 150.5
        assert schema.INSTALL_DATE == "1990-05-15"
        assert schema.REMOVAL_DATE is None
        assert schema.DECK_COUNT == 3
        assert schema.SLOT_COUNT == 24
        assert schema.LATITUDE == 28.945
        assert schema.LONGITUDE == -89.456
        assert schema.LEASE_NUMBER == "G12345"
        assert schema.DISTRICT_CODE == "3"

    def test_invalid_water_depth_negative(self):
        """Negative water depth raises ValidationError."""
        data = {
            "AREA_CODE": "WC",
            "BLOCK_NUMBER": "168",
            "STRUCTURE_NUMBER": "A001",
            "WATER_DEPTH": -50.0,
        }
        with pytest.raises(ValidationError, match="WATER_DEPTH"):
            PlatformStructureSchema(**data)

    def test_date_parsing_install_date(self):
        """Various date string formats are accepted for INSTALL_DATE."""
        formats = [
            "1990-05-15",
            "05/15/1990",
            "19900515",
        ]
        for date_str in formats:
            schema = PlatformStructureSchema(
                AREA_CODE="WC",
                BLOCK_NUMBER="168",
                STRUCTURE_NUMBER="A001",
                INSTALL_DATE=date_str,
            )
            assert schema.INSTALL_DATE is not None

    def test_optional_fields_default_none(self):
        """Optional fields default to None when not provided."""
        schema = PlatformStructureSchema(
            AREA_CODE="WC",
            BLOCK_NUMBER="168",
            STRUCTURE_NUMBER="A001",
        )
        assert schema.COMPLEX_ID_NUM is None
        assert schema.STRUCTURE_NAME is None
        assert schema.STRUC_TYPE_CODE is None
        assert schema.MAJ_STRUC_FLAG is None
        assert schema.FIELD_NAME_CODE is None
        assert schema.WATER_DEPTH is None
        assert schema.INSTALL_DATE is None
        assert schema.REMOVAL_DATE is None
        assert schema.DECK_COUNT is None
        assert schema.SLOT_COUNT is None
        assert schema.LATITUDE is None
        assert schema.LONGITUDE is None
        assert schema.LEASE_NUMBER is None
        assert schema.DISTRICT_CODE is None

    def test_latitude_longitude_bounds(self):
        """Latitude must be -90..90 and longitude -180..180."""
        # Valid bounds
        schema = PlatformStructureSchema(
            AREA_CODE="WC",
            BLOCK_NUMBER="168",
            STRUCTURE_NUMBER="A001",
            LATITUDE=28.5,
            LONGITUDE=-89.5,
        )
        assert schema.LATITUDE == 28.5
        assert schema.LONGITUDE == -89.5

        # Invalid latitude > 90
        with pytest.raises(ValidationError, match="LATITUDE"):
            PlatformStructureSchema(
                AREA_CODE="WC",
                BLOCK_NUMBER="168",
                STRUCTURE_NUMBER="A001",
                LATITUDE=91.0,
            )

        # Invalid latitude < -90
        with pytest.raises(ValidationError, match="LATITUDE"):
            PlatformStructureSchema(
                AREA_CODE="WC",
                BLOCK_NUMBER="168",
                STRUCTURE_NUMBER="A001",
                LATITUDE=-91.0,
            )

        # Invalid longitude > 180
        with pytest.raises(ValidationError, match="LONGITUDE"):
            PlatformStructureSchema(
                AREA_CODE="WC",
                BLOCK_NUMBER="168",
                STRUCTURE_NUMBER="A001",
                LONGITUDE=181.0,
            )

        # Invalid longitude < -180
        with pytest.raises(ValidationError, match="LONGITUDE"):
            PlatformStructureSchema(
                AREA_CODE="WC",
                BLOCK_NUMBER="168",
                STRUCTURE_NUMBER="A001",
                LONGITUDE=-181.0,
            )

    def test_whitespace_stripping(self):
        """String fields with leading/trailing whitespace are stripped."""
        schema = PlatformStructureSchema(
            AREA_CODE="  WC  ",
            BLOCK_NUMBER=" 168 ",
            STRUCTURE_NUMBER=" A001 ",
        )
        assert schema.AREA_CODE == "WC"
        assert schema.BLOCK_NUMBER == "168"
        assert schema.STRUCTURE_NUMBER == "A001"

    def test_water_depth_zero_valid(self):
        """Water depth of zero is valid."""
        schema = PlatformStructureSchema(
            AREA_CODE="WC",
            BLOCK_NUMBER="168",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH=0.0,
        )
        assert schema.WATER_DEPTH == 0.0

    def test_water_depth_coercion_from_string(self):
        """Water depth provided as string is coerced to float."""
        schema = PlatformStructureSchema(
            AREA_CODE="WC",
            BLOCK_NUMBER="168",
            STRUCTURE_NUMBER="A001",
            WATER_DEPTH="150.5",
        )
        assert schema.WATER_DEPTH == 150.5

    def test_empty_string_coerced_to_none(self):
        """Empty strings for optional fields are coerced to None."""
        schema = PlatformStructureSchema(
            AREA_CODE="WC",
            BLOCK_NUMBER="168",
            STRUCTURE_NUMBER="A001",
            COMPLEX_ID_NUM="",
            STRUCTURE_NAME="",
        )
        assert schema.COMPLEX_ID_NUM is None
        assert schema.STRUCTURE_NAME is None
