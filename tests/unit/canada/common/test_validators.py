"""Tests for Canada common data validators."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from worldenergydata.canada.common.validators import (
    CanadaDataValidator,
    ValidationError,
    ValidationResult,
)


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_create_basic(self):
        err = ValidationError(field="uwi", message="Invalid format")
        assert err.field == "uwi"
        assert err.message == "Invalid format"
        assert err.severity == "error"

    def test_create_with_all_fields(self):
        err = ValidationError(
            field="lat",
            message="Out of range",
            value=200.0,
            code="COORD_RANGE",
            severity="warning",
        )
        assert err.value == 200.0
        assert err.code == "COORD_RANGE"
        assert err.severity == "warning"

    def test_to_dict(self):
        err = ValidationError(
            field="uwi", message="Invalid", value="BAD", code="UWI_ERR"
        )
        d = err.to_dict()
        assert d["field"] == "uwi"
        assert d["message"] == "Invalid"
        assert d["value"] == "BAD"
        assert d["code"] == "UWI_ERR"
        assert d["severity"] == "error"

    def test_to_dict_none_value(self):
        err = ValidationError(field="uwi", message="Invalid")
        d = err.to_dict()
        assert d["value"] is None


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_valid(self):
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        result = ValidationResult()
        result.add_error("field", "message", "value", "CODE")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].severity == "error"

    def test_add_warning(self):
        result = ValidationResult()
        result.add_warning("field", "message")
        assert result.is_valid is True  # warnings don't make it invalid
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"

    def test_merge_errors(self):
        r1 = ValidationResult()
        r2 = ValidationResult()
        r2.add_error("f", "msg")
        r1.merge(r2)
        assert r1.is_valid is False
        assert len(r1.errors) == 1

    def test_merge_warnings(self):
        r1 = ValidationResult()
        r2 = ValidationResult()
        r2.add_warning("f", "msg")
        r1.merge(r2)
        assert r1.is_valid is True
        assert len(r1.warnings) == 1

    def test_merge_metadata(self):
        r1 = ValidationResult()
        r1.metadata["a"] = 1
        r2 = ValidationResult()
        r2.metadata["b"] = 2
        r1.merge(r2)
        assert r1.metadata == {"a": 1, "b": 2}

    def test_to_dict(self):
        result = ValidationResult()
        result.add_error("f1", "err1")
        result.add_warning("f2", "warn1")
        result.metadata["test"] = True
        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert len(d["errors"]) == 1
        assert len(d["warnings"]) == 1
        assert d["metadata"]["test"] is True


class TestCanadaDataValidatorProvinceCode:
    """Tests for CanadaDataValidator.validate_province_code."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_empty(self):
        result = self.v.validate_province_code("")
        assert result.is_valid is False
        assert result.errors[0].code == "PROVINCE_EMPTY"

    def test_none(self):
        result = self.v.validate_province_code(None)
        assert result.is_valid is False

    def test_wrong_length(self):
        result = self.v.validate_province_code("ABC")
        assert result.is_valid is False
        assert result.errors[0].code == "PROVINCE_LENGTH"

    def test_invalid_code(self):
        result = self.v.validate_province_code("ZZ")
        assert result.is_valid is False
        assert result.errors[0].code == "PROVINCE_INVALID"

    def test_valid_alberta(self):
        result = self.v.validate_province_code("AB")
        assert result.is_valid is True
        assert result.metadata["province_name"] == "Alberta"

    def test_lowercase(self):
        result = self.v.validate_province_code("ab")
        assert result.is_valid is True

    def test_non_og_province_warning(self):
        result = self.v.validate_province_code("ON")
        assert result.is_valid is True  # valid province but warning about no O&G
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "PROVINCE_NO_OG"

    def test_og_province_no_warning(self):
        result = self.v.validate_province_code("AB")
        assert len(result.warnings) == 0


