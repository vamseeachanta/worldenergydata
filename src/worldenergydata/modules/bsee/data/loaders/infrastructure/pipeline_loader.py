"""Pipeline data loader from binary files."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from loguru import logger


class PipelineLoader:
    """Load pipeline permit and location data from binary files."""

    def __init__(self):
        self.permit_data: Optional[pd.DataFrame] = None
        self.location_data: Optional[pd.DataFrame] = None
        self._permit_bin_dir = "data/modules/bsee/bin/pipeline_permit"
        self._location_bin_dir = "data/modules/bsee/bin/pipeline_location"

    def _load_permit_data(self, cfg: Optional[Dict] = None) -> Optional[pd.DataFrame]:
        """Load pipeline permit data from binary file."""
        if self.permit_data is not None:
            return self.permit_data
        try:
            bin_path = Path(self._permit_bin_dir)
            if cfg:
                custom_path = (
                    cfg.get("parameters", {})
                    .get("filepath", {})
                    .get("pipeline_permit", {})
                    .get("bin")
                )
                if custom_path:
                    bin_path = Path(custom_path)

            bin_files = list(bin_path.glob("*.bin"))
            if not bin_files:
                logger.warning(f"No pipeline permit binary files found in {bin_path}")
                return None

            frames = []
            for bf in bin_files:
                with open(bf, "rb") as f:
                    df = pickle.load(f)  # nosec B301
                    if isinstance(df, pd.DataFrame):
                        frames.append(df)

            if frames:
                self.permit_data = pd.concat(frames, ignore_index=True)
                logger.info(f"Loaded {len(self.permit_data)} pipeline permit records")
                return self.permit_data
            return None
        except Exception as e:
            logger.error(f"Error loading pipeline permit data: {str(e)}")
            return None

    def _load_location_data(self, cfg: Optional[Dict] = None) -> Optional[pd.DataFrame]:
        """Load pipeline location data from binary file."""
        if self.location_data is not None:
            return self.location_data
        try:
            bin_path = Path(self._location_bin_dir)
            if cfg:
                custom_path = (
                    cfg.get("parameters", {})
                    .get("filepath", {})
                    .get("pipeline_location", {})
                    .get("bin")
                )
                if custom_path:
                    bin_path = Path(custom_path)

            bin_files = list(bin_path.glob("*.bin"))
            if not bin_files:
                logger.warning(f"No pipeline location binary files found in {bin_path}")
                return None

            frames = []
            for bf in bin_files:
                with open(bf, "rb") as f:
                    df = pickle.load(f)  # nosec B301
                    if isinstance(df, pd.DataFrame):
                        frames.append(df)

            if frames:
                self.location_data = pd.concat(frames, ignore_index=True)
                logger.info(
                    f"Loaded {len(self.location_data)} pipeline location records"
                )
                return self.location_data
            return None
        except Exception as e:
            logger.error(f"Error loading pipeline location data: {str(e)}")
            return None

    def get_pipelines_by_status(
        self, status_code: str, cfg: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """Get pipelines by status code."""
        df = self._load_permit_data(cfg)
        if df is None:
            return None
        mask = df["STATUS_CODE"] == status_code
        result = df[mask]
        logger.info(f"Found {len(result)} pipelines with status {status_code}")
        return result if not result.empty else None

    def get_infrastructure_by_lease(
        self, lease_number: str, cfg: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """Get pipeline infrastructure by lease number."""
        df = self._load_permit_data(cfg)
        if df is None:
            return None
        mask = df["LEASE_NUMBER"] == str(lease_number)
        result = df[mask]
        logger.info(f"Found {len(result)} pipeline permits for lease {lease_number}")
        return result if not result.empty else None
