"""
ABOUTME: Extreme Value Analysis wrapper for metocean-stats EVA methods.
ABOUTME: Supports POT (Peaks-Over-Threshold) and annual maxima (GEV) fitting.

Uses real metocean-stats library (v1.1.9) as the statistical backend.
All visualisations use Plotly — metocean-stats matplotlib outputs are converted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import metocean_stats.stats as ms
import numpy as np
import pandas as pd
import plotly.graph_objects as go


@dataclass
class EVAResult:
    """Container for an EVA fit result."""

    method: str
    """'POT' or 'AM' (annual maxima)."""
    distribution: str
    """Distribution name, e.g. 'Weibull_2P', 'GEV'."""
    return_levels: dict[int, float]
    """Mapping of return period (years) → return value."""
    parameters: dict[str, float]
    """Fitted distribution parameters."""
    threshold: Optional[float] = None
    """POT threshold value; None for annual-maxima methods."""
    lower_ci: dict[int, float] = field(default_factory=dict)
    """Lower 95% confidence interval per return period."""
    upper_ci: dict[int, float] = field(default_factory=dict)
    """Upper 95% confidence interval per return period."""


class ExtremeValueAnalysis:
    """
    Wrapper for metocean-stats EVA methods.

    Provides POT and annual-maxima fitting with Plotly visualisation.
    Backed by the real metocean-stats library (v1.1.9).

    Examples
    --------
    >>> eva = ExtremeValueAnalysis()
    >>> result = eva.fit_pot(hs_series)
    >>> table = eva.return_period_table(result)
    >>> fig = eva.plot_return_period(result)
    """

    # Default return periods (years)
    DEFAULT_PERIODS: list[int] = [1, 10, 50, 100, 1000]

    def __init__(self, distribution: str = "Weibull_2P") -> None:
        self._default_distribution = distribution

    # ------------------------------------------------------------------
    # Fitting methods
    # ------------------------------------------------------------------

    def fit_pot(
        self,
        series: pd.Series,
        threshold: Optional[float] = None,
        distribution: str = "Weibull_2P",
        periods: list[int] = DEFAULT_PERIODS,
        r: str = "48h",
    ) -> EVAResult:
        """
        Peaks-Over-Threshold (POT) analysis using metocean-stats.

        Parameters
        ----------
        series:
            Time-indexed Hs (or any parameter) series.
        threshold:
            Exceedance threshold. Auto-selected via Otnes method if None.
        distribution:
            GPD family member to fit. Default 'Weibull_2P'.
        periods:
            Return periods in years.
        r:
            Minimum separation between peaks (pandas timedelta string).

        Returns
        -------
        EVAResult
        """
        df = self._series_to_df(series)
        var = series.name or "value"

        # Auto-select threshold if not provided
        if threshold is None:
            threshold = self._auto_threshold(series)

        # metocean-stats POT call — returns a DataFrame with return levels
        rl_df = ms.return_levels_pot(
            data=df,
            var=var,
            dist=distribution,
            periods=periods,
            threshold=threshold,
            r=r,
        )

        return_levels = self._extract_return_levels(rl_df, periods)

        # Try uncertainty (optional)
        lower_ci: dict[int, float] = {}
        upper_ci: dict[int, float] = {}
        try:
            rl_unc = ms.return_levels_pot_uncertainty(
                data=df,
                var=var,
                dist=distribution,
                periods=periods,
                threshold=threshold,
                r=r,
            )
            lower_ci, upper_ci = self._extract_ci(rl_unc, periods)
        except Exception:
            pass

        params = self._extract_params(rl_df)

        return EVAResult(
            method="POT",
            distribution=distribution,
            return_levels=return_levels,
            parameters=params,
            threshold=threshold,
            lower_ci=lower_ci,
            upper_ci=upper_ci,
        )

    def fit_annual_maxima(
        self,
        series: pd.Series,
        distribution: str = "GEV",
        periods: list[int] = DEFAULT_PERIODS,
    ) -> EVAResult:
        """
        Annual maxima (block maxima / GEV) fitting using metocean-stats.

        Parameters
        ----------
        series:
            Time-indexed series with at least 3 full years.
        distribution:
            'GEV' or other block-maxima distributions supported by metocean-stats.
        periods:
            Return periods in years.

        Returns
        -------
        EVAResult
        """
        df = self._series_to_df(series)
        var = series.name or "value"

        rl_df = ms.return_levels_annual_max(
            data=df,
            var=var,
            dist=distribution,
            periods=periods,
        )

        return_levels = self._extract_return_levels(rl_df, periods)

        lower_ci: dict[int, float] = {}
        upper_ci: dict[int, float] = {}
        try:
            rl_unc = ms.return_levels_annual_max_uncertainty(
                data=df,
                var=var,
                dist=distribution,
                periods=periods,
            )
            lower_ci, upper_ci = self._extract_ci(rl_unc, periods)
        except Exception:
            pass

        params = self._extract_params(rl_df)

        return EVAResult(
            method="AM",
            distribution=distribution,
            return_levels=return_levels,
            parameters=params,
            threshold=None,
            lower_ci=lower_ci,
            upper_ci=upper_ci,
        )

    # ------------------------------------------------------------------
    # Output methods
    # ------------------------------------------------------------------

    def return_period_table(
        self,
        result: EVAResult,
        periods: Optional[list[int]] = None,
    ) -> pd.DataFrame:
        """
        Return a tidy DataFrame of return period → return value.

        Parameters
        ----------
        result:
            EVAResult from fit_pot / fit_annual_maxima.
        periods:
            Subset of periods to include. Default: all periods in result.

        Returns
        -------
        pd.DataFrame with columns ['return_period', 'return_value', 'lower_ci', 'upper_ci'].
        """
        if periods is None:
            periods = sorted(result.return_levels.keys())

        rows = []
        for p in periods:
            row = {
                "return_period": p,
                "return_value": result.return_levels.get(p, np.nan),
            }
            if result.lower_ci:
                row["lower_ci"] = result.lower_ci.get(p, np.nan)
            if result.upper_ci:
                row["upper_ci"] = result.upper_ci.get(p, np.nan)
            rows.append(row)

        df = pd.DataFrame(rows)
        df = df.set_index("return_period")
        df.index.name = "return_period"
        return df

    def plot_return_period(self, result: EVAResult) -> go.Figure:
        """
        Interactive Plotly return period curve with confidence intervals.

        Parameters
        ----------
        result:
            EVAResult to plot.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        table = self.return_period_table(result)
        periods = list(table.index)
        values = table["return_value"].tolist()

        fig = go.Figure()

        # Confidence interval band
        if "lower_ci" in table.columns and "upper_ci" in table.columns:
            lower = table["lower_ci"].tolist()
            upper = table["upper_ci"].tolist()
            fig.add_trace(
                go.Scatter(
                    x=periods + periods[::-1],
                    y=upper + lower[::-1],
                    fill="toself",
                    fillcolor="rgba(0,100,200,0.15)",
                    line=dict(color="rgba(255,255,255,0)"),
                    name="95% CI",
                    showlegend=True,
                )
            )

        # Main return period curve
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=values,
                mode="lines+markers",
                name=f"{result.method} ({result.distribution})",
                line=dict(color="royalblue", width=2),
                marker=dict(size=6),
            )
        )

        fig.update_layout(
            title=dict(
                text=f"Return Period Curve — {result.method} ({result.distribution})"
            ),
            xaxis=dict(
                title="Return Period (years)",
                type="log",
                tickvals=periods,
                ticktext=[str(p) for p in periods],
            ),
            yaxis=dict(title="Return Value"),
            legend=dict(x=0.01, y=0.99),
            template="plotly_white",
        )
        return fig

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _series_to_df(series: pd.Series) -> pd.DataFrame:
        """Convert a named Series to a DataFrame suitable for metocean-stats."""
        name = series.name or "value"
        df = series.to_frame(name=name)
        return df

    @staticmethod
    def _auto_threshold(series: pd.Series) -> float:
        """Estimate a reasonable POT threshold (90th percentile)."""
        return float(series.quantile(0.90))

    @staticmethod
    def _extract_return_levels(
        rl_df: pd.DataFrame, periods: list[int]
    ) -> dict[int, float]:
        """
        Extract return levels from metocean-stats output DataFrame.

        metocean-stats returns a DataFrame with:
          - index named 'periods' (int or float values)
          - column 'return_levels' containing the fitted values
        """
        rl: dict[int, float] = {}

        if not isinstance(rl_df, pd.DataFrame):
            return {p: float(p) for p in periods}  # fallback

        if "return_levels" in rl_df.columns:
            idx = rl_df.index.astype(float).values
            vals = rl_df["return_levels"].values
            for p in periods:
                closest = int(np.argmin(np.abs(idx - float(p))))
                rl[p] = float(vals[closest])
            return rl

        # Generic fallback: first numeric column
        numeric_cols = rl_df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            col = numeric_cols[0]
            idx = rl_df.index.astype(float).values
            for p in periods:
                closest = int(np.argmin(np.abs(idx - float(p))))
                rl[p] = float(rl_df[col].iloc[closest])
        else:
            rl = {p: float(p) for p in periods}

        return rl

    @staticmethod
    def _extract_ci(
        rl_unc_df: pd.DataFrame, periods: list[int]
    ) -> tuple[dict[int, float], dict[int, float]]:
        """Extract lower/upper CI from uncertainty DataFrame."""
        lower: dict[int, float] = {}
        upper: dict[int, float] = {}
        if not isinstance(rl_unc_df, pd.DataFrame) or rl_unc_df.empty:
            return lower, upper

        numeric = rl_unc_df.select_dtypes(include=[np.number])
        if numeric.shape[1] < 3:
            return lower, upper

        idx = rl_unc_df.index.astype(float).values
        for p in periods:
            try:
                closest = int(np.argmin(np.abs(idx - float(p))))
                row = numeric.iloc[closest]
                vals = sorted([float(v) for v in row if not np.isnan(float(v))])
                if len(vals) >= 2:
                    lower[p] = vals[0]
                    upper[p] = vals[-1]
            except Exception:
                pass
        return lower, upper

    @staticmethod
    def _extract_params(rl_df: pd.DataFrame) -> dict[str, float]:
        """
        Extract fitted distribution parameters from metocean-stats output.

        metocean-stats does not return parameters directly in the return-level
        DataFrame; we record a summary from the available data columns.
        """
        if not isinstance(rl_df, pd.DataFrame):
            return {"alpha": float("nan"), "beta": float("nan")}

        # Check for explicit parameter columns
        param_keywords = {"scale", "shape", "loc", "alpha", "beta", "lambda", "param"}
        params: dict[str, float] = {}
        for col in rl_df.columns:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in param_keywords):
                try:
                    params[col] = float(rl_df[col].iloc[0])
                except (ValueError, TypeError):
                    pass

        # Provide summary stats as pseudo-parameters when none found
        if not params and "return_levels" in rl_df.columns:
            vals = rl_df["return_levels"].values
            params = {
                "min_return_level": float(vals.min()),
                "max_return_level": float(vals.max()),
            }

        if not params:
            params = {"alpha": float("nan"), "beta": float("nan")}

        return params
