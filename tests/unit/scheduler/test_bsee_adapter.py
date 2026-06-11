"""Tests for BSEE adapter: download, extract, write Parquet per dataset type.

Includes issue #267 hardening coverage: payload classification,
BSEE-shaped archives, the YAML catalog, and URL drift guards
(knowledge re-encoded from closed #9/#11/#12).
"""

import io
import os
import zipfile
from unittest.mock import patch

import pandas as pd
import pytest
import yaml

from worldenergydata.bsee.data.refresh.url_registry import get_regular_specs
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.scheduler.jobs.bsee_refresh import (
    BSEE_DATASETS,
    DEFAULT_CATALOG_PATH,
    BseeRefreshJob,
    load_dataset_catalog,
)


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


# ---------------------------------------------------------------------------
# Issue #267 hardening: payload classification, BSEE-shaped archives,
# YAML catalog, and URL drift guards (knowledge from closed #9/#11/#12).
# ---------------------------------------------------------------------------

HTML_ERROR_PAGE = (
    b"\r\n<!DOCTYPE html>\r\n<html><head><title>BSEE</title></head>"
    b"<body>moved</body></html>"
)

# Live BSEE archive shape: leading directory entry + quoted-CSV .txt
# members (verified against PlatStrucRawData.zip, 2026-06-10).
BSEE_TXT_CSV = (
    '"AREA_CODE","BLOCK_NUMBER","STRUCTURE_NAME"\r\n'
    '"MP","   20","3"\r\n'
    '"MI","  686","C-CMP"\r\n'
)


def _bsee_real_shape_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PlatStrucRawData/", "")
        zf.writestr("PlatStrucRawData/mv_platstruc_cgrefcodes.txt", '"A"\r\n"x"\r\n')
        zf.writestr("PlatStrucRawData/mv_platstruc_structures.txt", BSEE_TXT_CSV)
    return buf.getvalue()


class TestBseeAdapterHtmlPayload:
    """HTTP 200 + HTML (stale URL) must classify, not crash (issue #267)."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_html_payload_is_deterministic_failure_not_crash(
        self, MockScraper, tmp_path
    ):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = HTML_ERROR_PAGE

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "failure"
        assert "html" in result.error_msg.lower()
        assert "deterministic" in result.error_msg
        # All failures deterministic => prefixed for the retry layer (#460).
        assert result.error_msg.startswith("[deterministic]")

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_mixed_html_and_zip_is_partial_success(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value

        def selective(url, data_type="default", **kwargs):
            if data_type in ("pipeline_location", "deepwater_structure"):
                return HTML_ERROR_PAGE  # the observed #267 runtime failure
            return _bsee_real_shape_zip()

        scraper.download_zip_to_memory.side_effect = selective

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "success"
        assert (tmp_path / "bsee_platform_structures.parquet").exists()
        assert not (tmp_path / "bsee_pipeline_locations.parquet").exists()
        assert "pipeline_location" in result.error_msg
        assert "deterministic" in result.error_msg


class TestBseeAdapterRealArchiveShape:
    """Live archives hold .txt quoted-CSV members behind a dir entry."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_txt_members_extracted_via_primary_pattern(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = _bsee_real_shape_zip()

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "success"
        df = pd.read_parquet(tmp_path / "bsee_platform_structures.parquet")
        assert list(df.columns) == ["AREA_CODE", "BLOCK_NUMBER", "STRUCTURE_NAME"]
        assert len(df) == 2

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_zip_without_data_members_is_deterministic_failure(
        self, MockScraper, tmp_path
    ):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("X/", "")
            zf.writestr("X/readme.pdf", "nope")
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = buf.getvalue()

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "failure"
        assert "no .txt/.csv data members" in result.error_msg


class TestBseeCatalogConfig:
    """config/bsee.yml is the externalized catalog (issue #9 knowledge)."""

    def test_default_catalog_loads_four_scheduler_datasets(self):
        datasets = load_dataset_catalog()
        assert set(datasets) == set(BSEE_DATASETS)
        for name, info in datasets.items():
            assert info["url_key"] == BSEE_DATASETS[name]["url_key"]
            assert info["output_file"] == BSEE_DATASETS[name]["output_file"]

    def test_missing_catalog_falls_back_to_builtin(self, tmp_path):
        datasets = load_dataset_catalog(tmp_path / "absent.yml")
        assert datasets is BSEE_DATASETS

    def test_malformed_catalog_falls_back_to_builtin(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text("scheduler_datasets: []\n")
        assert load_dataset_catalog(bad) is BSEE_DATASETS

    def test_catalog_urls_match_scraper_registry(self):
        """Drift guard: YAML catalog, BSEEWebScraper.URLS, and the
        url_registry must agree on every dataset URL (issue #267 root
        cause was exactly this kind of silent drift)."""
        raw = yaml.safe_load(DEFAULT_CATALOG_PATH.read_text())
        registry = {s.bin_dir: s.zip_url for s in get_regular_specs()}
        for name, info in raw["scheduler_datasets"].items():
            assert info["url"] == BSEEWebScraper.URLS[info["url_key"]], name
            if info.get("registry_dir"):
                assert info["url"] == registry[info["registry_dir"]], name

    def test_stale_urls_are_gone(self):
        """The two URLs that caused #267's HTML payloads must not return."""
        urls = set(BSEEWebScraper.URLS.values())
        assert (
            "https://www.data.bsee.gov/Pipeline/Files/PipeLocAllRawData.zip" not in urls
        )
        assert (
            "https://www.data.bsee.gov/Platform/Files/PermStrucRawData.zip" not in urls
        )


@pytest.mark.network
@pytest.mark.smoke
@pytest.mark.skipif(
    os.environ.get("BSEE_LIVE_SMOKE") != "1",
    reason="live BSEE smoke test; set BSEE_LIVE_SMOKE=1 to run",
)
class TestBseeLiveSmoke:
    """Optional live probe: catalog URLs must serve zip content.

    HEAD-only (no payload download); BSEE regenerates these files daily
    around 09:45 UTC, so Last-Modified should also be present.
    """

    def test_catalog_urls_serve_zip_content_type(self):
        import requests

        raw = yaml.safe_load(DEFAULT_CATALOG_PATH.read_text())
        session = requests.Session()
        session.headers["User-Agent"] = "WorldEnergyData/1.0 (BSEE smoke test)"
        for name, info in raw["scheduler_datasets"].items():
            resp = session.head(info["url"], timeout=45)
            assert resp.status_code == 200, name
            ctype = resp.headers.get("Content-Type", "")
            assert (
                "zip" in ctype or "octet-stream" in ctype
            ), f"{name}: stale URL serves {ctype}"
