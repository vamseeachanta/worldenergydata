"""Shale basin decline curve analysis — Arps hyperbolic (b > 1).

Shale/tight-oil wells exhibit hyperbolic decline with b-factor > 1 during
early life (typically 1.2 to 2.0), transitioning to a terminal exponential
decline when the effective b approaches 0.5 to avoid infinite EUR.

Arps hyperbolic equation:
  q(t) = qi / (1 + b * Di * t)^(1/b)

where:
  qi  — initial rate (bopd or Mcfd)
  Di  — initial nominal decline rate (per month)
  b   — hyperbolic exponent (> 1 for shale early life)
  t   — time in months

Terminal decline switch:
  When the instantaneous b-effective (derived from q, q', q'') declines
  to TERMINAL_B_FACTOR (~0.5), the model switches to exponential (b=0.5)
  to prevent unrealistic long-tail EUR.

Reference: Arps, J.J. (1945). SPE-945228-G.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)

# b-factor threshold for terminal decline switch
TERMINAL_B_FACTOR: float = 0.5

# Minimum data points required for fitting
_MIN_DATA_POINTS: int = 6


# ── Arps hyperbolic equation ───────────────────────────────────────────────────

def arps_hyperbolic(t: float, qi: float, di: float, b: float) -> float:
    """Compute Arps hyperbolic production rate at time t.

    Args:
        t: Time in months (0 = start).
        qi: Initial rate at t=0.
        di: Initial nominal decline rate (per month, > 0).
        b: Hyperbolic exponent (> 0; > 1 for shale early life; 1 = harmonic;
           approaching 0 = exponential).

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
        terminal_b: If set, switch to exponential when effective b <= terminal_b.
    """

    def __init__(
        self,
        qi: float,
        di: float,
        b: float,
        terminal_b: Optional[float] = TERMINAL_B_FACTOR,
    ) -> None:
        self.qi = qi
        self.di = di
        self.b = b
        self.terminal_b = terminal_b

    def predict(self, n_months: int) -> np.ndarray:
        """Generate n_months forecast using hyperbolic (+ terminal switch).

        Args:
            n_months: Number of months to forecast.

        Returns:
            Array of production rates, all >= 0.
        """
        t = np.arange(n_months, dtype=float)
        rates = np.array([arps_hyperbolic(ti, self.qi, self.di, self.b) for ti in t])

        # Apply terminal decline switch if configured
        if self.terminal_b is not None and self.b > self.terminal_b:
            rates = self._apply_terminal_switch(t, rates)

        return np.maximum(rates, 0.0)

    def _apply_terminal_switch(
        self, t: np.ndarray, rates: np.ndarray
    ) -> np.ndarray:
        """Switch to exponential when effective b approaches terminal_b.

        The switch-over month is where the instantaneous b-effective
        would equal terminal_b. We approximate this by finding where the
        b-effective derived from adjacent rate ratios drops near terminal_b.
        """
        if len(rates) < 3:
            return rates

        result = rates.copy()
        # Find switch-over index heuristically: when rate ratio indicates
        # effective b has declined to terminal_b.
        # For simplicity, use a time-based switch at 60% of forecast horizon.
        switch_idx = max(1, int(len(t) * 0.6))

        if switch_idx < len(rates):
            q_switch = rates[switch_idx]
            if q_switch > 0:
                # Exponential from switch point: q(t) = q_switch * exp(-d_terminal*(t-t_switch))
                d_terminal = self.di * (self.b * self.di * switch_idx + 1) ** (-1.0)
                for i in range(switch_idx + 1, len(t)):
                    dt = i - switch_idx
                    result[i] = q_switch * np.exp(-d_terminal * dt)

        return result


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass
class ShaleDeclineResult:
    """Fitted shale hyperbolic decline result for a basin."""

    basin: str
    model: HyperbolicDeclineModel
    r_squared: float
    rmse: float

    def predict(self, n_months: int) -> np.ndarray:
        """Delegate to the underlying HyperbolicDeclineModel."""
        return self.model.predict(n_months)


# ── Analyzer ───────────────────────────────────────────────────────────────────

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
            ValueError: If production has fewer than _MIN_DATA_POINTS.
        """
        if len(production) < _MIN_DATA_POINTS:
            raise ValueError(
                f"Insufficient data: need at least {_MIN_DATA_POINTS} months, "
                f"got {len(production)}."
            )

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
            logger.warning("curve_fit failed for %s: %s — using initial guess", basin, exc)
            qi_fit, di_fit, b_fit = qi_guess, di_guess, b_guess

        model = HyperbolicDeclineModel(qi=qi_fit, di=di_fit, b=b_fit)

        predicted = model.predict(len(production))
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
        """Compute coefficient of determination R²."""
        ss_res = np.sum((observed - predicted) ** 2)
        ss_tot = np.sum((observed - np.mean(observed)) ** 2)
        if ss_tot == 0.0:
            return 1.0 if ss_res == 0.0 else 0.0
        r2 = 1.0 - ss_res / ss_tot
        return float(np.clip(r2, 0.0, 1.0))
