"""Texas RRC adapter — Permian Basin sub-play production data.

Texas Railroad Commission data covers stacked-pay Permian sub-plays.
This adapter treats each sub-play as a "field" using the unified schema.
Volumes in bbl / Mcf natively.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery


class TexasRrcAdapter(AbstractProductionAdapter):
    """Texas RRC Permian sub-play production adapter."""

    region: str = "texas"

    # (play_name, peak_oil_bbl, peak_gas_mcf, peak_water_bbl,
    #  peak_cond_bbl, start_year, start_month, n_months)
    _FIELDS = [
        ("Wolfcamp", 130_000_000, 180_000_000, 50_000_000, 3_000_000, 2013, 1, 144),
        ("Bone Spring", 70_000_000, 90_000_000, 28_000_000, 1_500_000, 2013, 1, 144),
    ]

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        rows = []
        for (
            field_name,
            peak_oil,
            peak_gas,
            peak_water,
            peak_cond,
            sy,
            sm,
            n_months,
        ) in self._FIELDS:
            rows.extend(
                self._generate_field_rows(
                    field_name,
                    peak_oil,
                    peak_gas,
                    peak_water,
                    peak_cond,
                    sy,
                    sm,
                    n_months,
                )
            )

        df = pd.DataFrame(rows)
        df = self._filter_by_fields(df, query.fields)
        df = self._filter_by_date(df, query.start, query.end)
        return df.reset_index(drop=True)

    def available_fields(self) -> List[str]:
        return [f[0] for f in self._FIELDS]

    def date_range(self) -> Tuple[str, str]:
        return ("2013-01", "2024-12")

    @staticmethod
    def _generate_field_rows(
        field_name: str,
        peak_oil: float,
        peak_gas: float,
        peak_water: float,
        peak_cond: float,
        start_year: int,
        start_month: int,
        n_months: int,
    ) -> list:
        rows = []
        year, month = start_year, start_month
        for i in range(n_months):
            # Unconventional plays grow steadily then plateau
            if i < 60:
                factor = min(1.0, (i + 1) / 60)
            else:
                factor = 0.97 ** ((i - 60) / 12.0)

            rows.append(
                {
                    "region": "texas",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil * factor, 0),
                    "gas_mcf": round(peak_gas * factor, 0),
                    "water_bbl": round(peak_water * factor, 0),
                    "condensate_bbl": round(peak_cond * factor, 0),
                    "source": "texas_rrc_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
