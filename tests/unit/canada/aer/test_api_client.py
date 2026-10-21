"""Tests for AER API client init, headers, cache key, UWI validation."""

import pandas as pd
import pytest

from worldenergydata.canada.aer.api_client import AERClient
from worldenergydata.canada.cache import FileDownloadCache
from worldenergydata.canada.errors import CanadaValidationError


@pytest.fixture(autouse=True)
def isolated_download_cache(monkeypatch, tmp_path):
    """Keep constructor tests' default cache within the test scratch directory."""
    monkeypatch.setattr(FileDownloadCache, "DEFAULT_CACHE_DIR", tmp_path)


class TestSearchWellFailures:
    """Issue 1270: distinguish no matches from failed or unapplied searches."""

    @pytest.fixture
    def client(self, tmp_path):
        with AERClient(cache_dir=tmp_path) as client:
            yield client

    @pytest.mark.parametrize("filter_name", ["field_name", "operator", "well_status"])
    def test_missing_filter_column_raises(self, client, monkeypatch, filter_name):
        """No column can satisfy the requested predicate; returning a row is invalid."""
        monkeypatch.setattr(
            client,
            "download_well_infrastructure",
            lambda **kw: pd.DataFrame([{"id": "a"}]),
        )
        with pytest.raises(CanadaValidationError, match=filter_name):
            client.search_wells(**{filter_name: "requested"})

    @pytest.mark.parametrize("error_type", [RuntimeError, pd.errors.EmptyDataError])
    def test_download_failure_propagates(self, client, monkeypatch, error_type):
        """Download/CSV parse failures are not empty results (issue 1270)."""

        def fail(**kw):
            raise error_type("download failed")

        monkeypatch.setattr(client, "download_well_infrastructure", fail)
        with pytest.raises(error_type, match="download failed"):
            client.search_wells()

    def test_filters_combine_on_source_index(self, client, monkeypatch):
        """Hand evaluation: only row a matches field AND licensee AND status.

        Rows b, c and d each fail one predicate. Index labels are synthetic.
        """
        frame = pd.DataFrame(
            [
                {
                    "id": "a",
                    "Field": "North",
                    "Licensee": "Example",
                    "Status": "ACTIVE",
                },
                {
                    "id": "b",
                    "Field": "South",
                    "Licensee": "Example",
                    "Status": "ACTIVE",
                },
                {"id": "c", "Field": "North", "Licensee": "Other", "Status": "ACTIVE"},
                {
                    "id": "d",
                    "Field": "North",
                    "Licensee": "Example",
                    "Status": "CLOSED",
                },
            ],
            index=["a", "b", "c", "d"],
        )
        monkeypatch.setattr(client, "download_well_infrastructure", lambda **kw: frame)
        result = client.search_wells(
            field_name="north", operator="example", well_status="active"
        )
        assert [row["id"] for row in result] == ["a"]

    @pytest.mark.parametrize("empty_source", [False, True])
    def test_empty_results_are_successful(self, client, monkeypatch, empty_source):
        """Hand evaluation: zero rows match North in an empty or South-only table."""
        frame = pd.DataFrame({"Field": [] if empty_source else ["South"]})
        monkeypatch.setattr(client, "download_well_infrastructure", lambda **kw: frame)
        assert client.search_wells(field_name="North") == []


# ---------------------------------------------------------------------------
# Init and defaults
# ---------------------------------------------------------------------------


