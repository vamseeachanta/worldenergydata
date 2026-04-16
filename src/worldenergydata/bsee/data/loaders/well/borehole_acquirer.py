"""Borehole data acquisition with download caching.

Downloads BoreholeRawData.zip from BSEE, extracts mv_boreholes_all.txt,
normalises columns, and returns a DataFrame.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from worldenergydata.bsee.data.utils.api_well_normalizer import (
    normalize_api_well_number,
)
from worldenergydata.common.data_resolver import get_module_data_safe

_DEFAULT_LOCAL_DIR = get_module_data_safe("bsee") / ".local"
_CACHE_FILENAME = "BoreholeRawData.zip"
_CACHE_MAX_AGE_DAYS = 30
_SOURCE_URL = "https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip"

# Columns to keep from the borehole data
_KEEP_COLUMNS = [
    "API_WELL_NUMBER",
    "WELL_NAME",
    "WELL_NAME_SUFFIX",
    "BOTM_LEASE_NUMBER",
    "BOTM_AREA_CODE",
    "BOTM_BLOCK_NUMBER",
    "COMPANY_NAME",
    "WELL_SPUD_DATE",
    "BH_TOTAL_MD",
    "WELL_BORE_TVD",
    "TOTAL_DEPTH_DATE",
    "BOREHOLE_STAT_CD",
    "WATER_DEPTH",
    "WELL_TYPE_CODE",
    "SURF_LATITUDE",
    "SURF_LONGITUDE",
    "BOTM_LATITUDE",
    "BOTM_LONGITUDE",
]


class BoreholeDataAcquirer:
    """Download and normalise BSEE borehole data.

    Uses dependency injection for downloader so tests can supply mocks
    without hitting the network.

    Args:
        downloader: Object with a ``download(url)`` method returning bytes.
        local_data_dir: Root of the .local/ cache directory.
    """

    def __init__(
        self,
        downloader=None,
        local_data_dir: Optional[Path] = None,
    ):
        self._downloader = downloader
        self._local_dir = local_data_dir or _DEFAULT_LOCAL_DIR
        self._cache_dir = self._local_dir / "borehole"

    def acquire_borehole_dataframe(self) -> Optional[pd.DataFrame]:
        """Download borehole zip, extract, parse, and normalise.

        Returns:
            DataFrame with normalised columns, or None on failure.
        """
        zip_data = self._get_zip_data()
        if zip_data is None:
            return None

        df = self._extract_and_parse(zip_data)
        if df is None:
            return None

        return self._normalize(df)

    def _get_zip_data(self) -> Optional[bytes]:
        """Return zip bytes, using cache when available."""
        cached = self._load_from_cache()
        if cached is not None:
            logger.info("Using cached borehole zip data")
            return cached

        if self._downloader is None:
            logger.error("No downloader provided and no cache available")
            return None

        logger.info("Downloading borehole data from BSEE...")
        zip_data = self._downloader.download(_SOURCE_URL)
        if zip_data is None:
            logger.error("Borehole download failed")
            return None

        self._save_to_cache(zip_data)
        return zip_data

    def _extract_and_parse(self, zip_data: bytes) -> Optional[pd.DataFrame]:
        """Extract mv_boreholes_all.txt from zip and parse as CSV."""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                txt_files = [n for n in zf.namelist() if n.endswith(".txt")]
                if not txt_files:
                    logger.error("No .txt files found in borehole zip")
                    return None
                target = txt_files[0]
                with zf.open(target) as f:
                    df = pd.read_csv(f, low_memory=False)
            logger.info(f"Parsed {len(df)} borehole records from {target}")
            return df
        except Exception as e:
            logger.error(f"Failed to parse borehole zip: {e}")
            return None

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column types and select relevant columns."""
        # Keep only columns we need (that exist)
        keep = [c for c in _KEEP_COLUMNS if c in df.columns]
        df = df[keep].copy()

        # Normalize API_WELL_NUMBER to string
        df["API_WELL_NUMBER"] = normalize_api_well_number(
            df["API_WELL_NUMBER"]
        )

        # Parse dates
        for col in ("WELL_SPUD_DATE", "TOTAL_DEPTH_DATE"):
            if col in df.columns:
                df[col] = pd.to_datetime(
                    df[col], format="mixed", dayfirst=False, errors="coerce"
                )

        # Numeric columns to float32
        for col in ("BH_TOTAL_MD", "WELL_BORE_TVD", "WATER_DEPTH"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(
                    "float32"
                )

        # Coordinates to float
        for col in (
            "SURF_LATITUDE",
            "SURF_LONGITUDE",
            "BOTM_LATITUDE",
            "BOTM_LONGITUDE",
        ):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Categorical columns
        for col in ("BOREHOLE_STAT_CD", "BOTM_AREA_CODE", "WELL_TYPE_CODE"):
            if col in df.columns:
                df[col] = df[col].astype("category")

        return df

    def _load_from_cache(self) -> Optional[bytes]:
        """Load cached zip if it exists and is fresh."""
        cache_file = self._cache_dir / _CACHE_FILENAME
        meta_file = self._cache_dir / "download_metadata.json"

        if not cache_file.exists():
            return None

        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                downloaded_at = datetime.fromisoformat(meta["downloaded_at"])
                age_days = (
                    datetime.now(tz=timezone.utc) - downloaded_at
                ).days
                if age_days > _CACHE_MAX_AGE_DAYS:
                    logger.info(
                        f"Cached borehole data is {age_days} days old "
                        f"(max {_CACHE_MAX_AGE_DAYS}), re-downloading"
                    )
                    return None
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        return cache_file.read_bytes()

    def _save_to_cache(self, zip_data: bytes) -> None:
        """Write zip data and metadata to cache directory."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_dir / _CACHE_FILENAME
        cache_file.write_bytes(zip_data)

        meta = {
            "downloaded_at": datetime.now(tz=timezone.utc).isoformat(),
            "size_bytes": len(zip_data),
            "checksum_sha256": hashlib.sha256(zip_data).hexdigest(),
            "source_url": _SOURCE_URL,
        }
        meta_file = self._cache_dir / "download_metadata.json"
        meta_file.write_text(json.dumps(meta, indent=2))
        logger.info(
            f"Cached borehole zip ({len(zip_data)} bytes) to {cache_file}"
        )