class TestCanadaDataValidatorCoordinates:
    """Tests for CanadaDataValidator.validate_coordinates."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_null_latitude(self):
        result = self.v.validate_coordinates(None, -113.0)
        assert result.is_valid is False
        assert result.errors[0].code == "COORD_NULL"

    def test_null_longitude(self):
        result = self.v.validate_coordinates(53.0, None)
        assert result.is_valid is False

    def test_valid_edmonton(self):
        result = self.v.validate_coordinates(53.5461, -113.4938)
        assert result.is_valid is True

    def test_latitude_out_of_range(self):
        result = self.v.validate_coordinates(100.0, -113.0)
        assert result.is_valid is False
        assert result.errors[0].code == "COORD_RANGE"

    def test_longitude_out_of_range(self):
        result = self.v.validate_coordinates(53.0, 200.0)
        assert result.is_valid is False

    def test_outside_canada(self):
        result = self.v.validate_coordinates(30.0, -90.0)
        assert result.is_valid is False
        assert result.errors[0].code == "COORD_OUTSIDE_CANADA"

    def test_province_outside_bounds_warning(self):
        # Valid Canada coords but outside Alberta's bbox
        result = self.v.validate_coordinates(55.0, -100.0, province="AB")
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "COORD_OUTSIDE_PROVINCE"

    def test_province_within_bounds_no_warning(self):
        result = self.v.validate_coordinates(53.5, -113.5, province="AB")
        assert len(result.warnings) == 0

    def test_unknown_province_no_bounds_check(self):
        result = self.v.validate_coordinates(53.5, -113.5, province="ON")
        assert result.is_valid is True  # ON has no defined bounds, skips check


class TestCanadaDataValidatorWellStatus:
    """Tests for CanadaDataValidator.validate_well_status."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_empty(self):
        result = self.v.validate_well_status("")
        assert result.is_valid is False
        assert result.errors[0].code == "STATUS_EMPTY"

    def test_valid_active(self):
        result = self.v.validate_well_status("ACTIVE")
        assert result.is_valid is True
        assert "status_description" in result.metadata

    def test_case_insensitive(self):
        result = self.v.validate_well_status("active")
        assert result.is_valid is True

    def test_invalid(self):
        result = self.v.validate_well_status("UNKNOWN_STATUS")
        assert result.is_valid is False
        assert result.errors[0].code == "STATUS_INVALID"

    def test_all_valid_statuses(self):
        for status in [
            "ACTIVE",
            "SUSPENDED",
            "ABANDONED",
            "COMPLETED",
            "DRILLING",
            "LICENSED",
            "CANCELLED",
            "RE-ENTERED",
        ]:
            result = self.v.validate_well_status(status)
            assert result.is_valid is True, f"Status {status} should be valid"


class TestCanadaDataValidatorFluidType:
    """Tests for CanadaDataValidator.validate_fluid_type."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_empty(self):
        result = self.v.validate_fluid_type("")
        assert result.is_valid is False
        assert result.errors[0].code == "FLUID_EMPTY"

    def test_valid_oil(self):
        result = self.v.validate_fluid_type("OIL")
        assert result.is_valid is True
        assert "fluid_description" in result.metadata

    def test_case_insensitive(self):
        result = self.v.validate_fluid_type("gas")
        assert result.is_valid is True

    def test_invalid(self):
        result = self.v.validate_fluid_type("DIESEL")
        assert result.is_valid is False

    def test_bitumen(self):
        result = self.v.validate_fluid_type("BITUMEN")
        assert result.is_valid is True


class TestCanadaDataValidatorDate:
    """Tests for CanadaDataValidator.validate_date."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_none_value(self):
        result = self.v.validate_date(None)
        assert result.is_valid is False
        assert result.errors[0].code == "DATE_NULL"

    def test_iso_string(self):
        result = self.v.validate_date("2020-06-15")
        assert result.is_valid is True
        assert "parsed_date" in result.metadata

    def test_slash_string(self):
        result = self.v.validate_date("2020/06/15")
        assert result.is_valid is True

    def test_compact_string(self):
        result = self.v.validate_date("20200615")
        assert result.is_valid is True

    def test_datetime_object(self):
        result = self.v.validate_date(datetime(2020, 6, 15))
        assert result.is_valid is True

    def test_date_object(self):
        result = self.v.validate_date(date(2020, 6, 15))
        assert result.is_valid is True

    def test_unparseable_string(self):
        result = self.v.validate_date("not-a-date")
        assert result.is_valid is False
        assert result.errors[0].code == "DATE_FORMAT"

    def test_too_old(self):
        result = self.v.validate_date("1850-01-01")
        assert result.is_valid is False
        assert result.errors[0].code == "DATE_TOO_OLD"

    def test_future_not_allowed(self):
        result = self.v.validate_date("2099-01-01")
        assert result.is_valid is False
        assert result.errors[0].code == "DATE_FUTURE"

    def test_future_allowed(self):
        result = self.v.validate_date("2099-01-01", allow_future=True)
        assert result.is_valid is True

    def test_invalid_type(self):
        result = self.v.validate_date(12345)
        assert result.is_valid is False
        assert result.errors[0].code == "DATE_TYPE"

    def test_custom_min_year(self):
        result = self.v.validate_date("1920-01-01", min_year=1950)
        assert result.is_valid is False


