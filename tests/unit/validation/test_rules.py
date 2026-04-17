"""Tests for validation rules engine."""

from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.validation.exceptions import (
    ConsistencyError,
    CrossFieldValidationError,
    DataTypeError,
    DateFormatError,
    RangeValidationError,
    RequiredFieldError,
    ValidationError,
)
from worldenergydata.validation.rules import (
    APINumberRule,
    CrossFieldRule,
    CrossFieldRules,
    CustomValidators,
    DataTypeRule,
    DateFormatRule,
    PatternRule,
    RangeRule,
    RequiredFieldRule,
    UniqueRule,
    ValidationRules,
)
from worldenergydata.validation.schema import DataType, DateFormat


class TestValidationRulesRequired:
    def test_required_present(self):
        assert ValidationRules.validate_required("value", "field", True) is True

    def test_required_missing_none(self):
        with pytest.raises(RequiredFieldError):
            ValidationRules.validate_required(None, "field", True)

    def test_required_missing_empty(self):
        with pytest.raises(RequiredFieldError):
            ValidationRules.validate_required("", "field", True)

    def test_not_required_none(self):
        assert ValidationRules.validate_required(None, "field", False) is True

    def test_not_required_empty(self):
        assert ValidationRules.validate_required("", "field", False) is True


class TestValidationRulesDataType:
    def test_string_valid(self):
        assert ValidationRules.validate_data_type("hello", "f", DataType.STRING) is True

    def test_string_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type(123, "f", DataType.STRING)

    def test_integer_valid(self):
        assert ValidationRules.validate_data_type(42, "f", DataType.INTEGER) is True

    def test_integer_string_valid(self):
        assert ValidationRules.validate_data_type("42", "f", DataType.INTEGER) is True

    def test_integer_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("abc", "f", DataType.INTEGER)

    def test_float_valid(self):
        assert ValidationRules.validate_data_type(3.14, "f", DataType.FLOAT) is True

    def test_float_string_valid(self):
        assert ValidationRules.validate_data_type("3.14", "f", DataType.FLOAT) is True

    def test_float_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("abc", "f", DataType.FLOAT)

    def test_boolean_valid(self):
        assert ValidationRules.validate_data_type(True, "f", DataType.BOOLEAN) is True
        assert ValidationRules.validate_data_type("true", "f", DataType.BOOLEAN) is True
        assert ValidationRules.validate_data_type("0", "f", DataType.BOOLEAN) is True

    def test_boolean_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("yes", "f", DataType.BOOLEAN)

    def test_date_valid(self):
        assert (
            ValidationRules.validate_data_type("2024-01-01", "f", DataType.DATE) is True
        )

    def test_date_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("not-a-date", "f", DataType.DATE)

    def test_datetime_valid(self):
        assert (
            ValidationRules.validate_data_type(
                "2024-01-01T12:00:00", "f", DataType.DATETIME
            )
            is True
        )

    def test_datetime_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("not-datetime", "f", DataType.DATETIME)

    def test_array_valid(self):
        assert ValidationRules.validate_data_type([1, 2], "f", DataType.ARRAY) is True

    def test_array_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("not array", "f", DataType.ARRAY)

    def test_object_valid(self):
        assert (
            ValidationRules.validate_data_type({"k": "v"}, "f", DataType.OBJECT) is True
        )

    def test_object_invalid(self):
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("not obj", "f", DataType.OBJECT)

    def test_none_skipped(self):
        assert ValidationRules.validate_data_type(None, "f", DataType.STRING) is True


class TestValidationRulesRange:
    def test_in_range(self):
        assert ValidationRules.validate_range(50, "f", 0, 100) is True

    def test_below_min(self):
        with pytest.raises(RangeValidationError):
            ValidationRules.validate_range(-1, "f", min_value=0)

    def test_above_max(self):
        with pytest.raises(RangeValidationError):
            ValidationRules.validate_range(101, "f", max_value=100)

    def test_none_skipped(self):
        assert ValidationRules.validate_range(None, "f", 0, 100) is True

    def test_non_numeric_skipped(self):
        assert ValidationRules.validate_range("abc", "f", 0, 100) is True

    def test_string_numeric(self):
        with pytest.raises(RangeValidationError):
            ValidationRules.validate_range("150", "f", max_value=100)


