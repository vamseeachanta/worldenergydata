"""
Tests for worldenergydata.common.exceptions module.

Tests cover:
- WorldEnergyDataError is base class
- DataError, ValidationError, ConfigError inherit correctly
- Exception messages and codes work
- Module-specific errors (BSEEError, etc.)
"""

import pytest


class TestWorldEnergyDataError:
    """Tests for WorldEnergyDataError base class."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        error = WorldEnergyDataError("Something went wrong")

        assert error.message == "Something went wrong"
        assert error.code == "WED_ERROR"
        assert error.context == {}
        assert error.cause is None

    def test_initialization_with_code(self):
        """Test exception with custom code."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        error = WorldEnergyDataError("Error occurred", code="CUSTOM_ERROR")

        assert error.code == "CUSTOM_ERROR"

    def test_initialization_with_context(self):
        """Test exception with context dictionary."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        context = {"key": "value", "count": 42}
        error = WorldEnergyDataError("Error occurred", context=context)

        assert error.context == context

    def test_initialization_with_cause(self):
        """Test exception with cause chaining."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        original = ValueError("Original error")
        error = WorldEnergyDataError("Wrapped error", cause=original)

        assert error.cause is original
        assert error.__cause__ is original

    def test_str_representation(self):
        """Test string representation."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        error = WorldEnergyDataError(
            "Error message",
            code="TEST_ERROR",
            context={"key": "value"},
        )

        str_repr = str(error)

        assert "[TEST_ERROR]" in str_repr
        assert "Error message" in str_repr
        assert "key=value" in str_repr

    def test_str_without_context(self):
        """Test string representation without context."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        error = WorldEnergyDataError("Error message")

        str_repr = str(error)

        assert "[WED_ERROR]" in str_repr
        assert "Error message" in str_repr
        assert "Context:" not in str_repr

    def test_repr_representation(self):
        """Test repr representation."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        error = WorldEnergyDataError(
            "Error message",
            code="TEST_ERROR",
            context={"key": "value"},
        )

        repr_str = repr(error)

        assert "WorldEnergyDataError" in repr_str
        assert "Error message" in repr_str
        assert "TEST_ERROR" in repr_str

    def test_to_dict(self):
        """Test to_dict() serialization."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        original = ValueError("Original")
        error = WorldEnergyDataError(
            "Error message",
            code="TEST_ERROR",
            context={"key": "value"},
            cause=original,
        )

        result = error.to_dict()

        assert result["error"] == "WorldEnergyDataError"
        assert result["code"] == "TEST_ERROR"
        assert result["message"] == "Error message"
        assert result["context"] == {"key": "value"}
        assert "Original" in result["cause"]

    def test_to_dict_without_optional_fields(self):
        """Test to_dict() without optional fields."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        error = WorldEnergyDataError("Error message")

        result = error.to_dict()

        assert "context" not in result
        assert "cause" not in result

    def test_exception_inheritance(self):
        """Test WorldEnergyDataError inherits from Exception."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        error = WorldEnergyDataError("Test")

        assert isinstance(error, Exception)

    def test_exception_can_be_raised(self):
        """Test exception can be raised and caught."""
        from worldenergydata.common.exceptions import WorldEnergyDataError

        with pytest.raises(WorldEnergyDataError) as exc_info:
            raise WorldEnergyDataError("Test error", code="RAISE_TEST")

        assert exc_info.value.message == "Test error"
        assert exc_info.value.code == "RAISE_TEST"


class TestConfigError:
    """Tests for ConfigError class."""

    def test_default_code(self):
        """Test ConfigError has correct default code."""
        from worldenergydata.common.exceptions import ConfigError

        error = ConfigError("Config issue")

        assert error.code == "CONFIG_ERROR"

    def test_inheritance(self):
        """Test ConfigError inherits from WorldEnergyDataError."""
        from worldenergydata.common.exceptions import ConfigError, WorldEnergyDataError

        error = ConfigError("Config issue")

        assert isinstance(error, WorldEnergyDataError)

    def test_missing_setting_factory(self):
        """Test missing_setting() factory method."""
        from worldenergydata.common.exceptions import ConfigError

        error = ConfigError.missing_setting("API_KEY")

        assert "API_KEY" in error.message
        assert error.code == "CONFIG_MISSING"
        assert error.context["setting"] == "API_KEY"

    def test_invalid_value_factory(self):
        """Test invalid_value() factory method."""
        from worldenergydata.common.exceptions import ConfigError

        error = ConfigError.invalid_value("LOG_LEVEL", "INVALID", "Must be DEBUG/INFO/etc")

        assert "LOG_LEVEL" in error.message
        assert error.code == "CONFIG_INVALID"
        assert error.context["setting"] == "LOG_LEVEL"
        assert error.context["value"] == "INVALID"
        assert error.context["reason"] == "Must be DEBUG/INFO/etc"


