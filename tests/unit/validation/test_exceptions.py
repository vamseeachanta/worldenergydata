"""Tests for validation module exceptions."""

import pytest

from worldenergydata.validation.exceptions import (
    ConsistencyError,
    CrossFieldValidationError,
    DataTypeError,
    DateFormatError,
    RangeValidationError,
    RequiredFieldError,
    SchemaValidationError,
    ValidationError,
)


class TestValidationError:
    def test_basic_message(self):
        err = ValidationError("test error")
        assert "test error" in str(err)

    def test_with_field(self):
        err = ValidationError("bad value", field="temperature")
        assert err.field == "temperature"
        assert "Field: temperature" in str(err)

    def test_with_value(self):
        err = ValidationError("out of range", value=-5)
        assert err.value == -5
        assert "Value: -5" in str(err)

    def test_with_rule(self):
        err = ValidationError("failed", rule="min_check")
        assert err.rule == "min_check"
        assert "Rule: min_check" in str(err)

    def test_with_row_index(self):
        err = ValidationError("bad row", row_index=42)
        assert err.row_index == 42

    def test_format_message_all_parts(self):
        err = ValidationError("msg", field="f", value="v", rule="r")
        msg = str(err)
        assert "msg" in msg
        assert "Field: f" in msg
        assert "Value: v" in msg
        assert "Rule: r" in msg

    def test_format_message_no_extras(self):
        err = ValidationError("just message")
        assert str(err) == "just message"

    def test_none_value_excluded(self):
        err = ValidationError("msg", field="f", value=None)
        assert "Value:" not in str(err)


class TestSchemaValidationError:
    def test_inherits_from_validation_error(self):
        err = SchemaValidationError("schema fail")
        assert isinstance(err, ValidationError)

    def test_with_field(self):
        err = SchemaValidationError("bad schema", field="col_a")
        assert err.field == "col_a"


class TestDataTypeError:
    def test_inherits_from_validation_error(self):
        err = DataTypeError("wrong type")
        assert isinstance(err, ValidationError)


class TestRangeValidationError:
    def test_inherits_from_validation_error(self):
        err = RangeValidationError("out of range")
        assert isinstance(err, ValidationError)


class TestRequiredFieldError:
    def test_inherits_from_validation_error(self):
        err = RequiredFieldError("missing field")
        assert isinstance(err, ValidationError)


class TestDateFormatError:
    def test_inherits_from_validation_error(self):
        err = DateFormatError("bad date")
        assert isinstance(err, ValidationError)


class TestConsistencyError:
    def test_inherits_from_validation_error(self):
        err = ConsistencyError("inconsistent")
        assert isinstance(err, ValidationError)


class TestCrossFieldValidationError:
    def test_basic(self):
        err = CrossFieldValidationError("cross fail")
        assert isinstance(err, ValidationError)
        assert err.fields == []

    def test_with_fields(self):
        err = CrossFieldValidationError("mismatch", fields=["start_date", "end_date"])
        assert err.fields == ["start_date", "end_date"]
        assert "Fields: start_date, end_date" in str(err)

    def test_with_rule(self):
        err = CrossFieldValidationError("fail", fields=["a", "b"], rule="date_order")
        assert "Rule: date_order" in str(err)

    def test_format_message_overrides_parent(self):
        err = CrossFieldValidationError("msg", fields=["x", "y"])
        msg = str(err)
        assert "msg" in msg
        assert "Fields:" in msg

    def test_empty_fields_excluded(self):
        err = CrossFieldValidationError("msg")
        assert "Fields:" not in str(err)


class TestInheritance:
    def test_all_subclass_validation_error(self):
        classes = [
            SchemaValidationError,
            DataTypeError,
            RangeValidationError,
            RequiredFieldError,
            DateFormatError,
            ConsistencyError,
            CrossFieldValidationError,
        ]
        for cls in classes:
            assert issubclass(cls, ValidationError)
            assert issubclass(cls, Exception)
