"""Load drilling riser component data from curated dataset.

Provides query interface for riser joints, BOPs, LMRPs, flex joints,
and telescopic joints by component type, size, and pressure rating.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Curated data ships INSIDE this member as package data (ADR 0001 Phase 2,
# batch 4, #529 — option (i): data travels with the package). See
# construction_vessel_loader for the resolution rationale.
_DATA_DIR = Path(__file__).resolve().parent.parent / "_data" / "curated"
_DEFAULT_FILE = "drilling_riser_components.csv"

VALID_COMPONENT_TYPES = (
    "riser_joint",
    "bop",
    "lmrp",
    "flex_joint",
    "telescopic_joint",
)


class DrillingRiserLoader:
    """Query drilling riser component data from the curated dataset.

    Loads riser components from CSV storage and provides query methods
    by component type, size, and pressure rating.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _DATA_DIR
        self._df: Optional[pd.DataFrame] = None

    def load(self) -> pd.DataFrame:
        """Load curated drilling riser component data (lazy, cached)."""
        if self._df is not None:
            return self._df

        csv_path = self._data_dir / _DEFAULT_FILE
        if not csv_path.exists():
            logger.warning("Drilling riser data not found: %s", csv_path)
            self._df = pd.DataFrame()
            return self._df

        df = pd.read_csv(csv_path)
        self._df = df
        logger.info("Loaded %d drilling riser components", len(df))
        return self._df

    def get_by_id(self, component_id: str) -> Optional[dict]:
        """Look up component by ID."""
        df = self.load()
        if df.empty:
            return None
        mask = df["COMPONENT_ID"] == component_id
        matches = df[mask]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    def get_by_type(self, component_type: str) -> pd.DataFrame:
        """Get all components of a given type.

        Args:
            component_type: One of riser_joint, bop, lmrp,
                flex_joint, telescopic_joint.
        """
        df = self.load()
        if df.empty:
            return df
        mask = df["COMPONENT_TYPE"] == component_type
        return df[mask].copy()

    def get_riser_joints(self) -> pd.DataFrame:
        """Get all riser joints."""
        return self.get_by_type("riser_joint")

    def get_bops(self) -> pd.DataFrame:
        """Get all BOPs."""
        return self.get_by_type("bop")

    def get_lmrps(self) -> pd.DataFrame:
        """Get all LMRPs."""
        return self.get_by_type("lmrp")

    def get_flex_joints(self) -> pd.DataFrame:
        """Get all flex joints."""
        return self.get_by_type("flex_joint")

    def get_telescopic_joints(self) -> pd.DataFrame:
        """Get all telescopic joints."""
        return self.get_by_type("telescopic_joint")

    def filter_by_size(
        self,
        od_in: float,
        tolerance_in: float = 0.1,
    ) -> pd.DataFrame:
        """Filter riser joints by OD (inches) with optional tolerance.

        Uses tolerance-based matching to handle floating-point OD values
        extracted from model files (e.g., OrcaFlex .dat → inches conversion).

        Args:
            od_in: Target outer diameter in inches.
            tolerance_in: Allowable deviation in inches (default 0.1").
                Set to 0.0 for exact equality matching.
        """
        df = self.get_riser_joints()
        if df.empty:
            return df
        mask = (df["OD_IN"] - od_in).abs() <= tolerance_in
        return df[mask].copy()

    def query(
        self,
        component_type: Optional[str] = None,
        od_in: Optional[float] = None,
        manufacturer: Optional[str] = None,
        min_pressure_psi: Optional[float] = None,
    ) -> pd.DataFrame:
        """General-purpose query across all riser components.

        Each kwarg filters the result; omit to skip that filter.

        Args:
            component_type: One of riser_joint, bop, lmrp,
                flex_joint, telescopic_joint.
            od_in: OD filter (tolerance ±0.1" applied automatically).
            manufacturer: Exact manufacturer name match.
            min_pressure_psi: Minimum pressure rating filter.
        """
        df = self.load()
        if df.empty:
            return df

        if component_type is not None:
            df = df[df["COMPONENT_TYPE"] == component_type]

        if od_in is not None and "OD_IN" in df.columns:
            df = df[(df["OD_IN"] - od_in).abs() <= 0.1]

        if manufacturer is not None and "MANUFACTURER" in df.columns:
            df = df[df["MANUFACTURER"] == manufacturer]

        if min_pressure_psi is not None and "PRESSURE_RATING_PSI" in df.columns:
            df = df[df["PRESSURE_RATING_PSI"] >= min_pressure_psi]

        return df.copy()

    def filter_by_pressure_rating(
        self,
        min_psi: float,
        max_psi: Optional[float] = None,
    ) -> pd.DataFrame:
        """Filter all components by pressure rating range."""
        df = self.load()
        if df.empty:
            return df
        mask = df["PRESSURE_RATING_PSI"] >= min_psi
        if max_psi is not None:
            mask = mask & (df["PRESSURE_RATING_PSI"] <= max_psi)
        return df[mask].copy()

    def filter_bops_by_bore(self, bore_in: float) -> pd.DataFrame:
        """Filter BOPs by bore size."""
        bops = self.get_bops()
        if bops.empty:
            return bops
        mask = bops["BORE_SIZE_IN"] == bore_in
        return bops[mask].copy()

    def filter_subsea_bops(self) -> pd.DataFrame:
        """Get subsea BOPs only."""
        bops = self.get_bops()
        if bops.empty:
            return bops
        mask = bops["BOP_TYPE"].str.lower() == "subsea"
        return bops[mask].copy()

    def component_type_summary(self) -> dict:
        """Count of components by type."""
        df = self.load()
        if df.empty:
            return {}
        return df["COMPONENT_TYPE"].value_counts().to_dict()

    def manufacturer_summary(self) -> dict:
        """Count of components by manufacturer."""
        df = self.load()
        if df.empty:
            return {}
        mfr = df["MANUFACTURER"].dropna()
        return mfr.value_counts().to_dict()
