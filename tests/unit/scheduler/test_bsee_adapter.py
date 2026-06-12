"""Tests for BSEE adapter: download, extract, write Parquet per dataset type.

Includes issue #267 hardening coverage: payload classification,
BSEE-shaped archives, the YAML catalog, and URL drift guards
(knowledge re-encoded from closed #9/#11/#12), plus the issue #460
retry contract: structural ``JobResult.retryable`` semantics, bounded
in-job transient retries, fail-closed member selection, and catalog
validation (PR #465 review round 1).
"""

import io
import os
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import yaml

from worldenergydata.bsee.data.refresh.payload import extract_primary_table
from worldenergydata.bsee.data.refresh.url_registry import get_regular_specs
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.scheduler.jobs.bsee_refresh import (
    BSEE_DATASETS,
    DEFAULT_CATALOG_PATH,
    TRANSIENT_DATASET_ATTEMPTS,
    BseeRefreshJob,
    load_dataset_catalog,
    validate_dataset_catalog,
)
from worldenergydata.scheduler.monitor import RetryManager

# Live BSEE archive member content shape: quoted CSV, CRLF, .txt
# (verified against PlatStrucRawData.zip, 2026-06-10).
BSEE_TXT_CSV = (
    '"AREA_CODE","BLOCK_NUMBER","STRUCTURE_NAME"\r\n'
    '"MP","   20","3"\r\n'
    '"MI","  686","C-CMP"\r\n'
)

#: Representative archive layout per scheduler dataset: directory entry
#: + primary member whose name matches the configured
#: primary_member_patterns in config/bsee.yml (live-observed names).
DATASET_MEMBERS = {
    "platform": ("PlatStrucRawData", "mv_platstruc_structures.txt"),
    "pipeline_permit": ("PipePermRawData", "mv_pipeperm_applications.txt"),
    "pipeline_location": ("PipeLocRawData", "mv_pipelinelocations.txt"),
    "deepwater_structure": ("PermStrucRawData", "mv_perm_platforms.txt"),
}

HTML_ERROR_PAGE = (
    b"\r\n<!DOCTYPE html>\r\n<html><head><title>BSEE</title></head>"
    b"<body>moved</body></html>"
)


def _dataset_zip(data_type: str, csv_content: str = BSEE_TXT_CSV) -> bytes:
    """Build a representative zip for one scheduler dataset.

    Includes a larger decoy member that does NOT match any configured
    pattern, so a regression back to silent largest-member fallback
    would pick the wrong member and fail the column assertions.
    """
    dir_name, member = DATASET_MEMBERS[data_type]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{dir_name}/", "")
        zf.writestr(f"{dir_name}/mv_decoy_large.txt", '"D"\r\n' + '"x"\r\n' * 5000)
        zf.writestr(f"{dir_name}/{member}", csv_content)
    return buf.getvalue()


def _per_dataset_download(url, data_type="default", **kwargs):
    """Scraper side_effect serving the matching archive per dataset."""
    return _dataset_zip(data_type)


class TestBseeAdapterPlatform:
    """Test 1: Platform data download, extract, and Parquet output."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_platform_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.side_effect = _per_dataset_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "success"
        parquet_path = tmp_path / "bsee_platform_structures.parquet"
        assert parquet_path.exists(), "Platform parquet file must be written"
        df = pd.read_parquet(parquet_path)
        assert list(df.columns) == ["AREA_CODE", "BLOCK_NUMBER", "STRUCTURE_NAME"]
        assert len(df) == 2


class TestBseeAdapterPipelines:
    """Test 2: Pipeline permit and location data."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_pipeline_permits_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.side_effect = _per_dataset_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert (tmp_path / "bsee_pipeline_permits.parquet").exists()

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_pipeline_locations_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.side_effect = _per_dataset_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert (tmp_path / "bsee_pipeline_locations.parquet").exists()


