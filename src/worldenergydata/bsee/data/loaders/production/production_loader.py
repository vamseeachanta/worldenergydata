# ABOUTME: BSEE production data loader from pickled binary files (WRK-1232).
# ABOUTME: Loads monthly production, filters by lease/year, provides annual summaries.

"""BSEE production data loader.

Loads monthly oil/gas/water production data from pickled binary files.
Data source: BSEE ProductionRawData.zip → mv_productiondata.bin

Binary files (production_raw/):
  - mv_productiondata.bin: 867K rows, monthly lease-level production
  - mv_productionsum.bin: summarized production
  - mv_production_waterdepth.bin: water depth per lease
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

_DEFAULT_BIN_DIR = "data/modules/bsee/bin/production_raw"


class ProductionLoader:
    """Load BSEE monthly production data from pickled binary files.

    Args:
        bin_dir: Path to directory containing production .bin files.
    """

    def __init__(self, bin_dir: Optional[Union[str, Path]] = None) -> None:
        self._bin_dir = str(bin_dir) if bin_dir else _DEFAULT_BIN_DIR
        self._cache: Optional[pd.DataFrame] = None

    def _load_bin(self, filename: str) -> Optional[pd.DataFrame]:
        """Load a single pickled DataFrame."""
        path = Path(self._bin_dir) / filename
        if not path.exists():
            logger.warning("Binary file not found: %s", path)
            return None
        with open(path, "rb") as f:
            obj = pickle.load(f)  # nosec B301
        if isinstance(obj, pd.DataFrame):
            logger.info("Loaded %d production records from %s", len(obj), path.name)
            return obj
        return None

    def load(self) -> Optional[pd.DataFrame]:
        """Load main production data. Cached after first call."""
        if self._cache is not None:
            return self._cache
        self._cache = self._load_bin("mv_productiondata.bin")
        return self._cache

    def get_by_lease(self, lease_number: str) -> pd.DataFrame:
        """Get all production records for a lease."""
        df = self.load()
        if df is None:
            return pd.DataFrame()
        return df[df["LEASE_NUMBER"] == lease_number].reset_index(drop=True)

    def get_by_year(self, year: int) -> pd.DataFrame:
        """Get all production records for a year."""
        df = self.load()
        if df is None:
            return pd.DataFrame()
        return df[df["PROD_YEAR"] == year].reset_index(drop=True)

    def get_by_lease_and_year(self, lease_number: str, year: int) -> pd.DataFrame:
        """Get production for a specific lease and year."""
        df = self.load()
        if df is None:
            return pd.DataFrame()
        mask = (df["LEASE_NUMBER"] == lease_number) & (df["PROD_YEAR"] == year)
        return df[mask].reset_index(drop=True)

    def annual_summary(self, year: int) -> Dict[str, Any]:
        """Compute annual production summary.

        Returns:
            Dict with total_oil_bbl, total_gas_mcf, total_water_bbl,
            lease_count for the given year.
        """
        df = self.get_by_year(year)
        if df.empty:
            return {
                "year": year,
                "total_oil_bbl": 0,
                "total_gas_mcf": 0,
                "total_water_bbl": 0,
                "lease_count": 0,
            }
        return {
            "year": year,
            "total_oil_bbl": df["LEASE_OIL_PROD"].sum(),
            "total_gas_mcf": df["LEASE_GWG_PROD"].sum(),
            "total_water_bbl": df["LEASE_WTR_PROD"].sum(),
            "lease_count": df["LEASE_NUMBER"].nunique(),
        }
