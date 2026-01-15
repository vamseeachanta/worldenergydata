# ABOUTME: Test suite for validation base classes (ValidationError, ValidationResult)
# ABOUTME: Foundation tests covering error representation, result aggregation, and state management

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from worldenergydata.validation.base import (
    ValidationError,
    ValidationResult,
    BaseValidator,
    FieldValidator,
    SchemaValidator,
    ValidationRule,
    ValidationSchema,
)


class TestValidationErrorInitialization:
    """Tests for ValidationError dataclass initialization and field assignment."""

    def test_validation_error_with_all_fields(self):
        """ValidationError stores all provided fields correctly."""
        error = ValidationError(
            field="api_well_number",
            message="Invalid well number format",
            value="INVALID-123",
            rule="APINumberRule",
            severity="error",
            row_index=5,
        )

        assert error.field == "api_well_number"
        assert error.message == "Invalid well number format"
        assert error.value == "INVALID-123"
        assert error.rule == "APINumberRule"
        assert error.severity == "error"
        assert error.row_index == 5

    def test_validation_error_with_required_fields_only(self):
        """ValidationError initializes with only required fields (field, message)."""
        error = ValidationError(
            field="production_date",
            message="Date is required",
        )

        assert error.field == "production_date"
        assert error.message == "Date is required"
        assert error.value is None
        assert error.rule is None
        assert error.severity == "error"
        assert error.row_index is None

    def test_validation_error_default_severity_is_error(self):
        """ValidationError defaults severity to 'error'."""
        error = ValidationError(field="test", message="test")
        assert error.severity == "error"

    def test_validation_error_with_custom_severity(self):
        """ValidationError accepts different severity levels."""
        for severity in ["error", "warning", "info"]:
            error = ValidationError(
                field="test",
                message="test",
                severity=severity,
            )
            assert error.severity == severity

    def test_validation_error_row_index_optional(self):
        """ValidationError row_index is optional."""
        error1 = ValidationError(field="f", message="m")
        error2 = ValidationError(field="f", message="m", row_index=10)

        assert error1.row_index is None
        assert error2.row_index == 10

    def test_validation_error_value_accepts_any_type(self):
        """ValidationError value field accepts various data types."""
        test_values = [
            "string",
            123,
            45.67,
            None,
            ["list"],
            {"dict": "value"},
            True,
        ]

        for val in test_values:
            error = ValidationError(field="test", message="test", value=val)
            assert error.value == val


class TestValidationErrorStringRepresentation:
    """Tests for ValidationError.__str__() method output formatting."""

    def test_error_string_without_row_index(self):
        """ValidationError.__str__() formats without row index when not provided."""
        error = ValidationError(
            field="api_well_number",
            message="Invalid format",
            severity="error",
        )
        result = str(error)

        assert "ERROR:" in result
        assert "api_well_number" in result
        assert "Invalid format" in result
        assert "at row" not in result

    def test_error_string_with_row_index(self):
        """ValidationError.__str__() includes row index when provided."""
        error = ValidationError(
            field="api_well_number",
            message="Invalid format",
            severity="error",
            row_index=42,
        )
        result = str(error)

        assert "ERROR:" in result
        assert "at row 42" in result
        assert "api_well_number" in result

    def test_error_string_severity_uppercase(self):
        """ValidationError.__str__() converts severity to uppercase."""
        for severity in ["error", "warning", "info"]:
            error = ValidationError(
                field="test",
                message="test",
                severity=severity,
            )
            result = str(error)
            assert f"{severity.upper()}:" in result

    def test_error_string_with_none_row_index(self):
        """ValidationError.__str__() handles None row_index correctly."""
        error = ValidationError(
            field="test",
            message="test",
            row_index=None,
        )
        result = str(error)

        assert "at row" not in result

    def test_error_string_format_consistency(self):
        """ValidationError.__str__() maintains consistent format."""
        error = ValidationError(
            field="production_date",
            message="Date must be in YYYY-MM-DD format",
            severity="warning",
            row_index=3,
        )
        result = str(error)

        # Check format: SEVERITY: field at row X: message
        assert result.startswith("WARNING:")
        assert "production_date" in result
        assert "at row 3" in result
        assert "Date must be in YYYY-MM-DD format" in result


