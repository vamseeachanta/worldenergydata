"""SODIR adapter — Norwegian Continental Shelf production data.

Returns mock data for the four benchmark NCS fields using realistic
production profiles.  Unit source: Sm3 → bbl via OilUnits.SM3_TO_BBL;
gas MSm3 → MCF via GasUnits.MSM3_TO_MMSCF * 1000.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.common.units import GasUnits, OilUnits
from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery

# 1 MSm3 gas → Mcf  (MSm3_TO_MMSCF gives MMscf; *1000 = Mcf)
_MSM3_TO_MCF = GasUnits.MSM3_TO_MMSCF * GasUnits.MMSCF_TO_MCF
_SM3_TO_BBL = OilUnits.SM3_TO_BBL


class SodirAdapter(AbstractProductionAdapter):
    """Norwegian Continental Shelf (SODIR) production adapter."""

    region: str = "ncs"

    # Each entry: (field_name, peak_oil_bbl_mo, peak_gas_mcf_mo, peak_water_bbl_mo,
    #               condensate_bbl_mo, start_year, start_month, n_months)
    _FIELDS = [
        ("Edvard Grieg", 5_800_000, 2_100_000, 420_000, 180_000, 2015, 11, 96),
        ("Valhall", 4_200_000, 1_500_000, 650_000, 90_000, 1982, 1, 504),
        ("Ivar Aasen", 1_600_000, 520_000, 190_000, 40_000, 2016, 12, 88),
        ("Solveig", 900_000, 310_000, 80_000, 30_000, 2019, 5, 60),
    ]

    def __init__(self, loader=None):
        """Initialize the SODIR adapter.

        Args:
            loader: optional object exposing ``load_all_production()`` and,
                optionally, ``load_field_production(field_name)`` that
                returns the SODIR ``MonthlyProductionLoader`` output columns
                (field_name/year/month/oil_sm3/.../oil_bbl/gas_mcf). When
                provided, ``fetch`` returns REAL SODIR production normalized to
                ``STANDARD_COLUMNS``. When ``None`` (default), ``fetch`` returns
                the synthetic benchmark profile — keeping the conformance suite
                non-empty without live data. Dependency-injected so this adapter
                carries no worldenergydata-sodir package dependency (#716).
        """
        self._loader = loader

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        if self._loader is not None:
            df = self._loader_to_standard_columns(self._load_from_loader(query))
        else:
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

    def _load_from_loader(self, query: ProductionQuery) -> pd.DataFrame:
        """Load fixture/live monthly rows, using field-specific calls when present."""
        if query.fields and hasattr(self._loader, "load_field_production"):
            frames = [
                self._loader.load_field_production(field_name)
                for field_name in query.fields
            ]
            frames = [frame for frame in frames if frame is not None and len(frame) > 0]
            if not frames:
                return pd.DataFrame()
            return pd.concat(frames, ignore_index=True)
        return self._loader.load_all_production()

    @staticmethod
    def _loader_to_standard_columns(loader_df: pd.DataFrame) -> pd.DataFrame:
        """Map ``MonthlyProductionLoader`` output → unified ``STANDARD_COLUMNS``.

        Per #716 review B1:
          - add ``region="ncs"`` + ``source="sodir"``;
          - ``condensate_bbl = condensate_sm3 * SM3_TO_BBL`` (loader leaves
            condensate in Sm3 — it converts only oil/gas);
          - ``water_bbl = NaN`` — the loader's ``water_injected_sm3`` is
            INJECTION, not production; produced water is not available from this
            endpoint, so it is ABSENT (NaN per the AbstractProductionAdapter
            contract), never a false measured 0.
        """
        import numpy as np

        if loader_df is None or len(loader_df) == 0:
            return pd.DataFrame(columns=list(STANDARD_COLUMNS))
        out = pd.DataFrame(
            {
                "region": "ncs",
                "field_name": loader_df["field_name"].values,
                "year": loader_df["year"].values,
                "month": loader_df["month"].values,
                "oil_bbl": loader_df["oil_bbl"].values,
                "gas_mcf": loader_df["gas_mcf"].values,
                "water_bbl": np.nan,
                "condensate_bbl": (
                    loader_df["condensate_sm3"].astype(float) * _SM3_TO_BBL
                ).values,
                "source": "sodir",
            }
        )
        return out[list(STANDARD_COLUMNS)]

    def available_fields(self) -> List[str]:
        return [f[0] for f in self._FIELDS]

    def date_range(self) -> Tuple[str, str]:
        return ("1982-01", "2024-12")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        """Generate a simple hyperbolic-ish production profile."""
        rows = []
        year, month = start_year, start_month
        for i in range(n_months):
            # Simple decline: plateau for first 12 months then ~8 % annual
            if i < 12:
                factor = 1.0
            else:
                factor = 0.92 ** ((i - 12) / 12.0)

            rows.append(
                {
                    "region": "ncs",
                    "field_name": field_name,
                    "year": year,
                    "month": month,
                    "oil_bbl": round(peak_oil * factor, 0),
                    "gas_mcf": round(peak_gas * factor, 0),
                    "water_bbl": round(peak_water * min(factor * 1.5, 3.0), 0),
                    "condensate_bbl": round(peak_cond * factor, 0),
                    "source": "sodir_mock",
                }
            )
            month += 1
            if month > 12:
                month = 1
                year += 1

        return rows
