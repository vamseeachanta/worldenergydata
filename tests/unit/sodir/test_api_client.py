"""Tests for SODIR API client."""

from unittest.mock import MagicMock, patch

from worldenergydata.sodir.api_client import SodirAPIClient


class TestSodirAPIClient:
    """Tests for SodirAPIClient."""

    def setup_method(self):
        self.client = SodirAPIClient(
            base_url="https://api.sodir.no/api/rest",
            rate_limit=0,
            cache_ttl=3600,
            max_retries=0,
        )

    def test_init_base_url_stripped(self):
        client = SodirAPIClient(base_url="https://api.sodir.no/api/rest/")
        assert client.base_url == "https://api.sodir.no/api/rest"

    def test_init_rate_limit(self):
        client = SodirAPIClient(base_url="https://test.com", rate_limit=10)
        assert client.rate_limit == 10
        assert client.min_interval == 0.1

    def test_init_rate_limit_disabled(self):
        client = SodirAPIClient(base_url="https://test.com", rate_limit=0)
        assert client.min_interval == 0

    def test_setup_headers_default(self):
        headers = self.client._setup_headers(None)
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers

    def test_setup_headers_custom(self):
        headers = self.client._setup_headers({"X-Custom": "value"})
        assert headers["X-Custom"] == "value"
        assert headers["Accept"] == "application/json"

    def test_generate_cache_key_without_params(self):
        key1 = self.client._generate_cache_key("/test", None)
        key2 = self.client._generate_cache_key("/test", None)
        assert key1 == key2

    def test_generate_cache_key_with_params(self):
        key = self.client._generate_cache_key("/test", {"a": "1", "b": "2"})
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hex digest length

    def test_generate_cache_key_different_endpoints(self):
        key1 = self.client._generate_cache_key("/test1", None)
        key2 = self.client._generate_cache_key("/test2", None)
        assert key1 != key2

    def test_generate_cache_key_param_order_irrelevant(self):
        key1 = self.client._generate_cache_key("/test", {"a": "1", "b": "2"})
        key2 = self.client._generate_cache_key("/test", {"b": "2", "a": "1"})
        assert key1 == key2

    def test_cache_hit(self):
        self.client.cache.set(
            self.client._generate_cache_key("/test", None),
            {"data": "cached"},
        )
        result = self.client.get("/test")
        assert result == {"data": "cached"}

    def test_cache_disabled(self):
        self.client.cache_enabled = False
        self.client.cache.set(
            self.client._generate_cache_key("/test", None),
            {"data": "cached"},
        )
        # Mock _make_request to avoid network calls
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        self.client._make_request = MagicMock(return_value=mock_resp)
        result = self.client.get("/test")
        assert result == {"data": []}

    def test_get_blocks_endpoint(self):
        self.client.cache.set(
            self.client._generate_cache_key("/1001", {}),
            {"data": [{"block": "1/1"}]},
        )
        result = self.client.get_blocks()
        assert result == [{"block": "1/1"}]

    def test_get_wellbores_endpoint(self):
        self.client.cache.set(
            self.client._generate_cache_key("/5000", {}),
            {"data": [{"wellbore": "35/11-1"}]},
        )
        result = self.client.get_wellbores()
        assert result == [{"wellbore": "35/11-1"}]

    def test_get_fields_endpoint(self):
        self.client.cache.set(
            self.client._generate_cache_key("/7100", {}),
            {"data": [{"field": "Troll"}]},
        )
        result = self.client.get_fields()
        assert result == [{"field": "Troll"}]

    def test_get_discoveries_endpoint(self):
        self.client.cache.set(
            self.client._generate_cache_key("/7000", {}),
            {"data": [{"discovery": "Test"}]},
        )
        result = self.client.get_discoveries()
        assert result == [{"discovery": "Test"}]

    def test_get_surveys_endpoint(self):
        self.client.cache.set(
            self.client._generate_cache_key("/4000", {}),
            {"data": [{"survey": "S1"}]},
        )
        result = self.client.get_surveys()
        assert result == [{"survey": "S1"}]

    def test_get_returns_empty_on_none_response(self):
        self.client.cache.set(
            self.client._generate_cache_key("/1001", {}),
            {},
        )
        result = self.client.get_blocks()
        assert result == []