class TestValidationRulesLength:
    def test_valid_length(self):
        assert (
            ValidationRules.validate_length("hello", "f", min_length=1, max_length=10)
            is True
        )

    def test_too_short(self):
        with pytest.raises(ValidationError):
            ValidationRules.validate_length("a", "f", min_length=5)

    def test_too_long(self):
        with pytest.raises(ValidationError):
            ValidationRules.validate_length("abcdefghijk", "f", max_length=5)

    def test_none_skipped(self):
        assert ValidationRules.validate_length(None, "f", min_length=1) is True

    def test_non_string_converted(self):
        assert (
            ValidationRules.validate_length(123, "f", min_length=1, max_length=5)
            is True
        )


class TestValidationRulesPattern:
    def test_valid_pattern(self):
        assert (
            ValidationRules.validate_pattern("123456789012", "f", r"^\d{12}$") is True
        )

    def test_invalid_pattern(self):
        with pytest.raises(ValidationError):
            ValidationRules.validate_pattern("abc", "f", r"^\d{12}$")

    def test_none_pattern_skipped(self):
        assert ValidationRules.validate_pattern("abc", "f", None) is True

    def test_none_value_skipped(self):
        assert ValidationRules.validate_pattern(None, "f", r"^\d+$") is True


class TestValidationRulesAllowedValues:
    def test_valid_value(self):
        assert (
            ValidationRules.validate_allowed_values(
                "ACTIVE", "f", ["ACTIVE", "INACTIVE"]
            )
            is True
        )

    def test_invalid_value(self):
        with pytest.raises(ValidationError):
            ValidationRules.validate_allowed_values(
                "UNKNOWN", "f", ["ACTIVE", "INACTIVE"]
            )

    def test_none_allowed_list(self):
        assert ValidationRules.validate_allowed_values("anything", "f", None) is True

    def test_none_value(self):
        assert ValidationRules.validate_allowed_values(None, "f", ["ACTIVE"]) is True


class TestValidationRulesDateFormat:
    def test_yyyymm_valid(self):
        assert (
            ValidationRules.validate_date_format("202301", "f", DateFormat.YYYYMM)
            is True
        )

    def test_yyyymm_invalid_format(self):
        with pytest.raises(DateFormatError):
            ValidationRules.validate_date_format("2023-01", "f", DateFormat.YYYYMM)

    def test_yyyymm_invalid_month(self):
        with pytest.raises(DateFormatError):
            ValidationRules.validate_date_format("202313", "f", DateFormat.YYYYMM)

    def test_yyyymm_invalid_year(self):
        with pytest.raises(DateFormatError):
            ValidationRules.validate_date_format("180001", "f", DateFormat.YYYYMM)

    def test_yyyy_mm_dd_valid(self):
        assert (
            ValidationRules.validate_date_format(
                "2024-01-15", "f", DateFormat.YYYY_MM_DD
            )
            is True
        )

    def test_yyyy_mm_dd_invalid(self):
        with pytest.raises(DateFormatError):
            ValidationRules.validate_date_format(
                "01/15/2024", "f", DateFormat.YYYY_MM_DD
            )

    def test_iso8601_valid(self):
        assert (
            ValidationRules.validate_date_format(
                "2024-01-15T12:00:00Z", "f", DateFormat.ISO8601
            )
            is True
        )

    def test_none_format_skipped(self):
        assert ValidationRules.validate_date_format("anything", "f", None) is True

    def test_none_value_skipped(self):
        assert (
            ValidationRules.validate_date_format(None, "f", DateFormat.YYYYMM) is True
        )


class TestValidationRulesHelpers:
    def test_is_numeric_string_true(self):
        assert ValidationRules._is_numeric_string("3.14") is True

    def test_is_numeric_string_false(self):
        assert ValidationRules._is_numeric_string("abc") is False

    def test_to_numeric_valid(self):
        assert ValidationRules._to_numeric("42") == 42.0

    def test_to_numeric_invalid(self):
        assert ValidationRules._to_numeric("abc") is None

    def test_is_date_string_yyyy_mm_dd(self):
        assert ValidationRules._is_date_string("2024-01-15") is True

    def test_is_date_string_mm_dd_yyyy(self):
        assert ValidationRules._is_date_string("01/15/2024") is True

    def test_is_date_string_yyyymm(self):
        assert ValidationRules._is_date_string("202301") is True

    def test_is_date_string_invalid(self):
        assert ValidationRules._is_date_string("not-a-date") is False

    def test_is_date_string_non_string(self):
        assert ValidationRules._is_date_string(42) is False

    def test_is_datetime_string_iso(self):
        assert ValidationRules._is_datetime_string("2024-01-15T12:00:00") is True

    def test_is_datetime_string_space(self):
        assert ValidationRules._is_datetime_string("2024-01-15 12:00:00") is True

    def test_is_datetime_string_invalid(self):
        assert ValidationRules._is_datetime_string("not-datetime") is False