class TestCanadaDataValidatorLicenseNumber:
    """Tests for CanadaDataValidator.validate_license_number."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_empty(self):
        result = self.v.validate_license_number("")
        assert result.is_valid is False
        assert result.errors[0].code == "LICENSE_EMPTY"

    def test_valid_no_province(self):
        result = self.v.validate_license_number("W0123456")
        assert result.is_valid is True

    def test_alberta_valid_format(self):
        result = self.v.validate_license_number("W0123456", province="AB")
        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_alberta_invalid_format_warning(self):
        result = self.v.validate_license_number("INVALID", province="AB")
        assert result.is_valid is True  # warning not error
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "LICENSE_FORMAT_AB"

    def test_bc_valid_format(self):
        result = self.v.validate_license_number("12345", province="BC")
        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_bc_invalid_format_warning(self):
        result = self.v.validate_license_number("INVALID", province="BC")
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "LICENSE_FORMAT_BC"

    def test_numeric_input_converted(self):
        result = self.v.validate_license_number(123456)
        assert result.is_valid is True


class TestCanadaDataValidatorUWI:
    """Tests for CanadaDataValidator.validate_uwi."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_empty_uwi(self):
        result = self.v.validate_uwi("")
        assert result.is_valid is False
        assert result.errors[0].code == "UWI_EMPTY"

    def test_valid_dls_uwi(self):
        result = self.v.validate_uwi("100.16-09-010-09W4.00")
        assert result.is_valid is True
        assert result.metadata.get("survey_system") == "DLS"
        assert result.metadata.get("province") == "AB"

    def test_invalid_uwi(self):
        result = self.v.validate_uwi("INVALID-FORMAT")
        assert result.is_valid is False


class TestCanadaDataValidatorWellRecord:
    """Tests for CanadaDataValidator.validate_well_record."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_valid_record(self):
        record = {
            "uwi": "100.16-09-010-09W4.00",
            "latitude": 53.5,
            "longitude": -113.5,
            "province": "AB",
            "status": "ACTIVE",
            "fluid_type": "OIL",
        }
        result = self.v.validate_well_record(record)
        assert result.is_valid is True

    def test_invalid_province(self):
        record = {"province": "ZZ"}
        result = self.v.validate_well_record(record)
        assert result.is_valid is False

    def test_invalid_status(self):
        record = {"status": "INVALID"}
        result = self.v.validate_well_record(record)
        assert result.is_valid is False

    def test_empty_record(self):
        result = self.v.validate_well_record({})
        assert result.is_valid is True

    def test_alternate_keys(self):
        record = {
            "lat": 53.5,
            "lon": -113.5,
            "prov": "AB",
            "well_status": "ACTIVE",
            "fluid": "GAS",
            "license": "W0123456",
        }
        result = self.v.validate_well_record(record)
        assert result.is_valid is True

    def test_date_validation(self):
        record = {"spud_date": "2020-06-15"}
        result = self.v.validate_well_record(record)
        assert result.is_valid is True


class TestCanadaDataValidatorBatch:
    """Tests for CanadaDataValidator.validate_batch."""

    def setup_method(self):
        self.v = CanadaDataValidator()

    def test_all_valid(self):
        records = [
            {"province": "AB"},
            {"province": "BC"},
        ]
        valid, invalid, results = self.v.validate_batch(records)
        assert valid == 2
        assert invalid == 0

    def test_mixed(self):
        records = [
            {"province": "AB"},
            {"province": "ZZ"},
        ]
        valid, invalid, results = self.v.validate_batch(records)
        assert valid == 1
        assert invalid == 1

    def test_empty_batch(self):
        valid, invalid, results = self.v.validate_batch([])
        assert valid == 0
        assert invalid == 0
        assert results == []
