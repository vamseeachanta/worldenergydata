"""Tests for SODIR module exception hierarchy."""

from worldenergydata.common.exceptions import SODIRError
from worldenergydata.sodir.errors import (
    SodirAPIError,
    SodirConfigurationError,
    SodirDataError,
    SodirError,
    SodirRateLimitError,
    SodirValidationError,
)


class TestSodirError:
    """Tests for base SodirError."""

    def test_create_basic(self):
        err = SodirError("Test error")
        assert str(err).startswith("[SODIR_ERROR]")
        assert err.module_name == "sodir"

    def test_inherits_from_sodir_error_base(self):
        err = SodirError("Test")
        assert isinstance(err, SODIRError)

    def test_context_contains_module(self):
        err = SodirError("Test")
        assert err.context["module"] == "sodir"


class TestSodirAPIError:
    """Tests for SodirAPIError."""

    def test_create_with_status_code(self):
        err = SodirAPIError("API failed", status_code=500, endpoint="/api/test")
        assert err.status_code == 500
        assert err.endpoint == "/api/test"
        assert err.context["status_code"] == 500
        assert err.context["endpoint"] == "/api/test"

    def test_create_with_response_data(self):
        err = SodirAPIError("API failed", response_data={"error": "bad request"})
        assert err.response_data == {"error": "bad request"}

    def test_request_failed_factory(self):
        err = SodirAPIError.request_failed("/api/test", 404, "Not found")
        assert err.status_code == 404
        assert err.endpoint == "/api/test"
        assert "SODIR_API_REQUEST_FAILED" == err.code

    def test_connection_failed_factory(self):
        err = SodirAPIError.connection_failed("/api/test", "DNS failure")
        assert "DNS failure" in err.message
        assert err.code == "SODIR_API_CONNECTION_FAILED"

    def test_connection_failed_without_reason(self):
        err = SodirAPIError.connection_failed("/api/test")
        assert "/api/test" in err.message

    def test_timeout_factory(self):
        err = SodirAPIError.timeout("/api/test", 30)
        assert err.code == "SODIR_API_TIMEOUT"
        assert err.context["timeout"] == 30

    def test_inherits_from_sodir_error(self):
        err = SodirAPIError("Test")
        assert isinstance(err, SodirError)


class TestSodirRateLimitError:
    """Tests for SodirRateLimitError."""

    def test_create_default(self):
        err = SodirRateLimitError()
        assert err.status_code == 429
        assert err.retry_after is None

    def test_create_with_retry_after(self):
        err = SodirRateLimitError(retry_after=60)
        assert err.retry_after == 60
        assert err.context["retry_after"] == 60

    def test_exceeded_factory(self):
        err = SodirRateLimitError.exceeded("/api/test", retry_after=30)
        assert err.retry_after == 30
        assert "30 seconds" in err.message

    def test_exceeded_without_retry_after(self):
        err = SodirRateLimitError.exceeded()
        assert err.retry_after is None

    def test_inherits_from_api_error(self):
        err = SodirRateLimitError()
        assert isinstance(err, SodirAPIError)


class TestSodirConfigurationError:
    """Tests for SodirConfigurationError."""

    def test_missing_setting_factory(self):
        err = SodirConfigurationError.missing_setting("api_key")
        assert "api_key" in err.message
        assert err.code == "SODIR_CONFIG_MISSING"
        assert err.context["setting"] == "api_key"

    def test_invalid_value_factory(self):
        err = SodirConfigurationError.invalid_value("timeout", -1, "must be positive")
        assert "timeout" in err.message
        assert err.code == "SODIR_CONFIG_INVALID"

    def test_missing_credentials_factory(self):
        err = SodirConfigurationError.missing_credentials()
        assert err.code == "SODIR_CONFIG_NO_CREDENTIALS"


class TestSodirDataError:
    """Tests for SodirDataError."""

    def test_create_with_operation(self):
        err = SodirDataError("Parse failed", operation="parse_csv")
        assert err.operation == "parse_csv"
        assert err.context["operation"] == "parse_csv"

    def test_parse_failed_factory(self):
        err = SodirDataError.parse_failed("wellbore", "invalid format")
        assert "wellbore" in err.message
        assert "invalid format" in err.message
        assert err.code == "SODIR_PARSE_FAILED"

    def test_parse_failed_without_reason(self):
        err = SodirDataError.parse_failed("field")
        assert "field" in err.message

    def test_transform_failed_factory(self):
        err = SodirDataError.transform_failed("normalize", "column missing")
        assert err.code == "SODIR_TRANSFORM_FAILED"
        assert "column missing" in err.message

    def test_transform_failed_without_reason(self):
        err = SodirDataError.transform_failed("aggregate")
        assert "aggregate" in err.message

    def test_missing_field_factory(self):
        err = SodirDataError.missing_field("wlbName", "wellbore")
        assert err.code == "SODIR_MISSING_FIELD"
        assert err.context["field"] == "wlbName"


class TestSodirValidationError:
    """Tests for SodirValidationError."""

    def test_create_empty(self):
        err = SodirValidationError("Validation failed")
        assert err.errors == []
        assert err.has_errors() is False

    def test_add_error(self):
        err = SodirValidationError("Validation failed")
        err.add_error("field_name", "required", "Field is required", "some_value")
        assert err.has_errors() is True
        assert len(err.errors) == 1
        assert err.errors[0]["field"] == "field_name"
        assert err.errors[0]["value"] == "some_value"

    def test_add_error_without_value(self):
        err = SodirValidationError("Validation failed")
        err.add_error("field", "type", "Wrong type")
        assert err.errors[0]["value"] is None

    def test_to_dict(self):
        err = SodirValidationError("Validation failed")
        err.add_error("f1", "required", "Missing")
        result = err.to_dict()
        assert "validation_errors" in result
        assert len(result["validation_errors"]) == 1

    def test_to_dict_without_errors(self):
        err = SodirValidationError("Validation failed")
        result = err.to_dict()
        assert "validation_errors" not in result

    def test_from_errors_factory(self):
        errors = [
            {"field": "f1", "type": "required", "message": "Missing"},
            {"field": "f2", "type": "type", "message": "Wrong type"},
        ]
        err = SodirValidationError.from_errors(errors)
        assert len(err.errors) == 2
        assert "2 error(s)" in err.message

    def test_required_field_factory(self):
        err = SodirValidationError.required_field("wlbName")
        assert err.code == "SODIR_REQUIRED_FIELD"
        assert err.has_errors() is True

    def test_invalid_type_factory(self):
        err = SodirValidationError.invalid_type("depth", "float", "str")
        assert err.code == "SODIR_INVALID_TYPE"
        assert err.has_errors() is True

    def test_invalid_format_factory(self):
        err = SodirValidationError.invalid_format("date", "YYYY-MM-DD", "2020/01/01")
        assert err.code == "SODIR_INVALID_FORMAT"

    def test_out_of_range_both_bounds(self):
        err = SodirValidationError.out_of_range("depth", 1500, min_val=0, max_val=1000)
        assert "between 0 and 1000" in err.message

    def test_out_of_range_min_only(self):
        err = SodirValidationError.out_of_range("depth", -5, min_val=0)
        assert ">= 0" in err.message

    def test_out_of_range_max_only(self):
        err = SodirValidationError.out_of_range("depth", 2000, max_val=1000)
        assert "<= 1000" in err.message