class TestValidationResultInitialization:
    """Tests for ValidationResult dataclass initialization."""

    def test_validation_result_default_initialization(self):
        """ValidationResult initializes with empty collections."""
        result = ValidationResult()

        assert result.errors == []
        assert result.warnings == []
        assert result.info == []
        assert result.metadata == {}

    def test_validation_result_with_initial_errors(self):
        """ValidationResult accepts initial errors list."""
        errors = [
            ValidationError(field="f1", message="m1"),
            ValidationError(field="f2", message="m2"),
        ]
        result = ValidationResult(errors=errors)

        assert len(result.errors) == 2
        assert result.errors[0].field == "f1"
        assert result.errors[1].field == "f2"

    def test_validation_result_with_initial_metadata(self):
        """ValidationResult accepts initial metadata dictionary."""
        metadata = {"source": "test", "timestamp": "2024-01-01"}
        result = ValidationResult(metadata=metadata)

        assert result.metadata == metadata
        assert result.metadata["source"] == "test"

    def test_validation_result_lists_independent(self):
        """ValidationResult maintains independent error/warning/info lists."""
        result = ValidationResult()

        # Add to each list
        result.errors.append(ValidationError(field="e", message="error"))
        result.warnings.append(ValidationError(field="w", message="warning"))
        result.info.append(ValidationError(field="i", message="info"))

        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.info) == 1


class TestValidationResultProperties:
    """Tests for ValidationResult property methods (is_valid, has_warnings, total_issues)."""

    def test_is_valid_true_when_no_errors(self):
        """ValidationResult.is_valid returns True when errors list is empty."""
        result = ValidationResult()
        assert result.is_valid is True

    def test_is_valid_false_when_errors_present(self):
        """ValidationResult.is_valid returns False when errors exist."""
        result = ValidationResult()
        result.errors.append(ValidationError(field="f", message="m"))
        assert result.is_valid is False

    def test_is_valid_false_with_multiple_errors(self):
        """ValidationResult.is_valid returns False with multiple errors."""
        result = ValidationResult(
            errors=[
                ValidationError(field="f1", message="m1"),
                ValidationError(field="f2", message="m2"),
            ]
        )
        assert result.is_valid is False

    def test_is_valid_ignores_warnings(self):
        """ValidationResult.is_valid ignores warnings when no errors."""
        result = ValidationResult()
        result.warnings.append(ValidationError(field="f", message="w"))
        assert result.is_valid is True

    def test_is_valid_ignores_info(self):
        """ValidationResult.is_valid ignores info messages."""
        result = ValidationResult()
        result.info.append(ValidationError(field="f", message="i"))
        assert result.is_valid is True

    def test_has_warnings_true_when_present(self):
        """ValidationResult.has_warnings returns True when warnings exist."""
        result = ValidationResult()
        result.warnings.append(ValidationError(field="f", message="w"))
        assert result.has_warnings is True

    def test_has_warnings_false_when_empty(self):
        """ValidationResult.has_warnings returns False with empty warnings."""
        result = ValidationResult()
        assert result.has_warnings is False

    def test_total_issues_counts_all_severities(self):
        """ValidationResult.total_issues sums errors, warnings, and info."""
        result = ValidationResult()
        result.errors.append(ValidationError(field="e", message="error"))
        result.warnings.append(ValidationError(field="w", message="warning"))
        result.info.append(ValidationError(field="i", message="info"))

        assert result.total_issues == 3

    def test_total_issues_zero_when_empty(self):
        """ValidationResult.total_issues returns 0 with no issues."""
        result = ValidationResult()
        assert result.total_issues == 0

    def test_total_issues_with_duplicates_in_one_category(self):
        """ValidationResult.total_issues counts all items in each category."""
        result = ValidationResult()
        result.errors.append(ValidationError(field="e1", message="m1"))
        result.errors.append(ValidationError(field="e2", message="m2"))
        result.warnings.append(ValidationError(field="w1", message="m1"))

        assert result.total_issues == 3


