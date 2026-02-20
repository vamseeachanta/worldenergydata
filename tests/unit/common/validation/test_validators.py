"""Tests for common validation utilities."""

from worldenergydata.common.validation.validators import (
    ValidationResult,
    validate_api_number,
    validate_coordinates,
    validate_date_format,
    validate_production_record,
)


class TestValidationResult:
    def test_default_valid(self):
        r = ValidationResult()
        assert r.is_valid is True
        assert r.errors == []
        assert r.warnings == []

    def test_add_error(self):
        r = ValidationResult()
        r.add_error("field", "type", "msg")
        assert r.is_valid is False
        assert len(r.errors) == 1

    def test_add_error_with_value_and_row(self):
        r = ValidationResult()
        r.add_error("field", "type", "msg", value="val", row=5)
        assert r.errors[0]["value"] == "val"
        assert r.errors[0]["row"] == 5

    def test_add_error_truncates_long_value(self):
        r = ValidationResult()
        r.add_error("field", "type", "msg", value="x" * 200)
        assert len(r.errors[0]["value"]) == 100

    def test_add_warning(self):
        r = ValidationResult()
        r.add_warning("field", "msg")
        assert r.is_valid is True
        assert len(r.warnings) == 1

    def test_add_warning_with_value_and_row(self):
        r = ValidationResult()
        r.add_warning("field", "msg", value="val", row=3)
        assert r.warnings[0]["value"] == "val"
        assert r.warnings[0]["row"] == 3

    def test_merge(self):
        r1 = ValidationResult(validated_count=5, failed_count=1)
        r2 = ValidationResult(validated_count=3, failed_count=2)
        r2.add_error("f", "t", "m")
        r2.add_warning("f", "m")
        r1.merge(r2)
        assert r1.is_valid is False
        assert r1.validated_count == 8
        assert r1.failed_count == 3
        assert len(r1.errors) == 1
        assert len(r1.warnings) == 1

    def test_to_dict(self):
        r = ValidationResult(validated_count=10, failed_count=2)
        r.add_error("f", "t", "m")
        d = r.to_dict()
        assert d["is_valid"] is False
        assert d["validated_count"] == 10
        assert d["failed_count"] == 2
        assert d["error_count"] == 1
        assert d["warning_count"] == 0


class TestValidateAPINumber:
    def test_empty(self):
        valid, err = validate_api_number("")
        assert valid is False

    def test_valid_10_digit(self):
        valid, err = validate_api_number("4212345678")
        assert valid is True

    def test_valid_12_digit(self):
        valid, err = validate_api_number("421234567800")
        assert valid is True

    def test_valid_14_digit(self):
        valid, err = validate_api_number("42123456780000")
        assert valid is True

    def test_with_dashes_stripped(self):
        valid, err = validate_api_number("42-123-45678")
        assert valid is True

    def test_invalid_length(self):
        valid, err = validate_api_number("12345")
        assert valid is False
        assert "digits" in err

    def test_invalid_state_code(self):
        valid, err = validate_api_number("0012345678")
        assert valid is False
        assert "state code" in err.lower()

    def test_required_length(self):
        valid, err = validate_api_number("4212345678", required_length=12)
        assert valid is False


class TestValidateCoordinates:
    def test_valid(self):
        valid, err = validate_coordinates(29.0, -95.0)
        assert valid is True

    def test_lat_out_of_range(self):
        valid, err = validate_coordinates(100.0, -95.0)
        assert valid is False

    def test_lon_out_of_range(self):
        valid, err = validate_coordinates(29.0, -200.0)
        assert valid is False

    def test_strict_ocean_valid(self):
        valid, err = validate_coordinates(27.0, -90.0, strict_ocean=True)
        assert valid is True

    def test_strict_ocean_lat_invalid(self):
        valid, err = validate_coordinates(10.0, -90.0, strict_ocean=True)
        assert valid is False

    def test_strict_ocean_lon_invalid(self):
        valid, err = validate_coordinates(27.0, -70.0, strict_ocean=True)
        assert valid is False


class TestValidateDateFormat:
    def test_valid_yearmonth(self):
        valid, err = validate_date_format("202006")
        assert valid is True

    def test_invalid_format(self):
        valid, err = validate_date_format("not-a-date")
        assert valid is False

    def test_custom_format(self):
        valid, err = validate_date_format("2020-06-15", "%Y-%m-%d")
        assert valid is True

    def test_out_of_range_year(self):
        valid, err = validate_date_format("180001")
        assert valid is False
        assert "range" in err.lower()


class TestValidateProductionRecord:
    def test_valid_record(self):
        record = {
            "api_well_number": "608114123400",
            "production_date": "202006",
            "oil_volume": 1000.0,
            "gas_volume": 5000.0,
        }
        result = validate_production_record(record)
        assert result.is_valid is True

    def test_missing_required(self):
        record = {"oil_volume": 1000.0}
        result = validate_production_record(record)
        assert result.is_valid is False
        assert result.failed_count == 1

    def test_negative_volume(self):
        record = {
            "api_well_number": "608114123400",
            "production_date": "202006",
            "oil_volume": -100.0,
            "gas_volume": 5000.0,
        }
        result = validate_production_record(record)
        assert result.is_valid is False

    def test_strict_high_volume_warning(self):
        record = {
            "api_well_number": "608114123400",
            "production_date": "202006",
            "oil_volume": 20000000.0,
            "gas_volume": 5000.0,
        }
        result = validate_production_record(record, strict=True)
        assert len(result.warnings) >= 1

    def test_invalid_days(self):
        record = {
            "api_well_number": "608114123400",
            "production_date": "202006",
            "oil_volume": 1000.0,
            "gas_volume": 5000.0,
            "days_on_production": 50,
        }
        result = validate_production_record(record)
        assert result.is_valid is False

    def test_non_numeric_volume(self):
        record = {
            "api_well_number": "608114123400",
            "production_date": "202006",
            "oil_volume": "abc",
            "gas_volume": 5000.0,
        }
        result = validate_production_record(record)
        assert result.is_valid is False
