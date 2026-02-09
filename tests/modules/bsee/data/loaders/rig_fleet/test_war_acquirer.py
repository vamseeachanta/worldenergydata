"""Tests for WARDataAcquirer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from worldenergydata.bsee.data.loaders.rig_fleet.war_acquirer import (
    WARDataAcquirer,
)


class TestNormalizeColumns:
    """Tests for WAR column normalization."""

    def test_normalize_renames_botm_columns(self):
        """BOTM_ prefixed columns are renamed to standard names."""
        df = pd.DataFrame({
            "BOTM_AREA_CODE": ["GC", "MC"],
            "BOTM_BLOCK_NUMBER": ["640", "711"],
            "RIG_NAME": ["RIG_A", "RIG_B"],
        })
        acquirer = WARDataAcquirer(scraper=MagicMock(), processor=MagicMock())
        result = acquirer._normalize_columns(df)

        assert "AREA_CODE" in result.columns
        assert "BLOCK_NUMBER" in result.columns
        assert "BOTM_AREA_CODE" not in result.columns
        assert "BOTM_BLOCK_NUMBER" not in result.columns

    def test_normalize_preserves_existing_columns(self):
        """Columns that already have standard names are kept."""
        df = pd.DataFrame({
            "AREA_CODE": ["GC"],
            "BLOCK_NUMBER": ["640"],
            "RIG_NAME": ["RIG_A"],
        })
        acquirer = WARDataAcquirer(scraper=MagicMock(), processor=MagicMock())
        result = acquirer._normalize_columns(df)

        assert "AREA_CODE" in result.columns
        assert result["AREA_CODE"].iloc[0] == "GC"

    def test_normalize_handles_missing_columns(self):
        """No error when expected columns are absent."""
        df = pd.DataFrame({"RIG_NAME": ["RIG_A"]})
        acquirer = WARDataAcquirer(scraper=MagicMock(), processor=MagicMock())
        result = acquirer._normalize_columns(df)

        assert "RIG_NAME" in result.columns

    def test_normalize_renames_war_start_dt(self):
        """WAR_RPT_START_DT renamed to WAR_START_DT."""
        df = pd.DataFrame({
            "WAR_RPT_START_DT": ["2020-01-01"],
            "RIG_NAME": ["RIG_A"],
        })
        acquirer = WARDataAcquirer(scraper=MagicMock(), processor=MagicMock())
        result = acquirer._normalize_columns(df)

        assert "WAR_START_DT" in result.columns


class TestAcquireWarDataframe:
    """Tests for the full acquire pipeline."""

    def test_acquire_returns_merged_dataframe(self):
        """Acquire merges all DataFrames from processor output."""
        mock_scraper = MagicMock()
        mock_scraper.download_war_data.return_value = b"fake_zip_data"

        df1 = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B"],
            "BOTM_AREA_CODE": ["GC", "MC"],
        })
        df2 = pd.DataFrame({
            "RIG_NAME": ["RIG_C"],
            "BOTM_AREA_CODE": ["GC"],
        })
        mock_processor = MagicMock()
        mock_processor.process_zip_in_memory.return_value = {
            "file1.txt": df1,
            "file2.txt": df2,
        }

        acquirer = WARDataAcquirer(
            scraper=mock_scraper,
            processor=mock_processor,
        )
        result = acquirer.acquire_war_dataframe()

        assert result is not None
        assert len(result) == 3
        assert "AREA_CODE" in result.columns

    def test_acquire_returns_none_on_download_failure(self, tmp_path: Path):
        """Returns None when scraper download fails."""
        mock_scraper = MagicMock()
        mock_scraper.download_war_data.return_value = None

        acquirer = WARDataAcquirer(
            scraper=mock_scraper,
            processor=MagicMock(),
            local_data_dir=tmp_path,
        )
        result = acquirer.acquire_war_dataframe()

        assert result is None

    def test_acquire_returns_none_on_empty_processor_output(self, tmp_path: Path):
        """Returns None when processor returns empty dict."""
        mock_scraper = MagicMock()
        mock_scraper.download_war_data.return_value = b"fake"

        mock_processor = MagicMock()
        mock_processor.process_zip_in_memory.return_value = {}

        acquirer = WARDataAcquirer(
            scraper=mock_scraper,
            processor=mock_processor,
            local_data_dir=tmp_path,
        )
        result = acquirer.acquire_war_dataframe()

        assert result is None


class TestCaching:
    """Tests for download caching to .local/ directory."""

    def test_cache_path_construction(self, tmp_path: Path):
        """Cache directory is constructed from local_data_dir."""
        acquirer = WARDataAcquirer(
            scraper=MagicMock(),
            processor=MagicMock(),
            local_data_dir=tmp_path,
        )
        assert acquirer._cache_dir == tmp_path / "war"

    def test_save_and_load_cache(self, tmp_path: Path):
        """Saved cache can be loaded back."""
        mock_scraper = MagicMock()
        mock_scraper.download_war_data.return_value = b"test_zip_bytes"

        mock_processor = MagicMock()
        mock_processor.process_zip_in_memory.return_value = {
            "data.txt": pd.DataFrame({"RIG_NAME": ["RIG_A"]}),
        }

        acquirer = WARDataAcquirer(
            scraper=mock_scraper,
            processor=mock_processor,
            local_data_dir=tmp_path,
        )
        result = acquirer.acquire_war_dataframe()

        assert result is not None
        # Verify the cache file was written
        cache_file = tmp_path / "war" / "eWellWARRawData.zip"
        assert cache_file.exists()
        assert cache_file.read_bytes() == b"test_zip_bytes"