class TestCrossFieldRulesDateConsistency:
    def test_valid_dates(self):
        data = {"start": "2024-01-01", "end": "2024-12-31"}
        assert CrossFieldRules.validate_date_consistency(data, "start", "end") is True

    def test_end_before_start(self):
        data = {"start": "2024-12-31", "end": "2024-01-01"}
        with pytest.raises(CrossFieldValidationError):
            CrossFieldRules.validate_date_consistency(data, "start", "end")

    def test_missing_date_skipped(self):
        data = {"start": "2024-01-01"}
        assert CrossFieldRules.validate_date_consistency(data, "start", "end") is True


class TestCrossFieldRulesProductionConsistency:
    def test_valid_production(self):
        data = {"DAYS_ON_PROD": 15, "MON_O_PROD_VOL": 1000, "MON_G_PROD_VOL": 500}
        assert CrossFieldRules.validate_production_consistency(data) is True

    def test_zero_days_with_production(self):
        data = {"DAYS_ON_PROD": 0, "MON_O_PROD_VOL": 1000, "MON_G_PROD_VOL": 0}
        with pytest.raises(ConsistencyError):
            CrossFieldRules.validate_production_consistency(data)

    def test_zero_days_zero_production(self):
        data = {"DAYS_ON_PROD": 0, "MON_O_PROD_VOL": 0, "MON_G_PROD_VOL": 0}
        assert CrossFieldRules.validate_production_consistency(data) is True


class TestCrossFieldRulesSumConsistency:
    def test_valid_sum(self):
        data = {"a": 30, "b": 70, "total": 100}
        assert (
            CrossFieldRules.validate_sum_consistency(data, ["a", "b"], "total") is True
        )

    def test_invalid_sum(self):
        data = {"a": 30, "b": 70, "total": 50}
        with pytest.raises(ConsistencyError):
            CrossFieldRules.validate_sum_consistency(data, ["a", "b"], "total")

    def test_within_tolerance(self):
        data = {"a": 30.005, "b": 69.999, "total": 100}
        assert (
            CrossFieldRules.validate_sum_consistency(
                data, ["a", "b"], "total", tolerance=0.01
            )
            is True
        )


class TestCrossFieldRulesPercentageSum:
    def test_valid_percentages(self):
        data = {"p1": 30, "p2": 70}
        assert CrossFieldRules.validate_percentage_sum(data, ["p1", "p2"]) is True

    def test_invalid_percentages(self):
        data = {"p1": 30, "p2": 60}
        with pytest.raises(ConsistencyError):
            CrossFieldRules.validate_percentage_sum(data, ["p1", "p2"])

    def test_within_tolerance(self):
        data = {"p1": 50.005, "p2": 49.999}
        assert (
            CrossFieldRules.validate_percentage_sum(data, ["p1", "p2"], tolerance=0.01)
            is True
        )


class TestCustomValidatorsAPIWellNumber:
    def test_valid(self):
        assert CustomValidators.validate_api_well_number("123456789012") is True

    def test_invalid_format(self):
        with pytest.raises(ValidationError):
            CustomValidators.validate_api_well_number("12345")

    def test_empty_string(self):
        assert CustomValidators.validate_api_well_number("") is True


class TestCustomValidatorsLeaseNumber:
    def test_valid(self):
        assert CustomValidators.validate_lease_number("ABC123") is True

    def test_invalid(self):
        with pytest.raises(ValidationError):
            CustomValidators.validate_lease_number("abc-123")

    def test_empty_string(self):
        assert CustomValidators.validate_lease_number("") is True


