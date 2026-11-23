"""Tests for Landman module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.landman.exceptions import (
    APIError,
    CacheError,
    ConfigurationError,
    CountyNotFoundError,
    LandmanError,
    ParsingError,
    ProviderError,
    RateLimitError,
    RecordNotFoundError,
    StateNotSupportedError,
)
from worldenergydata.landman.exceptions import TimeoutError as LMTimeoutError


class TestLandmanError:
    def test_basic(self):
        err = LandmanError("test")
        assert err.module_name == "landman"
        assert isinstance(err, ModuleError)

    def test_with_error_code(self):
        err = LandmanError("test", error_code="CUSTOM")
        assert err.code == "CUSTOM"
        assert err.error_code == "CUSTOM"

    def test_with_details(self):
        err = LandmanError("test", details={"k": "v"})
        assert err.details["k"] == "v"

    def test_with_cause(self):
        cause = ValueError("orig")
        err = LandmanError("wrapped", cause=cause)
        assert err.cause is cause


class TestProviderError:
    def test_basic(self):
        err = ProviderError("provider failed")
        assert isinstance(err, LandmanError)


class TestStateNotSupportedError:
    def test_default_message(self):
        err = StateNotSupportedError(state="AK", provider="CountyRecords")
        assert "AK" in str(err)
        assert "CountyRecords" in str(err)
        assert err.code == "STATE_NOT_SUPPORTED"

    def test_with_supported_states(self):
        err = StateNotSupportedError(
            state="AK", provider="CR", supported_states=["TX", "OK"]
        )
        assert "TX" in str(err)
        assert "OK" in str(err)

    def test_custom_message(self):
        err = StateNotSupportedError(state="X", provider="P", message="Custom msg")
        assert "Custom msg" in str(err)


class TestCountyNotFoundError:
    def test_default_message(self):
        err = CountyNotFoundError(county="Harris", state="TX")
        assert "Harris" in str(err)
        assert "TX" in str(err)
        assert err.code == "COUNTY_NOT_FOUND"

    def test_custom_message(self):
        err = CountyNotFoundError(county="C", state="S", message="Custom msg")
        assert "Custom msg" in str(err)


class TestAPIError:
    def test_default_message(self):
        err = APIError(url="https://api.example.com")
        assert "api.example.com" in str(err)
        assert err.code == "API_ERROR"

    def test_with_status_code(self):
        err = APIError(url="https://api.example.com", status_code=500)
        assert "500" in str(err)

    def test_custom_message(self):
        err = APIError(url="u", status_code=404, message="Not found!")
        assert "Not found!" in str(err)


class TestRateLimitError:
    def test_default_message(self):
        err = RateLimitError(provider="CountyAPI")
        assert "CountyAPI" in str(err)
        assert err.code == "RATE_LIMIT"

    def test_with_retry(self):
        err = RateLimitError(provider="API", retry_after=60)
        assert "60" in str(err)

    def test_custom_message(self):
        err = RateLimitError(provider="P", message="Custom")
        assert "Custom" in str(err)


class TestTimeoutError:
    def test_default_message(self):
        err = LMTimeoutError(url="https://slow.api", timeout=30)
        assert "slow.api" in str(err)
        assert "30" in str(err)
        assert err.code == "TIMEOUT"

    def test_custom_message(self):
        err = LMTimeoutError(url="u", timeout=5, message="Timed out!")
        assert "Timed out!" in str(err)


class TestParsingError:
    def test_default_message(self):
        err = ParsingError(source="HTML page", reason="bad format")
        assert "HTML page" in str(err)
        assert "bad format" in str(err)
        assert err.code == "PARSING_ERROR"

    def test_custom_message(self):
        err = ParsingError(source="s", reason="r", message="Custom")
        assert "Custom" in str(err)


class TestRecordNotFoundError:
    def test_default_message(self):
        err = RecordNotFoundError(record_type="Deed", identifier="12345")
        assert "Deed" in str(err)
        assert "12345" in str(err)
        assert err.code == "RECORD_NOT_FOUND"

    def test_custom_message(self):
        err = RecordNotFoundError(record_type="T", identifier="I", message="Not here")
        assert "Not here" in str(err)


class TestCacheError:
    def test_basic(self):
        err = CacheError("cache failed")
        assert isinstance(err, LandmanError)


class TestConfigurationError:
    def test_basic(self):
        err = ConfigurationError("bad config")
        assert isinstance(err, LandmanError)


class TestInheritanceChain:
    def test_provider_errors(self):
        classes = [
            StateNotSupportedError,
            CountyNotFoundError,
            APIError,
            RateLimitError,
            LMTimeoutError,
            ParsingError,
            RecordNotFoundError,
        ]
        for cls in classes:
            assert issubclass(cls, ProviderError)
            assert issubclass(cls, LandmanError)
            assert issubclass(cls, ModuleError)