class TestDataError:
    """Tests for DataError class."""

    def test_default_code(self):
        """Test DataError has correct default code."""
        from worldenergydata.common.exceptions import DataError

        error = DataError("Data issue")

        assert error.code == "DATA_ERROR"

    def test_inheritance(self):
        """Test DataError inherits from WorldEnergyDataError."""
        from worldenergydata.common.exceptions import DataError, WorldEnergyDataError

        error = DataError("Data issue")

        assert isinstance(error, WorldEnergyDataError)


class TestDataSourceError:
    """Tests for DataSourceError class."""

    def test_initialization_with_source(self):
        """Test DataSourceError requires source parameter."""
        from worldenergydata.common.exceptions import DataSourceError

        error = DataSourceError("Source unavailable", source="BSEE")

        assert error.source == "BSEE"
        assert error.context["source"] == "BSEE"

    def test_default_code(self):
        """Test DataSourceError has correct default code."""
        from worldenergydata.common.exceptions import DataSourceError

        error = DataSourceError("Error", source="test")

        assert error.code == "DATA_SOURCE_ERROR"

    def test_inheritance(self):
        """Test DataSourceError inherits from DataError."""
        from worldenergydata.common.exceptions import DataSourceError, DataError

        error = DataSourceError("Error", source="test")

        assert isinstance(error, DataError)

    def test_unavailable_factory(self):
        """Test unavailable() factory method."""
        from worldenergydata.common.exceptions import DataSourceError

        error = DataSourceError.unavailable("BSEE", "Connection timeout")

        assert "BSEE" in error.message
        assert "unavailable" in error.message.lower()
        assert error.code == "SOURCE_UNAVAILABLE"
        assert error.source == "BSEE"

    def test_unavailable_factory_without_reason(self):
        """Test unavailable() factory method without reason."""
        from worldenergydata.common.exceptions import DataSourceError

        error = DataSourceError.unavailable("SODIR")

        assert "SODIR" in error.message
        assert error.code == "SOURCE_UNAVAILABLE"

    def test_timeout_factory(self):
        """Test timeout() factory method."""
        from worldenergydata.common.exceptions import DataSourceError

        error = DataSourceError.timeout("EIA", 60)

        assert "EIA" in error.message
        assert "60" in error.message
        assert error.code == "SOURCE_TIMEOUT"
        assert error.context["timeout"] == 60


class TestValidationError:
    """Tests for ValidationError class."""

    def test_default_code(self):
        """Test ValidationError has correct default code."""
        from worldenergydata.common.exceptions import ValidationError

        error = ValidationError("Validation failed")

        assert error.code == "VALIDATION_ERROR"

    def test_inheritance(self):
        """Test ValidationError inherits from DataError."""
        from worldenergydata.common.exceptions import ValidationError, DataError

        error = ValidationError("Validation failed")

        assert isinstance(error, DataError)

    def test_errors_list(self):
        """Test ValidationError maintains errors list."""
        from worldenergydata.common.exceptions import ValidationError

        errors = [{"field": "api_number", "message": "Invalid"}]
        error = ValidationError("Validation failed", errors=errors)

        assert error.errors == errors

    def test_add_error(self):
        """Test add_error() method."""
        from worldenergydata.common.exceptions import ValidationError

        error = ValidationError("Validation failed")
        error.add_error("field1", "required", "Field is required", "value1")

        assert len(error.errors) == 1
        assert error.errors[0]["field"] == "field1"
        assert error.errors[0]["type"] == "required"
        assert error.errors[0]["message"] == "Field is required"
        assert error.errors[0]["value"] == "value1"

    def test_has_errors(self):
        """Test has_errors() method."""
        from worldenergydata.common.exceptions import ValidationError

        error = ValidationError("Validation failed")
        assert error.has_errors() is False

        error.add_error("field", "type", "Invalid type")
        assert error.has_errors() is True

    def test_to_dict_includes_errors(self):
        """Test to_dict() includes validation_errors."""
        from worldenergydata.common.exceptions import ValidationError

        error = ValidationError("Validation failed")
        error.add_error("field", "type", "Invalid")

        result = error.to_dict()

        assert "validation_errors" in result
        assert len(result["validation_errors"]) == 1

    def test_from_errors_factory(self):
        """Test from_errors() factory method."""
        from worldenergydata.common.exceptions import ValidationError

        errors = [
            {"field": "f1", "message": "Error 1"},
            {"field": "f2", "message": "Error 2"},
        ]
        error = ValidationError.from_errors(errors)

        assert "2 error" in error.message
        assert error.errors == errors
        assert error.code == "VALIDATION_FAILED"

    def test_required_field_factory(self):
        """Test required_field() factory method."""
        from worldenergydata.common.exceptions import ValidationError

        error = ValidationError.required_field("api_number")

        assert "api_number" in error.message
        assert error.code == "REQUIRED_FIELD"
        assert error.context["field"] == "api_number"
        assert len(error.errors) == 1

    def test_invalid_type_factory(self):
        """Test invalid_type() factory method."""
        from worldenergydata.common.exceptions import ValidationError

        error = ValidationError.invalid_type("volume", "float", "string")

        assert "volume" in error.message
        assert error.code == "INVALID_TYPE"
        assert error.context["expected"] == "float"
        assert error.context["actual"] == "string"


