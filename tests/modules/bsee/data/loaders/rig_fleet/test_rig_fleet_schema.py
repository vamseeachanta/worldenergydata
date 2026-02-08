"""Tests for RigFleetSchema pydantic model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldenergydata.bsee.data.schemas.rig_fleet import RigFleetSchema


class TestRigFleetSchema:
    """Tests for RigFleetSchema validation and coercion."""

    def _full_data(self, **overrides) -> dict:
        """Return a complete valid data dict, with optional overrides."""
        defaults = {
            "RIG_NAME": "DEEPWATER TITAN",
            "RIG_TYPE": "drillship",
            "RIG_STATUS": "active",
            "OWNER": "Transocean",
            "OPERATOR": "Shell",
            "WATER_DEPTH_RATING_FT": 12000.0,
            "DRILLING_DEPTH_RATING_FT": 40000.0,
            "LOA_M": 238.0,
            "BEAM_M": 42.0,
            "DISPLACEMENT_TONNES": 96000.0,
            "DP_CLASS": 3,
            "YEAR_BUILT": 2014,
            "IMO_NUMBER": "9612345",
            "FLAG_STATE": "MHL",
            "MOONPOOL_DIAMETER_M": 7.6,
            "WELLS_DRILLED_COUNT": 55,
            "LAST_WAR_DATE": "2024-12-15",
            "LAST_AREA_CODE": "GC",
        }
        defaults.update(overrides)
        return defaults

    def test_valid_schema_all_fields(self):
        """All fields populated correctly produces a valid schema instance."""
        data = self._full_data()
        schema = RigFleetSchema(**data)

        assert schema.RIG_NAME == "DEEPWATER TITAN"
        assert schema.RIG_TYPE == "drillship"
        assert schema.RIG_STATUS == "active"
        assert schema.OWNER == "Transocean"
        assert schema.OPERATOR == "Shell"
        assert schema.WATER_DEPTH_RATING_FT == 12000.0
        assert schema.DRILLING_DEPTH_RATING_FT == 40000.0
        assert schema.LOA_M == 238.0
        assert schema.BEAM_M == 42.0
        assert schema.DISPLACEMENT_TONNES == 96000.0
        assert schema.DP_CLASS == 3
        assert schema.YEAR_BUILT == 2014
        assert schema.IMO_NUMBER == "9612345"
        assert schema.FLAG_STATE == "MHL"
        assert schema.MOONPOOL_DIAMETER_M == 7.6
        assert schema.WELLS_DRILLED_COUNT == 55
        assert schema.LAST_WAR_DATE == "2024-12-15"
        assert schema.LAST_AREA_CODE == "GC"

    def test_valid_schema_required_only(self):
        """Only RIG_NAME is required; all other fields default to None."""
        schema = RigFleetSchema(RIG_NAME="ROWAN MISSISSIPPI")

        assert schema.RIG_NAME == "ROWAN MISSISSIPPI"
        assert schema.RIG_TYPE is None
        assert schema.RIG_STATUS is None
        assert schema.OWNER is None
        assert schema.OPERATOR is None
        assert schema.WATER_DEPTH_RATING_FT is None
        assert schema.DRILLING_DEPTH_RATING_FT is None
        assert schema.LOA_M is None
        assert schema.BEAM_M is None
        assert schema.DISPLACEMENT_TONNES is None
        assert schema.DP_CLASS is None
        assert schema.YEAR_BUILT is None
        assert schema.IMO_NUMBER is None
        assert schema.FLAG_STATE is None
        assert schema.MOONPOOL_DIAMETER_M is None
        assert schema.WELLS_DRILLED_COUNT is None
        assert schema.LAST_WAR_DATE is None
        assert schema.LAST_AREA_CODE is None

    def test_strip_rig_name_whitespace(self):
        """Leading/trailing whitespace is stripped from RIG_NAME."""
        schema = RigFleetSchema(RIG_NAME="  DEEPWATER TITAN  ")
        assert schema.RIG_NAME == "DEEPWATER TITAN"

    def test_strip_rig_name_quotes(self):
        """Surrounding quotes are stripped from RIG_NAME."""
        schema = RigFleetSchema(RIG_NAME='"DEEPWATER TITAN"')
        assert schema.RIG_NAME == "DEEPWATER TITAN"

    def test_empty_string_to_none_for_optional_str_fields(self):
        """Empty strings for optional string fields coerce to None."""
        schema = RigFleetSchema(
            RIG_NAME="TEST RIG",
            RIG_TYPE="",
            RIG_STATUS="",
            OWNER="",
            OPERATOR="",
            IMO_NUMBER="",
            FLAG_STATE="",
            LAST_WAR_DATE="",
            LAST_AREA_CODE="",
        )
        assert schema.RIG_TYPE is None
        assert schema.RIG_STATUS is None
        assert schema.OWNER is None
        assert schema.OPERATOR is None
        assert schema.IMO_NUMBER is None
        assert schema.FLAG_STATE is None
        assert schema.LAST_WAR_DATE is None
        assert schema.LAST_AREA_CODE is None

    def test_coerce_string_water_depth_to_float(self):
        """String water depth is coerced to float."""
        schema = RigFleetSchema(
            RIG_NAME="TEST RIG",
            WATER_DEPTH_RATING_FT="12000.5",
        )
        assert schema.WATER_DEPTH_RATING_FT == 12000.5

    def test_reject_negative_water_depth(self):
        """Negative water depth raises ValidationError."""
        with pytest.raises(ValidationError, match="WATER_DEPTH_RATING_FT"):
            RigFleetSchema(
                RIG_NAME="TEST RIG",
                WATER_DEPTH_RATING_FT=-100.0,
            )

    def test_coerce_string_year_built_to_int(self):
        """String year built is coerced to int."""
        schema = RigFleetSchema(
            RIG_NAME="TEST RIG",
            YEAR_BUILT="2014",
        )
        assert schema.YEAR_BUILT == 2014

    def test_reject_invalid_year_built_too_low(self):
        """Year built below 1900 raises ValidationError."""
        with pytest.raises(ValidationError, match="YEAR_BUILT"):
            RigFleetSchema(
                RIG_NAME="TEST RIG",
                YEAR_BUILT=1850,
            )

    def test_reject_invalid_year_built_too_high(self):
        """Year built above 2035 raises ValidationError."""
        with pytest.raises(ValidationError, match="YEAR_BUILT"):
            RigFleetSchema(
                RIG_NAME="TEST RIG",
                YEAR_BUILT=2050,
            )

    def test_coerce_string_moonpool_diameter(self):
        """String moonpool diameter is coerced to float."""
        schema = RigFleetSchema(
            RIG_NAME="TEST RIG",
            MOONPOOL_DIAMETER_M="7.6",
        )
        assert schema.MOONPOOL_DIAMETER_M == 7.6
