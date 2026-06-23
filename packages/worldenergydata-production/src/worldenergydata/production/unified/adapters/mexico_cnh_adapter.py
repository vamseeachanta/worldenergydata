"""Mexico CNH adapter — deepwater and shallow-water field production data.

CNH (Comisión Nacional de Hidrocarburos) data covers both shallow and
deepwater fields.  Volumes in bbl / Mcf natively.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery


class MexicoCnhAdapter(AbstractProductionAdapter):
    """Mexico CNH production adapter."""

    region: str = "mexico"

    # (field_name, peak_oil_bbl, peak_gas_mcf, peak_water_bbl,
    #  peak_cond_bbl, start_year, start_month, n_months)
    _FIELDS = [
        ("Zama", 2_000_000, 1_500_000, 300_000, 60_000, 2023, 1, 24),
        ("Trion", 800_000, 600_000, 100_000, 20_000, 2024, 6, 12),
        ("Ixachi", 1_200_000, 2_800_000, 200_000, 80_000, 2019, 1, 72),
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
        return ("2019-01", "2024-12")

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
            if i < 12:
                factor = min(1.0, (i + 1) / 12)
            else:
                factor = 0.91 ** ((i - 12) / 12.0)

            rows.append(
                {
                    "region": "mexico",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil * factor, 0),
                    "gas_mcf": round(peak_gas * factor, 0),
                    "water_bbl": round(peak_water * factor, 0),
                    "condensate_bbl": round(peak_cond * factor, 0),
                    "source": "mexico_cnh_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
