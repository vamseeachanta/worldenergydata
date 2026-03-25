"""Tests for landman module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.landman.errors import (
    LandmanAuthError,
    LandmanError,
    LandmanProviderError,
    LandmanRecordNotFoundError,
    LandmanValidationError,
)


class TestLandmanError:
    """Tests for base LandmanError."""

    def test_create_basic(self):
        err = LandmanError("Test error")
        assert err.module_name == "landman"
        assert err.code == "LANDMAN_ERROR"

    def test_inherits_from_module_error(self):
        err = LandmanError("Test")
        assert isinstance(err, ModuleError)


class TestLandmanProviderError:
    """Tests for LandmanProviderError."""

    def test_create_with_provider(self):
        err = LandmanProviderError("Failed", provider_name="County GIS", status_code=500)
        assert err.provider_name == "County GIS"
        assert err.status_code == 500

    def test_unavailable_factory(self):
        err = LandmanProviderError.unavailable("County GIS", "server down")
        assert err.code == "LANDMAN_PROVIDER_UNAVAILABLE"
        assert "server down" in err.message

    def test_unavailable_without_reason(self):
        err = LandmanProviderError.unavailable("County GIS")
        assert "County GIS" in err.message

    def test_request_failed_factory(self):
        err = LandmanProviderError.request_failed("BLM API", 404, "Not found")
        assert err.status_code == 404
        assert err.code == "LANDMAN_PROVIDER_REQUEST_FAILED"

    def test_timeout_factory(self):
        err = LandmanProviderError.timeout("County GIS", 30)
        assert err.code == "LANDMAN_PROVIDER_TIMEOUT"
        assert err.context["timeout"] == 30

    def test_rate_limited_factory(self):
        err = LandmanProviderError.rate_limited("BLM API", retry_after=60)
        assert err.status_code == 429
        assert "60 seconds" in err.message

    def test_rate_limited_without_retry_after(self):
        err = LandmanProviderError.rate_limited("BLM API")
        assert "BLM API" in err.message


class TestLandmanRecordNotFoundError:
    """Tests for LandmanRecordNotFoundError."""

    def test_create_basic(self):
        err = LandmanRecordNotFoundError("Not found", record_type="ownership")
        assert err.record_type == "ownership"

    def test_ownership_not_found_factory(self):
        err = LandmanRecordNotFoundError.ownership_not_found(
            "S16-T7N-R3W", state="TX", county="Reeves"
        )
        assert err.code == "LANDMAN_OWNERSHIP_NOT_FOUND"
        assert err.search_criteria["state"] == "TX"

    def test_ownership_not_found_without_location(self):
        err = LandmanRecordNotFoundError.ownership_not_found("S16-T7N-R3W")
        assert "S16-T7N-R3W" in err.message

    def test_lease_not_found_by_id(self):
        err = LandmanRecordNotFoundError.lease_not_found(lease_id="L-12345")
        assert err.code == "LANDMAN_LEASE_NOT_FOUND"
        assert "L-12345" in err.message

    def test_lease_not_found_by_owner(self):
        err = LandmanRecordNotFoundError.lease_not_found(owner_name="John Doe")
        assert "John Doe" in err.message

    def test_title_not_found_by_document(self):
        err = LandmanRecordNotFoundError.title_not_found(document_number="D-001")
        assert err.code == "LANDMAN_TITLE_NOT_FOUND"
        assert "D-001" in err.message

    def test_title_not_found_by_grantor(self):
        err = LandmanRecordNotFoundError.title_not_found(grantor="Smith")
        assert "Smith" in err.message


class TestLandmanValidationError:
    """Tests for LandmanValidationError."""

    def test_create_empty(self):
        err = LandmanValidationError("Validation failed")
        assert err.errors == []
        assert err.has_errors() is False

    def test_add_error(self):
        err = LandmanValidationError("Validation failed")
        err.add_error("field", "type", "Wrong type", "value")
        assert err.has_errors() is True

    def test_to_dict_with_errors(self):
        err = LandmanValidationError("Validation failed")
        err.add_error("f1", "required", "Missing")
        result = err.to_dict()
        assert "validation_errors" in result

    def test_to_dict_without_errors(self):
        err = LandmanValidationError("Validation failed")
        result = err.to_dict()
        assert "validation_errors" not in result

    def test_from_errors_factory(self):
        errors = [{"field": "f1", "type": "required", "message": "Missing"}]
        err = LandmanValidationError.from_errors(errors)
        assert len(err.errors) == 1

    def test_invalid_legal_description(self):
        err = LandmanValidationError.invalid_legal_description(
            "INVALID", "wrong format"
        )
        assert err.code == "LANDMAN_INVALID_LEGAL_DESC"
        assert err.has_errors() is True

    def test_invalid_interest_percentage(self):
        err = LandmanValidationError.invalid_interest_percentage(150.0)
        assert err.code == "LANDMAN_INVALID_INTEREST"

    def test_invalid_state_code(self):
        err = LandmanValidationError.invalid_state_code("ZZ")
        assert err.code == "LANDMAN_INVALID_STATE"


class TestLandmanAuthError:
    """Tests for LandmanAuthError."""

    def test_create_with_provider(self):
        err = LandmanAuthError("Auth failed", provider_name="TitleWave")
        assert err.provider_name == "TitleWave"

    def test_invalid_credentials(self):
        err = LandmanAuthError.invalid_credentials("TitleWave")
        assert err.code == "LANDMAN_AUTH_INVALID_CREDENTIALS"

    def test_expired_token(self):
        err = LandmanAuthError.expired_token("TitleWave")
        assert err.code == "LANDMAN_AUTH_TOKEN_EXPIRED"

    def test_subscription_required(self):
        err = LandmanAuthError.subscription_required("TitleWave")
        assert err.code == "LANDMAN_AUTH_SUBSCRIPTION_REQUIRED"

    def test_insufficient_permissions(self):
        err = LandmanAuthError.insufficient_permissions("TitleWave", "admin")
        assert err.code == "LANDMAN_AUTH_INSUFFICIENT_PERMISSIONS"
        assert err.context["required_permission"] == "admin"
