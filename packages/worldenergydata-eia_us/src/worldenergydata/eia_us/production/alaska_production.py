"""Alaska North Slope field-level crude + NGL production breakdown.

Fields covered:
  - Prudhoe Bay   — largest Alaska field, declining since 1988 peak
  - Kuparuk River — second-largest, supergiant
  - Point Thomson — newer development, NGL-rich

Caller-supplied monthly average rates use an explicit barrels/day schema.
This loader does not qualify source revisions or retrieve field measurements.
"""

import logging
from dataclasses import dataclass
from typing import Any, ClassVar

import pandas as pd

from .measurement import (
    RATE,
    VOLUME,
    annual_volumes,
    declared_unit,
    monthly_period,
    number_or_missing,
)

logger = logging.getLogger(__name__)

# Alaska North Slope fields
ALASKA_FIELDS: list[str] = [
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

    _REQUIRED_COLS: ClassVar[list[str]] = [
        "period",
        "field",
        "crude_bopd",
        "ngl_bopd",
        "crude_bopd_missing",
        "ngl_bopd_missing",
        "unit",
        "basis",
    ]

    def load(self, records: list[dict[str, Any]]) -> pd.DataFrame:
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
            # Named *_bopd fields explicitly declare bbl/day, rate_per_day.
            declared_unit(rec, schema_unit="bopd")
            monthly_period(rec.get("period"))
            crude = number_or_missing(rec.get("crude_bopd"))
            ngl = number_or_missing(rec.get("ngl_bopd"))
            rows.append(
                {
                    "period": rec.get("period", ""),
                    "field": rec.get("field", ""),
                    "crude_bopd": crude,
                    "ngl_bopd": ngl,
                    "crude_bopd_missing": pd.isna(crude),
                    "ngl_bopd_missing": pd.isna(ngl),
                    "unit": "bopd",
                    "basis": RATE,
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
        """Integrate monthly daily rates into annual crude_bbl and ngl_bbl.

        Incomplete components have unknown totals and explicit missing months.
        Rate columns are not retained with misleading annual volume values.
        """
        columns = ["crude_bbl", "ngl_bbl"]
        if df.empty:
            return annual_volumes(df, "field", columns)
        if not df["unit"].eq("bopd").all() or not df["basis"].eq(RATE).all():
            raise ValueError("Annual aggregation requires daily rate unit/basis")
        volumes = df.copy()
        periods = [monthly_period(period) for period in df["period"]]
        volumes["year"] = [period[0] for period in periods]
        volumes["month"] = [period[1] for period in periods]
        days = pd.Series([period[2] for period in periods], index=df.index)
        for rate, volume in zip(["crude_bopd", "ngl_bopd"], columns):
            # NIST SP 811 (2008), section 7.11: average rate * duration.
            volumes[volume] = df[rate].map(number_or_missing) * days
        volumes["unit"], volumes["basis"] = "bbl", VOLUME
        return annual_volumes(volumes, "field", columns)

    def to_records(self, df: pd.DataFrame) -> list[AlaskaFieldRecord]:
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
