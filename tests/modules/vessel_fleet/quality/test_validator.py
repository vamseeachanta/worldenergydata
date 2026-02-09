"""Tests for fleet validation."""

from worldenergydata.vessel_fleet.quality.validator import (
    validate_drilling_rig,
    validate_construction_vessel,
)


class TestValidateDrillingRig:
    def test_valid_record(self):
        result = validate_drilling_rig({
            "VESSEL_NAME": "TEST",
            "RIG_TYPE": "drillship",
            "WATER_DEPTH_RATING_FT": 12000.0,
            "YEAR_BUILT": 2014,
        })
        assert result.is_valid

    def test_negative_water_depth_error(self):
        result = validate_drilling_rig({
            "VESSEL_NAME": "TEST",
            "WATER_DEPTH_RATING_FT": -100,
        })
        assert not result.is_valid

    def test_future_year_error(self):
        result = validate_drilling_rig({
            "VESSEL_NAME": "TEST",
            "YEAR_BUILT": 2050,
        })
        assert not result.is_valid

    def test_jackup_high_dp_warning(self):
        result = validate_drilling_rig({
            "VESSEL_NAME": "TEST",
            "RIG_TYPE": "jack_up",
            "DP_CLASS": 3,
        })
        assert result.is_valid  # Warning, not error
        assert len(result.warnings) == 1

    def test_invalid_imo_error(self):
        result = validate_drilling_rig({
            "VESSEL_NAME": "TEST",
            "IMO_NUMBER": "123",
        })
        assert not result.is_valid


class TestValidateConstructionVessel:
    def test_valid_record(self):
        result = validate_construction_vessel({
            "VESSEL_NAME": "SLEIPNIR",
            "MAIN_CRANE_CAPACITY_T": 10000.0,
            "YEAR_BUILT": 2019,
        })
        assert result.is_valid

    def test_high_crane_capacity_warning(self):
        result = validate_construction_vessel({
            "VESSEL_NAME": "TEST",
            "MAIN_CRANE_CAPACITY_T": 30000.0,
        })
        assert result.is_valid  # Warning only
        assert len(result.warnings) == 1