class TestValidationResultAddMethods:
    """Tests for add_error, add_warning, add_info methods."""

    def test_add_error_creates_validation_error(self):
        """add_error() creates ValidationError with correct fields."""
        result = ValidationResult()
        result.add_error(
            field="api_number",
            message="Invalid format",
            value="TEST",
            rule="APIRule",
            row_index=5,
        )

        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.field == "api_number"
        assert error.message == "Invalid format"
        assert error.value == "TEST"
        assert error.rule == "APIRule"
        assert error.severity == "error"
        assert error.row_index == 5

    def test_add_error_with_minimal_params(self):
        """add_error() works with just field and message."""
        result = ValidationResult()
        result.add_error(field="test", message="test")

        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.field == "test"
        assert error.message == "test"
        assert error.value is None
        assert error.rule is None
        assert error.severity == "error"

    def test_add_warning_creates_validation_error_with_warning_severity(self):
        """add_warning() creates ValidationError with warning severity."""
        result = ValidationResult()
        result.add_warning(field="test", message="warning message")

        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert warning.field == "test"
        assert warning.message == "warning message"
        assert warning.severity == "warning"

    def test_add_info_creates_validation_error_with_info_severity(self):
        """add_info() creates ValidationError with info severity."""
        result = ValidationResult()
        result.add_info(field="test", message="info message")

        assert len(result.info) == 1
        info = result.info[0]
        assert info.field == "test"
        assert info.message == "info message"
        assert info.severity == "info"

    def test_add_multiple_errors(self):
        """Multiple add_error() calls accumulate in errors list."""
        result = ValidationResult()
        result.add_error(field="f1", message="m1")
        result.add_error(field="f2", message="m2")
        result.add_error(field="f3", message="m3")

        assert len(result.errors) == 3

    def test_add_mixed_severities(self):
        """Adding errors, warnings, and info maintains separate lists."""
        result = ValidationResult()
        result.add_error(field="e", message="error")
        result.add_warning(field="w", message="warning")
        result.add_info(field="i", message="info")

        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.info) == 1
        assert result.total_issues == 3


class TestValidationResultStateManagement:
    """Tests for state consistency and manipulation."""

    def test_merge_combines_all_issues(self):
        """merge() combines errors, warnings, info, and metadata."""
        result1 = ValidationResult()
        result1.add_error(field="e1", message="error1")
        result1.add_warning(field="w1", message="warning1")
        result1.metadata["source"] = "source1"

        result2 = ValidationResult()
        result2.add_error(field="e2", message="error2")
        result2.add_info(field="i1", message="info1")
        result2.metadata["timestamp"] = "2024-01-01"

        result1.merge(result2)

        assert len(result1.errors) == 2
        assert len(result1.warnings) == 1
        assert len(result1.info) == 1
        assert result1.metadata["source"] == "source1"
        assert result1.metadata["timestamp"] == "2024-01-01"

    def test_merge_returns_self(self):
        """merge() returns self for method chaining."""
        result1 = ValidationResult()
        result2 = ValidationResult()

        returned = result1.merge(result2)

        assert returned is result1

    def test_get_errors_by_field(self):
        """get_errors_by_field() returns only errors for specified field."""
        result = ValidationResult()
        result.add_error(field="api_number", message="error1")
        result.add_error(field="api_number", message="error2")
        result.add_error(field="date", message="error3")

        errors = result.get_errors_by_field("api_number")

        assert len(errors) == 2
        assert all(e.field == "api_number" for e in errors)

    def test_get_errors_by_field_empty_when_not_found(self):
        """get_errors_by_field() returns empty list when field not found."""
        result = ValidationResult()
        result.add_error(field="api_number", message="error")

        errors = result.get_errors_by_field("nonexistent")

        assert errors == []

    def test_get_errors_by_severity_returns_errors(self):
        """get_errors_by_severity('error') returns error list."""
        result = ValidationResult()
        result.add_error(field="f", message="e1")
        result.add_error(field="f", message="e2")

        errors = result.get_errors_by_severity("error")

        assert len(errors) == 2
        assert errors is result.errors

    def test_get_errors_by_severity_returns_warnings(self):
        """get_errors_by_severity('warning') returns warning list."""
        result = ValidationResult()
        result.add_warning(field="f", message="w")

        warnings = result.get_errors_by_severity("warning")

        assert len(warnings) == 1
        assert warnings is result.warnings

    def test_get_errors_by_severity_returns_info(self):
        """get_errors_by_severity('info') returns info list."""
        result = ValidationResult()
        result.add_info(field="f", message="i")

        info = result.get_errors_by_severity("info")

        assert len(info) == 1
        assert info is result.info

    def test_get_errors_by_severity_invalid_returns_empty(self):
        """get_errors_by_severity() returns empty list for invalid severity."""
        result = ValidationResult()
        result.add_error(field="f", message="e")

        errors = result.get_errors_by_severity("invalid")

        assert errors == []


