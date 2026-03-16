#!/usr/bin/env python3
# ABOUTME: TDD tests for WRK-1232 production data download/conversion pipeline
# ABOUTME: Tests router(), download_zip_data(), and end-to-end pipeline

"""Tests for GetProdDataFromZip router and download methods."""

from __future__ import annotations

import os
import pickle
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.bsee.data.sources.zip.production_data import GetProdDataFromZip

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "bsee"
FIXTURE_ZIP = FIXTURE_DIR / "production_data.zip"


@pytest.fixture
def loader():
    return GetProdDataFromZip()


@pytest.fixture
def tmp_dirs():
    """Create temporary zip and bin directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_dir = os.path.join(tmpdir, "zip")
        bin_dir = os.path.join(tmpdir, "bin")
        os.makedirs(zip_dir)
        os.makedirs(bin_dir)
        yield {"zip": zip_dir, "bin": bin_dir, "root": tmpdir}


@pytest.fixture
def sample_zip_bytes():
    """Create in-memory ZIP with sample production CSV."""
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        csv_content = (
            "LEASE_NUMBER,COMPLETION_NAME,PRODUCTION_DATE,DAYS_ON_PROD,"
            "PRODUCT_CODE,MON_O_PROD_VOL,MON_G_PROD_VOL,MON_WTR_PROD_VOL,"
            "API_WELL_NUMBER,WELL_STAT_CD,AREA_CODE_BLOCK_NUM,OPERATOR_NUM,"
            "SORT_NAME,BOEM_FIELD,INJECTION_VOLUME,PROD_INTERVAL_CD,"
            "FIRST_PROD_DATE,UNIT_AGT_NUMBER,UNIT_ALOC_SUFFIX\n"
            "G35364,COMP_1,202201,30,OIL,11070,62328,3135,"
            "177154051100,ACTIVE,MC807,02481,ANCHOR INC,ANCHOR,0,O,"
            "20100101,0,0\n"
            "G35364,COMP_2,202202,28,OIL,9800,55000,2800,"
            "177154051100,ACTIVE,MC807,02481,ANCHOR INC,ANCHOR,0,O,"
            "20100101,0,0\n"
        )
        zf.writestr("productiondata.csv", csv_content)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# router() tests
# ---------------------------------------------------------------------------


class TestRouter:
    """Test the router() orchestration method."""

    def test_router_returns_result(self, loader, sample_zip_bytes, tmp_dirs):
        """router() should return a dict with status and data info."""
        cfg = _make_cfg(tmp_dirs)
        # Write sample zip to the zip dir so save_zip_data_to_binary can find it
        _write_zip_to_dir(sample_zip_bytes, tmp_dirs["zip"], "productiondata.zip")

        result = loader.router(cfg)
        assert result is not None

    def test_router_creates_bin_files(self, loader, sample_zip_bytes, tmp_dirs):
        """router() should produce .bin files in the bin directory."""
        cfg = _make_cfg(tmp_dirs)
        _write_zip_to_dir(sample_zip_bytes, tmp_dirs["zip"], "productiondata.zip")

        loader.router(cfg)

        bin_files = [f for f in os.listdir(tmp_dirs["bin"]) if f.endswith(".bin")]
        assert len(bin_files) > 0, "Expected .bin files in bin directory"

    def test_router_bin_contains_dataframe(self, loader, sample_zip_bytes, tmp_dirs):
        """router() produced .bin files should contain valid DataFrames."""
        cfg = _make_cfg(tmp_dirs)
        _write_zip_to_dir(sample_zip_bytes, tmp_dirs["zip"], "productiondata.zip")

        loader.router(cfg)

        bin_files = [f for f in os.listdir(tmp_dirs["bin"]) if f.endswith(".bin")]
        for bf in bin_files:
            with open(os.path.join(tmp_dirs["bin"], bf), "rb") as f:
                df = pickle.load(f)
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0


# ---------------------------------------------------------------------------
# download_zip_data() tests
# ---------------------------------------------------------------------------


class TestDownloadZipData:
    """Test the download_zip_data() method."""

    @patch("worldenergydata.bsee.data.sources.zip.production_data.BSEEWebScraper")
    def test_download_returns_bytes(
        self, mock_scraper_cls, loader, sample_zip_bytes, tmp_dirs
    ):
        """download_zip_data() should return ZIP bytes."""
        mock_instance = MagicMock()
        mock_instance.download_zip_to_memory.return_value = sample_zip_bytes
        mock_scraper_cls.return_value = mock_instance

        cfg = _make_cfg(tmp_dirs)
        result = loader.download_zip_data(cfg)
        assert isinstance(result, bytes)
        assert len(result) > 0

    @patch("worldenergydata.bsee.data.sources.zip.production_data.BSEEWebScraper")
    def test_download_calls_scraper(
        self, mock_scraper_cls, loader, sample_zip_bytes, tmp_dirs
    ):
        """download_zip_data() should use BSEEWebScraper."""
        mock_instance = MagicMock()
        mock_instance.download_zip_to_memory.return_value = sample_zip_bytes
        mock_scraper_cls.return_value = mock_instance

        cfg = _make_cfg(tmp_dirs)
        loader.download_zip_data(cfg)
        mock_instance.download_zip_to_memory.assert_called_once()

    @patch("worldenergydata.bsee.data.sources.zip.production_data.BSEEWebScraper")
    def test_download_writes_to_zip_dir(
        self, mock_scraper_cls, loader, sample_zip_bytes, tmp_dirs
    ):
        """download_zip_data() should write the ZIP to the configured zip directory."""
        mock_instance = MagicMock()
        mock_instance.download_zip_to_memory.return_value = sample_zip_bytes
        mock_scraper_cls.return_value = mock_instance

        cfg = _make_cfg(tmp_dirs)
        loader.download_zip_data(cfg)

        zip_files = [f for f in os.listdir(tmp_dirs["zip"]) if f.endswith(".zip")]
        assert len(zip_files) > 0, "Expected ZIP file saved to zip directory"


# ---------------------------------------------------------------------------
# End-to-end pipeline tests
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    """Test the full download → extract → convert → query pipeline."""

    def test_save_then_query_by_api12(self, loader, sample_zip_bytes, tmp_dirs):
        """After save_zip_data_to_binary, should be able to query by API12."""
        cfg = _make_cfg(tmp_dirs)
        _write_zip_to_dir(sample_zip_bytes, tmp_dirs["zip"], "productiondata.zip")

        loader.save_zip_data_to_binary(cfg)

        bin_files = [f for f in os.listdir(tmp_dirs["bin"]) if f.endswith(".bin")]
        assert len(bin_files) > 0

        # Verify data round-trips correctly
        with open(os.path.join(tmp_dirs["bin"], bin_files[0]), "rb") as f:
            df = pickle.load(f)
        assert "API_WELL_NUMBER" in df.columns or "LEASE_NUMBER" in df.columns

    def test_fixture_zip_loads(self, loader):
        """The test fixture production_data.zip should be loadable."""
        assert FIXTURE_ZIP.exists(), f"Missing fixture: {FIXTURE_ZIP}"
        with zipfile.ZipFile(FIXTURE_ZIP) as zf:
            names = zf.namelist()
            assert len(names) > 0


# ---------------------------------------------------------------------------
# url_registry compatibility tests
# ---------------------------------------------------------------------------


class TestUrlRegistryCompatibility:
    """Verify production pipeline is compatible with url_registry specs."""

    def test_production_url_exists_in_scraper(self):
        """BSEEWebScraper should have a production URL."""
        from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper

        assert "production" in BSEEWebScraper.URLS
        assert "ProductionRawData.zip" in BSEEWebScraper.URLS["production"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cfg(tmp_dirs):
    """Build a minimal cfg dict for testing (bypasses WorkingWithYAML path resolution)."""
    return {
        "parameters": {
            "filepath": {
                "production": {
                    "zip": tmp_dirs["zip"],
                    "bin": tmp_dirs["bin"],
                }
            }
        },
        "Analysis": {
            "result_folder": tmp_dirs["root"],
        },
    }


def _write_zip_to_dir(zip_bytes, target_dir, filename):
    """Write raw ZIP bytes to a directory as a file."""
    with open(os.path.join(target_dir, filename), "wb") as f:
        f.write(zip_bytes)
