"""
Time Series Analysis for Safety Data

Build regular time series from irregular safety observations and incidents,
normalize by active assets, compute gradients and moving averages.

Generalized to work with any asset type (rigs, facilities, platforms)
via configurable column names.
"""

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class TimeSeriesBuilder:
    """Build regular time series from irregular event data."""

    def __init__(
        self,
        asset_id_column: str = "asset_id",
        datetime_column: str = "datetime",
        frequency: str = "W-SUN",
    ) -> None:
        self.asset_id_column = asset_id_column
        self.datetime_column = datetime_column
        self.frequency = frequency

    def approximate_asset_activity_periods(
        self,
        signals: List[pd.DataFrame],
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Determine min/max activity dates per asset across multiple signals.

        Args:
            signals: List of DataFrames, each with asset_id and datetime columns.
            min_date: Clip start dates to this minimum.
            max_date: Clip end dates to this maximum.

        Returns:
            DataFrame with columns: asset_id, start_date, end_date.
        """
        periods = None
        for signal in signals:
            sp = (
                signal.groupby(self.asset_id_column)
                .agg({self.datetime_column: ["min", "max"]})
                .reset_index()
            )
            sp.columns = [self.asset_id_column, "start_date", "end_date"]
            periods = sp if periods is None else pd.concat([periods, sp])

        periods = (
            periods.groupby(self.asset_id_column)
            .agg({"start_date": "min", "end_date": "max"})
            .reset_index()
        )

        if min_date is not None:
            periods["start_date"] = periods["start_date"].clip(
                lower=pd.Timestamp(min_date)
            )
        if max_date is not None:
            periods["end_date"] = periods["end_date"].clip(upper=pd.Timestamp(max_date))

        periods = periods[periods["start_date"] <= periods["end_date"]]
        return periods

    def collect_all_asset_ids(self, signals: List[pd.DataFrame]) -> np.ndarray:
        """Extract unique asset IDs across all signals."""
        ids = np.array([])
        for signal in signals:
            new_ids = signal[self.asset_id_column].dropna().unique()
            ids = np.append(ids, new_ids)
        return np.unique(ids)

    def create_binned_time_series(
        self,
        signal: pd.DataFrame,
        asset_ids: np.ndarray,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        Resample irregular events into regular time bins per asset.

        Returns DataFrame with datetime index, one column per asset,
        and a 'total' column.
        """
        index_dates = pd.date_range(start=start_date, end=end_date, freq=self.frequency)
        result = pd.DataFrame({"datetime": index_dates})

        filtered = signal[
            (signal[self.datetime_column] >= pd.Timestamp(start_date))
            & (signal[self.datetime_column] <= pd.Timestamp(end_date))
        ]

        for asset in asset_ids:
            asset_data = filtered[filtered[self.asset_id_column] == asset]
            binned = (
                asset_data.resample(
                    self.frequency, on=self.datetime_column, label="left"
                )
                .agg({self.asset_id_column: "count"})
                .reset_index()
            )
            binned.columns = ["datetime", str(asset)]
            result = pd.merge(result, binned, on="datetime", how="outer")

        asset_cols = [str(a) for a in asset_ids]
        result = result.fillna(0)
        result["total"] = result[asset_cols].sum(axis=1)
        result = result[
            (result["datetime"] >= pd.Timestamp(start_date))
            & (result["datetime"] <= pd.Timestamp(end_date))
        ]

        return result

    def create_multiple_binned_series(
        self,
        signals: List[pd.DataFrame],
        start_date: datetime,
        end_date: datetime,
    ) -> List[pd.DataFrame]:
        """Create binned time series for multiple signals."""
        asset_ids = self.collect_all_asset_ids(signals)
        return [
            self.create_binned_time_series(s, asset_ids, start_date, end_date)
            for s in signals
        ]

    def normalize_by_active_assets(
        self,
        time_series: pd.DataFrame,
        activity_periods: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Normalize time series counts by the number of active assets per bin.

        Args:
            time_series: Binned time series with 'datetime' and 'total' columns.
            activity_periods: DataFrame with asset_id, start_date, end_date.

        Returns:
            Input DataFrame with 'active_assets' and 'per_asset' columns added.
        """
        active_counts = []
        for dt in time_series["datetime"]:
            active = activity_periods[
                (activity_periods["start_date"] <= dt)
                & (activity_periods["end_date"] >= dt)
            ]
            active_counts.append(len(active))

        ts = time_series.copy()
        ts["active_assets"] = active_counts
        ts["per_asset"] = np.where(
            ts["active_assets"] > 0,
            ts["total"] / ts["active_assets"],
            0.0,
        )
        return ts


def calculate_gradient(
    time_series: pd.DataFrame, exclude_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Compute first differences (gradient) of a time series.

    Args:
        time_series: Regular time series DataFrame.
        exclude_columns: Columns to preserve without differencing.

    Returns:
        DataFrame of first differences, with excluded columns preserved.
    """
    exclude = set(exclude_columns or ["datetime", "active_assets"])
    gradient = time_series.copy()

    preserved = {}
    for col in exclude:
        if col in gradient.columns:
            preserved[col] = gradient[col].copy()
            gradient = gradient.drop(col, axis=1)

    gradient = gradient.diff().fillna(0)

    for col, values in preserved.items():
        gradient[col] = values

    return gradient


def calculate_moving_average(
    time_series: pd.DataFrame,
    window_size: int,
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """
    Calculate rolling mean of a time series.

    Args:
        time_series: Input time series.
        window_size: Rolling window size (in bins).
        datetime_column: Column to preserve.

    Returns:
        Smoothed DataFrame.
    """
    result = (
        time_series.drop(columns=[datetime_column], errors="ignore")
        .rolling(window=window_size)
        .mean()
    )
    if datetime_column in time_series.columns:
        result[datetime_column] = time_series[datetime_column].values
    return result


def calculate_multiple_moving_averages(
    time_series: pd.DataFrame,
    window_min: int,
    window_max: int,
    step: int = 1,
    datetime_column: str = "datetime",
) -> Dict[int, pd.DataFrame]:
    """Calculate moving averages for a range of window sizes."""
    averages = {}
    for w in range(window_min, window_max + 1, step):
        averages[w] = calculate_moving_average(time_series, w, datetime_column)
    return averages
