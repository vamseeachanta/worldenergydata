"""
ABOUTME: Arps decline curve analysis (exponential / hyperbolic / harmonic).
ABOUTME: Fits historical production to compute EUR and generate forecast curves.

Fitting uses scipy.optimize.curve_fit (nonlinear least squares).
All visualisations use Plotly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.optimize import curve_fit

_VALID_MODELS = frozenset({"exponential", "hyperbolic", "harmonic"})


@dataclass
class ForecastResult:
    """Result returned by :meth:`ArpsDeclineCurve.fit`.

    Attributes
    ----------
    model:
        Decline model used: ``'exponential'``, ``'hyperbolic'``, or ``'harmonic'``.
    qi:
        Fitted initial production rate (bbl/month).
    Di:
        Fitted nominal decline rate (1/month).
    b:
        Hyperbolic exponent (0 = exponential, 1 = harmonic).
    r_squared:
        Coefficient of determination for the fit.
    eur_bbl:
        Estimated ultimate recovery at the economic limit (bbl).
    forecast_df:
        Pre-populated forecast DataFrame with columns
        ``month``, ``rate_bbl``, ``cumulative_bbl``.
    lower_ci:
        Lower confidence interval DataFrame (optional).
    upper_ci:
        Upper confidence interval DataFrame (optional).
    """

    model: str
    qi: float
    Di: float
    b: float
    r_squared: float
    eur_bbl: float
    forecast_df: pd.DataFrame
    lower_ci: Optional[pd.DataFrame] = field(default=None)
    upper_ci: Optional[pd.DataFrame] = field(default=None)


class ArpsDeclineCurve:
    """Arps decline curve analysis for oil/gas production forecasting.

    Supports exponential (b=0), hyperbolic (0<b<2), and harmonic (b=1) models.

    Examples
    --------
    >>> adc = ArpsDeclineCurve()
    >>> result = adc.fit(production_df, model="hyperbolic")
    >>> fig = adc.plot(production_df, result)
    """

    def fit(
        self,
        production: pd.DataFrame,
        model: str = "hyperbolic",
        economic_limit: float = 10.0,
        months: int = 120,
    ) -> ForecastResult:
        """Fit an Arps decline curve to historical production data.

        Parameters
        ----------
        production:
            DataFrame with columns ``month`` (int, 1-based) and
            ``rate_bbl`` (float).
        model:
            Decline model: ``'exponential'``, ``'hyperbolic'``, or
            ``'harmonic'``.
        economic_limit:
            Economic limit rate in bbl/month for EUR computation.
        months:
            Number of months to pre-populate in ``forecast_df``.

        Returns
        -------
        ForecastResult
            Fitted parameters, R², EUR, and pre-populated forecast DataFrame.

        Raises
        ------
        ValueError
            If ``production`` is empty or ``model`` is not recognised.
        """
        if production.empty:
            raise ValueError("production DataFrame is empty")
        if model not in _VALID_MODELS:
            raise ValueError(
                f"Unknown model '{model}'. Valid models: {sorted(_VALID_MODELS)}"
            )

        t = production["month"].values.astype(float)
        q = production["rate_bbl"].values.astype(float)

        qi_fit, Di_fit, b_fit = self._fit_params(t, q, model)

        q_pred = self._rate_fn(model)(t, qi_fit, Di_fit, b_fit)
        r2 = self._r_squared(q, q_pred)
        eur = self._compute_eur(qi_fit, Di_fit, b_fit, economic_limit, model)

        forecast_df = self._build_forecast_df(qi_fit, Di_fit, b_fit, model, months)

        return ForecastResult(
            model=model,
            qi=float(qi_fit),
            Di=float(Di_fit),
            b=float(b_fit),
            r_squared=r2,
            eur_bbl=eur,
            forecast_df=forecast_df,
        )

    def forecast(self, result: ForecastResult, months: int = 120) -> pd.DataFrame:
        """Generate a forecast DataFrame from fitted parameters.

        Parameters
        ----------
        result:
            :class:`ForecastResult` with fitted model parameters.
        months:
            Number of months to forecast.

        Returns
        -------
        pd.DataFrame
            Columns: ``month``, ``rate_bbl``, ``cumulative_bbl``.
        """
        return self._build_forecast_df(result.qi, result.Di, result.b, result.model, months)

    def plot(self, historical: pd.DataFrame, result: ForecastResult) -> go.Figure:
        """Plot historical production and fitted decline curve / forecast.

        Parameters
        ----------
        historical:
            Historical production DataFrame with ``month`` and ``rate_bbl``.
        result:
            :class:`ForecastResult` from :meth:`fit`.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=historical["month"],
                y=historical["rate_bbl"],
                mode="markers",
                name="Historical",
                marker=dict(color="steelblue", size=6),
            )
        )

        fc = result.forecast_df
        fig.add_trace(
            go.Scatter(
                x=fc["month"],
                y=fc["rate_bbl"],
                mode="lines",
                name=f"Forecast ({result.model})",
                line=dict(color="firebrick", width=2),
            )
        )

        fig.update_layout(
            title=(
                f"Arps Decline Curve — {result.model.capitalize()}"
                f"  |  qi={result.qi:,.0f} bbl/mo"
                f"  |  R²={result.r_squared:.3f}"
                f"  |  EUR={result.eur_bbl:,.0f} bbl"
            ),
            xaxis_title="Month",
            yaxis_title="Production Rate (bbl/month)",
            template="plotly_white",
            legend=dict(x=0.7, y=0.95),
        )
        return fig

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fit_params(
        self,
        t: np.ndarray,
        q: np.ndarray,
        model: str,
    ) -> tuple[float, float, float]:
        """Run curve_fit and return (qi, Di, b)."""
        qi_guess = float(q[0])
        Di_guess = 0.05

        if model == "exponential":

            def _exp_fn(t, qi, Di):
                return qi * np.exp(-Di * t)

            popt, _ = curve_fit(
                _exp_fn,
                t,
                q,
                p0=[qi_guess, Di_guess],
                bounds=([0.0, 1e-6], [np.inf, np.inf]),
                maxfev=10_000,
            )
            return float(popt[0]), float(popt[1]), 0.0

        if model == "harmonic":

            def _harm_fn(t, qi, Di):
                return qi / (1.0 + Di * t)

            popt, _ = curve_fit(
                _harm_fn,
                t,
                q,
                p0=[qi_guess, Di_guess],
                bounds=([0.0, 1e-6], [np.inf, np.inf]),
                maxfev=10_000,
            )
            return float(popt[0]), float(popt[1]), 1.0

        # hyperbolic
        def _hyp_fn(t, qi, Di, b):
            return qi * (1.0 + b * Di * t) ** (-1.0 / b)

        popt, _ = curve_fit(
            _hyp_fn,
            t,
            q,
            p0=[qi_guess, Di_guess, 1.0],
            bounds=([0.0, 1e-6, 1e-6], [np.inf, np.inf, 2.0 - 1e-6]),
            maxfev=10_000,
        )
        return float(popt[0]), float(popt[1]), float(popt[2])

    def _rate_fn(self, model: str) -> Callable:
        """Return unified rate function ``f(t, qi, Di, b)`` for *model*."""
        if model == "exponential":
            def fn(t, qi, Di, b):  # b unused
                return qi * np.exp(-Di * t)
        elif model == "harmonic":
            def fn(t, qi, Di, b):  # b=1 enforced by math
                return qi / (1.0 + Di * t)
        else:  # hyperbolic
            def fn(t, qi, Di, b):
                return qi * (1.0 + b * Di * t) ** (-1.0 / b)
        return fn

    def _compute_eur(
        self,
        qi: float,
        Di: float,
        b: float,
        economic_limit: float,
        model: str,
    ) -> float:
        """Compute EUR (bbl) at *economic_limit* rate."""
        q_econ = max(economic_limit, 1.0)
        if qi <= q_econ:
            return 0.0

        if model == "exponential":
            t_econ = np.log(qi / q_econ) / Di
            eur = (qi / Di) * (1.0 - np.exp(-Di * t_econ))

        elif model == "harmonic":
            eur = (qi / Di) * np.log(qi / q_econ)

        else:  # hyperbolic
            if abs(b - 1.0) < 1e-6:
                # Degenerate case — use harmonic formula
                eur = (qi / Di) * np.log(qi / q_econ)
            else:
                eur = (qi**b / ((1.0 - b) * Di)) * (
                    qi ** (1.0 - b) - q_econ ** (1.0 - b)
                )

        return float(max(eur, 0.0))

    def _r_squared(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        """Coefficient of determination (R²)."""
        ss_res = float(np.sum((actual - predicted) ** 2))
        ss_tot = float(np.sum((actual - actual.mean()) ** 2))
        if ss_tot < 1e-12:
            return 1.0
        return 1.0 - ss_res / ss_tot

    def _build_forecast_df(
        self,
        qi: float,
        Di: float,
        b: float,
        model: str,
        months: int,
    ) -> pd.DataFrame:
        """Build forecast DataFrame for *months* periods."""
        t = np.arange(1, months + 1, dtype=float)
        rates = self._rate_fn(model)(t, qi, Di, b)
        cumulative = np.cumsum(rates)
        return pd.DataFrame(
            {
                "month": t.astype(int),
                "rate_bbl": rates,
                "cumulative_bbl": cumulative,
            }
        )
