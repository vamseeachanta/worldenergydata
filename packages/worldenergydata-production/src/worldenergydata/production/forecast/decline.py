"""
ABOUTME: Arps decline curve analysis (exponential / hyperbolic / harmonic).
ABOUTME: Fits historical production to compute EUR and generate forecast curves.

Fitting uses scipy.optimize.curve_fit (nonlinear least squares).
All visualisations use Plotly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from numbers import Integral, Real
from typing import Callable, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.optimize import curve_fit

from worldenergydata.common.decline import (
    exponential_rate,
    harmonic_rate,
    hyperbolic_rate,
)

_VALID_MODELS = frozenset({"exponential", "hyperbolic", "harmonic"})


def _comparable_rate(rate: Real) -> Real:
    """Keep NumPy promotion from rounding the other rate during comparison."""
    if isinstance(rate, np.integer):
        return int(rate)
    if isinstance(rate, np.floating):
        return Fraction(*rate.as_integer_ratio())
    return rate


@dataclass
class ForecastResult:
    """Result returned by Arps curve fitting or forward simulation.

    Attributes
    ----------
    model:
        Decline model used: ``'exponential'``, ``'hyperbolic'``, or ``'harmonic'``.
    qi:
        Initial production rate (bbl/month).
    Di:
        Nominal decline rate (1/month).
    b:
        Hyperbolic exponent (0 = exponential, 1 = harmonic).
    r_squared:
        Coefficient of determination for the fit; NaN for simulation.
    eur_bbl:
        Estimated ultimate recovery at the economic limit (bbl).
    forecast_df:
        Pre-populated forecast DataFrame with columns
        ``month``, ``rate_bbl``, ``cumulative_bbl``. Rates are month-end
        samples; cumulative values sum these samples, not integrated volumes.
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
        return self._build_forecast_df(
            result.qi, result.Di, result.b, result.model, months
        )

    def simulate(
        self,
        qi: float,
        Di: float,
        b: float,
        model: str,
        economic_limit: float,
        months: int,
    ) -> ForecastResult:
        """Evaluate explicit decline parameters without fitting historical data.

        ``qi`` and ``economic_limit`` are rates in bbl/month, ``Di`` is
        nominal decline in 1/month, and ``b`` is dimensionless. Rates and
        decline must be finite and positive. The exponent must be 0 for
        exponential, 1 for harmonic, or strictly positive for hyperbolic.
        ``months`` must be a positive integer. Booleans and duration scalars
        are invalid for all numeric parameters.

        EUR is in bbl and is zero when the limit is at or above ``qi``.
        If ``qi`` exceeds ``economic_limit`` but both round to the same
        float, simulation raises ``ValueError`` for the two rates.
        The limit must be at least 1 bbl/month, matching the existing EUR
        helper's minimum. The profile follows :meth:`forecast`: month-end
        rates at months 1 through ``months``, with their cumulative sum.
        These samples are not integrated monthly volumes. The horizon is
        fixed and is not truncated at the economic limit.

        Returns a :class:`ForecastResult` with ``r_squared=NaN`` and no
        confidence intervals because no fit occurred. Invalid inputs raise
        ``ValueError``. Fitting bounds on the hyperbolic exponent do not
        restrict this forward evaluation. Hyperbolic exponents above 1 are
        evaluated without physical qualification. Nonfinite EUR or profile
        fields raise ``ValueError`` without numerical overflow warnings.
        Profiles evaluate very small decay factors in log space to preserve
        representable month-end rates. Hyperbolic profiles preserve the
        exponential limit when the exponent-decline product underflows.
        An overflowing EUR intermediate can trigger rejection even when
        the mathematical recovery is finite.
        """
        if not isinstance(model, str) or model not in _VALID_MODELS:
            raise ValueError(
                f"Unknown model '{model}'. Valid models: {sorted(_VALID_MODELS)}"
            )
        validated = {}
        for name, value in (
            ("qi", qi),
            ("Di", Di),
            ("economic_limit", economic_limit),
            ("b", b),
        ):
            requirement = (
                "finite and nonnegative" if name == "b" else "finite and positive"
            )
            if isinstance(value, (bool, np.timedelta64)) or not isinstance(value, Real):
                raise ValueError(f"{name} must be {requirement}")
            try:
                value = float(value)
            except OverflowError as exc:
                raise ValueError(f"{name} must be {requirement}") from exc
            if not np.isfinite(value) or (value < 0 if name == "b" else value <= 0):
                raise ValueError(f"{name} must be {requirement}")
            validated[name] = value
        # Enforce exact boundaries before rounding accepted real inputs to float.
        if economic_limit < 1.0:
            raise ValueError("economic_limit must be at least 1 bbl/month")
        if (
            (model == "exponential" and b != 0)
            or (model == "harmonic" and b != 1)
            or (model == "hyperbolic" and (b <= 0 or validated["b"] <= 0))
        ):
            raise ValueError(f"b is inconsistent with model '{model}'")
        same_float_rate = validated["qi"] == validated["economic_limit"]
        if same_float_rate and _comparable_rate(qi) > _comparable_rate(economic_limit):
            raise ValueError("qi and economic_limit coincide at float precision")
        qi = validated["qi"]
        Di = validated["Di"]
        economic_limit = validated["economic_limit"]
        b = validated["b"]
        if (
            isinstance(months, (bool, np.timedelta64))
            or not isinstance(months, Integral)
            or months <= 0
        ):
            raise ValueError("months must be a positive integer")

        with np.errstate(over="ignore", invalid="ignore"):
            eur = self._compute_eur(qi, Di, b, economic_limit, model)
        if not np.isfinite(eur):
            raise ValueError("EUR is not representable in floating point")

        with np.errstate(over="ignore", invalid="ignore"):
            profile = self._build_forecast_df(qi, Di, b, model, int(months))
        if not np.isfinite(profile.to_numpy()).all():
            raise ValueError("Profile is not representable in floating point")

        return ForecastResult(
            model=model,
            qi=qi,
            Di=Di,
            b=b,
            r_squared=float("nan"),
            eur_bbl=eur,
            forecast_df=profile,
        )

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

            popt, _ = curve_fit(
                exponential_rate,
                t,
                q,
                p0=[qi_guess, Di_guess],
                bounds=([0.0, 1e-6], [np.inf, np.inf]),
                maxfev=10_000,
            )
            return float(popt[0]), float(popt[1]), 0.0

        if model == "harmonic":

            popt, _ = curve_fit(
                harmonic_rate,
                t,
                q,
                p0=[qi_guess, Di_guess],
                bounds=([0.0, 1e-6], [np.inf, np.inf]),
                maxfev=10_000,
            )
            return float(popt[0]), float(popt[1]), 1.0

        # hyperbolic
        popt, _ = curve_fit(
            hyperbolic_rate,
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
                return exponential_rate(t, qi, Di)

        elif model == "harmonic":

            def fn(t, qi, Di, b):  # b=1 enforced by math
                return harmonic_rate(t, qi, Di)

        else:  # hyperbolic

            def fn(t, qi, Di, b):
                return hyperbolic_rate(t, qi, Di, b)

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

        # Preserve adjacent floating-point rates before forming their ratio.
        log_ratio = np.log1p((qi - q_econ) / q_econ)
        if model == "exponential":
            eur = (qi - q_econ) / Di

        elif model == "harmonic":
            eur = (qi / Di) * log_ratio

        else:  # hyperbolic
            if b == 1.0:
                # Degenerate case — use harmonic formula
                eur = (qi / Di) * log_ratio
            else:
                # Use the rate ratio to avoid overflowing separate powers.
                x = (b - 1.0) * log_ratio
                if x > 50.0:
                    # Scale in log space before exponentiating: expm1(x) can
                    # overflow even when the full recovery is representable.
                    log_eur = (
                        np.log(qi)
                        - np.log(Di)
                        + x
                        + np.log1p(-np.exp(-x))
                        - np.log(b - 1.0)
                    )
                    eur = np.exp(log_eur)
                else:
                    # Preserve cancellation resistance near b = 1 and divide
                    # before scaling to avoid multiplication overflow.
                    rate_integral = np.expm1(x) / (b - 1.0)
                    eur = (qi / Di) * rate_integral

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
        rate_fn = self._rate_fn(model)
        exponent = 1.0 if model == "harmonic" else b
        if model != "exponential" and qi > 0 and Di > 0 and exponent > 0:
            with np.errstate(over="ignore", under="ignore"):
                log_decay = None
                if exponent * Di < np.finfo(float).tiny:
                    # Form Di*t first: rounding b*Di to a subnormal or zero
                    # loses its relative precision before division by b.
                    decline_time = Di * t
                    product = exponent * decline_time
                    correction = np.ones_like(product)
                    np.divide(
                        np.log1p(product), product, out=correction, where=product != 0
                    )
                    log_decay = -decline_time * correction
                    decay = np.exp(log_decay)
                else:
                    decay = rate_fn(t, 1.0, Di, b)
                rates = qi * decay
                # An overflowing denominator or a subnormal decay factor can
                # lose a representable rate before multiplication by qi.
                small = decay < np.finfo(float).tiny
                if small.any():
                    # Whitson manual, Decline Curve Analysis, web ed. 2026-10-19, §2.1.
                    # log(q) = log(qi) - log(1 + b*Di*t)/b.
                    if log_decay is None:
                        log_product = np.log(exponent) + np.log(Di) + np.log(t[small])
                        small_log_decay = -np.logaddexp(0.0, log_product) / exponent
                    else:
                        small_log_decay = log_decay[small]
                    rates[small] = np.exp(np.log(qi) + small_log_decay)
        elif model == "exponential" and qi > 0 and Di > 0:
            with np.errstate(over="ignore", under="ignore"):
                decay = np.exp(-Di * t)
                rates = qi * decay
                small = decay < np.finfo(float).tiny
                if small.any():
                    rates[small] = np.exp(np.log(qi) - Di * t[small])
        else:
            rates = rate_fn(t, qi, Di, b)
        cumulative = np.cumsum(rates)
        return pd.DataFrame(
            {
                "month": t.astype(int),
                "rate_bbl": rates,
                "cumulative_bbl": cumulative,
            }
        )
