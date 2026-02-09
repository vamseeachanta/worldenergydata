"""Tests for BoreholeDataAcquirer (WRK-116 Phase 1).

Covers: caching, download fallback, normalisation (types, dates, numerics,
categoricals, column filtering), zip extraction, and graceful failure.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.data.loaders.well.borehole_acquirer import (
    BoreholeDataAcquirer,
    _CACHE_FILENAME,
    _KEEP_COLUMNS,
    _SOURCE_URL,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_RAW_COLUMNS = (
    "API_WELL_NUMBER,WELL_NAME,WELL_NAME_SUFFIX,BOTM_LEASE_NUMBER,"
    "BOTM_AREA_CODE,BOTM_BLOCK_NUMBER,COMPANY_NAME,WELL_SPUD_DATE,"
    "BH_TOTAL_MD,WELL_BORE_TVD,WELL_TD_SS,RKB_ELEVATION,"
    "WELL_BP_ST_KICKOFF_MD,TOTAL_DEPTH_DATE,BOREHOLE_STAT_DT,"
    "WELL_TYPE_CODE,BOREHOLE_STAT_CD,CASING_CUT_CODE,WATER_DEPTH,"
    "UNDWTR_COMP_STUB,SURF_LEASE_NUMBER,SURF_LATITUDE,SURF_LONGITUDE,"
    "BOTM_LATITUDE,BOTM_LONGITUDE,REGION_CODE"
)


def _make_test_zip(rows: int = 5) -> bytes:
    """Create a minimal borehole zip for testing."""
    buf = io.BytesIO()
    lines = [_ALL_RAW_COLUMNS]
    for i in range(rows):
        api = 177114156300 + i
        lines.append(
            f'"{api}","W{i:03d}","ST00BP00","G01234","MC","123",'
            f'"TestCo",1/{i + 1}/2020,{10000 + i * 1000},'
            f"{9000 + i * 500},,,,6/{i + 1}/2020,,C,PA,Y,"
            f"{500 + i * 100},N,G01234,28.5,-89.5,28.5,-89.5,G"
        )
    csv_content = "\n".join(lines) + "\n"
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "BoreholeRawData/mv_boreholes_all.txt", csv_content
        )
    return buf.getvalue()


class _FakeDownloader:
    """Records calls and returns preset zip bytes."""

    def __init__(self, zip_bytes: bytes):
        self.zip_bytes = zip_bytes
        self.calls: list[str] = []

    def download(self, url: str) -> bytes:
        self.calls.append(url)
        return self.zip_bytes


def _seed_cache(cache_dir: Path, zip_bytes: bytes, age_days: int = 0) -> None:
    """Write a zip file and metadata to a cache directory."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / _CACHE_FILENAME).write_bytes(zip_bytes)
    downloaded_at = datetime.now(tz=timezone.utc) - timedelta(days=age_days)
    meta = {
        "downloaded_at": downloaded_at.isoformat(),
        "size_bytes": len(zip_bytes),
    }
    (cache_dir / "download_metadata.json").write_text(
        json.dumps(meta, indent=2)
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBoreholeAcquirer:
    """Unit tests for BoreholeDataAcquirer."""

    def test_acquire_returns_dataframe_from_cache(self, tmp_path: Path):
        """When a fresh cache exists, downloader is NOT called."""
        zip_bytes = _make_test_zip(3)
        local_dir = tmp_path / ".local"
        _seed_cache(local_dir / "borehole", zip_bytes, age_days=0)

        downloader = _FakeDownloader(zip_bytes)
        acquirer = BoreholeDataAcquirer(
            downloader=downloader, local_data_dir=local_dir
        )

        df = acquirer.acquire_borehole_dataframe()

        assert df is not None
        assert len(df) == 3
        assert downloader.calls == [], "Downloader should not be called"

    def test_acquire_downloads_when_no_cache(self, tmp_path: Path):
        """When no cache exists, downloader is called and returns valid df."""
        zip_bytes = _make_test_zip(5)
        local_dir = tmp_path / ".local"
        downloader = _FakeDownloader(zip_bytes)

        acquirer = BoreholeDataAcquirer(
            downloader=downloader, local_data_dir=local_dir
        )

        df = acquirer.acquire_borehole_dataframe()

        assert df is not None
        assert len(df) == 5
        assert len(downloader.calls) == 1
        assert downloader.calls[0] == _SOURCE_URL

    def test_normalize_converts_api_to_string(self, tmp_path: Path):
        """API_WELL_NUMBER should be normalised to string dtype."""
        zip_bytes = _make_test_zip(2)
        local_dir = tmp_path / ".local"
        _seed_cache(local_dir / "borehole", zip_bytes)

        acquirer = BoreholeDataAcquirer(local_data_dir=local_dir)
        df = acquirer.acquire_borehole_dataframe()

        assert pd.api.types.is_string_dtype(df["API_WELL_NUMBER"])
        # Should not have trailing .0
        for val in df["API_WELL_NUMBER"]:
            assert not str(val).endswith(".0")

    def test_normalize_parses_dates(self, tmp_path: Path):
        """WELL_SPUD_DATE and TOTAL_DEPTH_DATE become datetime64."""
        zip_bytes = _make_test_zip(2)
        local_dir = tmp_path / ".local"
        _seed_cache(local_dir / "borehole", zip_bytes)

        acquirer = BoreholeDataAcquirer(local_data_dir=local_dir)
        df = acquirer.acquire_borehole_dataframe()

        assert pd.api.types.is_datetime64_any_dtype(df["WELL_SPUD_DATE"])
        assert pd.api.types.is_datetime64_any_dtype(df["TOTAL_DEPTH_DATE"])

    def test_normalize_numeric_columns(self, tmp_path: Path):
        """BH_TOTAL_MD, WELL_BORE_TVD, WATER_DEPTH become float32."""
        zip_bytes = _make_test_zip(3)
        local_dir = tmp_path / ".local"
        _seed_cache(local_dir / "borehole", zip_bytes)

        acquirer = BoreholeDataAcquirer(local_data_dir=local_dir)
        df = acquirer.acquire_borehole_dataframe()

        for col in ("BH_TOTAL_MD", "WELL_BORE_TVD", "WATER_DEPTH"):
            assert df[col].dtype.name == "float32", (
                f"{col} should be float32, got {df[col].dtype}"
            )

    def test_normalize_categorical_columns(self, tmp_path: Path):
        """BOREHOLE_STAT_CD, BOTM_AREA_CODE, WELL_TYPE_CODE become category."""
        zip_bytes = _make_test_zip(3)
        local_dir = tmp_path / ".local"
        _seed_cache(local_dir / "borehole", zip_bytes)

        acquirer = BoreholeDataAcquirer(local_data_dir=local_dir)
        df = acquirer.acquire_borehole_dataframe()

        for col in ("BOREHOLE_STAT_CD", "BOTM_AREA_CODE", "WELL_TYPE_CODE"):
            assert df[col].dtype.name == "category", (
                f"{col} should be category, got {df[col].dtype}"
            )

    def test_extract_parses_csv_from_zip(self, tmp_path: Path):
        """_extract_and_parse correctly reads CSV from zip bytes."""
        zip_bytes = _make_test_zip(4)
        acquirer = BoreholeDataAcquirer(local_data_dir=tmp_path)

        df = acquirer._extract_and_parse(zip_bytes)

        assert df is not None
        assert len(df) == 4
        # Raw extraction should have all 26 columns
        assert len(df.columns) == 26

    def test_returns_none_when_no_downloader_and_no_cache(
        self, tmp_path: Path
    ):
        """Graceful None when no downloader is set and no cache exists."""
        acquirer = BoreholeDataAcquirer(
            downloader=None, local_data_dir=tmp_path
        )

        result = acquirer.acquire_borehole_dataframe()

        assert result is None

    def test_cache_freshness_check(self, tmp_path: Path):
        """Stale cache (>30 days) triggers a re-download."""
        zip_bytes = _make_test_zip(2)
        local_dir = tmp_path / ".local"
        _seed_cache(local_dir / "borehole", zip_bytes, age_days=31)

        downloader = _FakeDownloader(zip_bytes)
        acquirer = BoreholeDataAcquirer(
            downloader=downloader, local_data_dir=local_dir
        )

        df = acquirer.acquire_borehole_dataframe()

        assert df is not None
        assert len(downloader.calls) == 1, (
            "Stale cache should trigger download"
        )

    def test_keeps_only_relevant_columns(self, tmp_path: Path):
        """Columns not in _KEEP_COLUMNS are dropped after normalisation."""
        zip_bytes = _make_test_zip(2)
        local_dir = tmp_path / ".local"
        _seed_cache(local_dir / "borehole", zip_bytes)

        acquirer = BoreholeDataAcquirer(local_data_dir=local_dir)
        df = acquirer.acquire_borehole_dataframe()

        # Every column in result must be in _KEEP_COLUMNS
        for col in df.columns:
            assert col in _KEEP_COLUMNS, f"Unexpected column: {col}"

        # Columns that were in the raw data but NOT in _KEEP_COLUMNS
        # should be absent
        dropped = {
            "WELL_TD_SS",
            "RKB_ELEVATION",
            "WELL_BP_ST_KICKOFF_MD",
            "BOREHOLE_STAT_DT",
            "CASING_CUT_CODE",
            "UNDWTR_COMP_STUB",
            "SURF_LEASE_NUMBER",
            "REGION_CODE",
        }
        for col in dropped:
            assert col not in df.columns, f"{col} should have been dropped"
