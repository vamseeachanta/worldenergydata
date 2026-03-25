"""
ABOUTME: Weather window and operability analysis wrapping metocean-stats.
ABOUTME: Computes operability %, persistence statistics, and monthly heatmaps.

Uses real metocean-stats library (v1.1.9) as the statistical backend.
All visualisations use Plotly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import metocean_stats.stats as ms


@dataclass
class OperabilityResult:
    """Container for an operability / weather window analysis result."""

    threshold: float
    """Operability threshold (same units as input series)."""
    min_window_hours: int
    """Minimum continuous operable window in hours."""
    operability_pct: float
    """Percentage of time the series is below threshold."""
    mean_window_hours: float
    """Mean length of operable windows (hours)."""
    total_windows: int
    """Total number of operable windows found."""
    window_lengths_hours: Optional[np.ndarray] = None
    """Array of individual window durations in hours."""


class WeatherWindowAnalysis:
    """
    Operability and weather window analysis backed by metocean-stats.

    Wraps ``metocean_stats.stats.nb_hours_below_threshold`` and
    ``metocean_stats.stats.weather_window_length`` with a clean API
    and Plotly visualisation.

    Examples
    --------
    >>> wwa = WeatherWindowAnalysis()
    >>> result = wwa.operability(hs_series, threshold=2.5)
    >>> monthly_df = wwa.monthly_operability(hs_series, threshold=2.5)
    >>> fig = wwa.plot_monthly_heatmap(monthly_df)
    """

    # ------------------------------------------------------------------
    # Operability
    # ------------------------------------------------------------------

    def operability(
        self,
        series: pd.Series,
        threshold: float = 2.5,
        min_window_hours: int = 12,
    ) -> OperabilityResult:
        """
        Compute operability % and persistence statistics.

        Parameters
        ----------
        series:
            Time-indexed metocean parameter (e.g. Hs in metres).
        threshold:
            Maximum allowable value for operation.
        min_window_hours:
            Minimum continuous window required for an operation.

        Returns
        -------
        OperabilityResult
        """
        df = self._series_to_df(series)
        var = series.name or "value"
        timestep_hours = self._infer_timestep_hours(series)

        # nb_hours_below_threshold: returns array (1 threshold, n_years)
        nbhr = ms.nb_hours_below_threshold(df, var=var, thr_arr=[threshold])
        # Sum across all years, divide by total hours for percentage
        total_hours = len(series) * timestep_hours
        hours_below = float(nbhr[0].sum())
        operability_pct = min(100.0, hours_below / total_hours * 100.0) if total_hours > 0 else 0.0

        # Weather window lengths for the full series (all year)
        try:
            ww_lengths = ms.weather_window_length(
                time_series=series,
                threshold=threshold,
                op_duration=min_window_hours,
                timestep=timestep_hours,
            )
            if ww_lengths is None or len(ww_lengths) == 0:
                ww_arr = np.array([])
            else:
                ww_arr = np.asarray(ww_lengths, dtype=float)
        except Exception:
            ww_arr = np.array([])

        total_windows = int(np.sum(ww_arr > 0)) if len(ww_arr) > 0 else 0
        mean_window = float(np.mean(ww_arr[ww_arr > 0])) if total_windows > 0 else 0.0

        return OperabilityResult(
            threshold=threshold,
            min_window_hours=min_window_hours,
            operability_pct=round(operability_pct, 2),
            mean_window_hours=round(mean_window, 2),
            total_windows=total_windows,
            window_lengths_hours=ww_arr,
        )

    # ------------------------------------------------------------------
    # Monthly operability
    # ------------------------------------------------------------------

    def monthly_operability(
        self,
        series: pd.Series,
        threshold: float = 2.5,
    ) -> pd.DataFrame:
        """
        Compute per-month operability percentage.

        Parameters
        ----------
        series:
            Time-indexed metocean parameter.
        threshold:
            Operability threshold.

        Returns
        -------
        pd.DataFrame
            12-row DataFrame indexed by month number (1-12).
            Columns: ['month_name', 'operability_pct'].
            Values are in [0, 100].
        """
        months = range(1, 13)
        records = []
        for month in months:
            monthly_data = series[series.index.month == month]
            if len(monthly_data) == 0:
                pct = 0.0
            else:
                n_below = (monthly_data < threshold).sum()
                pct = round(n_below / len(monthly_data) * 100.0, 2)
            records.append(
                {
                    "month": month,
                    "month_name": pd.Timestamp(2000, month, 1).strftime("%b"),
                    "operability_pct": pct,
                }
            )

        df = pd.DataFrame(records).set_index("month")
        return df

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def plot_monthly_heatmap(
        self,
        monthly_df: pd.DataFrame,
        title: str = "Monthly Operability",
    ) -> go.Figure:
        """
        Plotly monthly operability heatmap.

        Parameters
        ----------
        monthly_df:
            DataFrame returned by ``monthly_operability``.
        title:
            Plot title.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        if "month_name" in monthly_df.columns:
            month_labels = monthly_df["month_name"].tolist()
        else:
            month_labels = [
                pd.Timestamp(2000, m, 1).strftime("%b")
                for m in monthly_df.index
            ]

        if "operability_pct" in monthly_df.columns:
            values = monthly_df["operability_pct"].tolist()
        else:
            # Take first numeric column
            numeric = monthly_df.select_dtypes(include=[np.number])
            values = numeric.iloc[:, 0].tolist() if not numeric.empty else [0.0] * 12

        fig = go.Figure(
            data=go.Heatmap(
                z=[values],
                x=month_labels,
                y=["Operability (%)"],
                colorscale="RdYlGn",
                zmin=0,
                zmax=100,
                text=[[f"{v:.1f}%" for v in values]],
                texttemplate="%{text}",
                showscale=True,
                colorbar=dict(title="Operability (%)"),
            )
        )

        fig.update_layout(
            title=title,
            xaxis=dict(title="Month"),
            yaxis=dict(title=""),
            template="plotly_white",
            height=250,
        )
        return fig

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _series_to_df(series: pd.Series) -> pd.DataFrame:
        """Convert a named Series to a DataFrame suitable for metocean-stats."""
        name = series.name or "value"
        return series.to_frame(name=name)

    @staticmethod
    def _infer_timestep_hours(series: pd.Series) -> float:
        """Infer the time step in hours from a DatetimeIndex series."""
        if len(series) < 2:
            return 1.0
        diffs = pd.Series(series.index).diff().dropna()
        median_seconds = diffs.dt.total_seconds().median()
        return median_seconds / 3600.0
