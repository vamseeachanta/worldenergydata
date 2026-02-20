"""Tests for validation rules."""

from worldenergydata.common.validation.rules import (
    CommonRules,
    CrossFieldRule,
    CustomRule,
    EnumRule,
    LengthRule,
    PatternRule,
    RangeRule,
    RequiredRule,
    RuleResult,
)


class TestRuleResult:
    def test_success(self):
        r = RuleResult.success()
        assert r.is_valid is True
        assert r.error_message is None

    def test_failure(self):
        r = RuleResult.failure("bad value")
        assert r.is_valid is False
        assert r.error_message == "bad value"
        assert r.error_type == "validation"

    def test_failure_custom_type(self):
        r = RuleResult.failure("msg", error_type="range")
        assert r.error_type == "range"


class TestRequiredRule:
    def test_none_fails(self):
        rule = RequiredRule("name")
        result = rule.validate(None)
        assert result.is_valid is False
        assert result.error_type == "required"

    def test_empty_string_fails(self):
        rule = RequiredRule("name")
        result = rule.validate("")
        assert result.is_valid is False

    def test_whitespace_fails(self):
        rule = RequiredRule("name")
        result = rule.validate("   ")
        assert result.is_valid is False

    def test_valid_string(self):
        rule = RequiredRule("name")
        result = rule.validate("John")
        assert result.is_valid is True

    def test_allow_empty_string(self):
        rule = RequiredRule("name", allow_empty_string=True)
        result = rule.validate("")
        assert result.is_valid is True

    def test_non_string_value(self):
        rule = RequiredRule("count")
        result = rule.validate(0)
        assert result.is_valid is True

    def test_custom_error(self):
        rule = RequiredRule("name", error_message="Name needed")
        result = rule.validate(None)
        assert result.error_message == "Name needed"


class TestRangeRule:
    def test_none_passes(self):
        rule = RangeRule("value", min_value=0, max_value=100)
        assert rule.validate(None).is_valid is True

    def test_within_range(self):
        rule = RangeRule("value", min_value=0, max_value=100)
        assert rule.validate(50).is_valid is True

    def test_below_min(self):
        rule = RangeRule("value", min_value=0)
        result = rule.validate(-1)
        assert result.is_valid is False
        assert result.error_type == "range"

    def test_above_max(self):
        rule = RangeRule("value", max_value=100)
        result = rule.validate(101)
        assert result.is_valid is False

    def test_on_boundary_inclusive(self):
        rule = RangeRule("value", min_value=0, max_value=100, inclusive=True)
        assert rule.validate(0).is_valid is True
        assert rule.validate(100).is_valid is True

    def test_on_boundary_exclusive(self):
        rule = RangeRule("value", min_value=0, max_value=100, inclusive=False)
        assert rule.validate(0).is_valid is False
        assert rule.validate(100).is_valid is False

    def test_non_numeric_fails(self):
        rule = RangeRule("value", min_value=0)
        result = rule.validate("abc")
        assert result.is_valid is False
        assert result.error_type == "type"

    def test_string_number(self):
        rule = RangeRule("value", min_value=0)
        result = rule.validate("50")
        assert result.is_valid is True

    def test_min_only(self):
        rule = RangeRule("value", min_value=0)
        assert rule.validate(999999).is_valid is True

    def test_max_only(self):
        rule = RangeRule("value", max_value=100)
        assert rule.validate(-999999).is_valid is True


class TestPatternRule:
    def test_none_passes(self):
        rule = PatternRule("api", pattern=r"^\d{10}$")
        assert rule.validate(None).is_valid is True

    def test_matches(self):
        rule = PatternRule("api", pattern=r"^\d{10}$")
        assert rule.validate("1234567890").is_valid is True

    def test_no_match(self):
        rule = PatternRule("api", pattern=r"^\d{10}$")
        result = rule.validate("12345")
        assert result.is_valid is False
        assert result.error_type == "pattern"

    def test_non_string_converted(self):
        rule = PatternRule("num", pattern=r"^\d+$")
        assert rule.validate(12345).is_valid is True

    def test_custom_description(self):
        rule = PatternRule("api", pattern=r"^\d{10}$", description="10-digit API")
        result = rule.validate("bad")
        assert "10-digit API" in result.error_message


