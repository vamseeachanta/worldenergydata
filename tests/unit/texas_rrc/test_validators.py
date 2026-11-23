"""Tests for Texas RRC data validators."""

from worldenergydata.texas_rrc.validators import (
    TexasDataValidator,
    is_valid_texas_api_number,
    is_valid_texas_coordinates,
    is_valid_texas_district,
)


class TestValidateAPINumber:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_empty(self):
        valid, err = self.v.validate_api_number("")
        assert valid is False

    def test_valid_with_dashes(self):
        valid, err = self.v.validate_api_number("42-123-45678")
        assert valid is True

    def test_valid_without_dashes(self):
        valid, err = self.v.validate_api_number("4212345678")
        assert valid is True

    def test_invalid_state_code(self):
        valid, err = self.v.validate_api_number("99-123-45678")
        assert valid is False

    def test_invalid_format(self):
        valid, err = self.v.validate_api_number("ABCDEF")
        assert valid is False

    def test_invalid_county_code(self):
        valid, err = self.v.validate_api_number("42-999-45678")
        assert valid is False
        assert "county" in err.lower()


class TestValidateDistrict:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_empty(self):
        valid, err = self.v.validate_district("")
        assert valid is False

    def test_valid_numeric(self):
        valid, err = self.v.validate_district("01")
        assert valid is True

    def test_single_digit_padded(self):
        valid, err = self.v.validate_district("1")
        assert valid is True

    def test_valid_7b(self):
        valid, err = self.v.validate_district("7B")
        assert valid is True

    def test_valid_8a(self):
        valid, err = self.v.validate_district("8A")
        assert valid is True

    def test_lowercase(self):
        valid, err = self.v.validate_district("7b")
        assert valid is True

    def test_invalid(self):
        valid, err = self.v.validate_district("99")
        assert valid is False


class TestValidateTexasCoordinates:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_none_lat(self):
        valid, err = self.v.validate_texas_coordinates(None, -96.0)
        assert valid is False

    def test_valid_houston(self):
        valid, err = self.v.validate_texas_coordinates(29.76, -95.37)
        assert valid is True

    def test_lat_too_low(self):
        valid, err = self.v.validate_texas_coordinates(20.0, -96.0)
        assert valid is False

    def test_lat_too_high(self):
        valid, err = self.v.validate_texas_coordinates(40.0, -96.0)
        assert valid is False

    def test_lon_too_low(self):
        valid, err = self.v.validate_texas_coordinates(30.0, -110.0)
        assert valid is False

    def test_lon_too_high(self):
        valid, err = self.v.validate_texas_coordinates(30.0, -90.0)
        assert valid is False

    def test_invalid_format(self):
        valid, err = self.v.validate_texas_coordinates("abc", -96.0)
        assert valid is False


class TestValidateSchema:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_valid_data(self):
        schema = {"required": ["name", "age"]}
        data = {"name": "John", "age": 30}
        valid, errors = self.v.validate_schema(data, schema)
        assert valid is True

    def test_missing_required(self):
        schema = {"required": ["name", "age"]}
        data = {"name": "John"}
        valid, errors = self.v.validate_schema(data, schema)
        assert valid is False
        assert len(errors) == 1

    def test_strict_mode(self):
        schema = {"required": ["name"], "optional": ["age"], "strict": True}
        data = {"name": "John", "extra": "value"}
        valid, errors = self.v.validate_schema(data, schema)
        assert valid is False
        assert any("Unexpected" in e for e in errors)


class TestValidateTypes:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_valid_types(self):
        data = {"name": "John", "age": 30}
        types = {"name": str, "age": int}
        valid, errors = self.v.validate_types(data, types)
        assert valid is True

    def test_convertible_type(self):
        data = {"age": "30"}
        types = {"age": int}
        valid, errors = self.v.validate_types(data, types)
        assert valid is True  # string "30" can convert to int

    def test_non_convertible_type(self):
        data = {"age": "abc"}
        types = {"age": int}
        valid, errors = self.v.validate_types(data, types)
        assert valid is False


class TestValidateDateRange:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_empty(self):
        valid, err = self.v.validate_date_range("")
        assert valid is False

    def test_valid_iso(self):
        valid, err = self.v.validate_date_range("2020-06-15")
        assert valid is True

    def test_valid_us(self):
        valid, err = self.v.validate_date_range("06/15/2020")
        assert valid is True

    def test_unparseable(self):
        valid, err = self.v.validate_date_range("not-a-date")
        assert valid is False

    def test_too_old(self):
        valid, err = self.v.validate_date_range("1850-01-01")
        assert valid is False


