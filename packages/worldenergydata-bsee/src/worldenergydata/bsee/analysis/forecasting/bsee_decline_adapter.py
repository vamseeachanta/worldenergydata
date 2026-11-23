"""Adapter bridging BSEE production data to sodir decline curve models.

Converts BSEE production DataFrames (monthly/annual) into (time, rate) arrays
suitable for ProductionForecaster.fit_decline_curve(). Handles data gaps,
shut-in periods, and rate conversions.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Columns in BSEE production data (annual totals from mv_productionsum.bin)
_OIL_VOL_CANDIDATES = ["MON_O_PROD_VOL", "OIL_STB", "OIL_PROD_VOL"]
_GAS_VOL_CANDIDATES = ["MON_G_PROD_VOL", "GAS_MCF", "GAS_PROD_VOL"]
_WATER_VOL_CANDIDATES = ["MON_WTR_PROD_VOL", "WATER_BBL", "WTR_PROD_VOL"]
_DATE_CANDIDATES = ["PRODUCTION_DATE", "PROD_YEAR", "PRODUCTION_DATETIME"]
_DAYS_CANDIDATES = ["DAYS_ON_PROD", "DAYS_PRODUCED"]
_FIELD_CANDIDATES = ["FIELD_NAME_CODE", "BOTM_FLD_NAME_CD", "FIELD_CODE", "BOEM_FIELD"]
_LEASE_CANDIDATES = ["LEASE_NUMBER", "LEASE_NUM"]


@dataclass
class ProductionTimeSeries:
    """Extracted time series ready for decline curve fitting."""

    time_indices: np.ndarray
    rates: np.ndarray
    dates: np.ndarray
    product_type: str
    field_name: str
    unit: str
    n_original: int
    n_after_filter: int
    shut_in_periods: int


def _pick_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
    """Find first matching column from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


class BseeDeclineAdapter:
    """Bridge between BSEE production data and sodir decline curve models."""

    def __init__(self, min_points: int = 3, shut_in_threshold_days: int = 5):
        self._min_points = min_points
        self._shut_in_threshold = shut_in_threshold_days

    def extract_field_production(
        self,
        production_df: pd.DataFrame,
        field_code: str,
        product: str = "oil",
    ) -> ProductionTimeSeries:
        """Extract production time series for a single field.

        Args:
            production_df: BSEE production DataFrame (monthly or annual).
            field_code: BSEE field code to filter on.
            product: "oil", "gas", or "water".

        Returns:
            ProductionTimeSeries ready for decline curve fitting.
        """
        field_col = _pick_col(production_df, _FIELD_CANDIDATES)
        if field_col is None:
            raise ValueError(
                f"No field column found. Expected one of: {_FIELD_CANDIDATES}"
            )

        field_df = production_df[
            production_df[field_col].astype(str) == str(field_code)
        ].copy()
        if field_df.empty:
            raise ValueError(f"No data found for field '{field_code}'")

        return self._extract_time_series(
            field_df, product=product, label=str(field_code)
        )

    def extract_lease_production(
        self,
        production_df: pd.DataFrame,
        lease_number: str,
        product: str = "oil",
    ) -> ProductionTimeSeries:
        """Extract production time series for a single lease."""
        lease_col = _pick_col(production_df, _LEASE_CANDIDATES)
        if lease_col is None:
            raise ValueError(
                f"No lease column found. Expected one of: {_LEASE_CANDIDATES}"
            )

        lease_df = production_df[
            production_df[lease_col].astype(str) == str(lease_number)
        ].copy()
        if lease_df.empty:
            raise ValueError(f"No data found for lease '{lease_number}'")

        return self._extract_time_series(
            lease_df, product=product, label=str(lease_number)
        )

    def extract_from_dataframe(
        self,
        df: pd.DataFrame,
        product: str = "oil",
        label: str = "custom",
    ) -> ProductionTimeSeries:
        """Extract time series from an already-filtered DataFrame."""
        return self._extract_time_series(df, product=product, label=label)

    def _extract_time_series(
        self,
        df: pd.DataFrame,
        product: str,
        label: str,
    ) -> ProductionTimeSeries:
        """Core extraction logic."""
        vol_col, unit = self._resolve_volume_column(df, product)
        date_col = _pick_col(df, _DATE_CANDIDATES)
        days_col = _pick_col(df, _DAYS_CANDIDATES)

        if date_col is None:
            raise ValueError(
                f"No date column found. Expected one of: {_DATE_CANDIDATES}"
            )

        # Aggregate by date period (sum across wells/completions)
        agg_dict = {vol_col: "sum"}
        if days_col:
            agg_dict[days_col] = "sum"

        grouped = df.groupby(date_col).agg(agg_dict).reset_index()
        grouped = grouped.sort_values(date_col)

        n_original = len(grouped)

        # Convert volume to daily rate if days available
        if days_col and days_col in grouped.columns:
            grouped["_rate"] = grouped[vol_col] / grouped[days_col].replace(0, np.nan)
            unit = f"{product}_per_day"
        else:
            grouped["_rate"] = grouped[vol_col]

        # Detect and exclude shut-in periods
        shut_in_mask = pd.Series(False, index=grouped.index)
        if days_col and days_col in grouped.columns:
            shut_in_mask = grouped[days_col] < self._shut_in_threshold
        shut_in_count = shut_in_mask.sum()

        active = grouped[~shut_in_mask].copy()

        # Drop zero/negative/NaN rates
        active = active[active["_rate"].notna() & (active["_rate"] > 0)]
        n_after = len(active)

        if n_after < self._min_points:
            raise ValueError(
                f"Insufficient data after filtering: {n_after} points "
                f"(need {self._min_points}). Original: {n_original}, "
                f"shut-in: {shut_in_count}"
            )

        rates = active["_rate"].values.astype(float)
        dates = active[date_col].values
        time_indices = np.arange(len(rates), dtype=float)

        return ProductionTimeSeries(
            time_indices=time_indices,
            rates=rates,
            dates=dates,
            product_type=product,
            field_name=label,
            unit=unit,
            n_original=n_original,
            n_after_filter=n_after,
            shut_in_periods=int(shut_in_count),
        )

    def _resolve_volume_column(self, df: pd.DataFrame, product: str) -> Tuple[str, str]:
        """Resolve volume column name based on product type."""
        if product == "oil":
            col = _pick_col(df, _OIL_VOL_CANDIDATES)
            unit = "bbl"
        elif product == "gas":
            col = _pick_col(df, _GAS_VOL_CANDIDATES)
            unit = "mcf"
        elif product == "water":
            col = _pick_col(df, _WATER_VOL_CANDIDATES)
            unit = "bbl"
        else:
            raise ValueError(f"Unknown product type: {product}")

        if col is None:
            raise ValueError(
                f"No {product} volume column found in DataFrame. "
                f"Columns: {list(df.columns)}"
            )
        return col, unit

    def load_production_binary(self, bin_path: Path) -> Optional[pd.DataFrame]:
        """Load a BSEE production .bin file, handling LFS stubs.

        Returns None if the file is an LFS stub.
        """
        if not bin_path.exists():
            logger.warning("Production binary not found: %s", bin_path)
            return None

        with open(bin_path, "rb") as f:
            header = f.read(40)

        if header.startswith(b"version https://git-lfs"):
            logger.info("LFS stub detected: %s", bin_path.name)
            return None

        try:
            return pd.read_pickle(bin_path)
        except Exception as e:
            logger.error("Failed to load %s: %s", bin_path, e)
            return None
