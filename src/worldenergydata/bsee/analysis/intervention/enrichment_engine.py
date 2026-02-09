"""Multi-source join engine for WAR data enrichment (WRK-116 Phase 2).

Joins WAR records with fleet, borehole, and paleowells data to produce
a row-level enriched DataFrame suitable for downstream analysis.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.bsee.analysis.intervention.activity_aggregator import (
    classify_activity,
)
from worldenergydata.bsee.data.loaders.rig_fleet.constants import (
    RigType,
    classify_rig_type,
)
from worldenergydata.bsee.data.utils.api_well_normalizer import (
    normalize_api_well_number,
)

_DEPTH_BINS: list[tuple[float, float, str]] = [
    (0, 200, "Shallow"),
    (200, 1000, "Mid"),
    (1000, 5000, "Deep"),
    (5000, float("inf"), "Ultra-deep"),
]

_CATEGORY_COLS: list[str] = [
    "RIG_TYPE",
    "ACTIVITY_CATEGORY",
    "AREA_CODE",
    "WATER_DEPTH_CLASS",
]


def _classify_water_depth(depth: float) -> str:
    """Return water depth classification string."""
    if pd.isna(depth):
        return "Unknown"
    for low, high, label in _DEPTH_BINS:
        if low <= depth < high:
            return label
    return "Unknown"


class ActivityEnrichmentEngine:
    """Multi-source join engine for WAR data enrichment."""

    def __init__(
        self,
        war_df: pd.DataFrame,
        fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame | None = None,
        era_map: dict[str, str] | None = None,
    ) -> None:
        self._war_df = war_df.copy()
        self._fleet_df = fleet_df.copy()
        self._borehole_df = borehole_df.copy() if borehole_df is not None else None
        self._era_map = era_map
        self._result: pd.DataFrame | None = None

    # -- Step 1: WAR to Fleet join -------------------------------------------

    def _join_fleet(self, df: pd.DataFrame) -> pd.DataFrame:
        """Left-join WAR to fleet, apply heuristic fallback, add category."""
        df = df.merge(
            self._fleet_df[["RIG_NAME", "RIG_TYPE"]],
            on="RIG_NAME",
            how="left",
        )
        # Track which rows came from fleet (before fallback fills them).
        df["_fleet_matched"] = df["RIG_TYPE"].notna()

        # Heuristic fallback for unmatched rigs.
        mask = df["RIG_TYPE"].isna()
        if mask.any():
            df.loc[mask, "RIG_TYPE"] = df.loc[mask, "RIG_NAME"].apply(
                lambda name: classify_rig_type(str(name)).value
                if pd.notna(name)
                else RigType.UNKNOWN.value
            )

        df["ACTIVITY_CATEGORY"] = df["RIG_TYPE"].map(classify_activity)

        # Parse YEAR from WAR_START_DT with WAR_END_DT fallback.
        dt = pd.to_datetime(
            df["WAR_START_DT"], format="mixed", dayfirst=False, errors="coerce",
        )
        if "WAR_END_DT" in df.columns:
            fallback = pd.to_datetime(
                df["WAR_END_DT"], format="mixed", dayfirst=False, errors="coerce",
            )
            dt = dt.fillna(fallback)
        df["YEAR"] = dt.dt.year.astype("Int64")

        return df

    # -- Step 2: WAR to Borehole join ----------------------------------------

    def _join_borehole(self, df: pd.DataFrame) -> pd.DataFrame:
        """Left-join borehole data, compute drilling days and coalesce depth."""
        if self._borehole_df is None:
            return df

        bh = self._borehole_df.rename(
            columns={"WATER_DEPTH": "BH_WATER_DEPTH"},
        )
        bh["WELL_SPUD_DATE"] = pd.to_datetime(bh["WELL_SPUD_DATE"])
        bh["TOTAL_DEPTH_DATE"] = pd.to_datetime(bh["TOTAL_DEPTH_DATE"])

        # Drilling days: clamp negatives to NaN.
        raw_days = (bh["TOTAL_DEPTH_DATE"] - bh["WELL_SPUD_DATE"]).dt.days
        bh["DRILLING_DAYS"] = raw_days.where(raw_days >= 0).astype(float)

        # Normalize API well numbers on both sides for robust join.
        df["_api_norm"] = normalize_api_well_number(df["API_WELL_NUMBER"])
        bh["_api_norm"] = normalize_api_well_number(bh["API_WELL_NUMBER"])

        bh_cols = [
            "_api_norm", "WELL_SPUD_DATE", "TOTAL_DEPTH_DATE",
            "BH_TOTAL_MD", "BH_WATER_DEPTH", "BOREHOLE_STAT_CD",
            "WELL_NAME_SUFFIX", "DRILLING_DAYS",
        ]
        df = df.merge(bh[bh_cols], on="_api_norm", how="left")
        df.drop(columns=["_api_norm"], inplace=True)

        # Derived columns.
        df["WATER_DEPTH_FINAL"] = df["WATER_DEPTH"].fillna(df["BH_WATER_DEPTH"])
        df["WELL_STATUS"] = df["BOREHOLE_STAT_CD"]

        return df

    # -- Step 3: Water depth classification ----------------------------------

    def _classify_depth(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add WATER_DEPTH_CLASS based on WATER_DEPTH_FINAL or WATER_DEPTH."""
        depth_col = "WATER_DEPTH_FINAL" if "WATER_DEPTH_FINAL" in df.columns else "WATER_DEPTH"
        df["WATER_DEPTH_CLASS"] = df[depth_col].map(_classify_water_depth)
        return df

    # -- Step 4: Paleowells era mapping --------------------------------------

    def _map_era(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map geological era from paleowells data (vectorized)."""
        if self._era_map is None:
            return df
        api_norm = normalize_api_well_number(df["API_WELL_NUMBER"])
        df["GEOLOGICAL_ERA"] = api_norm.map(self._era_map)
        return df

    # -- Step 5: Memory optimization -----------------------------------------

    @staticmethod
    def _optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        """Cast string columns to category dtype for memory savings."""
        for col in _CATEGORY_COLS:
            if col in df.columns:
                df[col] = df[col].astype("category")
        if "WELL_STATUS" in df.columns:
            df["WELL_STATUS"] = df["WELL_STATUS"].astype("category")
        return df

    # -- Public API ----------------------------------------------------------

    def enrich(self) -> pd.DataFrame:
        """Run the full enrichment pipeline and return enriched DataFrame."""
        df = self._war_df.copy()
        if df.empty:
            return df

        df = self._join_fleet(df)
        df = self._join_borehole(df)
        df = self._classify_depth(df)
        df = self._map_era(df)
        df = self._optimize_dtypes(df)

        self._result = df
        return df

    def get_join_stats(self) -> dict:
        """Return join diagnostics after enrichment has been run."""
        if self._result is None:
            return {
                "total_war_records": 0,
                "fleet_match_rate": 0.0,
                "borehole_match_rate": 0.0,
                "era_match_rate": 0.0,
                "water_depth_fill_rate": 0.0,
            }

        df = self._result
        n = len(df)

        fleet_rate = float(df["_fleet_matched"].sum() / n) if n else 0.0

        bh_rate = 0.0
        if "BH_TOTAL_MD" in df.columns and n:
            bh_rate = float(df["BH_TOTAL_MD"].notna().sum() / n)

        era_rate = 0.0
        if "GEOLOGICAL_ERA" in df.columns and n:
            era_rate = float(df["GEOLOGICAL_ERA"].notna().sum() / n)

        depth_col = "WATER_DEPTH_FINAL" if "WATER_DEPTH_FINAL" in df.columns else "WATER_DEPTH"
        depth_rate = float(df[depth_col].notna().sum() / n) if n else 0.0

        return {
            "total_war_records": n,
            "fleet_match_rate": fleet_rate,
            "borehole_match_rate": bh_rate,
            "era_match_rate": era_rate,
            "water_depth_fill_rate": depth_rate,
        }
