"""Buckskin field data extractor -- filters BSEE datasets to KC blocks.

Buckskin spans Keathley Canyon (KC) blocks 785, 828, 829, 830, 871, 872.
Each ``extract_*`` method loads a pickled ``.bin`` file and returns only
the rows that belong to the Buckskin field.  Supports both block-based
and BOEM lease-number-based filtering.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from .buckskin_config import BUCKSKIN

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WAR zip helper (module-level so tests can mock it)
# ---------------------------------------------------------------------------


def load_war_from_zip(path: Path) -> pd.DataFrame:
    """Read the WAR main table from the eWellWARRawData zip archive.

    The zip contains CSV-like ``.txt`` files.  We read ``mv_war_main.txt``
    which has columns including BOTM_AREA_CODE, BOTM_BLOCK_NUM, etc.
    """
    target = "eWellWARRawData/mv_war_main.txt"
    with zipfile.ZipFile(path) as zf:
        with zf.open(target) as f:
            return pd.read_csv(f, low_memory=False, dtype=str)


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class BuckskinExtractor:
    """Extract and filter BSEE datasets for the Buckskin field."""

    BLOCKS: list[int] = list(BUCKSKIN.blocks)
    AREA_CODE: str = BUCKSKIN.area_code

    _REAL_PATHS: dict[str, str] = {
        "production": "production_raw/mv_productiondata.bin",
        "production_sum": "production_raw/mv_productionsum.bin",
        "wells": "apiraw/mv_api_list.bin",
        "wells_all": "apiraw/mv_api_list_all.bin",
        "leases": "lab/mv_lease_area_block.bin",
        "completions": "apiraw/mv_api_wellcomps.bin",
        "completions_all": "apiraw/mv_api_wellcomps_all.bin",
    }

    def __init__(
        self,
        bin_dir: Path,
        war_zip_path: Path | None = None,
    ) -> None:
        self._bin_dir = Path(bin_dir)
        self._war_zip_path = war_zip_path

    # -- public API ---------------------------------------------------------

    def extract_production(self) -> pd.DataFrame:
        """Load production data and filter to Buckskin blocks."""
        df = self._load_bin("production")
        if df.empty:
            return df
        return self._filter_botm(df)

    def extract_wells(self) -> pd.DataFrame:
        """Load well data and filter to Buckskin blocks or leases.

        Tries ``wells_all`` first (larger dataset), then ``wells``.
        Uses lease-based filtering if ``BOTM_LEASE_NUMBER`` exists,
        falling back to block-based filtering.
        """
        df = self._load_bin("wells_all")
        if df.empty:
            df = self._load_bin("wells")
        if df.empty:
            return df
        result = self._filter_by_lease(df)
        if result.empty:
            result = self._filter_botm(df)
        return result

    def extract_war_activity(self) -> pd.DataFrame:
        """Load WAR activity data and filter to Buckskin blocks."""
        if self._war_zip_path is not None:
            df = load_war_from_zip(self._war_zip_path)
            df = self._strip_strings(df)
        else:
            df = self._load_bin("war_activity")
        if df.empty:
            return df
        return self._filter_botm(df)

    def extract_leases(self) -> pd.DataFrame:
        """Load lease data and filter to Buckskin blocks."""
        df = self._load_bin("leases")
        if df.empty:
            return df
        mask = (df["AREA_CODE"] == self.AREA_CODE) & (
            df["BLOCK_NUM"].isin(self._block_set())
        )
        return df.loc[mask].reset_index(drop=True)

    def extract_completions(self) -> pd.DataFrame:
        """Load completions filtered to wells that are in Buckskin."""
        wells = self.extract_wells()
        if wells.empty:
            return pd.DataFrame()
        api_set = set(wells["API_WELL_NUMBER"].unique())
        df = self._load_bin("completions_all")
        if df.empty:
            df = self._load_bin("completions")
        if df.empty:
            return df
        return df.loc[df["API_WELL_NUMBER"].isin(api_set)].reset_index(drop=True)

    def extract_production_for_decline(self) -> pd.DataFrame:
        """Load production data suitable for decline curve analysis.

        Tries ``production`` (monthly) first, then ``production_sum``
        (annual totals).  Returns the full filtered DataFrame.
        """
        df = self._load_bin("production")
        if df.empty:
            df = self._load_bin("production_sum")
        if df.empty:
            return df
        result = self._filter_by_lease(df)
        if result.empty:
            result = self._filter_botm(df)
        return result

    def boem_lease_table(self) -> pd.DataFrame:
        """Return the BOEM lease mapping as a DataFrame."""
        rows = []
        for ocs_id, blocks in BUCKSKIN.boem_leases.items():
            rows.append({"BOEM_OCS_Lease": ocs_id, "Blocks": blocks})
        return pd.DataFrame(rows)

    def extract_all(self) -> dict[str, pd.DataFrame]:
        """Return all Buckskin datasets as a dictionary."""
        return {
            "production": self.extract_production(),
            "wells": self.extract_wells(),
            "war_activity": self.extract_war_activity(),
            "leases": self.extract_leases(),
            "completions": self.extract_completions(),
        }

    # -- private helpers ----------------------------------------------------

    def _load_bin(self, key: str) -> pd.DataFrame:
        """Load a pickled DataFrame, trying real path then generic name."""
        for path in self._candidate_paths(key):
            if path.exists():
                logger.debug("Loading %s from %s", key, path)
                return self._read_pickle_safe(path)
        logger.warning("No file found for %s in %s", key, self._bin_dir)
        return pd.DataFrame()

    def _candidate_paths(self, key: str) -> list[Path]:
        """Return ordered list of paths to try for *key*."""
        paths: list[Path] = []
        real_rel = self._REAL_PATHS.get(key)
        if real_rel is not None:
            paths.append(self._bin_dir / real_rel)
        paths.append(self._bin_dir / f"{key}.bin")
        return paths

    def _read_pickle_safe(self, path: Path) -> pd.DataFrame:
        """Read a pickle file, returning empty DataFrame on failure."""
        try:
            df = pd.read_pickle(path)  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input
        except Exception as exc:
            logger.warning(
                "Cannot unpickle %s: %s (file may be a Git LFS pointer)", path, exc
            )
            return pd.DataFrame()
        if not isinstance(df, pd.DataFrame):
            logger.warning("%s is not a DataFrame", path)
            return pd.DataFrame()
        return self._strip_strings(df)

    @staticmethod
    def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace and quotes from all object columns."""
        for col in df.select_dtypes(include="object"):
            df[col] = df[col].str.strip().str.strip('"')
        return df

    def _block_set(self) -> set[Any]:
        """Return BLOCKS as a set containing both int and str forms."""
        s: set[Any] = set()
        for b in self.BLOCKS:
            s.add(b)
            s.add(str(b))
        return s

    def _filter_by_lease(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter by BOEM lease number columns if available."""
        lease_set = BUCKSKIN.lease_set()
        for col in ("BOTM_LEASE_NUMBER", "TRIM_LEASE_NUM", "LEASE_NUMBER"):
            if col in df.columns:
                mask = df[col].isin(lease_set)
                result = df.loc[mask].reset_index(drop=True)
                if not result.empty:
                    logger.debug("Filtered %d rows via %s", len(result), col)
                    return result
        return pd.DataFrame()

    def _filter_botm(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter on BOTM_AREA_CODE / BOTM_BLOCK_NUM for Buckskin."""
        if "BOTM_AREA_CODE" not in df.columns or "BOTM_BLOCK_NUM" not in df.columns:
            return pd.DataFrame()
        mask = (df["BOTM_AREA_CODE"] == self.AREA_CODE) & (
            df["BOTM_BLOCK_NUM"].isin(self._block_set())
        )
        return df.loc[mask].reset_index(drop=True)
