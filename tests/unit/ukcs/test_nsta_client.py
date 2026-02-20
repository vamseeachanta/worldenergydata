"""Tests for NSTA CSV downloader client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.ukcs.production.nsta_client import NSTAClient


MOCK_PRODUCTION_CSV = (
    "FieldName,Year,Month,OilProduction (Thousand Tonnes),"
    "GasProduction (MMscf),WaterProduction (Thousand Tonnes)\n"
    "FORTIES,2022,1,450.3,12.5,310.2\n"
    "BUZZARD,2022,1,780.1,8.9,210.5\n"
    "FORTIES,2022,2,430.0,11.0,295.7\n"
)


class TestNSTAClientInit:
    def test_default_cache_dir_created(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert client.cache_dir == Path(tmp_path)

    def test_creates_cache_dir_if_missing(self, tmp_path):
        cache = tmp_path / "nsta_cache"
        NSTAClient(cache_dir=str(cache))
        assert cache.exists()

    def test_default_base_url_contains_nsta(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert "nstauthority" in client.base_url or "nsta" in client.base_url.lower()


class TestNSTAClientCacheKey:
    def test_cache_key_includes_year(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        key = client._cache_key(year=2022)
        assert "2022" in key

    def test_cache_key_includes_dataset_type(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        key = client._cache_key(year=2022, dataset="monthly")
        assert "monthly" in key.lower() or "2022" in key

    def test_cache_key_differs_by_year(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert client._cache_key(year=2021) != client._cache_key(year=2022)

    def test_cache_key_differs_by_dataset(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        k1 = client._cache_key(year=2022, dataset="monthly")
        k2 = client._cache_key(year=2022, dataset="annual")
        assert k1 != k2


class TestNSTAClientCache:
    def test_is_cached_false_when_missing(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert client.is_cached(year=2022) is False

    def test_is_cached_true_when_file_exists(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)
        assert client.is_cached(year=2022) is True

    def test_load_cached_returns_dataframe(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)
        df = client.load_cached(year=2022)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_load_cached_field_column_present(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)
        df = client.load_cached(year=2022)
        assert any("field" in col.lower() or "Field" in col for col in df.columns)


class TestNSTAClientDownload:
    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_saves_to_cache(self, mock_requests, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = MOCK_PRODUCTION_CSV.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download(year=2022)
        assert isinstance(df, pd.DataFrame)
        assert client.is_cached(year=2022)

    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_uses_cache_when_available(self, mock_requests, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)

        df = client.download(year=2022)
        mock_requests.get.assert_not_called()
        assert len(df) == 3

    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_force_refresh_ignores_cache(self, mock_requests, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text("old,data\n1,2\n")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = MOCK_PRODUCTION_CSV.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download(year=2022, force_refresh=True)
        mock_requests.get.assert_called_once()
        assert "FieldName" in df.columns or "field" in df.columns[0].lower()

    def test_download_without_requests_raises(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        with patch("worldenergydata.ukcs.production.nsta_client.requests", None):
            with pytest.raises(RuntimeError, match="requests"):
                client.download(year=2022, force_refresh=True)