class TestProcessingError:
    """Tests for ProcessingError class."""

    def test_initialization_with_operation(self):
        """Test ProcessingError requires operation parameter."""
        from worldenergydata.common.exceptions import ProcessingError

        error = ProcessingError("Processing failed", operation="transform")

        assert error.operation == "transform"
        assert error.context["operation"] == "transform"

    def test_default_code(self):
        """Test ProcessingError has correct default code."""
        from worldenergydata.common.exceptions import ProcessingError

        error = ProcessingError("Error", operation="test")

        assert error.code == "PROCESSING_ERROR"

    def test_inheritance(self):
        """Test ProcessingError inherits from DataError."""
        from worldenergydata.common.exceptions import ProcessingError, DataError

        error = ProcessingError("Error", operation="test")

        assert isinstance(error, DataError)

    def test_failed_factory(self):
        """Test failed() factory method."""
        from worldenergydata.common.exceptions import ProcessingError

        original = ValueError("Original error")
        error = ProcessingError.failed("aggregation", "Division by zero", cause=original)

        assert "aggregation" in error.message
        assert "Division by zero" in error.message
        assert error.code == "PROCESSING_FAILED"
        assert error.cause is original


class TestAPIError:
    """Tests for APIError class."""

    def test_initialization(self):
        """Test APIError initialization."""
        from worldenergydata.common.exceptions import APIError

        error = APIError("API error", api_name="BSEE", status_code=500)

        assert error.api_name == "BSEE"
        assert error.status_code == 500
        assert error.context["api"] == "BSEE"
        assert error.context["status_code"] == 500

    def test_default_code(self):
        """Test APIError has correct default code."""
        from worldenergydata.common.exceptions import APIError

        error = APIError("Error", api_name="test")

        assert error.code == "API_ERROR"

    def test_inheritance(self):
        """Test APIError inherits from WorldEnergyDataError."""
        from worldenergydata.common.exceptions import APIError, WorldEnergyDataError

        error = APIError("Error", api_name="test")

        assert isinstance(error, WorldEnergyDataError)

    def test_request_failed_factory(self):
        """Test request_failed() factory method."""
        from worldenergydata.common.exceptions import APIError

        error = APIError.request_failed("BSEE", 404, "Not found")

        assert "BSEE" in error.message
        assert "404" in error.message
        assert error.code == "API_REQUEST_FAILED"
        assert error.status_code == 404
        assert error.context["response"] == "Not found"

    def test_request_failed_truncates_long_response(self):
        """Test request_failed() truncates long response body."""
        from worldenergydata.common.exceptions import APIError

        long_response = "x" * 1000
        error = APIError.request_failed("API", 500, long_response)

        assert len(error.context["response"]) <= 500

    def test_rate_limited_factory(self):
        """Test rate_limited() factory method."""
        from worldenergydata.common.exceptions import APIError

        error = APIError.rate_limited("EIA", retry_after=60)

        assert "EIA" in error.message
        assert error.code == "API_RATE_LIMITED"
        assert error.status_code == 429
        assert error.context["retry_after"] == 60

    def test_rate_limited_without_retry_after(self):
        """Test rate_limited() without retry_after."""
        from worldenergydata.common.exceptions import APIError

        error = APIError.rate_limited("EIA")

        assert error.code == "API_RATE_LIMITED"
        assert "retry_after" not in error.context


