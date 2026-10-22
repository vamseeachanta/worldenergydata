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
from typing import Any, ClassVar

import pandas as pd

from .measurement import RATE, declared_unit, monthly_period, number_or_missing

logger = logging.getLogger(__name__)

# EIA DPR region names
DPR_BASINS: list[str] = [
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
    legacy_decline_bopd: float  # Signed legacy change; NaN if unreported.
    total_production_bopd: float

    @property
    def net_change_bopd(self) -> float:
        """Net monthly production change = new well additions + legacy decline."""
        return self.new_well_ip_bopd + self.legacy_decline_bopd


class BasinProductionLoader:
    """Load and normalise EIA DPR basin-level production data."""

    _REQUIRED_COLS: ClassVar[list[str]] = [
        "period",
        "basin",
        "rig_count",
        "new_well_ip_bopd",
        "legacy_decline_bopd",
        "total_production_bopd",
    ]

    _NUMERIC_COLS = _REQUIRED_COLS[2:]
    _REQUIRED_COLS = _REQUIRED_COLS + [f"{col}_missing" for col in _NUMERIC_COLS]

    def load(self, records: list[dict[str, Any]]) -> pd.DataFrame:
        """Convert raw DPR records to normalised basin production DataFrame.

        Args:
            records: List of dicts with DPR field names.

        Returns:
            DataFrame with columns matching _REQUIRED_COLS.
            Empty DataFrame (same columns) if records is empty.
        """
        rows = []
        for rec in records:
            # Named *_bopd fields declare bbl/day; rig_count is a count.
            declared_unit(rec, schema_unit="bopd")
            monthly_period(rec.get("period"))
            row = {
                "period": rec["period"],
                "basin": rec.get("basin", ""),
            }
            for column in self._NUMERIC_COLS:
                value = number_or_missing(
                    rec.get(column), signed=column == "legacy_decline_bopd"
                )
                row[column] = value
                row[f"{column}_missing"] = pd.isna(value)
            rows.append(row)
        frame = pd.DataFrame(rows, columns=self._REQUIRED_COLS)
        frame.attrs["measurements"] = {
            column: (
                {"unit": "rigs", "basis": "count"}
                if column == "rig_count"
                else {"unit": "bopd", "basis": RATE}
            )
            for column in self._NUMERIC_COLS
        }
        return frame

    def filter_basin(self, df: pd.DataFrame, basin: str) -> pd.DataFrame:
        """Return rows for a specific basin (exact match)."""
        return df[df["basin"] == basin].copy()

    def filter_period(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """Return rows for a specific YYYY-MM period."""
        return df[df["period"] == period].copy()

    def to_records(self, df: pd.DataFrame) -> list[BasinRecord]:
        """Convert DataFrame rows to BasinRecord dataclass instances."""
        result = []
        for _, row in df.iterrows():
            result.append(
                BasinRecord(
                    period=row["period"],
                    basin=row["basin"],
                    rig_count=row["rig_count"],
                    new_well_ip_bopd=row["new_well_ip_bopd"],
                    legacy_decline_bopd=row["legacy_decline_bopd"],
                    total_production_bopd=row["total_production_bopd"],
                )
            )
        return result
