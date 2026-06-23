"""Brazil ANP adapter — pre-salt and post-salt field production data.

Mock data for four benchmark Brazilian fields.  ANP reports in Sm3; this
adapter converts to bbl using OilUnits.SM3_TO_BBL and gas to Mcf.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.common.units import GasUnits, OilUnits
from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery

_SM3_TO_BBL = OilUnits.SM3_TO_BBL
# 1 Sm3 gas → scf → /1000 = Mcf
_SM3_GAS_TO_MCF = GasUnits.SM3_TO_SCF / 1000.0


class BrazilAnpAdapter(AbstractProductionAdapter):
    """Brazilian ANP production adapter (pre-salt + post-salt)."""

    region: str = "brazil"

    # (field_name, peak_oil_sm3, peak_gas_sm3, peak_water_sm3,
    #  peak_cond_sm3, start_year, start_month, n_months)
    _FIELDS = [
        ("Lula", 1_400_000, 2_000_000, 300_000, 80_000, 2010, 10, 170),
        ("Búzios", 1_800_000, 2_800_000, 200_000, 120_000, 2018, 4, 80),
        ("Mero", 900_000, 1_200_000, 150_000, 60_000, 2021, 11, 38),
        ("Marlim", 600_000, 700_000, 800_000, 20_000, 1994, 9, 363),
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
        return ("1994-09", "2024-12")

    @staticmethod
    def _generate_field_rows(
        field_name: str,
        peak_oil_sm3: float,
        peak_gas_sm3: float,
        peak_water_sm3: float,
        peak_cond_sm3: float,
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
                factor = 0.88 ** ((i - 24) / 12.0)

            rows.append(
                {
                    "region": "brazil",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil_sm3 * _SM3_TO_BBL * factor, 0),
                    "gas_mcf": round(peak_gas_sm3 * _SM3_GAS_TO_MCF * factor, 0),
                    "water_bbl": round(
                        peak_water_sm3 * _SM3_TO_BBL * min(factor * 1.8, 3.5), 0
                    ),
                    "condensate_bbl": round(peak_cond_sm3 * _SM3_TO_BBL * factor, 0),
                    "source": "brazil_anp_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
