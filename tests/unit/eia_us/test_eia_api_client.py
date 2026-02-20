"""Tests for EIA API v2 client — uses MOCK data, no live API calls."""

import os
import time
import pytest

from worldenergydata.eia_us.client.eia_api import (
    EIAApiClient,
    EIACache,
    EIAApiError,
    EIARateLimitError,
    RATE_LIMIT_PER_HOUR,
)


# ── Cache tests ────────────────────────────────────────────────────────────────

class TestEIACache:
    def test_cache_miss_returns_none(self):
        cache = EIACache()
        assert cache.get("nonexistent") is None

    def test_cache_set_then_get(self):
        cache = EIACache()
        cache.set("key1", {"data": [1, 2, 3]})
        result = cache.get("key1")
        assert result == {"data": [1, 2, 3]}

    def test_cache_expired_returns_none(self):
        cache = EIACache(default_ttl=0.01)
        cache.set("key_exp", {"val": 42}, ttl=0.01)
        time.sleep(0.05)
        assert cache.get("key_exp") is None

    def test_cache_clear_removes_all(self):
        cache = EIACache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_cache_hit_returns_data(self):
        cache = EIACache()
        cache.set("series_x", [{"period": "2024-01", "value": "100"}])
        assert cache.get("series_x") is not None


# ── Rate limit constant ────────────────────────────────────────────────────────

class TestRateLimitConstant:
    def test_rate_limit_per_hour_is_500(self):
        assert RATE_LIMIT_PER_HOUR == 500


# ── EIAApiClient initialisation ───────────────────────────────────────────────

class TestEIAApiClientInit:
    def test_client_defaults_to_v2_base_url(self):
        client = EIAApiClient(api_key="TEST_KEY")
        assert "api.eia.gov/v2" in client.base_url

    def test_client_stores_api_key(self):
        client = EIAApiClient(api_key="MY_KEY_123")
        assert client.api_key == "MY_KEY_123"

    def test_client_reads_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("EIA_API_KEY", "ENV_KEY_ABC")
        client = EIAApiClient()
        assert client.api_key == "ENV_KEY_ABC"

    def test_client_raises_if_no_api_key(self, monkeypatch):
        monkeypatch.delenv("EIA_API_KEY", raising=False)
        with pytest.raises(EIAApiError, match="[Aa][Pp][Ii].*[Kk]ey"):
            EIAApiClient()

    def test_client_cache_enabled_by_default(self):
        client = EIAApiClient(api_key="K")
        assert client.cache_enabled is True

    def test_client_can_disable_cache(self):
        client = EIAApiClient(api_key="K", cache_enabled=False)
        assert client.cache_enabled is False

    def test_rate_limit_per_hour_matches_constant(self):
        client = EIAApiClient(api_key="K")
        assert client.rate_limit_per_hour == RATE_LIMIT_PER_HOUR


# ── Mock-based fetch tests ─────────────────────────────────────────────────────

class TestEIAApiClientFetch:
    """All tests use mock responses — no live HTTP."""

    @pytest.fixture
    def mock_client(self):
        client = EIAApiClient(api_key="TEST_KEY")
        client.cache_enabled = False
        return client

    def test_build_series_url_crude_us(self, mock_client):
        url = mock_client.build_series_url("PET.MCRFPUS2.M")
        assert "PET.MCRFPUS2.M" in url

    def test_build_series_url_alaska(self, mock_client):
        url = mock_client.build_series_url("PET.MCRFPAK2.M")
        assert "PET.MCRFPAK2.M" in url

    def test_build_series_url_texas(self, mock_client):
        url = mock_client.build_series_url("PET.MCRFPTX2.M")
        assert "PET.MCRFPTX2.M" in url

    def test_parse_series_response_extracts_data(self, mock_client):
        raw = {
            "response": {
                "data": [
                    {"period": "2024-01", "value": "12345", "unit": "Thousand Barrels"},
                    {"period": "2024-02", "value": "11800", "unit": "Thousand Barrels"},
                ]
            }
        }
        records = mock_client.parse_series_response(raw)
        assert len(records) == 2
        assert records[0]["period"] == "2024-01"
        assert records[0]["value"] == 12345.0

    def test_parse_series_response_handles_empty(self, mock_client):
        raw = {"response": {"data": []}}
        records = mock_client.parse_series_response(raw)
        assert records == []

    def test_parse_series_response_handles_null_value(self, mock_client):
        raw = {
            "response": {
                "data": [{"period": "2024-01", "value": None, "unit": "Thousand Barrels"}]
            }
        }
        records = mock_client.parse_series_response(raw)
        assert records[0]["value"] is None

    def test_generate_cache_key_is_deterministic(self, mock_client):
        key1 = mock_client.generate_cache_key("PET.MCRFPUS2.M", {"start": "2020-01"})
        key2 = mock_client.generate_cache_key("PET.MCRFPUS2.M", {"start": "2020-01"})
        assert key1 == key2

    def test_generate_cache_key_differs_by_series(self, mock_client):
        key1 = mock_client.generate_cache_key("PET.MCRFPUS2.M", {})
        key2 = mock_client.generate_cache_key("PET.MCRFPAK2.M", {})
        assert key1 != key2

    def test_fetch_series_returns_cached_on_hit(self, mock_client):
        mock_client.cache_enabled = True
        mock_client.cache.set(
            mock_client.generate_cache_key("PET.MCRFPUS2.M", {}),
            [{"period": "2024-01", "value": 9000.0}],
        )
        result = mock_client.fetch_series("PET.MCRFPUS2.M", use_mock=True)
        assert isinstance(result, list)


# ── Error classes ──────────────────────────────────────────────────────────────

class TestEIAErrors:
    def test_eia_api_error_is_exception(self):
        err = EIAApiError("bad request")
        assert isinstance(err, Exception)

    def test_eia_rate_limit_error_inherits_api_error(self):
        err = EIARateLimitError("too many requests")
        assert isinstance(err, EIAApiError)

    def test_eia_api_error_message(self):
        err = EIAApiError("something failed")
        assert "something failed" in str(err)
