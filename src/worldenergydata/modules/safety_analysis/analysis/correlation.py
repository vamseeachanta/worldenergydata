"""
Lag Correlation Analysis for Safety Data

Compute lag-N cross-correlation between observation counts and incident
counts to identify leading/lagging indicator relationships.

Ported from ENIGMA sshe_lib_correlation_tools.py.
"""

import numpy as np
import pandas as pd

from worldenergydata.modules.safety_analysis.core.models import CorrelationResult
from worldenergydata.modules.safety_analysis.exceptions import SafetyCorrelationError


def crosscorr(
    datax: pd.Series, datay: pd.Series, lag: int = 0, wrap: bool = False
) -> float:
    """
    Compute lag-N cross-correlation between two Series.

    Args:
        datax: First series.
        datay: Second series (will be shifted).
        lag: Number of periods to shift datay.
        wrap: If True, wrap shifted values instead of filling NaN.

    Returns:
        Pearson correlation coefficient at the given lag.
    """
    if wrap:
        shiftedy = datay.shift(lag)
        shiftedy.iloc[:lag] = datay.iloc[-lag:].values
        return datax.corr(shiftedy)
    return datax.corr(datay.shift(lag))


class LaggedCrossCorrelation:
    """Compute and analyze lagged cross-correlations."""

    def __init__(
        self,
        lag_min: int = -30,
        lag_max: int = 30,
        min_observations: int = 30,
    ) -> None:
        self.lag_min = lag_min
        self.lag_max = lag_max
        self.min_observations = min_observations

    def compute(
        self,
        observations: pd.Series,
        incidents: pd.Series,
        asset_id: str = "unknown",
    ) -> CorrelationResult:
        """
        Compute cross-correlation across a range of lags.

        Args:
            observations: Observation count time series.
            incidents: Incident count time series.
            asset_id: Identifier for the asset being analyzed.

        Returns:
            CorrelationResult with lag values, correlations, and peak info.

        Raises:
            SafetyCorrelationError: If insufficient data points.
        """
        n_obs = min(len(observations.dropna()), len(incidents.dropna()))
        if n_obs < self.min_observations:
            raise SafetyCorrelationError.insufficient_data(
                asset_id, self.min_observations, n_obs
            )

        lags = list(range(self.lag_min, self.lag_max + 1))
        correlations = [crosscorr(observations, incidents, lag) for lag in lags]

        # Replace NaN correlations with 0
        correlations = [0.0 if np.isnan(c) else c for c in correlations]

        abs_corrs = [abs(c) for c in correlations]
        peak_idx = int(np.argmax(abs_corrs))
        peak_lag = lags[peak_idx]
        peak_corr = correlations[peak_idx]

        return CorrelationResult(
            asset_id=asset_id,
            lag_values=lags,
            correlation_values=correlations,
            peak_correlation=peak_corr,
            peak_lag=peak_lag,
        )

    def compute_rolling(
        self,
        observations: pd.Series,
        incidents: pd.Series,
        window_size: int = 16,
        step_size: int = 1,
    ) -> pd.DataFrame:
        """
        Compute rolling windowed time-lagged cross-correlation.

        Returns a DataFrame where each row is a window epoch and each
        column is a lag value, with correlation as values (heatmap-ready).
        """
        pad = abs(self.lag_min)
        max_t = max(len(observations), len(incidents))
        t_start = pad
        t_end = t_start + window_size

        results = []
        while t_end < max_t - pad:
            obs_window = observations.iloc[t_start - pad : t_end + pad]
            inc_window = incidents.iloc[t_start - pad : t_end + pad]
            row = [
                crosscorr(obs_window, inc_window, lag)
                for lag in range(self.lag_min, self.lag_max + 1)
            ]
            row = [0.0 if np.isnan(c) else c for c in row]
            results.append(row)
            t_start += step_size
            t_end += step_size

        lags = list(range(self.lag_min, self.lag_max + 1))
        return pd.DataFrame(results, columns=lags)


def create_observation_counts(
    observations: pd.DataFrame,
    datetime_column: str = "observed_at",
    asset_id_column: str = "asset_id",
) -> pd.DataFrame:
    """
    Count observations per day per asset.

    Returns DataFrame with datetime index, asset_id, and obs_count columns.
    """
    df = observations.copy()
    df["_count"] = 1
    result = (
        df.groupby([datetime_column, asset_id_column])
        .agg({"_count": "count"})
        .reset_index()
    )
    result.columns = [datetime_column, asset_id_column, "obs_count"]
    result = result.set_index(datetime_column)
    return result


def create_incident_counts(
    incidents: pd.DataFrame,
    datetime_column: str = "occurred_at",
    asset_id_column: str = "asset_id",
) -> pd.DataFrame:
    """
    Count incidents per day per asset.

    Returns DataFrame with datetime index, asset_id, and inc_count columns.
    """
    df = incidents.copy()
    df["_count"] = 1
    result = (
        df.groupby([datetime_column, asset_id_column])
        .agg({"_count": "count"})
        .reset_index()
    )
    result.columns = [datetime_column, asset_id_column, "inc_count"]
    result = result.set_index(datetime_column)
    return result


def extract_asset_rates(
    counts: pd.DataFrame,
    asset_id: str,
    start: str,
    end: str,
    freq: str = "D",
    asset_id_column: str = "asset_id",
    count_column: str = "inc_count",
) -> pd.DataFrame:
    """
    Extract daily event rates for a single asset over a date range.

    Fills missing dates with zeros.
    """
    rng = pd.date_range(start, end, freq=freq)
    ts = pd.DataFrame({count_column: np.zeros(len(rng))}, index=rng)

    asset_data = counts[counts[asset_id_column] == asset_id]
    if not asset_data.empty:
        ts[count_column] = asset_data[count_column]
        ts[count_column] = ts[count_column].fillna(0)

    return ts