class TestCustomValidatorsProductionDate:
    def test_valid(self):
        assert CustomValidators.validate_production_date("202301") is True

    def test_invalid_format(self):
        with pytest.raises(DateFormatError):
            CustomValidators.validate_production_date("2023-01")

    def test_invalid_month(self):
        with pytest.raises(DateFormatError):
            CustomValidators.validate_production_date("202313")

    def test_invalid_year(self):
        with pytest.raises(DateFormatError):
            CustomValidators.validate_production_date("180001")

    def test_empty_string(self):
        assert CustomValidators.validate_production_date("") is True


# ========================================================================
# Wrapper Rule Classes Tests
# ========================================================================


class TestAPINumberRule:
    def test_valid_api_numbers(self):
        data = pd.Series(["123456789012", "987654321098"])
        rule = APINumberRule()
        result = rule.validate(data)
        assert result.is_valid

    def test_invalid_api_number(self):
        data = pd.Series(["12345", "123456789012"])
        rule = APINumberRule()
        result = rule.validate(data)
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_null_values_skipped(self):
        data = pd.Series([None, "123456789012"])
        rule = APINumberRule()
        result = rule.validate(data)
        assert result.is_valid


class TestDataTypeRule:
    def test_valid_int_type(self):
        data = pd.Series([1, 2, 3])
        rule = DataTypeRule(int)
        result = rule.validate(data)
        assert result.is_valid

    def test_invalid_type(self):
        data = pd.Series([1, "not_int", 3])
        rule = DataTypeRule(int)
        result = rule.validate(data)
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_multiple_allowed_types(self):
        data = pd.Series([1, 2.5, 3])
        rule = DataTypeRule([int, float])
        result = rule.validate(data)
        assert result.is_valid

    def test_null_allowed_by_default(self):
        data = pd.Series(["a", None, "c"])
        rule = DataTypeRule(str, allow_null=True)
        result = rule.validate(data)
        assert result.is_valid

    def test_null_not_allowed(self):
        data = pd.Series(["a", None, "c"])
        rule = DataTypeRule(str, allow_null=False)
        result = rule.validate(data)
        assert not result.is_valid
        assert len(result.errors) == 1


class TestDateFormatRule:
    def test_valid_dates(self):
        data = pd.Series(["2024-01-15", "2024-06-30"])
        rule = DateFormatRule(formats=["%Y-%m-%d"])
        result = rule.validate(data)
        assert result.is_valid

    def test_invalid_date(self):
        data = pd.Series(["2024-01-15", "not-a-date"])
        rule = DateFormatRule(formats=["%Y-%m-%d"])
        result = rule.validate(data)
        assert not result.is_valid

    def test_null_skipped(self):
        data = pd.Series(["2024-01-15", None])
        rule = DateFormatRule(formats=["%Y-%m-%d"])
        result = rule.validate(data)
        assert result.is_valid

    def test_min_date_enforcement(self):
        data = pd.Series(["2020-01-01", "2024-06-15"])
        rule = DateFormatRule(
            formats=["%Y-%m-%d"],
            min_date=datetime(2023, 1, 1),
        )
        result = rule.validate(data)
        assert not result.is_valid

    def test_max_date_enforcement(self):
        data = pd.Series(["2024-01-15", "2030-12-31"])
        rule = DateFormatRule(
            formats=["%Y-%m-%d"],
            max_date=datetime(2025, 12, 31),
        )
        result = rule.validate(data)
        assert not result.is_valid

    def test_multiple_formats(self):
        data = pd.Series(["2024-01-15", "01/15/2024"])
        rule = DateFormatRule(formats=["%Y-%m-%d", "%m/%d/%Y"])
        result = rule.validate(data)
        assert result.is_valid


