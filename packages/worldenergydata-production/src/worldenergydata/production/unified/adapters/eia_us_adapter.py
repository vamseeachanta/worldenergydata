"""EIA US adapter — state-level shale play production data.

EIA reports production at the basin/play level rather than individual fields.
This adapter treats each play as a "field" for consistency with the unified
schema.  Volumes are natively in bbl / Mcf.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery


class EiaUsAdapter(AbstractProductionAdapter):
    """EIA US shale play production adapter."""

    region: str = "eia_us"

    # (play_name, peak_oil_bbl, peak_gas_mcf, peak_water_bbl,
    #  peak_cond_bbl, start_year, start_month, n_months)
    _FIELDS = [
        ("Permian", 250_000_000, 350_000_000, 90_000_000, 5_000_000, 2010, 1, 180),
        ("Bakken", 80_000_000, 50_000_000, 30_000_000, 1_000_000, 2008, 1, 192),
        ("Eagle Ford", 60_000_000, 220_000_000, 20_000_000, 8_000_000, 2010, 6, 174),
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
        return ("2008-01", "2024-12")

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
            # Shale plays ramp faster and stay higher longer
            if i < 48:
                factor = min(1.0, (i + 1) / 48)
            else:
                factor = 0.95 ** ((i - 48) / 12.0)

            rows.append(
                {
                    "region": "eia_us",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil * factor, 0),
                    "gas_mcf": round(peak_gas * factor, 0),
                    "water_bbl": round(peak_water * factor, 0),
                    "condensate_bbl": round(peak_cond * factor, 0),
                    "source": "eia_us_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
