"""Tests for Texas RRC module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.texas_rrc.errors import (
    TexasRRCAPIError,
    TexasRRCConfigurationError,
    TexasRRCDataError,
    TexasRRCError,
    TexasRRCRateLimitError,
    TexasRRCValidationError,
)


class TestTexasRRCError:
    def test_create_basic(self):
        err = TexasRRCError("Test error")
        assert err.module_name == "texas_rrc"
        assert err.code == "TEXAS_RRC_ERROR"

    def test_inherits_from_module_error(self):
        assert isinstance(TexasRRCError("Test"), ModuleError)


class TestTexasRRCAPIError:
    def test_create_with_details(self):
        err = TexasRRCAPIError("Failed", status_code=500, endpoint="/api/wells")
        assert err.status_code == 500
        assert err.endpoint == "/api/wells"

    def test_request_failed(self):
        err = TexasRRCAPIError.request_failed("/wells", 404, "Not found")
        assert err.code == "TEXAS_RRC_API_REQUEST_FAILED"
        assert err.status_code == 404

    def test_connection_failed(self):
        err = TexasRRCAPIError.connection_failed("/wells", "DNS error")
        assert err.code == "TEXAS_RRC_API_CONNECTION_FAILED"
        assert "DNS error" in err.message

    def test_connection_failed_no_reason(self):
        err = TexasRRCAPIError.connection_failed("/wells")
        assert "/wells" in err.message

    def test_timeout(self):
        err = TexasRRCAPIError.timeout("/wells", 30)
        assert err.code == "TEXAS_RRC_API_TIMEOUT"
        assert err.context["timeout"] == 30

    def test_download_failed(self):
        err = TexasRRCAPIError.download_failed("PDQ", "corrupt file")
        assert err.code == "TEXAS_RRC_DOWNLOAD_FAILED"
        assert "PDQ" in err.message

    def test_download_failed_no_reason(self):
        err = TexasRRCAPIError.download_failed("PDQ")
        assert "PDQ" in err.message


class TestTexasRRCRateLimitError:
    def test_create_default(self):
        err = TexasRRCRateLimitError()
        assert err.status_code == 429

    def test_create_with_retry(self):
        err = TexasRRCRateLimitError(retry_after=60)
        assert err.retry_after == 60

    def test_exceeded(self):
        err = TexasRRCRateLimitError.exceeded("/wells", retry_after=120)
        assert err.retry_after == 120
        assert "120" in err.message

    def test_exceeded_no_retry(self):
        err = TexasRRCRateLimitError.exceeded()
        assert err.retry_after is None

    def test_inherits_from_api_error(self):
        assert isinstance(TexasRRCRateLimitError(), TexasRRCAPIError)


class TestTexasRRCConfigurationError:
    def test_missing_setting(self):
        err = TexasRRCConfigurationError.missing_setting("api_key")
        assert err.code == "TEXAS_RRC_CONFIG_MISSING"

    def test_invalid_value(self):
        err = TexasRRCConfigurationError.invalid_value("timeout", -1, "must be positive")
        assert err.code == "TEXAS_RRC_CONFIG_INVALID"


class TestTexasRRCDataError:
    def test_create_with_operation(self):
        err = TexasRRCDataError("Failed", operation="parse")
        assert err.operation == "parse"

    def test_parse_failed(self):
        err = TexasRRCDataError.parse_failed("well", "bad format")
        assert err.code == "TEXAS_RRC_PARSE_FAILED"
        assert "well" in err.message

    def test_parse_failed_no_reason(self):
        err = TexasRRCDataError.parse_failed("production")
        assert "production" in err.message

    def test_transform_failed(self):
        err = TexasRRCDataError.transform_failed("normalize", "bad input")
        assert err.code == "TEXAS_RRC_TRANSFORM_FAILED"

    def test_missing_field(self):
        err = TexasRRCDataError.missing_field("api_number", "well")
        assert err.code == "TEXAS_RRC_MISSING_FIELD"
        assert err.context["field"] == "api_number"


class TestTexasRRCValidationError:
    def test_create_empty(self):
        err = TexasRRCValidationError("Validation failed")
        assert err.errors == []
        assert err.has_errors() is False

    def test_add_error(self):
        err = TexasRRCValidationError("Validation failed")
        err.add_error("field", "type", "Wrong", "value")
        assert err.has_errors() is True

    def test_to_dict_with_errors(self):
        err = TexasRRCValidationError("Validation failed")
        err.add_error("f1", "required", "Missing")
        result = err.to_dict()
        assert "validation_errors" in result

    def test_to_dict_without_errors(self):
        err = TexasRRCValidationError("Validation failed")
        result = err.to_dict()
        assert "validation_errors" not in result

    def test_from_errors(self):
        errors = [{"field": "f1", "type": "required", "message": "Missing"}]
        err = TexasRRCValidationError.from_errors(errors)
        assert err.code == "TEXAS_RRC_VALIDATION_FAILED"
        assert len(err.errors) == 1

    def test_invalid_api_number(self):
        err = TexasRRCValidationError.invalid_api_number("BAD-API", "wrong format")
        assert err.code == "TEXAS_RRC_INVALID_API"
        assert err.has_errors() is True