class TestValidateNumericRange:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_none_optional(self):
        valid, err = self.v.validate_numeric_range(None)
        assert valid is True

    def test_valid(self):
        valid, err = self.v.validate_numeric_range(50.0)
        assert valid is True

    def test_negative_not_allowed(self):
        valid, err = self.v.validate_numeric_range(-1.0)
        assert valid is False

    def test_negative_allowed(self):
        valid, err = self.v.validate_numeric_range(-1.0, allow_negative=True)
        assert valid is True

    def test_zero_not_allowed(self):
        valid, err = self.v.validate_numeric_range(0.0, allow_zero=False)
        assert valid is False

    def test_below_min(self):
        valid, err = self.v.validate_numeric_range(5.0, min_val=10.0)
        assert valid is False

    def test_above_max(self):
        valid, err = self.v.validate_numeric_range(100.0, max_val=50.0)
        assert valid is False

    def test_invalid_format(self):
        valid, err = self.v.validate_numeric_range("abc")
        assert valid is False


class TestValidateLeaseNumber:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_empty(self):
        valid, err = self.v.validate_lease_number("")
        assert valid is False

    def test_valid(self):
        valid, err = self.v.validate_lease_number("123456")
        assert valid is True

    def test_non_numeric(self):
        valid, err = self.v.validate_lease_number("ABC123")
        assert valid is False

    def test_too_long(self):
        valid, err = self.v.validate_lease_number("12345678901")
        assert valid is False


class TestValidateOperatorNumber:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_empty(self):
        valid, err = self.v.validate_operator_number("")
        assert valid is False

    def test_valid(self):
        valid, err = self.v.validate_operator_number("123456")
        assert valid is True

    def test_non_numeric(self):
        valid, err = self.v.validate_operator_number("ABC")
        assert valid is False

    def test_too_long(self):
        valid, err = self.v.validate_operator_number("123456789")
        assert valid is False


class TestValidateWellData:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_valid(self):
        data = {
            "api_number": "42-123-45678",
            "district": "01",
            "latitude": 30.0,
            "longitude": -96.0,
            "total_depth": 5000,
            "completion_date": "2020-06-15",
        }
        valid, errors = self.v.validate_well_data(data)
        assert valid is True

    def test_invalid_api(self):
        data = {"api_number": "INVALID"}
        valid, errors = self.v.validate_well_data(data)
        assert valid is False

    def test_empty(self):
        valid, errors = self.v.validate_well_data({})
        assert valid is True


class TestValidateProductionData:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_valid(self):
        data = {
            "district": "01",
            "oil_production": 1000.0,
            "production_date": "2020-06-15",
        }
        valid, errors = self.v.validate_production_data(data)
        assert valid is True

    def test_negative_production(self):
        data = {"oil_production": -100.0}
        valid, errors = self.v.validate_production_data(data)
        assert valid is False


class TestValidatePermitData:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_valid(self):
        data = {
            "api_number": "42-123-45678",
            "district": "01",
            "latitude": 30.0,
            "longitude": -96.0,
            "approved_date": "2020-06-15",
            "total_depth": 5000,
        }
        valid, errors = self.v.validate_permit_data(data)
        assert valid is True

    def test_empty(self):
        valid, errors = self.v.validate_permit_data({})
        assert valid is True


class TestNormalizeAPINumber:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_empty(self):
        assert self.v.normalize_api_number("") is None

    def test_with_dashes(self):
        assert self.v.normalize_api_number("42-123-45678") == "42-123-45678"

    def test_without_dashes(self):
        assert self.v.normalize_api_number("4212345678") == "42-123-45678"

    def test_invalid_returns_none(self):
        assert self.v.normalize_api_number("INVALID") is None

    def test_wrong_state(self):
        assert self.v.normalize_api_number("9912345678") is None


class TestNormalizeDistrict:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_empty(self):
        assert self.v.normalize_district("") is None

    def test_valid(self):
        assert self.v.normalize_district("01") == "01"

    def test_single_digit(self):
        assert self.v.normalize_district("1") == "01"

    def test_lowercase(self):
        assert self.v.normalize_district("7b") == "7B"

    def test_invalid(self):
        assert self.v.normalize_district("99") is None


class TestGetStatistics:
    def setup_method(self):
        self.v = TexasDataValidator()

    def test_initial(self):
        stats = self.v.get_statistics()
        assert stats["validations"] == 0


class TestConvenienceFunctions:
    def test_is_valid_api_true(self):
        assert is_valid_texas_api_number("42-123-45678") is True

    def test_is_valid_api_false(self):
        assert is_valid_texas_api_number("") is False

    def test_is_valid_district_true(self):
        assert is_valid_texas_district("01") is True

    def test_is_valid_district_false(self):
        assert is_valid_texas_district("99") is False

    def test_is_valid_coords_true(self):
        assert is_valid_texas_coordinates(30.0, -96.0) is True

    def test_is_valid_coords_false(self):
        assert is_valid_texas_coordinates(50.0, -96.0) is False
