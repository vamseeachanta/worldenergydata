"""Canada adapter — C-NLOER offshore Newfoundland production (#719).

DI-loader adapter (mirrors ``SodirAdapter``/``SpainCoresAdapter``): a real
C-NLOER loader (or an injected duck-typed loader) supplies per-field monthly
rows; the bare default loads the committed labeled-synthetic fixture. Replaces
the previous self-contained synthetic peak-rate mock.

``condensate_bbl``/``water_bbl`` defaulting: C-NLOER publishes water but no
condensate stream → ``condensate_bbl`` is NaN.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery


class CanadaAdapter(AbstractProductionAdapter):
    """Canadian offshore Newfoundland (C-NLOER) production adapter."""

    region: str = "canada"

    def __init__(self, loader=None):
        self.loader = loader if loader is not None else self._default_loader()

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        df = self._loader_to_standard_columns(self._load_from_loader(query))
        df = self._filter_by_fields(df, query.fields)
        df = self._filter_by_date(df, query.start, query.end)
        return df.reset_index(drop=True)

    def available_fields(self) -> List[str]:
        df = self._loader_to_standard_columns(
            self._load_from_loader(ProductionQuery(regions=[self.region]))
        )
        return sorted(df["field_name"].dropna().unique().tolist())

    def date_range(self) -> Tuple[str, str]:
        df = self._loader_to_standard_columns(
            self._load_from_loader(ProductionQuery(regions=[self.region]))
        )
        if df.empty:
            return ("", "")
        periods = df["year"].astype(int) * 100 + df["month"].astype(int)
        start = int(periods.min())
        end = int(periods.max())
        return (
            f"{start // 100:04d}-{start % 100:02d}",
            f"{end // 100:04d}-{end % 100:02d}",
        )

    def _load_from_loader(self, query: ProductionQuery) -> pd.DataFrame:
        if query.fields and hasattr(self.loader, "load_field_production"):
            frames = [
                self.loader.load_field_production(field_name)
                for field_name in query.fields
            ]
            frames = [f for f in frames if f is not None and len(f) > 0]
            if not frames:
                return pd.DataFrame()
            return pd.concat(frames, ignore_index=True)
        if hasattr(self.loader, "load_all_production"):
            return self.loader.load_all_production()
        raise TypeError(
            "Canada C-NLOER loader must expose load_all_production() or "
            "load_field_production(field_name)"
        )

    def _loader_to_standard_columns(self, loader_df: pd.DataFrame) -> pd.DataFrame:
        if loader_df is None or loader_df.empty:
            return self._empty_frame()

        out = pd.DataFrame()
        out["field_name"] = loader_df["field_name"].astype(str).str.strip()
        out["region"] = self.region
        out["year"] = loader_df["year"].astype(int)
        out["month"] = loader_df["month"].astype(int)
        out["oil_bbl"] = _numeric_or_default(loader_df, "oil_bbl", default=0.0)
        out["gas_mcf"] = _numeric_or_default(loader_df, "gas_mcf", default=0.0)
        out["water_bbl"] = _numeric_or_default(loader_df, "water_bbl", default=np.nan)
        out["condensate_bbl"] = _numeric_or_default(
            loader_df, "condensate_bbl", default=np.nan
        )
        if "source" in loader_df.columns:
            out["source"] = loader_df["source"].astype(str).values
        else:
            out["source"] = "cnloer"
        return out[list(STANDARD_COLUMNS)]

    @staticmethod
    def _default_loader():
        from worldenergydata.canada.production.cnloer_loader import (
            CnloerFixtureLoader,
        )

        return CnloerFixtureLoader()


def _numeric_or_default(
    frame: pd.DataFrame,
    column: str,
    *,
    default: float,
) -> pd.Series:
    if column in frame.columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if pd.isna(default):
            return values
        return values.fillna(default)
    return pd.Series(default, index=frame.index, dtype="float64")
