"""Platform data loader from binary files."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from loguru import logger

from worldenergydata.common.data_resolver import get_module_data_safe


class PlatformLoader:
    """Load platform structure data from binary files."""

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self._bin_dir = str(get_module_data_safe("bsee") / "bin" / "platform")

    def _load_data(self, cfg: Optional[Dict] = None) -> Optional[pd.DataFrame]:
        """Load platform data from binary file."""
        if self.data is not None:
            return self.data
        try:
            bin_path = Path(self._bin_dir)
            if cfg:
                custom_path = (
                    cfg.get("parameters", {})
                    .get("filepath", {})
                    .get("platform", {})
                    .get("bin")
                )
                if custom_path:
                    bin_path = Path(custom_path)

            bin_files = list(bin_path.glob("*.bin"))
            if not bin_files:
                logger.warning(f"No platform binary files found in {bin_path}")
                return None

            frames = []
            for bf in bin_files:
                with open(bf, "rb") as f:
                    df = pickle.load(f)  # nosec B301
                    if isinstance(df, pd.DataFrame):
                        frames.append(df)

            if frames:
                self.data = pd.concat(frames, ignore_index=True)
                logger.info(f"Loaded {len(self.data)} platform records")
                return self.data
            return None
        except Exception as e:
            logger.error(f"Error loading platform data: {str(e)}")
            return None

    def get_platforms_by_area_block(
        self, area_code: str, block_number: str, cfg: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """Get platforms by OCS area and block."""
        df = self._load_data(cfg)
        if df is None:
            return None
        mask = (df["AREA_CODE"] == area_code) & (
            df["BLOCK_NUMBER"] == str(block_number)
        )
        result = df[mask]
        logger.info(f"Found {len(result)} platforms in {area_code} {block_number}")
        return result if not result.empty else None

    def get_platforms_by_complex(
        self, complex_id: str, cfg: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """Get all platforms in a complex."""
        df = self._load_data(cfg)
        if df is None:
            return None
        mask = df["COMPLEX_ID_NUM"] == str(complex_id)
        result = df[mask]
        logger.info(f"Found {len(result)} platforms in complex {complex_id}")
        return result if not result.empty else None

    def get_infrastructure_by_lease(
        self, lease_number: str, cfg: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """Get platform infrastructure by lease number."""
        df = self._load_data(cfg)
        if df is None:
            return None
        mask = df["LEASE_NUMBER"] == str(lease_number)
        result = df[mask]
        logger.info(f"Found {len(result)} structures for lease {lease_number}")
        return result if not result.empty else None
