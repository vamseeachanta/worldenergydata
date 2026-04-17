"""Baker Hughes rig count data collector.

Downloads weekly rig count data from rigcount.bakerhughes.com.
Publicly available Excel files with international and North American
rig counts by region, type, and basin.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Optional

import pandas as pd

from worldenergydata.vessel_fleet.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

_BH_NA_URL = "https://rigcount.bakerhughes.com/static-files/na-702b0e93-5e46-4a5c-8ba2-e11cd1e14d49"
_BH_INTL_URL = "https://rigcount.bakerhughes.com/static-files/intl-a0e5dc74-c07b-4c84-a93e-a8f12a3dce80"


class BakerHughesCollector(BaseCollector):
    """Collect rig count data from Baker Hughes."""

    def __init__(self) -> None:
        super().__init__(
            name="baker_hughes",
            rate_limit=0.5,
            cache_ttl=86400.0 * 7,  # Weekly data
        )

    def collect(self) -> list[dict[str, Any]]:
        """Not used directly — call specific methods."""
        return []

    def download_na_rig_count(
        self,
        url: Optional[str] = None,
    ) -> pd.DataFrame:
        """Download North American rig count Excel."""
        target = url or _BH_NA_URL
        try:
            content = self.get_bytes(target)
            df = pd.read_excel(io.BytesIO(content))
            logger.info(
                "Downloaded NA rig count: %d rows x %d cols",
                len(df),
                len(df.columns),
            )
            return df
        except Exception as exc:
            logger.warning("Baker Hughes NA download failed: %s", exc)
            return pd.DataFrame()

    def download_international_rig_count(
        self,
        url: Optional[str] = None,
    ) -> pd.DataFrame:
        """Download international rig count Excel."""
        target = url or _BH_INTL_URL
        try:
            content = self.get_bytes(target)
            df = pd.read_excel(io.BytesIO(content))
            logger.info(
                "Downloaded international rig count: %d rows x %d cols",
                len(df),
                len(df.columns),
            )
            return df
        except Exception as exc:
            logger.warning("Baker Hughes international download failed: %s", exc)
            return pd.DataFrame()
