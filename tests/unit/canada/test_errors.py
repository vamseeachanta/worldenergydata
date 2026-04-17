"""Tests for Canada module exception hierarchy."""

from worldenergydata.canada.errors import (
    CanadaAERError,
    CanadaAPIError,
    CanadaBCERError,
    CanadaConfigurationError,
    CanadaDataError,
    CanadaError,
    CanadaRateLimitError,
    CanadaUWIError,
    CanadaValidationError,
)
from worldenergydata.common.exceptions import ModuleError


class TestCanadaError:
    """Tests for base CanadaError."""

    def test_create_basic(self):
        err = CanadaError("Test error")
        assert err.module_name == "canada"
        assert err.code == "CANADA_ERROR"

    def test_inherits_from_module_error(self):
        err = CanadaError("Test")
        assert isinstance(err, ModuleError)


class TestCanadaAERError:
    """Tests for CanadaAERError."""

    def test_create_with_license(self):
        err = CanadaAERError("Failed", license_number="W0123456")
        assert err.license_number == "W0123456"
        assert err.context["regulator"] == "AER"
        assert err.context["license_number"] == "W0123456"

    def test_create_without_license(self):
        err = CanadaAERError("Failed")
        assert err.license_number is None
        assert "license_number" not in err.context

    def test_license_not_found_factory(self):
        err = CanadaAERError.license_not_found("W0123456")
        assert err.code == "AER_LICENSE_NOT_FOUND"
        assert "W0123456" in err.message

    def test_data_unavailable_factory(self):
        err = CanadaAERError.data_unavailable("production", "server down")
        assert err.code == "AER_DATA_UNAVAILABLE"
        assert "production" in err.message
        assert "server down" in err.message

    def test_data_unavailable_without_reason(self):
        err = CanadaAERError.data_unavailable("well")
        assert "well" in err.message


class TestCanadaBCERError:
    """Tests for CanadaBCERError."""

    def test_create_with_permit(self):
        err = CanadaBCERError("Failed", permit_number="12345")
        assert err.permit_number == "12345"
        assert err.context["regulator"] == "BCER"

    def test_create_without_permit(self):
        err = CanadaBCERError("Failed")
        assert err.permit_number is None

    def test_permit_not_found_factory(self):
        err = CanadaBCERError.permit_not_found("12345")
        assert err.code == "BCER_PERMIT_NOT_FOUND"
        assert "12345" in err.message

    def test_arcgis_error_factory(self):
        err = CanadaBCERError.arcgis_error("/wells", "timeout")
        assert err.code == "BCER_ARCGIS_ERROR"
        assert "/wells" in err.message
        assert "timeout" in err.message

    def test_arcgis_error_without_reason(self):
        err = CanadaBCERError.arcgis_error("/wells")
        assert "/wells" in err.message


class TestCanadaUWIError:
    """Tests for CanadaUWIError."""

    def test_create_with_uwi(self):
        err = CanadaUWIError("Invalid", uwi="100.16-09-010-09W4.00")
        assert err.uwi == "100.16-09-010-09W4.00"
        assert err.context["uwi"] == "100.16-09-010-09W4.00"

    def test_create_with_field(self):
        err = CanadaUWIError("Invalid", field="section")
        assert err.field == "section"

    def test_invalid_format_factory(self):
        err = CanadaUWIError.invalid_format("BAD-UWI", "wrong structure")
        assert err.code == "UWI_INVALID_FORMAT"
        assert "BAD-UWI" in err.message

    def test_invalid_format_without_reason(self):
        err = CanadaUWIError.invalid_format("BAD-UWI")
        assert "BAD-UWI" in err.message

    def test_invalid_field_factory(self):
        err = CanadaUWIError.invalid_field(
            "100.99-09-010-09W4.00", "legal_subdivision", "99", "01-16"
        )
        assert err.code == "UWI_INVALID_FIELD"
        assert err.context["value"] == "99"
        assert err.context["expected"] == "01-16"

    def test_unknown_province_factory(self):
        err = CanadaUWIError.unknown_province("100.16-09-010-09W4.00", "XX")
        assert err.code == "UWI_UNKNOWN_PROVINCE"
        assert err.field == "province"


