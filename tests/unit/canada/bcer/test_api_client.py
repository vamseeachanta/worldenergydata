"""Tests for BCER ArcGIS REST API client init, headers, cache key, params."""

import pytest

from worldenergydata.canada.bcer.api_client import BCERClient


# ---------------------------------------------------------------------------
# Init and defaults
# ---------------------------------------------------------------------------

class TestBCERClientInit:
    def test_default_values(self):
        client = BCERClient()
        assert client.rate_limit > 0
        assert client.cache_ttl > 0
        assert client.max_retries >= 1
        assert client.retry_delay > 0
        assert client.timeout > 0
        assert client.cache_enabled is True
        assert client.max_records > 0
        client.close()

    def test_custom_rate_limit(self):
        client = BCERClient(rate_limit=20)
        assert client.rate_limit == 20
        assert client.min_interval == pytest.approx(0.05)
        client.close()

    def test_custom_params(self):
        client = BCERClient(
            cache_ttl=3600,
            max_retries=5,
            retry_delay=2.0,
            timeout=90,
            max_records_per_request=500,
        )
        assert client.cache_ttl == 3600
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
        assert client.timeout == 90
        assert client.max_records == 500
        client.close()

    def test_config_dict(self):
        cfg = {"rate_limit": 5, "cache_ttl": 7200}
        client = BCERClient(config=cfg)
        assert client.rate_limit == 5
        assert client.cache_ttl == 7200
        client.close()

    def test_base_url_custom(self):
        client = BCERClient(base_url="https://custom.url.com")
        assert client.base_url == "https://custom.url.com"
        client.close()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestBCERClientConstants:
    def test_base_url(self):
        assert "bcer.gov.bc.ca" in BCERClient.BASE_URL

    def test_feature_services(self):
        services = BCERClient.FEATURE_SERVICES
        assert "wells" in services
        assert "facilities" in services
        assert "pipelines" in services
        assert "pools" in services

    def test_default_constants(self):
        assert BCERClient.DEFAULT_TIMEOUT == 30
        assert BCERClient.DEFAULT_RATE_LIMIT == 10
        assert BCERClient.DEFAULT_MAX_RETRIES == 3
        assert BCERClient.DEFAULT_MAX_RECORDS == 1000

    def test_crs_constants(self):
        assert BCERClient.BC_ALBERS_EPSG == 3005
        assert BCERClient.WGS84_EPSG == 4326


# ---------------------------------------------------------------------------
# _setup_headers
# ---------------------------------------------------------------------------

class TestSetupHeaders:
    def test_default_headers(self):
        client = BCERClient()
        headers = client.headers
        assert "User-Agent" in headers
        assert "WorldEnergyData" in headers["User-Agent"]
        assert "BCER" in headers["User-Agent"]
        assert "Accept" in headers
        client.close()

    def test_custom_headers_merged(self):
        client = BCERClient(headers={"X-Custom": "value"})
        assert client.headers["X-Custom"] == "value"
        assert "User-Agent" in client.headers
        client.close()

    def test_custom_headers_override(self):
        client = BCERClient(headers={"User-Agent": "CustomAgent"})
        assert client.headers["User-Agent"] == "CustomAgent"
        client.close()


# ---------------------------------------------------------------------------
# _generate_cache_key
# ---------------------------------------------------------------------------

class TestGenerateCacheKey:
    def test_without_params(self):
        client = BCERClient()
        key = client._generate_cache_key("/api/wells")
        assert isinstance(key, str)
        assert len(key) == 32
        client.close()

    def test_with_params(self):
        client = BCERClient()
        key = client._generate_cache_key("/api/wells", {"where": "1=1"})
        assert isinstance(key, str)
        assert len(key) == 32
        client.close()

    def test_same_params_same_key(self):
        client = BCERClient()
        key1 = client._generate_cache_key("/api", {"a": 1, "b": 2})
        key2 = client._generate_cache_key("/api", {"b": 2, "a": 1})
        assert key1 == key2
        client.close()

    def test_different_params_different_key(self):
        client = BCERClient()
        key1 = client._generate_cache_key("/api", {"year": 2024})
        key2 = client._generate_cache_key("/api", {"year": 2025})
        assert key1 != key2
        client.close()


# ---------------------------------------------------------------------------
# _build_arcgis_params
# ---------------------------------------------------------------------------

class TestBuildArcgisParams:
    def test_defaults(self):
        client = BCERClient()
        params = client._build_arcgis_params()
        assert params["where"] == "1=1"
        assert params["outFields"] == "*"
        assert params["f"] == "json"
        assert params["returnGeometry"] == "true"
        assert params["resultOffset"] == "0"
        client.close()

    def test_custom_where(self):
        client = BCERClient()
        params = client._build_arcgis_params(where="STATUS='Active'")
        assert params["where"] == "STATUS='Active'"
        client.close()

    def test_no_geometry(self):
        client = BCERClient()
        params = client._build_arcgis_params(return_geometry=False)
        assert params["returnGeometry"] == "false"
        client.close()

    def test_with_result_count(self):
        client = BCERClient()
        params = client._build_arcgis_params(result_record_count=100)
        assert params["resultRecordCount"] == "100"
        client.close()

    def test_with_geometry(self):
        client = BCERClient()
        geom = {"xmin": -125, "ymin": 55, "xmax": -120, "ymax": 60}
        params = client._build_arcgis_params(geometry=geom)
        assert "geometry" in params
        assert params["geometryType"] == "esriGeometryEnvelope"
        assert params["inSR"] == "4326"
        client.close()

    def test_with_order_by(self):
        client = BCERClient()
        params = client._build_arcgis_params(order_by_fields="OBJECTID ASC")
        assert params["orderByFields"] == "OBJECTID ASC"
        client.close()

    def test_with_offset(self):
        client = BCERClient()
        params = client._build_arcgis_params(result_offset=500)
        assert params["resultOffset"] == "500"
        client.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_enter_exit(self):
        with BCERClient() as client:
            assert client.session is not None
        assert client.session is None

    def test_close(self):
        client = BCERClient()
        assert client.session is not None
        client.close()
        assert client.session is None

    def test_double_close(self):
        client = BCERClient()
        client.close()
        client.close()  # Should not raise
