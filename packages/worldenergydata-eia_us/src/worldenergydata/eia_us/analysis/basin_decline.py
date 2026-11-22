"""Empirical Arps decline with a horizon-independent exponential tail.

Method and derivation (t in months; qi in bopd or Mcfd; Di in 1/month)::

    q(t) = qi / (1 + b*Di*t)**(1/b)
    D(t) = -d(log(q))/dt = Di / (1 + b*Di*t)
    ts = (Di/Dterminal - 1) / (b*Di)
    q(t > ts) = q(ts) * exp(-Dterminal*(t - ts))

For b>0 and Di>Dterminal, the exact, possibly fractional ts is where
D(t) reaches the configured nominal terminal decline rate. Both rate and
slope q'=-D*q are continuous. The constant Arps exponent b does not fall
with time: b=0 is exponential, b=0.5 is still hyperbolic. If Di is already
at or below the limit, an exponential starts at t=0 with Di, preserving
the initial slope. Di=0 remains flat; b=0 remains exponential with Di.
Forecast samples start at the fitted origin, including observed months.

Public basis:
* EIA, Production Decline Curve Analysis in the Annual Energy Outlook 2020
  (March 18, 2020), methodology paragraph on the terminal transition:
  https://www.eia.gov/analysis/drilling/curve_analysis/2020/
* IHS Harmony, Decline Analysis Theory (February 24, 2020), sections
  "Exponential Decline Rate: Nominal vs. Effective", "Limited Decline Rate"
  and "Practical Decline Analysis Key Points":
  https://www.ihsenergy.ca/support/documentation_ca/Harmony/content/html_files/reference_material/analysis_method_theory/decline_theory.htm

The default interprets EIA's stated monthly 0.8% as an effective monthly
fraction and converts it to nominal Dterminal=-log(1-0.008). This explicit
modelling convention does not reproduce the full EIA estimation procedure
or its rounded annual equivalent. A caller can supply a different nominal
monthly limit or disable switching.

Applicability: traditional Arps extrapolation assumes boundary-dominated
flow and stable operating conditions. Fits with b>1 are empirical extensions,
not evidence of that flow regime. Basin aggregates can include new wells and
operating changes; fitting them does not establish well reserves or forecast
accuracy. Inputs require consistent rate units and equally spaced monthly
observations. No calendar normalization, flow-regime detection, economic
limit, EUR or uncertainty qualification is performed here.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.optimize import curve_fit

# Deprecated compatibility constant; not a physical transition criterion.
TERMINAL_B_FACTOR: float = 0.5

# Nominal 1/month, from an assumed effective monthly fraction of 0.008.
# Basis and the scope of this interpretation are documented above.
TERMINAL_DECLINE_RATE: float = float(-np.log1p(-0.008))

# Minimum data points required for fitting
_MIN_DATA_POINTS: int = 6


# ── Arps hyperbolic equation ───────────────────────────────────────────────────


def arps_hyperbolic(t: float, qi: float, di: float, b: float) -> float:
    """Compute Arps hyperbolic production rate at time t.

    Args:
        t: Time in months (0 = start).
        qi: Initial rate at t=0.
        di: Initial nominal decline rate (per month, >= 0; zero is flat).
        b: Hyperbolic exponent (>= 0; > 1 is an empirical extension;
           1 = harmonic; 0 = exponential).

    Returns:
        Production rate q(t) >= 0.
    """
    if b == 0.0:
        # Limiting case: exponential
        return qi * np.exp(-di * t)
    denominator = (1.0 + b * di * t) ** (1.0 / b)
    return qi / denominator


# ── Model ──────────────────────────────────────────────────────────────────────


class HyperbolicDeclineModel:
    """Arps hyperbolic decline model with optional terminal decline switch.

    Attributes:
        qi: Initial rate.
        di: Initial nominal decline rate (per month).
        b: Hyperbolic exponent.
        terminal_b: Deprecated compatibility option: None disables switching;
            a finite nonnegative number enables it, regardless of b. Its value
            is no longer a threshold. Deprecation is documentation-only.
        terminal_decline_rate: Positive nominal monthly limit; None disables
            switching. Either None option takes precedence over the other.
            Positive b values, including b<=0.5, use the same rate criterion.
    """

    def __init__(
        self,
        qi: float,
        di: float,
        b: float,
        terminal_b: Optional[float] = TERMINAL_B_FACTOR,
        terminal_decline_rate: Optional[float] = TERMINAL_DECLINE_RATE,
    ) -> None:
        for name, value in (
            ("qi", qi),
            ("di", di),
            ("b", b),
            ("terminal_b", terminal_b),
        ):
            if name == "terminal_b" and value is None:
                continue
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative.")
        if terminal_decline_rate is not None and (
            not np.isfinite(terminal_decline_rate) or terminal_decline_rate <= 0
        ):
            raise ValueError(
                "terminal_decline_rate must be finite and positive or None."
            )
        self.qi = qi
        self.di = di
        self.b = b
        self.terminal_b = terminal_b
        self.terminal_decline_rate = terminal_decline_rate

    def predict(self, n_months: int) -> np.ndarray:
        """Generate n_months forecast using hyperbolic (+ terminal switch).

        Args:
            n_months: Nonnegative integer sample count, starting at month zero.

        Returns:
            Array of production rates, all >= 0.
        """
        if (
            isinstance(n_months, bool)
            or not isinstance(n_months, (int, np.integer))
            or n_months < 0
        ):
            raise ValueError("n_months must be a nonnegative integer.")
        t = np.arange(n_months, dtype=float)
        rates = np.array([arps_hyperbolic(ti, self.qi, self.di, self.b) for ti in t])

        # Apply terminal decline switch if configured
        if self.terminal_b is not None and self.terminal_decline_rate is not None:
            rates = self._apply_terminal_switch(t, rates)

        return np.maximum(rates, 0.0)

    def _apply_terminal_switch(self, t: np.ndarray, rates: np.ndarray) -> np.ndarray:
        """Join rate and nominal decline at an analytical, fixed crossing time."""
        if self.terminal_decline_rate is None or self.b == 0.0 or self.di == 0.0:
            return rates

        d_terminal = min(self.di, self.terminal_decline_rate)
        switch_time = (self.di / d_terminal - 1.0) / (self.b * self.di)
        tail_indices = np.flatnonzero(t > switch_time)
        if len(tail_indices) == 0:
            return rates
        q_switch = arps_hyperbolic(switch_time, self.qi, self.di, self.b)
        result = rates.copy()
        # Scalar evaluation keeps identical samples bitwise equal across horizons.
        for i in tail_indices:
            result[i] = q_switch * np.exp(-d_terminal * (t[i] - switch_time))
        return result


# ── Result ─────────────────────────────────────────────────────────────────────


@dataclass
class ShaleDeclineResult:
    """Fitted shale hyperbolic decline result for a basin.

    Diagnostics describe the fitted hyperbolic objective at observation times,
    before the forecast terminal switch. R-squared can be negative; RMSE has
    the same production-rate unit as the supplied observations.
    """

    basin: str
    model: HyperbolicDeclineModel
    r_squared: float
    rmse: float

    def predict(self, n_months: int) -> np.ndarray:
        """Delegate to the underlying HyperbolicDeclineModel."""
        return self.model.predict(n_months)


# ── Analyzer ───────────────────────────────────────────────────────────────────


class DeclineFitError(RuntimeError):
    """The optimizer failed; no fitted result is available.

    The original optimizer exception is retained as the chained cause.
    """


class ShaleDeclineAnalyzer:
    """Fit Arps hyperbolic decline curve to shale basin production data."""

    def fit(
        self,
        production: np.ndarray,
        basin: str = "Unknown",
        b_min: float = 0.5,
        b_max: float = 3.0,
    ) -> ShaleDeclineResult:
        """Fit hyperbolic decline to observed production data.

        Args:
            production: Array of monthly production rates (bopd or Mcfd).
            basin: Basin name for labelling the result.
            b_min: Minimum b-factor for fitting.
            b_max: Maximum b-factor for fitting.

        Returns:
            ShaleDeclineResult with fitted parameters.

        Raises:
            ValueError: If production has fewer than _MIN_DATA_POINTS or the
                fitting bounds do not satisfy finite 0 <= b_min < b_max.
            DeclineFitError: If curve_fit raises RuntimeError or ValueError;
                initial guesses are never returned as a fitted result.
        """
        if len(production) < _MIN_DATA_POINTS:
            raise ValueError(
                f"Insufficient data: need at least {_MIN_DATA_POINTS} months, "
                f"got {len(production)}."
            )

        if not (np.isfinite(b_min) and np.isfinite(b_max) and 0 <= b_min < b_max):
            raise ValueError("b_min and b_max must be finite with 0 <= b_min < b_max.")

        t = np.arange(len(production), dtype=float)
        qi_guess = float(production[0]) if production[0] > 0 else 1.0
        di_guess = 0.08
        b_guess = 1.5

        try:
            popt, _ = curve_fit(
                arps_hyperbolic,
                t,
                production,
                p0=[qi_guess, di_guess, b_guess],
                bounds=(
                    [0.0, 1e-6, b_min],
                    [qi_guess * 10, 2.0, b_max],
                ),
                maxfev=5000,
            )
            qi_fit, di_fit, b_fit = popt
        except (RuntimeError, ValueError) as exc:
            raise DeclineFitError("Hyperbolic decline fit failed.") from exc

        model = HyperbolicDeclineModel(qi=qi_fit, di=di_fit, b=b_fit)

        predicted = arps_hyperbolic(t, qi_fit, di_fit, b_fit)
        r_squared = self._r_squared(production, predicted)
        rmse = float(np.sqrt(np.mean((production - predicted) ** 2)))

        return ShaleDeclineResult(
            basin=basin,
            model=model,
            r_squared=r_squared,
            rmse=rmse,
        )

    @staticmethod
    def _r_squared(observed: np.ndarray, predicted: np.ndarray) -> float:
        """Compute R² without clipping negative values.

        Constant observations have undefined R². Preserve the existing
        degenerate convention: one for an exact match, zero otherwise.
        """
        ss_res = np.sum((observed - predicted) ** 2)
        ss_tot = np.sum((observed - np.mean(observed)) ** 2)
        if ss_tot == 0.0:
            return 1.0 if ss_res == 0.0 else 0.0
        return float(1.0 - ss_res / ss_tot)
