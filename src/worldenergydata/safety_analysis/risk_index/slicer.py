"""HSE Risk Index Multi-Dimensional Slicer.

Groups incident data by field, water depth band, or geological era
and computes per-group metrics suitable for downstream risk scoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.safety_analysis.risk_index.config_loader import (
    RiskConfig,
    default_config,
)

logger = logging.getLogger(__name__)

# Output columns for sliced metrics
SLICE_COLUMNS = [
    "group_key",
    "group_type",
    "total_incidents",
    "fatalities",
    "injuries",
    "fatality_rate",
    "injury_rate",
]


class RiskSlicer:
    """Groups incident DataFrames by a dimension and aggregates metrics.

    Supports slicing by:
    - field_name (oil/gas field)
    - water_depth_ft (shallow / mid / deep bands)
    - geological_era (Oligocene, Eocene, Paleocene, etc.)
    """

    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        self._config = config or default_config()

    def slice_by_field(self, incidents: pd.DataFrame) -> pd.DataFrame:
        """Group incidents by field name and aggregate."""
        if len(incidents) == 0:
            return self._empty_result()
        df = incidents.copy()
        df["_group"] = df["field_name"].fillna("Unknown").astype(str)
        return self._aggregate(df, group_type="field")

    def slice_by_water_depth(self, incidents: pd.DataFrame) -> pd.DataFrame:
        """Group incidents by water depth band and aggregate."""
        if len(incidents) == 0:
            return self._empty_result()
        df = incidents.copy()
        depth_col = pd.to_numeric(df.get("water_depth_ft", pd.Series(dtype=float)), errors="coerce")
        df["_group"] = depth_col.apply(
            lambda d: self._config.get_water_depth_band(d) if pd.notna(d) else "unknown"
        )
        return self._aggregate(df, group_type="water_depth")

    def slice_by_era(self, incidents: pd.DataFrame) -> pd.DataFrame:
        """Group incidents by geological era and aggregate."""
        if len(incidents) == 0:
            return self._empty_result()
        df = incidents.copy()
        df["_group"] = df["geological_era"].fillna("Unknown").astype(str)
        return self._aggregate(df, group_type="era")

    def _aggregate(self, df: pd.DataFrame, group_type: str) -> pd.DataFrame:
        """Aggregate incidents by the _group column."""
        df["fatalities"] = pd.to_numeric(df.get("fatalities", 0), errors="coerce").fillna(0)
        df["injuries"] = pd.to_numeric(df.get("injuries", 0), errors="coerce").fillna(0)

        grouped = df.groupby("_group", sort=True)
        rows: List[Dict[str, Any]] = []

        for key, group in grouped:
            total = len(group)
            fatalities = int(group["fatalities"].sum())
            injuries = int(group["injuries"].sum())
            rows.append({
                "group_key": str(key),
                "group_type": group_type,
                "total_incidents": total,
                "fatalities": fatalities,
                "injuries": injuries,
                "fatality_rate": fatalities / total if total > 0 else 0.0,
                "injury_rate": injuries / total if total > 0 else 0.0,
            })

        return pd.DataFrame(rows, columns=SLICE_COLUMNS)

    @staticmethod
    def _empty_result() -> pd.DataFrame:
        """Return an empty DataFrame with the correct schema."""
        return pd.DataFrame(columns=SLICE_COLUMNS)
