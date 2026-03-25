"""Tests for vessel fleet cross-field validation."""

from worldenergydata.vessel_fleet.quality.validator import (
    ValidationResult,
    validate_construction_vessel,
    validate_drilling_rig,
    validate_fleet,
)


class TestValidationResult:
    def test_is_valid_no_errors(self):
        r = ValidationResult(vessel_name="Test")
        assert r.is_valid is True

    def test_is_valid_with_errors(self):
        r = ValidationResult(vessel_name="Test", errors=["bad field"])
        assert r.is_valid is False

    def test_warnings_dont_invalidate(self):
        r = ValidationResult(vessel_name="Test", warnings=["unusual value"])
        assert r.is_valid is True


class TestValidateDrillingRig:
    def test_valid_record(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "Rig A",
            "RIG_TYPE": "drillship",
            "WATER_DEPTH_RATING_FT": 12000.0,
            "YEAR_BUILT": 2015,
            "IMO_NUMBER": "1234567",
        })
        assert r.is_valid is True
        assert len(r.warnings) == 0

    def test_jackup_high_dp_warning(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "JU-01",
            "RIG_TYPE": "jack_up",
            "DP_CLASS": 3,
        })
        assert r.is_valid is True
        assert any("Jack-up" in w for w in r.warnings)

    def test_land_rig_displacement_warning(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "LR-01",
            "RIG_TYPE": "land_rig",
            "DISPLACEMENT_TONNES": 5000.0,
        })
        assert any("Land rig" in w for w in r.warnings)

    def test_negative_water_depth_error(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "R-01",
            "WATER_DEPTH_RATING_FT": -100.0,
        })
        assert r.is_valid is False
        assert any("Negative" in e for e in r.errors)

    def test_excessive_water_depth_error(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "R-01",
            "WATER_DEPTH_RATING_FT": 50000.0,
        })
        assert r.is_valid is False

    def test_year_built_old_warning(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "R-01",
            "YEAR_BUILT": 1940,
        })
        assert any("1950" in w for w in r.warnings)

    def test_year_built_future_error(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "R-01",
            "YEAR_BUILT": 2035,
        })
        assert r.is_valid is False

    def test_invalid_imo_error(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "R-01",
            "IMO_NUMBER": "ABC",
        })
        assert r.is_valid is False
        assert any("IMO" in e for e in r.errors)

    def test_imo_wrong_length_error(self):
        r = validate_drilling_rig({
            "VESSEL_NAME": "R-01",
            "IMO_NUMBER": "12345",
        })
        assert r.is_valid is False

    def test_unknown_name_default(self):
        r = validate_drilling_rig({})
        assert r.vessel_name == "UNKNOWN"


class TestValidateConstructionVessel:
    def test_valid_record(self):
        r = validate_construction_vessel({
            "VESSEL_NAME": "Sleipnir",
            "MAIN_CRANE_CAPACITY_T": 10000.0,
            "YEAR_BUILT": 2019,
            "IMO_NUMBER": "9781478",
        })
        assert r.is_valid is True

    def test_crane_capacity_warning(self):
        r = validate_construction_vessel({
            "VESSEL_NAME": "V-01",
            "MAIN_CRANE_CAPACITY_T": 30000.0,
        })
        assert any("25,000" in w for w in r.warnings)

    def test_negative_water_depth_error(self):
        r = validate_construction_vessel({
            "VESSEL_NAME": "V-01",
            "WATER_DEPTH_RATING_M": -10.0,
        })
        assert r.is_valid is False

    def test_deep_water_warning(self):
        r = validate_construction_vessel({
            "VESSEL_NAME": "V-01",
            "WATER_DEPTH_RATING_M": 6000.0,
        })
        assert any("5,000" in w for w in r.warnings)

    def test_year_built_future_error(self):
        r = validate_construction_vessel({
            "VESSEL_NAME": "V-01",
            "YEAR_BUILT": 2035,
        })
        assert r.is_valid is False


class TestValidateFleet:
    def test_drilling_rig_fleet(self):
        records = [
            {"VESSEL_NAME": "R1", "YEAR_BUILT": 2020},
            {"VESSEL_NAME": "R2", "WATER_DEPTH_RATING_FT": -100.0},
        ]
        results = validate_fleet(records, "drilling_rig")
        assert len(results) == 2
        assert results[0].is_valid is True
        assert results[1].is_valid is False

    def test_construction_vessel_fleet(self):
        records = [
            {"VESSEL_NAME": "V1"},
        ]
        results = validate_fleet(records, "construction_vessel")
        assert len(results) == 1
        assert results[0].is_valid is True

    def test_empty_fleet(self):
        results = validate_fleet([], "drilling_rig")
        assert results == []
