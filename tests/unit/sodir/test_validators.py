"""Tests for SODIR data validators."""

from worldenergydata.sodir.validators import DataValidator


class TestDataValidator:
    """Tests for DataValidator."""

    def setup_method(self):
        self.validator = DataValidator()

    def test_validate_schema_all_required_present(self):
        data = {"name": "Test", "value": 42}
        schema = {"required": ["name", "value"]}
        valid, errors = self.validator.validate_schema(data, schema)
        assert valid is True
        assert errors == []

    def test_validate_schema_missing_required(self):
        data = {"name": "Test"}
        schema = {"required": ["name", "value"]}
        valid, errors = self.validator.validate_schema(data, schema)
        assert valid is False
        assert len(errors) == 1
        assert "value" in errors[0]

    def test_validate_schema_none_value_is_missing(self):
        data = {"name": None}
        schema = {"required": ["name"]}
        valid, errors = self.validator.validate_schema(data, schema)
        assert valid is False

    def test_validate_schema_empty_string_is_missing(self):
        data = {"name": ""}
        schema = {"required": ["name"]}
        valid, errors = self.validator.validate_schema(data, schema)
        assert valid is False

    def test_validate_schema_strict_rejects_extra_fields(self):
        data = {"name": "Test", "extra": "value"}
        schema = {"required": ["name"], "strict": True}
        valid, errors = self.validator.validate_schema(data, schema)
        assert valid is False
        assert "Unexpected field: extra" in errors

    def test_validate_schema_optional_fields_allowed(self):
        data = {"name": "Test", "desc": "optional"}
        schema = {"required": ["name"], "optional": ["desc"], "strict": True}
        valid, errors = self.validator.validate_schema(data, schema)
        assert valid is True

    def test_validate_schema_increments_count(self):
        data = {"name": "Test"}
        schema = {"required": ["name"]}
        self.validator.validate_schema(data, schema)
        assert self.validator.validation_count == 1
        assert self.validator.error_count == 0

    def test_validate_schema_increments_error_count(self):
        data = {}
        schema = {"required": ["name"]}
        self.validator.validate_schema(data, schema)
        assert self.validator.error_count == 1

    def test_validate_types_correct_types(self):
        data = {"name": "Test", "value": 42}
        type_schema = {"name": str, "value": int}
        assert self.validator.validate_types(data, type_schema) is True

    def test_validate_types_convertible_type(self):
        data = {"value": "42"}
        type_schema = {"value": int}
        assert self.validator.validate_types(data, type_schema) is True

    def test_validate_types_wrong_type(self):
        data = {"value": "not_a_number"}
        type_schema = {"value": int}
        assert self.validator.validate_types(data, type_schema) is False

    def test_validate_types_none_value_skipped(self):
        data = {"value": None}
        type_schema = {"value": int}
        assert self.validator.validate_types(data, type_schema) is True

    def test_validate_types_missing_field_skipped(self):
        data = {}
        type_schema = {"value": int}
        assert self.validator.validate_types(data, type_schema) is True

    def test_validate_norwegian_coordinates_valid(self):
        assert self.validator.validate_norwegian_coordinates(60.0, 5.0) is True

    def test_validate_norwegian_coordinates_at_boundary(self):
        assert self.validator.validate_norwegian_coordinates(56.0, -5.0) is True
        assert self.validator.validate_norwegian_coordinates(72.0, 35.0) is True

    def test_validate_norwegian_coordinates_out_of_bounds_lat(self):
        assert self.validator.validate_norwegian_coordinates(55.0, 5.0) is False
        assert self.validator.validate_norwegian_coordinates(73.0, 5.0) is False

    def test_validate_norwegian_coordinates_out_of_bounds_lon(self):
        assert self.validator.validate_norwegian_coordinates(60.0, -6.0) is False
        assert self.validator.validate_norwegian_coordinates(60.0, 36.0) is False

    def test_validate_norwegian_coordinates_none(self):
        assert self.validator.validate_norwegian_coordinates(None, 5.0) is False
        assert self.validator.validate_norwegian_coordinates(60.0, None) is False

    def test_validate_norwegian_coordinates_invalid_type(self):
        assert self.validator.validate_norwegian_coordinates("invalid", 5.0) is False

    def test_validate_utm_zone_valid(self):
        assert self.validator.validate_utm_zone(31) is True
        assert self.validator.validate_utm_zone(33) is True

    def test_validate_utm_zone_invalid(self):
        assert self.validator.validate_utm_zone(30) is False
        assert self.validator.validate_utm_zone(36) is False

    def test_validate_utm_zone_none(self):
        assert self.validator.validate_utm_zone(None) is False

    def test_validate_utm_zone_string_coercion(self):
        assert self.validator.validate_utm_zone("32") is True

    def test_validate_utm_zone_invalid_string(self):
        assert self.validator.validate_utm_zone("abc") is False

    def test_validate_date_range_valid_iso(self):
        assert self.validator.validate_date_range("2020-01-01") is True

    def test_validate_date_range_valid_iso_with_time(self):
        assert self.validator.validate_date_range("2020-01-01T12:00:00Z") is True

    def test_validate_date_range_too_old(self):
        assert self.validator.validate_date_range("1950-01-01") is False

    def test_validate_date_range_custom_min(self):
        assert self.validator.validate_date_range("1950-01-01", min_year=1940) is True

    def test_validate_date_range_custom_max(self):
        assert self.validator.validate_date_range("2100-01-01", max_year=2050) is False

    def test_validate_date_range_none(self):
        assert self.validator.validate_date_range(None) is False

    def test_validate_date_range_empty(self):
        assert self.validator.validate_date_range("") is False

    def test_validate_date_range_invalid_format(self):
        assert self.validator.validate_date_range("not-a-date") is False

    def test_validate_numeric_range_none_is_valid(self):
        assert self.validator.validate_numeric_range(None) is True

    def test_validate_numeric_range_positive(self):
        assert self.validator.validate_numeric_range(5.0) is True

    def test_validate_numeric_range_negative_disallowed(self):
        assert self.validator.validate_numeric_range(-1.0) is False

    def test_validate_numeric_range_negative_allowed(self):
        assert self.validator.validate_numeric_range(-1.0, allow_negative=True) is True

    def test_validate_numeric_range_zero_allowed(self):
        assert self.validator.validate_numeric_range(0.0, allow_zero=True) is True

    def test_validate_numeric_range_zero_disallowed(self):
        assert self.validator.validate_numeric_range(0.0, allow_zero=False) is False

    def test_validate_numeric_range_with_bounds(self):
        assert self.validator.validate_numeric_range(5.0, min_val=0, max_val=10) is True
        assert (
            self.validator.validate_numeric_range(15.0, min_val=0, max_val=10) is False
        )

    def test_validate_numeric_range_invalid_type(self):
        assert self.validator.validate_numeric_range("not_a_number") is False

    def test_validate_block_name_valid(self):
        assert self.validator.validate_block_name("35/11") is True
        assert self.validator.validate_block_name("1/1") is True

    def test_validate_block_name_with_suffix(self):
        assert self.validator.validate_block_name("35/11-1") is True

    def test_validate_block_name_invalid(self):
        assert self.validator.validate_block_name("abc") is False
        assert self.validator.validate_block_name("") is False

    def test_validate_wellbore_name_valid(self):
        assert self.validator.validate_wellbore_name("35/11-1") is True

    def test_validate_wellbore_name_with_suffix(self):
        assert self.validator.validate_wellbore_name("35/11-1 S") is True

    def test_validate_wellbore_name_invalid(self):
        assert self.validator.validate_wellbore_name("abc") is False
        assert self.validator.validate_wellbore_name("") is False

    def test_validate_field_data_valid(self):
        data = {
            "fldName": "Test Field",
            "fldOriginalReservesOil": 100,
            "fldRemainingReservesOil": 50,
            "fldDiscoveryYear": 1990,
            "fldProductionStartYear": 1995,
        }
        valid, errors = self.validator.validate_field_data(data)
        assert valid is True

    def test_validate_field_data_missing_name(self):
        data = {}
        valid, errors = self.validator.validate_field_data(data)
        assert valid is False
        assert "Missing field name" in errors

    def test_validate_field_data_remaining_exceeds_original(self):
        data = {
            "fldName": "Test",
            "fldOriginalReservesOil": 50,
            "fldRemainingReservesOil": 100,
        }
        valid, errors = self.validator.validate_field_data(data)
        assert valid is False
        assert any("exceed" in e.lower() for e in errors)

    def test_validate_field_data_prod_before_discovery(self):
        data = {
            "fldName": "Test",
            "fldDiscoveryYear": 2000,
            "fldProductionStartYear": 1990,
        }
        valid, errors = self.validator.validate_field_data(data)
        assert valid is False

    def test_validate_field_data_cessation_before_prod_start(self):
        data = {
            "fldName": "Test",
            "fldProductionStartYear": 2000,
            "fldCessationYear": 1990,
        }
        valid, errors = self.validator.validate_field_data(data)
        assert valid is False

    def test_validate_discovery_data_valid(self):
        data = {
            "dscName": "Test Discovery",
            "dscDiscoveryYear": 2010,
            "dscRecoverableOil": 100.0,
        }
        valid, errors = self.validator.validate_discovery_data(data)
        assert valid is True

    def test_validate_discovery_data_missing_name(self):
        data = {"dscRecoverableOil": 100.0}
        valid, errors = self.validator.validate_discovery_data(data)
        assert valid is False
        assert "Missing discovery name" in errors

    def test_validate_discovery_data_no_resources(self):
        data = {"dscName": "Test"}
        valid, errors = self.validator.validate_discovery_data(data)
        assert valid is False
        assert "No resource estimates" in errors[0]

    def test_validate_survey_data_valid(self):
        data = {
            "srvName": "Test Survey",
            "srvAcquisitionStartDate": "2020-01-01",
            "srvAcquisitionEndDate": "2020-06-01",
            "srvAreaKm2": 500,
        }
        valid, errors = self.validator.validate_survey_data(data)
        assert valid is True

    def test_validate_survey_data_missing_name(self):
        data = {}
        valid, errors = self.validator.validate_survey_data(data)
        assert valid is False
        assert "Missing survey name" in errors

    def test_validate_survey_data_end_before_start(self):
        data = {
            "srvName": "Test",
            "srvAcquisitionStartDate": "2020-06-01",
            "srvAcquisitionEndDate": "2020-01-01",
        }
        valid, errors = self.validator.validate_survey_data(data)
        assert valid is False

    def test_get_statistics(self):
        self.validator.validate_schema({"name": "Test"}, {"required": ["name"]})
        self.validator.validate_schema({}, {"required": ["name"]})
        stats = self.validator.get_statistics()
        assert stats["validations"] == 2
        assert stats["errors"] == 1
        assert stats["success_rate"] == 0.5
