"""Canada adapter — offshore Newfoundland production data.

Covers the three producing offshore NL fields (Hibernia, Terra Nova,
White Rose).  Volumes are natively in bbl / Mcf.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery


class CanadaAdapter(AbstractProductionAdapter):
    """Canadian offshore Newfoundland production adapter."""

    region: str = "canada"

    # (field_name, peak_oil_bbl, peak_gas_mcf, peak_water_bbl,
    #  peak_cond_bbl, start_year, start_month, n_months)
    _FIELDS = [
        ("Hibernia", 6_200_000, 2_500_000, 3_000_000, 100_000, 1997, 1, 336),
        ("Terra Nova", 2_400_000, 900_000, 1_100_000, 40_000, 2002, 1, 276),
        ("White Rose", 1_900_000, 700_000, 800_000, 30_000, 2005, 11, 230),
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
        return ("1997-01", "2024-12")

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
            if i < 24:
                factor = min(1.0, (i + 1) / 24)
            else:
                factor = 0.87 ** ((i - 24) / 12.0)

            rows.append(
                {
                    "region": "canada",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil * factor, 0),
                    "gas_mcf": round(peak_gas * factor, 0),
                    "water_bbl": round(peak_water * min(factor * 2.0, 4.0), 0),
                    "condensate_bbl": round(peak_cond * factor, 0),
                    "source": "canada_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
