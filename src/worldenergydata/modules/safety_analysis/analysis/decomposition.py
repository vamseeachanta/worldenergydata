"""
Seasonal Decomposition for Safety Time Series

Decompose safety signals into trend, seasonal, and residual components
using statsmodels.

Optional dependency: statsmodels.
"""

from typing import Any, List

import pandas as pd

from worldenergydata.modules.safety_analysis.exceptions import OptionalDependencyError

try:
    from statsmodels.tsa.seasonal import seasonal_decompose

    _HAS_STATSMODELS = True
except ImportError:
    _HAS_STATSMODELS = False


def _require_statsmodels() -> None:
    if not _HAS_STATSMODELS:
        raise OptionalDependencyError.missing("statsmodels", "safety-ml")


def decompose_signal(
    time_series: pd.DataFrame,
    column: str,
    period: int,
    model: str = "additive",
) -> Any:
    """
    Decompose a single time series column into trend, seasonal, residual.

    Args:
        time_series: DataFrame with the signal.
        column: Column name to decompose.
        period: Seasonal period (e.g., 52 for weekly data with yearly cycle).
        model: 'additive' or 'multiplicative'.

    Returns:
        statsmodels DecomposeResult with .trend, .seasonal, .resid, .observed.
    """
    _require_statsmodels()
    signal = time_series[column].copy()
    return seasonal_decompose(signal, model=model, period=period)


def remove_trend_and_seasonality(
    time_series: pd.DataFrame,
    periods: List[int],
    model: str = "additive",
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """
    Remove trend and seasonality from all numeric columns.

    Applies seasonal decomposition iteratively for each period,
    keeping only the residual component.

    Args:
        time_series: Input time series.
        periods: List of seasonal periods to remove.
        model: Decomposition model.
        datetime_column: Column to preserve.

    Returns:
        DataFrame of residuals with datetime column preserved.
    """
    _require_statsmodels()
    columns = [c for c in time_series.columns if c != datetime_column]
    signal = time_series[columns].copy()

    for p in periods:
        signal = signal.apply(
            lambda col, _p=p: seasonal_decompose(col, model=model, period=_p).resid
        )

    if datetime_column in time_series.columns:
        signal[datetime_column] = time_series[datetime_column].values

    return signal