class TestEnumRule:
    def test_none_passes(self):
        rule = EnumRule("status", allowed_values={"A", "B"})
        assert rule.validate(None).is_valid is True

    def test_allowed_value(self):
        rule = EnumRule("status", allowed_values={"Active", "Inactive"})
        assert rule.validate("Active").is_valid is True

    def test_disallowed_value(self):
        rule = EnumRule("status", allowed_values={"Active", "Inactive"})
        result = rule.validate("Unknown")
        assert result.is_valid is False
        assert result.error_type == "enum"

    def test_case_sensitive(self):
        rule = EnumRule("status", allowed_values={"Active"}, case_sensitive=True)
        assert rule.validate("active").is_valid is False

    def test_case_insensitive(self):
        rule = EnumRule("status", allowed_values={"Active"}, case_sensitive=False)
        assert rule.validate("active").is_valid is True
        assert rule.validate("ACTIVE").is_valid is True


class TestLengthRule:
    def test_none_passes(self):
        rule = LengthRule("name", min_length=1)
        assert rule.validate(None).is_valid is True

    def test_within_range(self):
        rule = LengthRule("name", min_length=1, max_length=10)
        assert rule.validate("hello").is_valid is True

    def test_too_short(self):
        rule = LengthRule("name", min_length=3)
        result = rule.validate("ab")
        assert result.is_valid is False
        assert result.error_type == "length"

    def test_too_long(self):
        rule = LengthRule("name", max_length=5)
        result = rule.validate("toolong")
        assert result.is_valid is False

    def test_non_string_converted(self):
        rule = LengthRule("val", min_length=1)
        assert rule.validate(123).is_valid is True


class TestCrossFieldRule:
    def test_no_record_passes(self):
        rule = CrossFieldRule(
            "start", ["end"], lambda r: r["start"] < r["end"], "start must be before end"
        )
        assert rule.validate("x", record=None).is_valid is True

    def test_valid_cross_field(self):
        rule = CrossFieldRule(
            "start", ["end"], lambda r: r["start"] < r["end"], "start must be before end"
        )
        record = {"start": 1, "end": 10}
        assert rule.validate(1, record=record).is_valid is True

    def test_invalid_cross_field(self):
        rule = CrossFieldRule(
            "start", ["end"], lambda r: r["start"] < r["end"], "start must be before end"
        )
        record = {"start": 10, "end": 1}
        result = rule.validate(10, record=record)
        assert result.is_valid is False
        assert result.error_type == "cross_field"

    def test_missing_related_field_passes(self):
        rule = CrossFieldRule(
            "start", ["end"], lambda r: r["start"] < r["end"], "msg"
        )
        record = {"start": 10}
        assert rule.validate(10, record=record).is_valid is True

    def test_validator_exception(self):
        rule = CrossFieldRule(
            "a", ["b"], lambda r: r["a"] / r["b"] > 0, "msg"
        )
        record = {"a": 1, "b": 0}
        result = rule.validate(1, record=record)
        assert result.is_valid is False


class TestCustomRule:
    def test_none_passes(self):
        rule = CustomRule("val", lambda v: v > 0, "must be positive")
        assert rule.validate(None).is_valid is True

    def test_valid(self):
        rule = CustomRule("val", lambda v: v > 0, "must be positive")
        assert rule.validate(5).is_valid is True

    def test_invalid(self):
        rule = CustomRule("val", lambda v: v > 0, "must be positive")
        result = rule.validate(-1)
        assert result.is_valid is False
        assert result.error_type == "custom"

    def test_validator_exception(self):
        rule = CustomRule("val", lambda v: int(v) > 0, "msg")
        result = rule.validate("abc")
        assert result.is_valid is False


class TestCommonRules:
    def test_api_number_10(self):
        rule = CommonRules.api_number_10()
        assert rule.validate("1234567890").is_valid is True
        assert rule.validate("12345").is_valid is False

    def test_api_number_12(self):
        rule = CommonRules.api_number_12()
        assert rule.validate("123456789012").is_valid is True
        assert rule.validate("1234567890").is_valid is False

    def test_production_date(self):
        rule = CommonRules.production_date()
        assert rule.validate("202401").is_valid is True
        assert rule.validate("2024-01").is_valid is False

    def test_positive_number(self):
        rule = CommonRules.positive_number("oil")
        assert rule.validate(0).is_valid is True
        assert rule.validate(100).is_valid is True
        assert rule.validate(-1).is_valid is False

    def test_percentage(self):
        rule = CommonRules.percentage("pct")
        assert rule.validate(0.5).is_valid is True
        assert rule.validate(1.5).is_valid is False

    def test_latitude(self):
        rule = CommonRules.latitude()
        assert rule.validate(45).is_valid is True
        assert rule.validate(91).is_valid is False
        assert rule.validate(-91).is_valid is False

    def test_longitude(self):
        rule = CommonRules.longitude()
        assert rule.validate(90).is_valid is True
        assert rule.validate(181).is_valid is False

    def test_days_in_month(self):
        rule = CommonRules.days_in_month()
        assert rule.validate(15).is_valid is True
        assert rule.validate(32).is_valid is False
