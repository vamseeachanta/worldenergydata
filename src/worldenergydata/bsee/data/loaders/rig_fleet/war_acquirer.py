"""WAR data acquisition with download caching.

Downloads the full BSEE WAR zip via BSEEWebScraper, extracts via
MemoryProcessor, normalises column names, and returns a merged DataFrame.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from worldenergydata.common.data_resolver import DataNotFoundError, get_module_data

try:
    _DEFAULT_LOCAL_DIR = get_module_data("bsee") / ".local"
except DataNotFoundError:
    _DEFAULT_LOCAL_DIR = Path("data/modules/bsee/.local")

# Column rename map: WAR raw names -> standardised names
_COLUMN_RENAME_MAP: dict[str, str] = {
    "BOTM_AREA_CODE": "AREA_CODE",
    "BOTM_BLOCK_NUMBER": "BLOCK_NUMBER",
    "WAR_RPT_START_DT": "WAR_START_DT",
    "WAR_RPT_END_DT": "WAR_END_DT",
}

_CACHE_FILENAME = "eWellWARRawData.zip"
_CACHE_MAX_AGE_DAYS = 30


class WARDataAcquirer:
    """Download and normalise WAR data for rig fleet extraction.

    Uses dependency injection for scraper and processor so that tests
    can supply mocks without hitting the network.

    Args:
        scraper: BSEEWebScraper instance (or mock).
        processor: MemoryProcessor instance (or mock).
        local_data_dir: Root of the .local/ cache directory.
    """

    def __init__(
        self,
        scraper,
        processor,
        local_data_dir: Optional[Path] = None,
    ):
        self._scraper = scraper
        self._processor = processor
        self._local_dir = local_data_dir or _DEFAULT_LOCAL_DIR
        self._cache_dir = self._local_dir / "war"

    def acquire_war_dataframe(self) -> Optional[pd.DataFrame]:
        """Download full WAR zip, extract, merge, and normalise.

        Returns:
            Merged DataFrame with normalised column names,
            or None on failure.
        """
        zip_data = self._get_zip_data()
        if zip_data is None:
            return None

        dataframes = self._processor.process_zip_in_memory(zip_data)
        if not dataframes:
            logger.warning("Processor returned no DataFrames from WAR zip")
            return None

        merged = pd.concat(dataframes.values(), ignore_index=True)
        logger.info(
            f"Merged {len(dataframes)} WAR files -> {len(merged)} total rows"
        )

        return self._normalize_columns(merged)

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename WAR-specific column names to standard names.

        Only renames columns that exist in the DataFrame; missing
        columns are silently skipped.
        """
        rename = {
            old: new
            for old, new in _COLUMN_RENAME_MAP.items()
            if old in df.columns
        }
        if rename:
            df = df.rename(columns=rename)
        return df

    def _get_zip_data(self) -> Optional[bytes]:
        """Return WAR zip bytes, using cache when available."""
        cached = self._load_from_cache()
        if cached is not None:
            logger.info("Using cached WAR zip data")
            return cached

        logger.info("Downloading WAR data from BSEE...")
        zip_data = self._scraper.download_war_data()
        if zip_data is None:
            logger.error("WAR download failed")
            return None

        self._save_to_cache(zip_data)
        return zip_data

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
                        f"Cached WAR data is {age_days} days old "
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
            "source_url": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
        }
        meta_file = self._cache_dir / "download_metadata.json"
        meta_file.write_text(json.dumps(meta, indent=2))
        logger.info(f"Cached WAR zip ({len(zip_data)} bytes) to {cache_file}")
