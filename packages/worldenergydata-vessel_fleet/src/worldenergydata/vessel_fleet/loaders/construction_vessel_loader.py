"""Load construction vessel data from curated fleet.

Provides query interface for construction and service vessels including
crane vessels, pipelay vessels, heavy-lift vessels, and wind installation
vessels.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Curated data ships INSIDE this member as package data (ADR 0001 Phase 2,
# batch 4, #529 — option (i): data travels with the package). It lives at
# ``worldenergydata/vessel_fleet/_data/curated/`` (one level up from this
# ``loaders/`` subpackage), so it resolves identically whether installed
# editable in the workspace or unpacked from the built wheel — no repo-root
# walk.
_DATA_DIR = Path(__file__).resolve().parent.parent / "_data" / "curated"
_DEFAULT_FILE = "construction_vessels.parquet"
_HEAVY_LIFT_THRESHOLD_T = 5000.0
_DEEPWATER_THRESHOLD_M = 2000.0


class ConstructionVesselLoader:
    """Query construction vessel data from the curated fleet.

    Loads construction vessels from Parquet storage and provides
    query methods by name, type, operator, and capabilities.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize loader.

        Args:
            data_dir: Optional custom data directory. Defaults to
                data/modules/vessel_fleet/curated.
        """
        self._data_dir = data_dir or _DATA_DIR
        self._df: Optional[pd.DataFrame] = None

    def load(self) -> pd.DataFrame:
        """Load curated construction vessel data (lazy, cached).

        Returns:
            DataFrame with construction vessel records.
        """
        if self._df is not None:
            return self._df

        pq = self._data_dir / _DEFAULT_FILE
        if not pq.exists():
            logger.warning("Construction vessel data not found: %s", pq)
            self._df = pd.DataFrame()
            return self._df

        df = pd.read_parquet(pq)
        self._df = df
        logger.info("Loaded %d construction vessels", len(df))
        return self._df

    def get_by_name(self, vessel_name: str) -> Optional[dict]:
        """Look up vessel by name (case-insensitive).

        Args:
            vessel_name: Vessel name to search for.

        Returns:
            Dictionary of vessel data if found, None otherwise.
        """
        df = self.load()
        if df.empty:
            return None

        mask = df["VESSEL_NAME"].str.upper() == vessel_name.upper()
        matches = df[mask]

        if matches.empty:
            return None

        return matches.iloc[0].to_dict()

    def get_by_imo(self, imo_number: str) -> Optional[dict]:
        """Look up vessel by IMO number.

        Args:
            imo_number: 7-digit IMO number.

        Returns:
            Dictionary of vessel data if found, None otherwise.
        """
        df = self.load()
        if df.empty or "IMO_NUMBER" not in df.columns:
            return None

        mask = df["IMO_NUMBER"] == imo_number
        matches = df[mask]

        if matches.empty:
            return None

        return matches.iloc[0].to_dict()

    def get_by_vessel_type(self, vessel_type: str) -> pd.DataFrame:
        """Get all vessels of a specific type.

        Args:
            vessel_type: Type such as 'crane_vessel', 'pipelay_vessel', etc.

        Returns:
            DataFrame of matching vessels.
        """
        df = self.load()
        if df.empty or "VESSEL_TYPE" not in df.columns:
            return pd.DataFrame()

        mask = df["VESSEL_TYPE"] == vessel_type
        return df[mask].copy()

    def get_by_operator(self, operator: str) -> pd.DataFrame:
        """Get all vessels for a specific operator.

        Args:
            operator: Operator name.

        Returns:
            DataFrame of matching vessels.
        """
        df = self.load()
        if df.empty or "OPERATOR" not in df.columns:
            return pd.DataFrame()

        mask = df["OPERATOR"] == operator
        return df[mask].copy()

    def filter_by_crane_capacity(
        self,
        min_capacity_t: Optional[float] = None,
        max_capacity_t: Optional[float] = None,
    ) -> pd.DataFrame:
        """Filter vessels by main crane capacity range.

        Args:
            min_capacity_t: Minimum crane capacity in tonnes.
            max_capacity_t: Maximum crane capacity in tonnes.

        Returns:
            DataFrame of vessels matching capacity criteria.
        """
        df = self.load()
        if df.empty or "MAIN_CRANE_CAPACITY_T" not in df.columns:
            return pd.DataFrame()

        result = df.copy()

        if min_capacity_t is not None:
            result = result[result["MAIN_CRANE_CAPACITY_T"] >= min_capacity_t]

        if max_capacity_t is not None:
            result = result[result["MAIN_CRANE_CAPACITY_T"] <= max_capacity_t]

        return result

    def filter_by_water_depth(
        self,
        min_depth_m: Optional[float] = None,
        max_depth_m: Optional[float] = None,
    ) -> pd.DataFrame:
        """Filter vessels by water depth rating.

        Args:
            min_depth_m: Minimum water depth rating in metres.
            max_depth_m: Maximum water depth rating in metres.

        Returns:
            DataFrame of vessels matching depth criteria.
        """
        df = self.load()
        if df.empty or "WATER_DEPTH_RATING_M" not in df.columns:
            return pd.DataFrame()

        result = df.copy()

        if min_depth_m is not None:
            result = result[result["WATER_DEPTH_RATING_M"] >= min_depth_m]

        if max_depth_m is not None:
            result = result[result["WATER_DEPTH_RATING_M"] <= max_depth_m]

        return result

    def filter_by_dp_class(self, min_class: int) -> pd.DataFrame:
        """Filter vessels by minimum DP class.

        Args:
            min_class: Minimum DP class (1, 2, or 3).

        Returns:
            DataFrame of vessels with DP class >= min_class.
        """
        df = self.load()
        if df.empty or "DP_CLASS" not in df.columns:
            return pd.DataFrame()

        return df[df["DP_CLASS"] >= min_class].copy()

    def filter_by_deck_area(
        self,
        min_area_m2: Optional[float] = None,
        max_area_m2: Optional[float] = None,
    ) -> pd.DataFrame:
        """Filter vessels by deck area.

        Args:
            min_area_m2: Minimum deck area in square metres.
            max_area_m2: Maximum deck area in square metres.

        Returns:
            DataFrame of vessels matching area criteria.
        """
        df = self.load()
        if df.empty or "DECK_AREA_M2" not in df.columns:
            return pd.DataFrame()

        result = df.copy()

        if min_area_m2 is not None:
            result = result[result["DECK_AREA_M2"] >= min_area_m2]

        if max_area_m2 is not None:
            result = result[result["DECK_AREA_M2"] <= max_area_m2]

        return result

    def vessel_type_summary(self) -> dict[str, int]:
        """Return count of vessels per type.

        Returns:
            Dictionary mapping vessel type to count.
        """
        df = self.load()
        if df.empty or "VESSEL_TYPE" not in df.columns:
            return {}

        return df["VESSEL_TYPE"].value_counts().to_dict()

    def operator_summary(self) -> dict[str, int]:
        """Return count of vessels per operator.

        Returns:
            Dictionary mapping operator to count.
        """
        df = self.load()
        if df.empty or "OPERATOR" not in df.columns:
            return {}

        return df["OPERATOR"].value_counts().to_dict()

    def capability_summary(self) -> dict[str, int]:
        """Return summary of vessel capabilities.

        Returns:
            Dictionary with capability counts:
            - total_vessels
            - has_crane
            - has_pipelay
            - deepwater_capable
            - heavy_lift_capable
        """
        df = self.load()
        if df.empty:
            return {
                "total_vessels": 0,
                "has_crane": 0,
                "has_pipelay": 0,
                "deepwater_capable": 0,
                "heavy_lift_capable": 0,
            }

        has_crane = 0
        has_pipelay = 0
        deepwater = 0
        heavy_lift = 0

        if "MAIN_CRANE_CAPACITY_T" in df.columns:
            has_crane = int(df["MAIN_CRANE_CAPACITY_T"].notna().sum())
            heavy_lift = int(
                (df["MAIN_CRANE_CAPACITY_T"] >= _HEAVY_LIFT_THRESHOLD_T).sum()
            )

        if "PIPELAY_TENSION_T" in df.columns:
            has_pipelay = int(df["PIPELAY_TENSION_T"].notna().sum())

        if "WATER_DEPTH_RATING_M" in df.columns:
            deepwater = int(
                (df["WATER_DEPTH_RATING_M"] >= _DEEPWATER_THRESHOLD_M).sum()
            )

        return {
            "total_vessels": len(df),
            "has_crane": has_crane,
            "has_pipelay": has_pipelay,
            "deepwater_capable": deepwater,
            "heavy_lift_capable": heavy_lift,
        }

    def get_pipelay_vessels(self) -> pd.DataFrame:
        """Get all vessels with pipelay capability.

        Returns:
            DataFrame of vessels with pipelay tension or method specified.
        """
        df = self.load()
        if df.empty:
            return df

        mask = pd.Series(False, index=df.index)

        if "PIPELAY_TENSION_T" in df.columns:
            mask |= df["PIPELAY_TENSION_T"].notna()

        if "PIPELAY_METHOD" in df.columns:
            mask |= df["PIPELAY_METHOD"].notna()

        return df[mask].copy()

    def get_crane_vessels(self) -> pd.DataFrame:
        """Get all vessels with crane capability.

        Returns:
            DataFrame of vessels with main or auxiliary crane.
        """
        df = self.load()
        if df.empty:
            return df

        mask = pd.Series(False, index=df.index)

        if "MAIN_CRANE_CAPACITY_T" in df.columns:
            mask |= df["MAIN_CRANE_CAPACITY_T"].notna()

        if "AUX_CRANE_CAPACITY_T" in df.columns:
            mask |= df["AUX_CRANE_CAPACITY_T"].notna()

        return df[mask].copy()

    def get_heavy_lift_vessels(self) -> pd.DataFrame:
        """Get all vessels with heavy-lift capability.

        Returns:
            DataFrame of vessels with crane >= 5000 tonnes or
            heavy_lift_capacity >= 5000 tonnes.
        """
        df = self.load()
        if df.empty:
            return df

        mask = pd.Series(False, index=df.index)

        if "MAIN_CRANE_CAPACITY_T" in df.columns:
            mask |= df["MAIN_CRANE_CAPACITY_T"] >= _HEAVY_LIFT_THRESHOLD_T

        if "HEAVY_LIFT_CAPACITY_T" in df.columns:
            mask |= df["HEAVY_LIFT_CAPACITY_T"] >= _HEAVY_LIFT_THRESHOLD_T

        return df[mask].copy()
