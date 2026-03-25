"""Decline curve analysis for Brazilian pre-salt and post-salt fields.

Reuses the DCA approach from sodir/forecasting.py:
- Exponential: q(t) = qi * exp(-D*t)
- Hyperbolic:  q(t) = qi / (1 + b*D*t)^(1/b)
- Harmonic:    q(t) = qi / (1 + D*t)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import optimize
from sklearn.metrics import mean_squared_error

logger = logging.getLogger(__name__)


class DeclineModel(Enum):
    EXPONENTIAL = "exponential"
    HYPERBOLIC = "hyperbolic"
    HARMONIC = "harmonic"


@dataclass
class DeclineCurveResult:
    model_type: str
    initial_rate: float
    decline_rate: float
    b_factor: Optional[float] = None
    r_squared: float = 0.0
    rmse: float = 0.0
    parameters: Dict[str, float] = field(default_factory=dict)

    def predict(self, periods: Union[int, List[int]]) -> np.ndarray:
        if isinstance(periods, int):
            periods = list(range(periods))

        predictions = []
        for t in periods:
            if self.model_type == "exponential":
                pred = self.initial_rate * np.exp(-self.decline_rate * t)
            elif self.model_type == "hyperbolic" and self.b_factor is not None:
                pred = self.initial_rate / (
                    (1 + self.b_factor * self.decline_rate * t)
                    ** (1 / self.b_factor)
                )
            elif self.model_type == "harmonic":
                pred = self.initial_rate / (1 + self.decline_rate * t)
            else:
                pred = self.initial_rate * np.exp(-self.decline_rate * t)
            predictions.append(max(0.0, pred))

        return np.array(predictions)


class DeclineCurveAnalyzer:
    """Fit decline curves to production data."""

    def fit(
        self,
        production: pd.Series,
        model: DeclineModel = DeclineModel.EXPONENTIAL,
    ) -> DeclineCurveResult:
        clean = production.dropna()
        clean = clean[clean > 0]

        if len(clean) < 3:
            raise ValueError("Insufficient data for decline curve fitting")

        time = np.arange(len(clean))
        values = clean.values.astype(float)
        qi_guess = float(values[0])

        if model == DeclineModel.EXPONENTIAL:
            return self._fit_exponential(time, values, qi_guess)
        elif model == DeclineModel.HYPERBOLIC:
            return self._fit_hyperbolic(time, values, qi_guess)
        elif model == DeclineModel.HARMONIC:
            return self._fit_harmonic(time, values, qi_guess)
        else:
            return self._fit_exponential(time, values, qi_guess)

    def best_fit(self, production: pd.Series) -> DeclineCurveResult:
        results = []
        for model in DeclineModel:
            try:
                result = self.fit(production, model)
                results.append(result)
            except Exception:
                continue

        if not results:
            raise ValueError("No model could be fitted")

        return max(results, key=lambda r: r.r_squared)

    def _fit_exponential(
        self, time: np.ndarray, values: np.ndarray, qi_guess: float
    ) -> DeclineCurveResult:
        def exponential(t, qi, d):
            return qi * np.exp(-d * t)

        try:
            popt, _ = optimize.curve_fit(
                exponential, time, values,
                p0=[qi_guess, 0.05],
                bounds=([0, 0], [np.inf, 2.0]),
                maxfev=5000,
            )
            qi, d = popt
            predicted = exponential(time, qi, d)
            return DeclineCurveResult(
                model_type="exponential",
                initial_rate=qi,
                decline_rate=d,
                r_squared=self._r_squared(values, predicted),
                rmse=np.sqrt(mean_squared_error(values, predicted)),
                parameters={"qi": qi, "D": d},
            )
        except Exception:
            return DeclineCurveResult(
                model_type="exponential",
                initial_rate=qi_guess,
                decline_rate=0.05,
                r_squared=0.0,
                rmse=float("inf"),
            )

    def _fit_hyperbolic(
        self, time: np.ndarray, values: np.ndarray, qi_guess: float
    ) -> DeclineCurveResult:
        def hyperbolic(t, qi, d, b):
            return qi / ((1 + b * d * t) ** (1 / b))

        try:
            popt, _ = optimize.curve_fit(
                hyperbolic, time, values,
                p0=[qi_guess, 0.05, 0.5],
                bounds=([0, 0, 0.01], [np.inf, 2.0, 1.0]),
                maxfev=5000,
            )
            qi, d, b = popt
            predicted = hyperbolic(time, qi, d, b)
            return DeclineCurveResult(
                model_type="hyperbolic",
                initial_rate=qi,
                decline_rate=d,
                b_factor=b,
                r_squared=self._r_squared(values, predicted),
                rmse=np.sqrt(mean_squared_error(values, predicted)),
                parameters={"qi": qi, "D": d, "b": b},
            )
        except Exception:
            return self._fit_exponential(time, values, qi_guess)

    def _fit_harmonic(
        self, time: np.ndarray, values: np.ndarray, qi_guess: float
    ) -> DeclineCurveResult:
        def harmonic(t, qi, d):
            return qi / (1 + d * t)

        try:
            popt, _ = optimize.curve_fit(
                harmonic, time, values,
                p0=[qi_guess, 0.05],
                bounds=([0, 0], [np.inf, 2.0]),
                maxfev=5000,
            )
            qi, d = popt
            predicted = harmonic(time, qi, d)
            return DeclineCurveResult(
                model_type="harmonic",
                initial_rate=qi,
                decline_rate=d,
                r_squared=self._r_squared(values, predicted),
                rmse=np.sqrt(mean_squared_error(values, predicted)),
                parameters={"qi": qi, "D": d},
            )
        except Exception:
            return self._fit_exponential(time, values, qi_guess)

    @staticmethod
    def _r_squared(actual: np.ndarray, predicted: np.ndarray) -> float:
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        if ss_tot == 0:
            return 0.0
        return 1.0 - (ss_res / ss_tot)
