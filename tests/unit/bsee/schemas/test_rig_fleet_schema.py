"""Tests for BSEE rig fleet schema."""

import pytest
from pydantic import ValidationError

from worldenergydata.bsee.data.schemas.rig_fleet import RigFleetSchema


class TestRigFleetSchema:
    """Tests for RigFleetSchema."""

    def test_create_with_required_fields(self):
        schema = RigFleetSchema(RIG_NAME="Deepwater Horizon")
        assert schema.RIG_NAME == "Deepwater Horizon"

    def test_create_with_all_fields(self):
        schema = RigFleetSchema(
            RIG_NAME="Ocean Star",
            RIG_TYPE="drillship",
            RIG_STATUS="active",
            OWNER="Company A",
            OPERATOR="Operator B",
            WATER_DEPTH_RATING_FT=10000.0,
            DRILLING_DEPTH_RATING_FT=40000.0,
            LOA_M=238.0,
            BEAM_M=42.0,
            DISPLACEMENT_TONNES=97000.0,
            DP_CLASS=3,
            YEAR_BUILT=2010,
            IMO_NUMBER="9431752",
            FLAG_STATE="Marshall Islands",
            MOONPOOL_DIAMETER_M=12.0,
            WELLS_DRILLED_COUNT=50,
            IS_OFFSHORE=True,
        )
        assert schema.RIG_TYPE == "drillship"
        assert schema.WATER_DEPTH_RATING_FT == 10000.0
        assert schema.DP_CLASS == 3

    def test_strip_quotes_from_rig_name(self):
        schema = RigFleetSchema(RIG_NAME='"Ocean Star"')
        assert schema.RIG_NAME == "Ocean Star"

    def test_strip_single_quotes_from_rig_name(self):
        schema = RigFleetSchema(RIG_NAME="'Ocean Star'")
        assert schema.RIG_NAME == "Ocean Star"

    def test_empty_string_coerced_to_none(self):
        schema = RigFleetSchema(
            RIG_NAME="Test Rig",
            RIG_TYPE="",
            RIG_STATUS="   ",
            OWNER="  ",
            FLAG_STATE="",
        )
        assert schema.RIG_TYPE is None
        assert schema.RIG_STATUS is None
        assert schema.OWNER is None
        assert schema.FLAG_STATE is None

    def test_float_string_coercion(self):
        schema = RigFleetSchema(
            RIG_NAME="Test",
            WATER_DEPTH_RATING_FT="10000.5",
            LOA_M=" 238 ",
        )
        assert schema.WATER_DEPTH_RATING_FT == 10000.5
        assert schema.LOA_M == 238.0

    def test_empty_float_string_to_none(self):
        schema = RigFleetSchema(
            RIG_NAME="Test",
            WATER_DEPTH_RATING_FT="",
            LOA_M="  ",
        )
        assert schema.WATER_DEPTH_RATING_FT is None
        assert schema.LOA_M is None

    def test_negative_float_raises_error(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            RigFleetSchema(RIG_NAME="Test", WATER_DEPTH_RATING_FT=-100.0)

    def test_negative_loa_raises_error(self):
        with pytest.raises(ValidationError, match="Value must be >= 0"):
            RigFleetSchema(RIG_NAME="Test", LOA_M=-10.0)

    def test_int_string_coercion(self):
        schema = RigFleetSchema(
            RIG_NAME="Test",
            DP_CLASS="3",
            YEAR_BUILT=" 2010 ",
            WELLS_DRILLED_COUNT="50",
        )
        assert schema.DP_CLASS == 3
        assert schema.YEAR_BUILT == 2010
        assert schema.WELLS_DRILLED_COUNT == 50

    def test_empty_int_string_to_none(self):
        schema = RigFleetSchema(RIG_NAME="Test", DP_CLASS="", YEAR_BUILT="  ")
        assert schema.DP_CLASS is None
        assert schema.YEAR_BUILT is None

    def test_year_built_too_old_raises_error(self):
        with pytest.raises(
            ValidationError, match="YEAR_BUILT must be between 1900 and 2035"
        ):
            RigFleetSchema(RIG_NAME="Test", YEAR_BUILT=1899)

    def test_year_built_too_new_raises_error(self):
        with pytest.raises(
            ValidationError, match="YEAR_BUILT must be between 1900 and 2035"
        ):
            RigFleetSchema(RIG_NAME="Test", YEAR_BUILT=2036)

    def test_year_built_boundary_values(self):
        schema_min = RigFleetSchema(RIG_NAME="Test", YEAR_BUILT=1900)
        schema_max = RigFleetSchema(RIG_NAME="Test", YEAR_BUILT=2035)
        assert schema_min.YEAR_BUILT == 1900
        assert schema_max.YEAR_BUILT == 2035

    def test_zero_floats_are_valid(self):
        schema = RigFleetSchema(
            RIG_NAME="Test",
            WATER_DEPTH_RATING_FT=0.0,
            LOA_M=0.0,
        )
        assert schema.WATER_DEPTH_RATING_FT == 0.0
        assert schema.LOA_M == 0.0