class TestAERClientInit:
    def test_default_values(self):
        client = AERClient()
        assert client.rate_limit > 0
        assert client.cache_ttl > 0
        assert client.max_retries >= 1
        assert client.retry_delay > 0
        assert client.timeout > 0
        assert client.cache_enabled is True
        assert client.session is not None
        client.close()

    def test_custom_rate_limit(self):
        client = AERClient(rate_limit=10)
        assert client.rate_limit == 10
        assert client.min_interval == pytest.approx(0.1)
        client.close()

    def test_min_interval_positive(self):
        # rate_limit=10 means min_interval=0.1
        client = AERClient(rate_limit=10)
        assert client.min_interval == pytest.approx(0.1)
        client.close()

    def test_custom_params(self):
        client = AERClient(
            cache_ttl=3600,
            max_retries=5,
            retry_delay=1.0,
            timeout=60,
        )
        assert client.cache_ttl == 3600
        assert client.max_retries == 5
        assert client.retry_delay == 1.0
        assert client.timeout == 60
        client.close()

    def test_config_dict(self):
        cfg = {"rate_limit": 2, "cache_ttl": 7200}
        client = AERClient(config=cfg)
        assert client.rate_limit == 2
        assert client.cache_ttl == 7200
        client.close()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestAERClientConstants:
    def test_base_urls(self):
        assert "aer.ca" in AERClient.AER_BASE_URL
        assert "petrinex" in AERClient.PETRINEX_BASE_URL.lower()

    def test_csv_endpoints(self):
        endpoints = AERClient.PETRINEX_CSV_ENDPOINTS
        assert "well_infrastructure" in endpoints
        assert "volumetric_oil" in endpoints
        assert "volumetric_gas" in endpoints
        assert "volumetric_water" in endpoints
        assert "facility_licence" in endpoints

    def test_default_constants(self):
        assert AERClient.DEFAULT_TIMEOUT == 120
        assert AERClient.DEFAULT_RATE_LIMIT == 5
        assert AERClient.DEFAULT_MAX_RETRIES == 3


# ---------------------------------------------------------------------------
# _setup_headers
# ---------------------------------------------------------------------------


class TestSetupHeaders:
    def test_default_headers(self):
        client = AERClient()
        headers = client.headers
        assert "User-Agent" in headers
        assert "WorldEnergyData" in headers["User-Agent"]
        assert "Accept" in headers
        client.close()

    def test_custom_headers_merged(self):
        client = AERClient(headers={"X-Custom": "value"})
        assert client.headers["X-Custom"] == "value"
        assert "User-Agent" in client.headers
        client.close()

    def test_custom_headers_override(self):
        client = AERClient(headers={"User-Agent": "CustomAgent"})
        assert client.headers["User-Agent"] == "CustomAgent"
        client.close()


# ---------------------------------------------------------------------------
# _generate_cache_key
# ---------------------------------------------------------------------------


class TestGenerateCacheKey:
    def test_without_params(self):
        client = AERClient()
        key = client._generate_cache_key("/api/wells")
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hex digest
        client.close()

    def test_with_params(self):
        client = AERClient()
        key = client._generate_cache_key("/api/wells", {"year": 2024})
        assert isinstance(key, str)
        assert len(key) == 32
        client.close()

    def test_same_params_same_key(self):
        client = AERClient()
        key1 = client._generate_cache_key("/api", {"a": 1, "b": 2})
        key2 = client._generate_cache_key("/api", {"b": 2, "a": 1})
        assert key1 == key2
        client.close()

    def test_different_params_different_key(self):
        client = AERClient()
        key1 = client._generate_cache_key("/api", {"year": 2024})
        key2 = client._generate_cache_key("/api", {"year": 2025})
        assert key1 != key2
        client.close()


# ---------------------------------------------------------------------------
# _validate_uwi
# ---------------------------------------------------------------------------


class TestValidateUWI:
    def test_valid_uwi(self):
        client = AERClient()
        result = client._validate_uwi("100/06-12-078-06W6/00")
        assert result == "100/06-12-078-06W6/00"
        client.close()

    def test_strips_whitespace(self):
        client = AERClient()
        result = client._validate_uwi("  100/06-12-078-06W6/00  ")
        assert result == "100/06-12-078-06W6/00"
        client.close()

    def test_invalid_uwi(self):
        client = AERClient()
        with pytest.raises(CanadaValidationError):
            client._validate_uwi("INVALID!UWI@#$")
        client.close()

    def test_uwi_with_e_direction(self):
        client = AERClient()
        result = client._validate_uwi("100/06-12-078-06E6/00")
        assert "E" in result
        client.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_enter_exit(self):
        with AERClient() as client:
            assert client.session is not None
        assert client.session is None

    def test_close(self):
        client = AERClient()
        assert client.session is not None
        client.close()
        assert client.session is None

    def test_double_close(self):
        client = AERClient()
        client.close()
        client.close()  # Should not raise