class TestCanadaAPIError:
    """Tests for CanadaAPIError."""

    def test_create_with_details(self):
        err = CanadaAPIError(
            "Request failed",
            status_code=500,
            endpoint="/api/wells",
        )
        assert err.status_code == 500
        assert err.endpoint == "/api/wells"
        assert err.context["status_code"] == 500

    def test_request_failed_factory(self):
        err = CanadaAPIError.request_failed("/api/wells", 404, "Not found")
        assert err.code == "CANADA_API_REQUEST_FAILED"
        assert err.status_code == 404

    def test_connection_failed_factory(self):
        err = CanadaAPIError.connection_failed("/api/wells", "DNS failed")
        assert err.code == "CANADA_API_CONNECTION_FAILED"
        assert "DNS failed" in err.message

    def test_connection_failed_without_reason(self):
        err = CanadaAPIError.connection_failed("/api/wells")
        assert "/api/wells" in err.message

    def test_timeout_factory(self):
        err = CanadaAPIError.timeout("/api/wells", 30)
        assert err.code == "CANADA_API_TIMEOUT"
        assert err.context["timeout"] == 30


class TestCanadaRateLimitError:
    """Tests for CanadaRateLimitError."""

    def test_create_default(self):
        err = CanadaRateLimitError()
        assert err.status_code == 429
        assert "rate limit" in err.message.lower()

    def test_create_with_retry_after(self):
        err = CanadaRateLimitError(retry_after=60)
        assert err.retry_after == 60

    def test_exceeded_factory(self):
        err = CanadaRateLimitError.exceeded("/api/wells", retry_after=120)
        assert err.retry_after == 120
        assert "120" in err.message

    def test_exceeded_without_retry(self):
        err = CanadaRateLimitError.exceeded()
        assert err.retry_after is None

    def test_inherits_from_api_error(self):
        err = CanadaRateLimitError()
        assert isinstance(err, CanadaAPIError)


class TestCanadaConfigurationError:
    """Tests for CanadaConfigurationError."""

    def test_missing_setting(self):
        err = CanadaConfigurationError.missing_setting("api_key")
        assert err.code == "CANADA_CONFIG_MISSING"
        assert "api_key" in err.message

    def test_invalid_value(self):
        err = CanadaConfigurationError.invalid_value("timeout", -1, "must be positive")
        assert err.code == "CANADA_CONFIG_INVALID"
        assert "must be positive" in err.message


class TestCanadaDataError:
    """Tests for CanadaDataError."""

    def test_create_with_operation(self):
        err = CanadaDataError("Failed", operation="parse_wells")
        assert err.operation == "parse_wells"
        assert err.context["operation"] == "parse_wells"

    def test_parse_failed_factory(self):
        err = CanadaDataError.parse_failed("well", "malformed JSON")
        assert err.code == "CANADA_PARSE_FAILED"
        assert "well" in err.message
        assert "malformed JSON" in err.message

    def test_parse_failed_without_reason(self):
        err = CanadaDataError.parse_failed("production")
        assert "production" in err.message

    def test_transform_failed_factory(self):
        err = CanadaDataError.transform_failed("normalize_uwi", "bad input")
        assert err.code == "CANADA_TRANSFORM_FAILED"
        assert "normalize_uwi" in err.message


class TestCanadaValidationError:
    """Tests for CanadaValidationError."""

    def test_create_empty(self):
        err = CanadaValidationError("Validation failed")
        assert err.errors == []
        assert err.has_errors() is False

    def test_add_error(self):
        err = CanadaValidationError("Validation failed")
        err.add_error("field", "type", "Wrong type", "value")
        assert err.has_errors() is True
        assert len(err.errors) == 1

    def test_to_dict_with_errors(self):
        err = CanadaValidationError("Validation failed")
        err.add_error("f1", "required", "Missing")
        result = err.to_dict()
        assert "validation_errors" in result

    def test_to_dict_without_errors(self):
        err = CanadaValidationError("Validation failed")
        result = err.to_dict()
        assert "validation_errors" not in result

    def test_from_errors_factory(self):
        errors = [{"field": "f1", "type": "required", "message": "Missing"}]
        err = CanadaValidationError.from_errors(errors)
        assert err.code == "CANADA_VALIDATION_FAILED"
        assert len(err.errors) == 1
