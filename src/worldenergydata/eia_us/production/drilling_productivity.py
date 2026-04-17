"""DPR (Drilling Productivity Report) loader — rig count, new well IP, legacy decline.

EIA publishes the DPR monthly for seven major tight-oil/shale-gas regions.
This module provides helpers to load and summarise DPR data by region.

Note: The core per-basin data model lives in basin_production.py.
This module provides higher-level summaries across regions.
"""

import logging
from typing import Any, Dict, List

import pandas as pd

from .basin_production import DPR_BASINS, BasinProductionLoader

logger = logging.getLogger(__name__)


class DrillingProductivityReport:
    """High-level DPR aggregator across all EIA regions."""

    def __init__(self) -> None:
        self._loader = BasinProductionLoader()

    def load_all_basins(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Load DPR records for all basins into a single DataFrame.

        Args:
            records: Combined records across all basins.

        Returns:
            Normalised DataFrame with basin column.
        """
        return self._loader.load(records)

    def rig_count_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return latest rig count by basin, sorted descending.

        Args:
            df: Normalised DPR DataFrame from load_all_basins().

        Returns:
            DataFrame with columns: basin, period, rig_count.
        """
        if df.empty:
            return pd.DataFrame(columns=["basin", "period", "rig_count"])

        idx = df.groupby("basin")["period"].idxmax()
        latest = df.loc[idx, ["basin", "period", "rig_count"]].copy()
        return latest.sort_values("rig_count", ascending=False).reset_index(drop=True)

    def net_change_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return net production change (new IP + legacy decline) per basin-period.

        Args:
            df: Normalised DPR DataFrame.

        Returns:
            DataFrame with columns: basin, period, net_change_bopd.
        """
        if df.empty:
            return pd.DataFrame(columns=["basin", "period", "net_change_bopd"])

        result = df[["basin", "period"]].copy()
        result["net_change_bopd"] = df["new_well_ip_bopd"] + df["legacy_decline_bopd"]
        return result.reset_index(drop=True)