class TestModuleError:
    """Tests for ModuleError base class."""

    def test_default_module_name(self):
        """Test ModuleError has default module name."""
        from worldenergydata.common.exceptions import ModuleError

        error = ModuleError("Module error")

        assert error.module_name == "unknown"
        assert error.context["module"] == "unknown"

    def test_default_code(self):
        """Test ModuleError has correct default code."""
        from worldenergydata.common.exceptions import ModuleError

        error = ModuleError("Error")

        assert error.code == "MODULE_ERROR"

    def test_inheritance(self):
        """Test ModuleError inherits from WorldEnergyDataError."""
        from worldenergydata.common.exceptions import ModuleError, WorldEnergyDataError

        error = ModuleError("Error")

        assert isinstance(error, WorldEnergyDataError)


class TestBSEEError:
    """Tests for BSEEError class."""

    def test_module_name(self):
        """Test BSEEError has correct module name."""
        from worldenergydata.common.exceptions import BSEEError

        error = BSEEError("BSEE error")

        assert error.module_name == "bsee"
        assert error.context["module"] == "bsee"

    def test_default_code(self):
        """Test BSEEError has correct default code."""
        from worldenergydata.common.exceptions import BSEEError

        error = BSEEError("Error")

        assert error.code == "BSEE_ERROR"

    def test_inheritance(self):
        """Test BSEEError inherits from ModuleError."""
        from worldenergydata.common.exceptions import BSEEError, ModuleError

        error = BSEEError("Error")

        assert isinstance(error, ModuleError)


class TestSODIRError:
    """Tests for SODIRError class."""

    def test_module_name(self):
        """Test SODIRError has correct module name."""
        from worldenergydata.common.exceptions import SODIRError

        error = SODIRError("SODIR error")

        assert error.module_name == "sodir"
        assert error.context["module"] == "sodir"

    def test_default_code(self):
        """Test SODIRError has correct default code."""
        from worldenergydata.common.exceptions import SODIRError

        error = SODIRError("Error")

        assert error.code == "SODIR_ERROR"

    def test_inheritance(self):
        """Test SODIRError inherits from ModuleError."""
        from worldenergydata.common.exceptions import SODIRError, ModuleError

        error = SODIRError("Error")

        assert isinstance(error, ModuleError)


class TestEIAError:
    """Tests for EIAError class."""

    def test_module_name(self):
        """Test EIAError has correct module name."""
        from worldenergydata.common.exceptions import EIAError

        error = EIAError("EIA error")

        assert error.module_name == "eia"
        assert error.context["module"] == "eia"

    def test_default_code(self):
        """Test EIAError has correct default code."""
        from worldenergydata.common.exceptions import EIAError

        error = EIAError("Error")

        assert error.code == "EIA_ERROR"

    def test_inheritance(self):
        """Test EIAError inherits from ModuleError."""
        from worldenergydata.common.exceptions import EIAError, ModuleError

        error = EIAError("Error")

        assert isinstance(error, ModuleError)


class TestExceptionHierarchy:
    """Tests for exception hierarchy relationships."""

    def test_all_inherit_from_base(self):
        """Test all exception types inherit from WorldEnergyDataError."""
        from worldenergydata.common.exceptions import (
            WorldEnergyDataError,
            ConfigError,
            DataError,
            DataSourceError,
            ValidationError,
            ProcessingError,
            APIError,
            ModuleError,
            BSEEError,
            SODIRError,
            EIAError,
        )

        error_classes = [
            ConfigError,
            DataError,
            DataSourceError,
            ValidationError,
            ProcessingError,
            APIError,
            ModuleError,
            BSEEError,
            SODIRError,
            EIAError,
        ]

        for error_class in error_classes:
            assert issubclass(error_class, WorldEnergyDataError)

    def test_data_errors_inherit_from_data_error(self):
        """Test data-related errors inherit from DataError."""
        from worldenergydata.common.exceptions import (
            DataError,
            DataSourceError,
            ValidationError,
            ProcessingError,
        )

        for error_class in [DataSourceError, ValidationError, ProcessingError]:
            assert issubclass(error_class, DataError)

    def test_module_errors_inherit_from_module_error(self):
        """Test module-specific errors inherit from ModuleError."""
        from worldenergydata.common.exceptions import (
            ModuleError,
            BSEEError,
            SODIRError,
            EIAError,
        )

        for error_class in [BSEEError, SODIRError, EIAError]:
            assert issubclass(error_class, ModuleError)

    def test_catch_base_catches_all(self):
        """Test catching base exception catches all subclasses."""
        from worldenergydata.common.exceptions import (
            WorldEnergyDataError,
            BSEEError,
            ValidationError,
        )

        caught = []

        try:
            raise BSEEError("BSEE error")
        except WorldEnergyDataError as e:
            caught.append(e)

        try:
            raise ValidationError("Validation error")
        except WorldEnergyDataError as e:
            caught.append(e)

        assert len(caught) == 2
