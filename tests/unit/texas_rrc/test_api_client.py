"""Tests for Texas RRC API client init, headers, cache key, validation."""

import pytest

from worldenergydata.texas_rrc.api_client import TexasRRCClient
from worldenergydata.texas_rrc.errors import TexasRRCValidationError

# ---------------------------------------------------------------------------
# Init and defaults
# ---------------------------------------------------------------------------


class TestTexasRRCClientInit:
    def test_default_values(self):
        client = TexasRRCClient()
        assert client.rate_limit == 2
        assert client.cache_ttl == 86400
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert client.timeout == 60
        assert client.cache_enabled is True
        assert client.session is not None
        client.close()

    def test_custom_rate_limit(self):
        client = TexasRRCClient(rate_limit=10)
        assert client.rate_limit == 10
        assert client.min_interval == pytest.approx(0.1)
        client.close()

    def test_custom_params(self):
        client = TexasRRCClient(
            cache_ttl=3600,
            max_retries=5,
            retry_delay=2.0,
            timeout=120,
        )
        assert client.cache_ttl == 3600
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
        assert client.timeout == 120
        client.close()

    def test_disable_rate_limit(self):
        client = TexasRRCClient(rate_limit=0)
        assert client.min_interval == 0
        client.close()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestTexasRRCClientConstants:
    def test_base_url(self):
        assert "rrc.texas.gov" in TexasRRCClient.BASE_URL

    def test_pdq_url(self):
        assert "rrc.texas.gov" in TexasRRCClient.PDQ_URL

    def test_pdq_endpoints(self):
        endpoints = TexasRRCClient.PDQ_ENDPOINTS
        assert "og_production" in endpoints
        assert "og_completion" in endpoints
        assert "og_well" in endpoints
        assert "drilling_permits" in endpoints

    def test_default_constants(self):
        assert TexasRRCClient.DEFAULT_TIMEOUT == 60
        assert TexasRRCClient.DEFAULT_RATE_LIMIT == 2
        assert TexasRRCClient.DEFAULT_MAX_RETRIES == 3


# ---------------------------------------------------------------------------
# _setup_headers
# ---------------------------------------------------------------------------


class TestSetupHeaders:
    def test_default_headers(self):
        client = TexasRRCClient()
        headers = client.headers
        assert "User-Agent" in headers
        assert "TexasRRC" in headers["User-Agent"]
        assert "Accept" in headers
        client.close()

    def test_custom_headers_merged(self):
        client = TexasRRCClient(headers={"X-Custom": "value"})
        assert client.headers["X-Custom"] == "value"
        assert "User-Agent" in client.headers
        client.close()

    def test_custom_headers_override(self):
        client = TexasRRCClient(headers={"User-Agent": "CustomAgent"})
        assert client.headers["User-Agent"] == "CustomAgent"
        client.close()


# ---------------------------------------------------------------------------
# _generate_cache_key
# ---------------------------------------------------------------------------


class TestGenerateCacheKey:
    def test_without_params(self):
        client = TexasRRCClient()
        key = client._generate_cache_key("/api/wells")
        assert isinstance(key, str)
        assert len(key) == 32
        client.close()

    def test_with_params(self):
        client = TexasRRCClient()
        key = client._generate_cache_key("/api/wells", {"year": 2024})
        assert isinstance(key, str)
        assert len(key) == 32
        client.close()

    def test_same_params_same_key(self):
        client = TexasRRCClient()
        key1 = client._generate_cache_key("/api", {"a": 1, "b": 2})
        key2 = client._generate_cache_key("/api", {"b": 2, "a": 1})
        assert key1 == key2
        client.close()

    def test_different_params_different_key(self):
        client = TexasRRCClient()
        key1 = client._generate_cache_key("/api", {"year": 2024})
        key2 = client._generate_cache_key("/api", {"year": 2025})
        assert key1 != key2
        client.close()


# ---------------------------------------------------------------------------
# _validate_api_number
# ---------------------------------------------------------------------------


class TestValidateApiNumber:
    def test_valid_with_dashes(self):
        client = TexasRRCClient()
        result = client._validate_api_number("42-123-45678")
        assert result == "4212345678"
        client.close()

    def test_valid_no_dashes(self):
        client = TexasRRCClient()
        result = client._validate_api_number("4212345678")
        assert result == "4212345678"
        client.close()

    def test_valid_with_spaces(self):
        client = TexasRRCClient()
        result = client._validate_api_number("42 123 45678")
        assert result == "4212345678"
        client.close()

    def test_too_short(self):
        client = TexasRRCClient()
        with pytest.raises(TexasRRCValidationError):
            client._validate_api_number("42-123")
        client.close()

    def test_non_texas(self):
        client = TexasRRCClient()
        with pytest.raises(TexasRRCValidationError):
            client._validate_api_number("4312345678")
        client.close()

    def test_non_digits(self):
        client = TexasRRCClient()
        with pytest.raises(TexasRRCValidationError):
            client._validate_api_number("42-ABC-12345")
        client.close()


# ---------------------------------------------------------------------------
# _parse_well_response
# ---------------------------------------------------------------------------


class TestParseWellResponse:
    def test_basic_structure(self):
        client = TexasRRCClient()
        result = client._parse_well_response("", "4212345678")
        assert result["api_number"] == "4212345678"
        assert result["state_code"] == "42"
        assert result["county_code"] == "123"
        assert result["well_number"] == "45678"
        client.close()

    def test_extracts_lease_name(self):
        client = TexasRRCClient()
        html = "Lease Name: SMITH RANCH"
        result = client._parse_well_response(html, "4212345678")
        assert result.get("lease_name") == "SMITH RANCH"
        client.close()

    def test_extracts_operator(self):
        client = TexasRRCClient()
        html = "Operator: ACME OIL CO"
        result = client._parse_well_response(html, "4212345678")
        assert result.get("operator_name") == "ACME OIL CO"
        client.close()

    def test_extracts_district(self):
        client = TexasRRCClient()
        html = "District: 8"
        result = client._parse_well_response(html, "4212345678")
        assert result.get("district") == "8"
        client.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_enter_exit(self):
        with TexasRRCClient() as client:
            assert client.session is not None
        assert client.session is None

    def test_close(self):
        client = TexasRRCClient()
        assert client.session is not None
        client.close()
        assert client.session is None

    def test_double_close(self):
        client = TexasRRCClient()
        client.close()
        client.close()  # Should not raise
