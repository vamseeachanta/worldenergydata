"""Tests for BSEE adapter: download, extract, write Parquet per dataset type."""

import io
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.scheduler.jobs.base import JobResult
from worldenergydata.scheduler.jobs.bsee_refresh import BSEE_DATASETS, BseeRefreshJob


def _make_zip_bytes(csv_content: str, csv_filename: str = "data.csv") -> bytes:
    """Create in-memory zip containing a single CSV file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_filename, csv_content)
    return buf.getvalue()


SAMPLE_CSV = "col_a,col_b\n1,hello\n2,world\n3,test\n"
SAMPLE_ZIP = _make_zip_bytes(SAMPLE_CSV)


class TestBseeAdapterPlatform:
    """Test 1: Platform data download, extract, and Parquet output."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_platform_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = SAMPLE_ZIP

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        parquet_path = tmp_path / "bsee_platform_structures.parquet"
        assert parquet_path.exists(), "Platform parquet file must be written"
        df = pd.read_parquet(parquet_path)
        assert len(df) == 3


class TestBseeAdapterPipelines:
    """Test 2: Pipeline permit and location data."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_pipeline_permits_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = SAMPLE_ZIP

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert (tmp_path / "bsee_pipeline_permits.parquet").exists()

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_pipeline_locations_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = SAMPLE_ZIP

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert (tmp_path / "bsee_pipeline_locations.parquet").exists()


class TestBseeAdapterDeepwater:
    """Test 3: Deepwater structure data."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_deepwater_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = SAMPLE_ZIP

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert (tmp_path / "bsee_deepwater_structures.parquet").exists()


class TestBseeAdapterPartialFailure:
    """Test 4: Partial failure - one dataset fails, others succeed."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_partial_failure_returns_success(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value

        def selective_download(url, data_type="default", **kwargs):
            if data_type == "platform":
                return None  # platform fails
            return SAMPLE_ZIP

        scraper.download_zip_to_memory.side_effect = selective_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "success", "Partial failure should still succeed"
        assert not (tmp_path / "bsee_platform_structures.parquet").exists()
        assert (tmp_path / "bsee_pipeline_permits.parquet").exists()


class TestBseeAdapterAllFail:
    """Test 5: All downloads fail => status='failure'."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_all_fail_returns_failure(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = None

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "failure"
        assert result.error_msg is not None


class TestBseeAdapterRecordCount:
    """Test 6: records_updated is sum of rows across all Parquet files."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_records_updated_is_total_rows(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = SAMPLE_ZIP

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        # 4 datasets x 3 rows each = 12
        assert result.records_updated == 12
        assert result.status == "success"
