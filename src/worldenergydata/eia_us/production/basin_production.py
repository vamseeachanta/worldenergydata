"""DPR (Drilling Productivity Report) basin-level production loader.

Covers the seven EIA DPR regions:
  Permian, Bakken, Eagle Ford, DJ Basin (Niobrara),
  Appalachian, Haynesville, Anadarko

Each region has monthly data for:
  - Rig count
  - New well IP (initial production) in bopd
  - Legacy decline in bopd (negative — represents aggregate output loss
    from all previously drilled wells)
  - Total production in bopd
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# EIA DPR region names
DPR_BASINS: List[str] = [
    "Permian",
    "Bakken",
    "Eagle Ford",
    "DJ Basin",
    "Appalachian",
    "Haynesville",
    "Anadarko",
]


@dataclass
class BasinRecord:
    """Single monthly DPR record for one basin."""

    period: str
    basin: str
    rig_count: float
    new_well_ip_bopd: float
    legacy_decline_bopd: float  # Always <= 0
    total_production_bopd: float

    @property
    def net_change_bopd(self) -> float:
        """Net monthly production change = new well additions + legacy decline."""
        return self.new_well_ip_bopd + self.legacy_decline_bopd


class BasinProductionLoader:
    """Load and normalise EIA DPR basin-level production data."""

    _REQUIRED_COLS = [
        "period",
        "basin",
        "rig_count",
        "new_well_ip_bopd",
        "legacy_decline_bopd",
        "total_production_bopd",
    ]

    def load(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert raw DPR records to normalised basin production DataFrame.

        Args:
            records: List of dicts with DPR field names.

        Returns:
            DataFrame with columns matching _REQUIRED_COLS.
            Empty DataFrame (same columns) if records is empty.
        """
        if not records:
            return pd.DataFrame(columns=self._REQUIRED_COLS)

        rows = []
        for rec in records:
            rows.append({
                "period": rec.get("period", ""),
                "basin": rec.get("basin", ""),
                "rig_count": float(rec.get("rig_count", 0)),
                "new_well_ip_bopd": float(rec.get("new_well_ip_bopd", 0.0)),
                "legacy_decline_bopd": float(rec.get("legacy_decline_bopd", 0.0)),
                "total_production_bopd": float(rec.get("total_production_bopd", 0.0)),
            })

        return pd.DataFrame(rows)[self._REQUIRED_COLS].reset_index(drop=True)

    def filter_basin(self, df: pd.DataFrame, basin: str) -> pd.DataFrame:
        """Return rows for a specific basin (exact match)."""
        return df[df["basin"] == basin].copy()

    def filter_period(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """Return rows for a specific YYYY-MM period."""
        return df[df["period"] == period].copy()

    def to_records(self, df: pd.DataFrame) -> List[BasinRecord]:
        """Convert DataFrame rows to BasinRecord dataclass instances."""
        result = []
        for _, row in df.iterrows():
            result.append(BasinRecord(
                period=row["period"],
                basin=row["basin"],
                rig_count=row["rig_count"],
                new_well_ip_bopd=row["new_well_ip_bopd"],
                legacy_decline_bopd=row["legacy_decline_bopd"],
                total_production_bopd=row["total_production_bopd"],
            ))
        return result