class TestValidationResultSerialization:
    """Tests for serialization methods (to_dict, get_summary)."""

    def test_to_dict_with_empty_result(self):
        """to_dict() handles empty ValidationResult."""
        result = ValidationResult()
        data = result.to_dict()

        assert data["is_valid"] is True
        assert data["total_errors"] == 0
        assert data["total_warnings"] == 0
        assert data["total_info"] == 0
        assert data["errors"] == []
        assert data["warnings"] == []

    def test_to_dict_with_errors(self):
        """to_dict() includes error details."""
        result = ValidationResult()
        result.add_error(field="api_number", message="Invalid", value="TEST", rule="Rule1", row_index=5)

        data = result.to_dict()

        assert data["is_valid"] is False
        assert data["total_errors"] == 1
        assert len(data["errors"]) == 1

        error_dict = data["errors"][0]
        assert error_dict["field"] == "api_number"
        assert error_dict["message"] == "Invalid"
        assert error_dict["value"] == "TEST"
        assert error_dict["rule"] == "Rule1"
        assert error_dict["row_index"] == 5

    def test_to_dict_with_warnings(self):
        """to_dict() includes warning details."""
        result = ValidationResult()
        result.add_warning(field="date", message="Unusual", value="2099-01-01")

        data = result.to_dict()

        assert data["total_warnings"] == 1
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["field"] == "date"

    def test_to_dict_excludes_info_in_output(self):
        """to_dict() does not include info in JSON output."""
        result = ValidationResult()
        result.add_info(field="f", message="info")

        data = result.to_dict()

        assert "info" not in data
        # But total_info should still be available
        assert data["total_info"] == 1

    def test_to_dict_with_metadata(self):
        """to_dict() includes metadata."""
        result = ValidationResult()
        result.metadata["source"] = "csv"
        result.metadata["timestamp"] = "2024-01-01"

        data = result.to_dict()

        assert data["metadata"]["source"] == "csv"
        assert data["metadata"]["timestamp"] == "2024-01-01"

    def test_get_summary_valid_result(self):
        """get_summary() shows PASSED for valid result."""
        result = ValidationResult()
        summary = result.get_summary()

        assert "Validation PASSED" in summary
        assert "✅" in summary

    def test_get_summary_invalid_result(self):
        """get_summary() shows FAILED for invalid result."""
        result = ValidationResult()
        result.add_error(field="f", message="error")
        summary = result.get_summary()

        assert "Validation FAILED" in summary
        assert "❌" in summary

    def test_get_summary_includes_counts(self):
        """get_summary() includes error/warning/info counts."""
        result = ValidationResult()
        result.add_error(field="e", message="error")
        result.add_warning(field="w", message="warning")
        result.add_info(field="i", message="info")

        summary = result.get_summary()

        assert "Errors: 1" in summary
        assert "Warnings: 1" in summary
        assert "Info: 1" in summary

    def test_get_summary_includes_metadata_when_present(self):
        """get_summary() includes metadata in output."""
        result = ValidationResult()
        result.metadata["source"] = "test_data.csv"

        summary = result.get_summary()

        assert "Metadata:" in summary
        assert "test_data.csv" in summary


class TestValidationResultEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_to_dict_with_none_value(self):
        """to_dict() handles None values in error data."""
        result = ValidationResult()
        result.add_error(field="f", message="m", value=None, rule=None)

        data = result.to_dict()
        error_dict = data["errors"][0]

        assert error_dict["value"] is None
        assert error_dict["rule"] is None

    def test_to_dict_converts_non_string_values(self):
        """to_dict() converts non-string values to strings."""
        result = ValidationResult()
        result.add_error(field="number", message="m", value=123)

        data = result.to_dict()
        error_dict = data["errors"][0]

        assert error_dict["value"] == "123"
        assert isinstance(error_dict["value"], str)

    def test_merge_empty_with_non_empty(self):
        """merge() adds issues from non-empty result to empty result."""
        result1 = ValidationResult()
        result2 = ValidationResult()
        result2.add_error(field="f", message="e")

        result1.merge(result2)

        assert len(result1.errors) == 1

    def test_get_summary_with_zero_metadata(self):
        """get_summary() handles empty metadata gracefully."""
        result = ValidationResult()
        result.metadata = {}

        summary = result.get_summary()

        assert "Metadata:" not in summary or "{}" in summary

    def test_large_number_of_errors(self):
        """ValidationResult handles large number of errors."""
        result = ValidationResult()

        for i in range(1000):
            result.add_error(field=f"field_{i}", message=f"Error {i}")

        assert result.total_issues == 1000
        assert not result.is_valid

    def test_special_characters_in_messages(self):
        """ValidationResult handles special characters in messages."""
        special_message = "Invalid: @#$%^&*() <>{}[]|\\\"'`~"
        result = ValidationResult()
        result.add_error(field="f", message=special_message)

        assert result.errors[0].message == special_message
        summary = result.get_summary()
        assert "Validation FAILED" in summary


class TestBaseValidatorAbstractClass:
    """Tests for BaseValidator abstract base class."""

    def test_base_validator_cannot_instantiate(self):
        """BaseValidator cannot be instantiated directly (abstract class)."""
        with pytest.raises(TypeError):
            BaseValidator()

    def test_base_validator_with_subclass(self):
        """Subclass of BaseValidator can be instantiated."""
        class ConcreteValidator(BaseValidator):
            def validate(self, data):
                return ValidationResult()

        validator = ConcreteValidator("TestValidator")
        assert validator.name == "TestValidator"

    def test_base_validator_add_rule(self):
        """BaseValidator.add_rule() adds validation rule."""
        class ConcreteValidator(BaseValidator):
            def validate(self, data):
                return ValidationResult()

        class ConcreteRule(ValidationRule):
            def validate(self, data, field_name=None):
                return ValidationResult()

        validator = ConcreteValidator()
        rule = ConcreteRule()

        result = validator.add_rule(rule)

        assert result is validator  # Returns self for chaining
        assert len(validator.rules) == 1
        assert validator.rules[0] is rule

    def test_base_validator_create_result_includes_metadata(self):
        """_create_result() creates result with validator metadata."""
        class ConcreteValidator(BaseValidator):
            def validate(self, data):
                return self._create_result()

        validator = ConcreteValidator("TestValidator")
        result = validator.validate(None)

        assert result.metadata["validator"] == "TestValidator"
        assert "timestamp" in result.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