class TestRangeRule:
    def test_in_range(self):
        data = pd.Series([10, 50, 90])
        rule = RangeRule(min_value=0, max_value=100)
        result = rule.validate(data)
        assert result.is_valid

    def test_below_min(self):
        data = pd.Series([10, -5, 50])
        rule = RangeRule(min_value=0)
        result = rule.validate(data)
        assert not result.is_valid

    def test_above_max(self):
        data = pd.Series([50, 150])
        rule = RangeRule(max_value=100)
        result = rule.validate(data)
        assert not result.is_valid

    def test_null_skipped(self):
        data = pd.Series([10, None, 50])
        rule = RangeRule(min_value=0, max_value=100)
        result = rule.validate(data)
        assert result.is_valid

    def test_non_numeric_error(self):
        data = pd.Series([10, "abc", 50])
        rule = RangeRule(min_value=0)
        result = rule.validate(data)
        assert not result.is_valid

    def test_min_only(self):
        data = pd.Series([100, 200, 300])
        rule = RangeRule(min_value=50)
        result = rule.validate(data)
        assert result.is_valid

    def test_max_only(self):
        data = pd.Series([1, 2, 3])
        rule = RangeRule(max_value=10)
        result = rule.validate(data)
        assert result.is_valid


class TestPatternRule:
    def test_valid_pattern(self):
        data = pd.Series(["ABC123", "DEF456"])
        rule = PatternRule(pattern=r"^[A-Z]{3}\d{3}$")
        result = rule.validate(data)
        assert result.is_valid

    def test_invalid_pattern(self):
        data = pd.Series(["ABC123", "invalid"])
        rule = PatternRule(pattern=r"^[A-Z]{3}\d{3}$")
        result = rule.validate(data)
        assert not result.is_valid

    def test_null_skipped(self):
        data = pd.Series(["ABC123", None])
        rule = PatternRule(pattern=r"^[A-Z]{3}\d{3}$")
        result = rule.validate(data)
        assert result.is_valid

    def test_custom_message(self):
        data = pd.Series(["invalid"])
        rule = PatternRule(pattern=r"^\d+$", message="Must be numeric")
        result = rule.validate(data)
        assert not result.is_valid
        assert "Must be numeric" in result.errors[0].message

    def test_default_message(self):
        data = pd.Series(["invalid"])
        rule = PatternRule(pattern=r"^\d+$")
        result = rule.validate(data)
        assert not result.is_valid
        assert "pattern" in result.errors[0].message.lower()


class TestUniqueRule:
    def test_unique_values(self):
        data = pd.Series([1, 2, 3, 4])
        rule = UniqueRule()
        result = rule.validate(data)
        assert result.is_valid

    def test_duplicate_values(self):
        data = pd.Series([1, 2, 2, 3])
        rule = UniqueRule()
        result = rule.validate(data)
        assert not result.is_valid
        # Both duplicate entries flagged
        assert len(result.errors) == 2

    def test_all_duplicates(self):
        data = pd.Series([1, 1, 1])
        rule = UniqueRule()
        result = rule.validate(data)
        assert not result.is_valid
        assert len(result.errors) == 3


class TestRequiredFieldRule:
    def test_all_fields_present(self):
        df = pd.DataFrame({"name": ["A", "B"], "value": [1, 2]})
        rule = RequiredFieldRule(required_fields=["name", "value"])
        result = rule.validate(df)
        assert result.is_valid

    def test_missing_field(self):
        df = pd.DataFrame({"name": ["A", "B"]})
        rule = RequiredFieldRule(required_fields=["name", "value"])
        result = rule.validate(df)
        assert not result.is_valid

    def test_field_with_nulls(self):
        df = pd.DataFrame({"name": ["A", None], "value": [1, 2]})
        rule = RequiredFieldRule(required_fields=["name"])
        result = rule.validate(df)
        assert not result.is_valid

    def test_no_required_fields(self):
        df = pd.DataFrame({"name": ["A"]})
        rule = RequiredFieldRule(required_fields=[])
        result = rule.validate(df)
        assert result.is_valid


class TestCrossFieldRule:
    def test_valid_cross_field(self):
        df = pd.DataFrame({"start": [1], "end": [10]})
        rule = CrossFieldRule(
            validation_func=lambda d: [],
            dependent_fields=["start", "end"],
        )
        result = rule.validate(df)
        assert result.is_valid

    def test_invalid_cross_field(self):
        df = pd.DataFrame({"start": [10], "end": [1]})
        rule = CrossFieldRule(
            validation_func=lambda d: ["end must be after start"],
            dependent_fields=["start", "end"],
        )
        result = rule.validate(df)
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_multiple_errors(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        rule = CrossFieldRule(
            validation_func=lambda d: ["error 1", "error 2"],
            dependent_fields=["a", "b"],
        )
        result = rule.validate(df)
        assert len(result.errors) == 2
