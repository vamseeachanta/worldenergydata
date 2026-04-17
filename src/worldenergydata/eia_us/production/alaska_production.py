"""Alaska North Slope field-level crude + NGL production breakdown.

Fields covered:
  - Prudhoe Bay   — largest Alaska field, declining since 1988 peak
  - Kuparuk River — second-largest, supergiant
  - Point Thomson — newer development, NGL-rich

Production data derived from EIA Alaska state series + AOGCC field reports.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

# Alaska North Slope fields
ALASKA_FIELDS: List[str] = [
    "Prudhoe Bay",
    "Kuparuk",
    "Point Thomson",
]


@dataclass
class AlaskaFieldRecord:
    """Single monthly production record for one Alaska North Slope field."""

    period: str
    field: str
    crude_bopd: float
    ngl_bopd: float

    @property
    def total_liquids_bopd(self) -> float:
        """Total liquids = crude + NGL in bopd."""
        return self.crude_bopd + self.ngl_bopd


class AlaskaProductionLoader:
    """Load and normalise Alaska North Slope field-level production data."""

    _REQUIRED_COLS = ["period", "field", "crude_bopd", "ngl_bopd"]

    def load(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert raw Alaska field records to normalised DataFrame.

        Args:
            records: List of dicts with 'period', 'field',
                     'crude_bopd', 'ngl_bopd' keys.

        Returns:
            DataFrame with columns: period, field, crude_bopd, ngl_bopd.
            Empty DataFrame (same columns) if records is empty.
        """
        if not records:
            return pd.DataFrame(columns=self._REQUIRED_COLS)

        rows = []
        for rec in records:
            crude = float(rec.get("crude_bopd", 0.0))
            rows.append(
                {
                    "period": rec.get("period", ""),
                    "field": rec.get("field", ""),
                    "crude_bopd": max(crude, 0.0),
                    "ngl_bopd": float(rec.get("ngl_bopd", 0.0)),
                }
            )

        return pd.DataFrame(rows)[self._REQUIRED_COLS].reset_index(drop=True)

    def filter_field(self, df: pd.DataFrame, field: str) -> pd.DataFrame:
        """Return rows for a specific field (exact match)."""
        return df[df["field"] == field].copy()

    def filter_period(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """Return rows for a specific YYYY-MM period."""
        return df[df["period"] == period].copy()

    def annual_total(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate monthly records to annual totals per field.

        Returns:
            DataFrame with columns: field, year, crude_bopd, ngl_bopd.
        """
        if df.empty:
            return pd.DataFrame(columns=["field", "year", "crude_bopd", "ngl_bopd"])

        df = df.copy()
        df["year"] = df["period"].str[:4].astype(int)
        return (
            df.groupby(["field", "year"])[["crude_bopd", "ngl_bopd"]]
            .sum()
            .reset_index()
        )

    def to_records(self, df: pd.DataFrame) -> List[AlaskaFieldRecord]:
        """Convert DataFrame rows to AlaskaFieldRecord dataclass instances."""
        result = []
        for _, row in df.iterrows():
            result.append(
                AlaskaFieldRecord(
                    period=row["period"],
                    field=row["field"],
                    crude_bopd=row["crude_bopd"],
                    ngl_bopd=row["ngl_bopd"],
                )
            )
        return result