class TestBseeAdapterDeepwater:
    """Test 3: Deepwater structure data."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_deepwater_parquet_written(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.side_effect = _per_dataset_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert (tmp_path / "bsee_deepwater_structures.parquet").exists()


class TestBseeAdapterPartialFailure:
    """Test 4: Partial failure semantics (issue #460, review R1-3).

    A transient partial failure must NOT be reported as success (the
    scheduler retry layer needs to re-run the job); a deterministic
    partial failure stays tolerated but explicitly marked.
    """

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_transient_partial_failure_is_retryable_failure(
        self, MockScraper, tmp_path
    ):
        scraper = MockScraper.return_value
        platform_calls = {"n": 0}

        def selective_download(url, data_type="default", **kwargs):
            if data_type == "platform":
                platform_calls["n"] += 1
                return None  # download failed after scraper retries
            return _dataset_zip(data_type)

        scraper.download_zip_to_memory.side_effect = selective_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "failure", "Transient partial must not be success"
        assert result.retryable is True
        assert "transient" in result.error_msg
        # The failed dataset got bounded in-job retries before giving up.
        assert platform_calls["n"] == TRANSIENT_DATASET_ATTEMPTS
        # Other datasets were still written (rows reported honestly).
        assert not (tmp_path / "bsee_platform_structures.parquet").exists()
        assert (tmp_path / "bsee_pipeline_permits.parquet").exists()
        assert result.records_updated == 6  # 3 datasets x 2 rows

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_deterministic_partial_failure_is_marked_success(
        self, MockScraper, tmp_path
    ):
        scraper = MockScraper.return_value

        def selective_download(url, data_type="default", **kwargs):
            if data_type == "platform":
                return HTML_ERROR_PAGE  # stale URL: deterministic
            return _dataset_zip(data_type)

        scraper.download_zip_to_memory.side_effect = selective_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "success"
        assert result.error_msg.startswith("[partial:deterministic]")
        assert "platform" in result.error_msg
        # Deterministic failures get no in-job retry: 4 calls total.
        assert scraper.download_zip_to_memory.call_count == 4


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
        # All-transient failure stays retryable for the scheduler layer.
        assert result.retryable is True


class TestBseeAdapterRecordCount:
    """Test 6: records_updated is sum of rows across all Parquet files."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_records_updated_is_total_rows(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.side_effect = _per_dataset_download

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        # 4 datasets x 2 rows each = 8
        assert result.records_updated == 8
        assert result.status == "success"


# ---------------------------------------------------------------------------
# Issue #267 hardening: payload classification, BSEE-shaped archives,
# YAML catalog, and URL drift guards (knowledge from closed #9/#11/#12).
# ---------------------------------------------------------------------------


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
        # All failures deterministic => structurally non-retryable (#460)
        # plus the operator-facing prefix.
        assert result.retryable is False
        assert result.error_msg.startswith("[deterministic]")

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_mixed_html_and_zip_is_partial_success(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value

        def selective(url, data_type="default", **kwargs):
            if data_type in ("pipeline_location", "deepwater_structure"):
                return HTML_ERROR_PAGE  # the observed #267 runtime failure
            return _dataset_zip(data_type)

        scraper.download_zip_to_memory.side_effect = selective

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "success"
        assert (tmp_path / "bsee_platform_structures.parquet").exists()
        assert not (tmp_path / "bsee_pipeline_locations.parquet").exists()
        assert "pipeline_location" in result.error_msg
        assert "deterministic" in result.error_msg


class TestBseeAdapterUnknownPayload:
    """Unknown non-zip, non-HTML payloads are transient (review R1-5).

    A plain-text gateway error or proxy banner is not evidence of a
    stale URL; only HTML/empty bodies carry that deterministic meaning.
    """

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_unknown_payload_is_transient_and_not_blamed_on_stale_url(
        self, MockScraper, tmp_path
    ):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = b"\x00\x01 bad gateway"

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "failure"
        assert result.retryable is True
        assert "stale" not in result.error_msg.lower()
        assert "transient" in result.error_msg
        # Transient => bounded in-job retry per dataset.
        assert (
            scraper.download_zip_to_memory.call_count
            == 4 * TRANSIENT_DATASET_ATTEMPTS
        )


class TestBseeSchedulerRetryContract:
    """Scheduler-level retry semantics via RetryManager (review R1-1/R1-3)."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    @patch("worldenergydata.scheduler.monitor.time.sleep")
    def test_deterministic_failure_runs_exactly_once_with_zero_sleeps(
        self, mock_sleep, MockScraper, tmp_path
    ):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = HTML_ERROR_PAGE

        job = BseeRefreshJob()
        manager = RetryManager(max_retries=3, backoff_seconds=60)
        run_count = {"n": 0}

        def run_job():
            run_count["n"] += 1
            return job.run({"output_dir": str(tmp_path)})

        result = manager.run_with_retry(run_job)

        assert result.status == "failure"
        assert result.retryable is False
        assert run_count["n"] == 1, "deterministic failure must not be re-run"
        mock_sleep.assert_not_called()
        # No in-job retries either: 4 datasets x 1 attempt.
        assert scraper.download_zip_to_memory.call_count == 4

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    @patch("worldenergydata.scheduler.monitor.time.sleep")
    def test_transient_partial_failure_is_retried_by_retry_manager(
        self, mock_sleep, MockScraper, tmp_path
    ):
        scraper = MockScraper.return_value
        loc_calls = {"n": 0}

        def flaky(url, data_type="default", **kwargs):
            if data_type == "pipeline_location":
                loc_calls["n"] += 1
                # Fail every in-job attempt of the first job run only.
                if loc_calls["n"] <= TRANSIENT_DATASET_ATTEMPTS:
                    return None
            return _dataset_zip(data_type)

        scraper.download_zip_to_memory.side_effect = flaky

        job = BseeRefreshJob()
        manager = RetryManager(max_retries=3, backoff_seconds=60)
        results = []

        def run_job():
            r = job.run({"output_dir": str(tmp_path)})
            results.append(r)
            return r

        final = manager.run_with_retry(run_job)

        assert len(results) == 2, "transient partial must be re-run by RetryManager"
        assert results[0].status == "failure"
        assert results[0].retryable is True
        assert final.status == "success"
        assert (tmp_path / "bsee_pipeline_locations.parquet").exists()
        assert mock_sleep.call_count == 1  # one backoff between the two runs


class TestBseeAdapterRealArchiveShape:
    """Live archives hold .txt quoted-CSV members behind a dir entry."""

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_txt_members_extracted_via_primary_pattern(self, MockScraper, tmp_path):
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.side_effect = _per_dataset_download

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
        assert result.retryable is False
        assert "no .txt/.csv data members" in result.error_msg

    @patch("worldenergydata.scheduler.jobs.bsee_refresh.BSEEWebScraper")
    def test_member_rename_is_deterministic_failure_not_silent_fallback(
        self, MockScraper, tmp_path
    ):
        """Fail-closed member selection (review R1-2): if BSEE renames
        the primary member, the job must fail deterministically instead
        of silently writing the largest member."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("PlatStrucRawData/", "")
            zf.writestr("PlatStrucRawData/mv_renamed_member.txt", BSEE_TXT_CSV)
        scraper = MockScraper.return_value
        scraper.download_zip_to_memory.return_value = buf.getvalue()

        job = BseeRefreshJob()
        result = job.run({"output_dir": str(tmp_path)})

        assert result.status == "failure"
        assert result.retryable is False
        assert "primary_member_patterns" in result.error_msg
        assert not list(tmp_path.glob("*.parquet"))


class TestBseeConfiguredPatternsMatchRepresentativeArchives:
    """Each configured pattern is proven against a representative
    archive whose member names mirror the live BSEE files (review R1-2)."""

    def test_each_catalog_dataset_extracts_via_configured_pattern(self):
        datasets = load_dataset_catalog()
        assert set(datasets) == set(DATASET_MEMBERS)
        for name, info in datasets.items():
            dir_name, member_name = DATASET_MEMBERS[name]
            df, member = extract_primary_table(
                _dataset_zip(name), info["primary_member_patterns"]
            )
            # Selection is fail-closed, so reaching here proves the
            # configured pattern matched; assert it picked the primary
            # member, not the larger decoy.
            assert member == f"{dir_name}/{member_name}", name
            assert len(df) == 2, name


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

    def test_builtin_defaults_pass_validation(self):
        validate_dataset_catalog(BSEE_DATASETS)

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

    def test_stale_urls_absent_from_bsee_source_tree(self):
        """Stronger drift guard (review R1-6): the two known-stale URLs
        must not appear anywhere in live BSEE/scheduler source or the
        YAML catalog. Tests and docs may mention them as history."""
        stale_urls = (
            "https://www.data.bsee.gov/Platform/Files/PermStrucRawData.zip",
            "https://www.data.bsee.gov/Pipeline/Files/PipeLocAllRawData.zip",
        )
        import worldenergydata

        src_root = Path(worldenergydata.__file__).resolve().parent
        scan_files = [DEFAULT_CATALOG_PATH]
        for tree in ("bsee", "scheduler"):
            scan_files.extend(sorted((src_root / tree).rglob("*.py")))

        offenders = []
        for path in scan_files:
            text = path.read_text(encoding="utf-8", errors="replace")
            for stale in stale_urls:
                if stale in text:
                    offenders.append(f"{path}: {stale}")
        assert not offenders, "stale BSEE URLs reintroduced:\n" + "\n".join(offenders)


class TestBseeCatalogValidation:
    """Catalog entries are validated on load (review R1-4): the catalog
    path is runtime-overridable config, so URLs and output paths are an
    injection surface."""

    def _write_catalog(self, tmp_path, overrides: dict) -> Path:
        entry = {
            "url": "https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip",
            "url_key": "platform",
            "output_file": "bsee_platform_structures.parquet",
            "primary_member_patterns": ["mv_platstruc_structures.txt"],
        }
        entry.update(overrides)
        catalog = tmp_path / "bsee.yml"
        catalog.write_text(yaml.safe_dump({"scheduler_datasets": {"platform": entry}}))
        return catalog

    def test_valid_catalog_passes(self, tmp_path):
        catalog = self._write_catalog(tmp_path, {})
        datasets = load_dataset_catalog(catalog)
        assert set(datasets) == {"platform"}

    def test_path_traversal_output_file_rejected(self, tmp_path):
        catalog = self._write_catalog(tmp_path, {"output_file": "../escape.parquet"})
        with pytest.raises(ValueError, match="output_file"):
            load_dataset_catalog(catalog)

    def test_non_parquet_output_file_rejected(self, tmp_path):
        catalog = self._write_catalog(tmp_path, {"output_file": "evil.sh"})
        with pytest.raises(ValueError, match="output_file"):
            load_dataset_catalog(catalog)

    def test_http_url_rejected(self, tmp_path):
        catalog = self._write_catalog(
            tmp_path,
            {"url": "http://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip"},
        )
        with pytest.raises(ValueError, match="url"):
            load_dataset_catalog(catalog)

    def test_foreign_host_url_rejected(self, tmp_path):
        catalog = self._write_catalog(
            tmp_path, {"url": "https://evil.example.com/PlatStrucRawData.zip"}
        )
        with pytest.raises(ValueError, match="url"):
            load_dataset_catalog(catalog)

    def test_empty_member_patterns_rejected(self, tmp_path):
        catalog = self._write_catalog(tmp_path, {"primary_member_patterns": []})
        with pytest.raises(ValueError, match="primary_member_patterns"):
            load_dataset_catalog(catalog)

    def test_unknown_url_key_rejected(self, tmp_path):
        catalog = self._write_catalog(tmp_path, {"url_key": "not_a_real_key"})
        with pytest.raises(ValueError, match="url_key"):
            load_dataset_catalog(catalog)

    def test_job_reports_invalid_catalog_as_deterministic_failure(self, tmp_path):
        catalog = self._write_catalog(tmp_path, {"output_file": "../escape.parquet"})
        out_dir = tmp_path / "out"

        job = BseeRefreshJob()
        result = job.run(
            {"output_dir": str(out_dir), "catalog_path": str(catalog)}
        )

        assert result.status == "failure"
        assert result.retryable is False
        assert result.error_msg.startswith("[deterministic]")
        assert not (tmp_path / "escape.parquet").exists()


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
