"""BOEM (Bureau of Ocean Energy Management) data collector.

Downloads platform structures CSV and drilling permit data from
data.boem.gov. All data is publicly available.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Optional

import pandas as pd

from worldenergydata.vessel_fleet.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

_BOEM_PLATFORM_URL = "https://www.data.boem.gov/Platform/PlatformStructures/Default.aspx"
_BOEM_DRILLING_PERMIT_URL = "https://www.data.boem.gov/Permit/APD/Default.aspx"


class BOEMCollector(BaseCollector):
    """Collect platform and drilling data from BOEM Data Center."""

    def __init__(self) -> None:
        super().__init__(
            name="boem",
            rate_limit=0.5,
            cache_ttl=86400.0,
        )

    def collect(self) -> list[dict[str, Any]]:
        """Not used directly — call specific methods."""
        return []

    def download_platform_structures(
        self,
        csv_url: Optional[str] = None,
    ) -> pd.DataFrame:
        """Download BOEM platform structures data as DataFrame.

        The CSV is available at data.boem.gov. Returns an empty
        DataFrame on failure.
        """
        url = csv_url or _BOEM_PLATFORM_URL
        try:
            content = self.get_text(url)
            df = pd.read_csv(io.StringIO(content))
            logger.info("Downloaded %d platform records from BOEM", len(df))
            return df
        except Exception as exc:
            logger.warning("BOEM platform download failed: %s", exc)
            return pd.DataFrame()

    def get_active_platforms_by_area(
        self,
        df: pd.DataFrame,
        area_code: str,
    ) -> pd.DataFrame:
        """Filter platform structures by area code."""
        if df.empty:
            return df
        col = "AREA_CODE" if "AREA_CODE" in df.columns else df.columns[0]
        return df[df[col].astype(str) == area_code]
