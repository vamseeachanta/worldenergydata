"""UKCS adapter — UK Continental Shelf production data.

When constructed with an NSTA loader, this adapter returns direct-source UKCS
production rows bridged to the unified ``STANDARD_COLUMNS`` contract. Without a
loader it retains the historical benchmark fixture used by legacy adapter tests.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery


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

    def __init__(self, loader=None):
        self.loader = loader

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        if self.loader is not None:
            loader_df = self._load_from_loader(query)
            df = self._loader_to_standard_columns(loader_df)
            df = self._filter_by_fields(df, query.fields)
            df = self._filter_by_date(df, query.start, query.end)
            return df.reset_index(drop=True)

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
        if self.loader is not None:
            df = self._loader_to_standard_columns(
                self._load_from_loader(ProductionQuery(regions=[self.region]))
            )
            return sorted(df["field_name"].dropna().unique().tolist())
        return [f[0] for f in self._FIELDS]

    def date_range(self) -> Tuple[str, str]:
        if self.loader is not None:
            df = self._loader_to_standard_columns(
                self._load_from_loader(ProductionQuery(regions=[self.region]))
            )
            if df.empty:
                return ("", "")
            periods = df["year"].astype(int) * 100 + df["month"].astype(int)
            start = periods.min()
            end = periods.max()
            return (
                f"{start // 100:04d}-{start % 100:02d}",
                f"{end // 100:04d}-{end % 100:02d}",
            )
        return ("1975-09", "2024-12")

    def _load_from_loader(self, query: ProductionQuery) -> pd.DataFrame:
        """Load normalized NSTA rows from a duck-typed fixture/live loader."""
        if query.fields and hasattr(self.loader, "load_field_production"):
            frames = [
                self.loader.load_field_production(field) for field in query.fields
            ]
            if not frames:
                return pd.DataFrame()
            return pd.concat(frames, ignore_index=True)
        if hasattr(self.loader, "load_all_production"):
            return self.loader.load_all_production()
        raise TypeError(
            "UKCS loader must expose load_all_production() or "
            "load_field_production(field_name)"
        )

    def _loader_to_standard_columns(self, loader_df: pd.DataFrame) -> pd.DataFrame:
        """Bridge UKCSFieldProductionLoader output into STANDARD_COLUMNS."""
        if loader_df is None or loader_df.empty:
            return self._empty_frame()

        out = pd.DataFrame()
        out["field_name"] = loader_df["field"].astype(str).str.strip().str.title()
        out["region"] = self.region
        out["year"] = loader_df["year"].astype(int)
        out["month"] = loader_df["month"].astype(int)
        out["oil_bbl"] = pd.to_numeric(loader_df["oil_bbl"], errors="coerce")
        out["gas_mcf"] = pd.to_numeric(loader_df["gas_mcf"], errors="coerce")
        out["water_bbl"] = pd.to_numeric(loader_df["water_bbl"], errors="coerce")
        out["condensate_bbl"] = np.nan
        out["source"] = "nsta"
        return out[list(STANDARD_COLUMNS)]

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
