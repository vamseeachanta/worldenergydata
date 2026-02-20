"""Tests for ANP CSV downloader client."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.brazil_anp.production.anp_client import ANPClient


class TestANPClientInit:
    def test_default_cache_dir(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        assert client.cache_dir == Path(tmp_path)

    def test_creates_cache_dir(self, tmp_path):
        cache = tmp_path / "anp_cache"
        client = ANPClient(cache_dir=str(cache))
        assert cache.exists()

    def test_default_base_url(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        assert "anp.gov.br" in client.base_url or "dados.gov.br" in client.base_url


class TestANPClientCacheKey:
    def test_cache_key_includes_year_and_semester(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        key = client._cache_key(year=2023, semester=1)
        assert "2023" in key
        assert "1" in key

    def test_cache_key_different_for_different_params(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        key1 = client._cache_key(year=2023, semester=1)
        key2 = client._cache_key(year=2023, semester=2)
        assert key1 != key2


class TestANPClientCache:
    def test_is_cached_returns_false_when_missing(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        assert client.is_cached(year=2023, semester=1) is False

    def test_is_cached_returns_true_when_present(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2023, semester=1)
        cache_path.write_text("header\ndata")
        assert client.is_cached(year=2023, semester=1) is True

    def test_load_cached_csv(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2023, semester=1)
        csv_content = "campo;poco;data;oleo_sm3\nLULA;7LL55;2023-01-01;1000.5\n"
        cache_path.write_text(csv_content, encoding="latin-1")
        df = client.load_cached(year=2023, semester=1, encoding="latin-1")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1


class TestANPClientDownload:
    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_download_saves_to_cache(self, mock_requests, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"campo;poco;data;oleo_sm3\nLULA;7LL55;2023-01-01;1000.5\n"
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download(year=2023, semester=1)
        assert isinstance(df, pd.DataFrame)
        assert client.is_cached(year=2023, semester=1)

    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_download_uses_cache_when_available(self, mock_requests, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2023, semester=1)
        csv_content = "campo;poco;data;oleo_sm3\nLULA;7LL55;2023-01-01;1000.5\n"
        cache_path.write_text(csv_content, encoding="latin-1")

        df = client.download(year=2023, semester=1)
        mock_requests.get.assert_not_called()
        assert len(df) == 1

    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_download_force_refresh(self, mock_requests, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2023, semester=1)
        cache_path.write_text("old;data\n", encoding="latin-1")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"campo;poco;data;oleo_sm3\nLULA;7LL55;2023-01-01;1000.5\n"
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download(year=2023, semester=1, force_refresh=True)
        mock_requests.get.assert_called_once()
