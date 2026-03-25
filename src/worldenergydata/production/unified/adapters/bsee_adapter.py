"""BSEE adapter — Gulf of Mexico deepwater production data.

Mock data for four benchmark GoM deepwater fields.  All volumes already in
field units (bbl / Mcf) — no conversion required because GoM data is
natively reported in these units.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery


class BseeAdapter(AbstractProductionAdapter):
    """Gulf of Mexico (BSEE) production adapter."""

    region: str = "gom"

    # (field_name, peak_oil_bbl, peak_gas_mcf, peak_water_bbl,
    #  condensate_bbl, start_year, start_month, n_months)
    _FIELDS = [
        ("Atlantis",      8_000_000, 10_000_000, 1_200_000, 200_000, 2007,  2, 216),
        ("Thunder Horse", 9_500_000, 14_000_000, 1_500_000, 300_000, 2008,  6, 200),
        ("Mars-Ursa",     7_200_000,  9_000_000, 2_100_000, 150_000, 1997,  1, 324),
        ("Na Kika",       3_800_000,  5_500_000,   800_000,  80_000, 2003,  6, 254),
    ]

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        rows = []
        for field_name, peak_oil, peak_gas, peak_water, peak_cond, sy, sm, n_months in self._FIELDS:
            rows.extend(
                self._generate_field_rows(
                    field_name, peak_oil, peak_gas, peak_water, peak_cond, sy, sm, n_months
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
            if i < 18:
                factor = 1.0
            else:
                factor = 0.90 ** ((i - 18) / 12.0)

            rows.append(
                {
                    "region": "gom",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil * factor, 0),
                    "gas_mcf": round(peak_gas * factor, 0),
                    "water_bbl": round(peak_water * min(factor * 2.0, 4.0), 0),
                    "condensate_bbl": round(peak_cond * factor, 0),
                    "source": "bsee_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
