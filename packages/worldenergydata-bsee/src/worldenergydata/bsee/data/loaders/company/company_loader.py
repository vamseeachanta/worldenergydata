# ABOUTME: BSEE company/operator data loader from pickled binary files (WRK-1231).
# ABOUTME: Loads active and all companies, filters by operator ID, name, and region.

"""BSEE company/operator data loader.

Loads company hierarchy data from pickled binary files downloaded via
the BSEE data refresh pipeline (url_registry.py companydetails spec).

Binary files:
  - mv_companies_active.bin: 3,069 active operators (20 columns)
  - mv_companies_all.bin: 3,841 all operators incl. terminated (21 columns)
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

_DEFAULT_BIN_DIR = str(get_module_data_safe("bsee") / "bin" / "companydetails")

_REGION_COL_MAP = {
    "GOM": "GOM_REGION_CODE",
    "PAC": "PAC_REGION_CODE",
    "ALASKA": "ALASKA_RGN_CODE",
    "ATL": "ATL_REGION_CODE",
}


class CompanyLoader:
    """Load BSEE company/operator data from pickled binary files.

    Args:
        bin_dir: Path to directory containing company .bin files.
                 Defaults to data/modules/bsee/bin/companydetails.
    """

    def __init__(self, bin_dir: Optional[Union[str, Path]] = None) -> None:
        self._bin_dir = str(bin_dir) if bin_dir else _DEFAULT_BIN_DIR
        self._active_cache: Optional[pd.DataFrame] = None
        self._all_cache: Optional[pd.DataFrame] = None

    def _load_bin(self, filename: str) -> Optional[pd.DataFrame]:
        """Load a single pickled DataFrame from bin_dir."""
        path = Path(self._bin_dir) / filename
        if not path.exists():
            logger.warning("Binary file not found: %s", path)
            return None
        with open(path, "rb") as f:
            obj = pickle.load(f)  # nosec B301
        if isinstance(obj, pd.DataFrame):
            logger.info("Loaded %d records from %s", len(obj), path.name)
            return obj
        logger.warning("Unexpected type in %s: %s", path.name, type(obj).__name__)
        return None

    def load_active(self) -> Optional[pd.DataFrame]:
        """Load active companies. Cached after first call."""
        if self._active_cache is not None:
            return self._active_cache
        self._active_cache = self._load_bin("mv_companies_active.bin")
        return self._active_cache

    def load_all(self) -> Optional[pd.DataFrame]:
        """Load all companies (active + terminated). Cached after first call."""
        if self._all_cache is not None:
            return self._all_cache
        self._all_cache = self._load_bin("mv_companies_all.bin")
        return self._all_cache

    def get_by_operator_id(self, operator_id: int) -> pd.DataFrame:
        """Find company by MMS_COMPANY_NUM.

        Args:
            operator_id: The BSEE/BOEM company number.

        Returns:
            DataFrame of matching rows (may be empty).
        """
        df = self.load_active()
        if df is None:
            return pd.DataFrame()
        return df[df["MMS_COMPANY_NUM"] == operator_id].reset_index(drop=True)

    def get_by_company_name(self, name: str) -> pd.DataFrame:
        """Search companies by name (case-insensitive partial match).

        Args:
            name: Search string to match against BUS_ASC_NAME.

        Returns:
            DataFrame of matching rows (may be empty).
        """
        df = self.load_active()
        if df is None:
            return pd.DataFrame()
        mask = df["BUS_ASC_NAME"].str.contains(name, case=False, na=False)
        return df[mask].reset_index(drop=True)

    def get_by_region(self, region: str) -> pd.DataFrame:
        """Filter companies by OCS region code.

        Args:
            region: One of 'GOM', 'PAC', 'ALASKA', 'ATL'.

        Returns:
            DataFrame of companies active in that region.
        """
        col = _REGION_COL_MAP.get(region.upper())
        if not col:
            logger.warning("Unknown region: %s (use GOM, PAC, ALASKA, ATL)", region)
            return pd.DataFrame()
        df = self.load_active()
        if df is None:
            return pd.DataFrame()
        return df[df[col].notna()].reset_index(drop=True)
