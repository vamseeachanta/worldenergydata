"""UKCS adapter — UK Continental Shelf production data.

Mock data for four benchmark UKCS fields.  UKCS data is typically reported
in tonnes/bbl already; this adapter uses bbl natively.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery


class UkcsAdapter(AbstractProductionAdapter):
    """UK Continental Shelf (NSTA) production adapter."""

    region: str = "ukcs"

    # (field_name, peak_oil_bbl, peak_gas_mcf, peak_water_bbl,
    #  peak_cond_bbl, start_year, start_month, n_months)
    _FIELDS = [
        ("Forties", 12_000_000, 5_000_000, 8_000_000, 200_000, 1975, 9, 588),
        ("Buzzard", 8_000_000, 1_800_000, 3_500_000, 100_000, 2007, 1, 216),
        ("Mariner", 1_800_000, 600_000, 900_000, 30_000, 2019, 6, 66),
        ("Clair Ridge", 2_500_000, 900_000, 1_200_000, 50_000, 2018, 11, 74),
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
        return ("1975-09", "2024-12")

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
            if i < 6:
                factor = min(1.0, (i + 1) / 6)
            else:
                factor = 0.85 ** ((i - 6) / 12.0)

            rows.append(
                {
                    "region": "ukcs",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil * factor, 0),
                    "gas_mcf": round(peak_gas * factor, 0),
                    "water_bbl": round(peak_water * min(factor * 2.5, 5.0), 0),
                    "condensate_bbl": round(peak_cond * factor, 0),
                    "source": "ukcs_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
