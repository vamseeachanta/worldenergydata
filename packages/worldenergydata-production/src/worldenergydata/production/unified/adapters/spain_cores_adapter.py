"""Spain CORES adapter for per-field monthly production (#763)."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery


class SpainCoresAdapter(AbstractProductionAdapter):
    """Spain CORES production adapter backed by fixture or injected loader."""

    region: str = "spain"

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
            frames = [frame for frame in frames if frame is not None and len(frame) > 0]
            if not frames:
                return pd.DataFrame()
            return pd.concat(frames, ignore_index=True)
        if hasattr(self.loader, "load_all_production"):
            return self.loader.load_all_production()
        if hasattr(self.loader, "load_oil_production") or hasattr(
            self.loader, "load_gas_production"
        ):
            return self._merge_product_frames()
        raise TypeError(
            "Spain CORES loader must expose load_all_production(), "
            "load_field_production(field_name), or product-specific "
            "load_oil_production()/load_gas_production() methods"
        )

    def _merge_product_frames(self) -> pd.DataFrame:
        frames = []
        keys = ["field_name", "year", "month"]
        if hasattr(self.loader, "load_oil_production"):
            frames.append(self.loader.load_oil_production())
        if hasattr(self.loader, "load_gas_production"):
            frames.append(self.loader.load_gas_production())
        frames = [frame for frame in frames if frame is not None and len(frame) > 0]
        if not frames:
            return pd.DataFrame()
        merged = frames[0].copy()
        for frame in frames[1:]:
            merged = merged.merge(frame, how="outer", on=keys)
        return merged

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
            loader_df,
            "condensate_bbl",
            default=np.nan,
        )
        out["source"] = "cores"
        return out[list(STANDARD_COLUMNS)]

    @staticmethod
    def _default_loader():
        try:
            from worldenergydata.spain.production.cores_loader import (
                CoresFixtureProductionLoader,
            )

            return CoresFixtureProductionLoader()
        except ModuleNotFoundError:
            return _EmbeddedCoresFixtureLoader()


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


class _EmbeddedCoresFixtureLoader:
    """Direct-source Ayoluengo sample fallback for production-only installs."""

    _ROWS = [
        {"field_name": "Ayoluengo", "year": 1968, "month": 1, "oil_bbl": 69356.46},
        {"field_name": "Ayoluengo", "year": 1968, "month": 2, "oil_bbl": 92160.09},
        {"field_name": "Ayoluengo", "year": 1968, "month": 3, "oil_bbl": 87468.89},
        {"field_name": "Ayoluengo", "year": 1968, "month": 4, "oil_bbl": 101175.99},
        {"field_name": "Ayoluengo", "year": 1968, "month": 5, "oil_bbl": 96712.02},
        {"field_name": "Ayoluengo", "year": 1968, "month": 6, "oil_bbl": 55656.69},
    ]

    def load_all_production(self) -> pd.DataFrame:
        frame = pd.DataFrame(self._ROWS)
        frame["gas_mcf"] = 0.0
        return frame

    def load_field_production(self, field_name: str) -> pd.DataFrame:
        frame = self.load_all_production()
        mask = frame["field_name"].astype(str).str.lower() == field_name.lower()
        return frame[mask].copy()
