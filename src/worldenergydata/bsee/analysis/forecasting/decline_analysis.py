"""Decline curve model fitting, comparison, and forecasting for BSEE fields.

Fits exponential, hyperbolic, and harmonic decline curves to BSEE production
data using the sodir ProductionForecaster. Adds AIC-based model comparison
and auto-selection of best-fit model.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
    ProductionTimeSeries,
)
from worldenergydata.sodir.forecasting import (
    DeclineCurve,
    ForecastResult,
    ProductionForecaster,
)

logger = logging.getLogger(__name__)

_MODEL_TYPES = ["exponential", "hyperbolic", "harmonic"]


@dataclass
class ModelFit:
    """Result of fitting a single decline model."""

    curve: DeclineCurve
    aic: float
    n_params: int
    residuals: np.ndarray
    predicted: np.ndarray


@dataclass
class ModelComparison:
    """Comparison of multiple decline models for one production series."""

    field_name: str
    product_type: str
    fits: Dict[str, ModelFit]
    best_model: str
    best_fit: ModelFit
    data_points: int
    time_span: int

    def summary_table(self) -> pd.DataFrame:
        """Summary of all model fits as a DataFrame."""
        rows = []
        for name, fit in self.fits.items():
            rows.append(
                {
                    "model": name,
                    "qi": fit.curve.initial_rate,
                    "D": fit.curve.decline_rate,
                    "b": fit.curve.b_factor,
                    "r_squared": fit.curve.r_squared,
                    "rmse": fit.curve.rmse,
                    "aic": fit.aic,
                    "n_params": fit.n_params,
                    "is_best": name == self.best_model,
                }
            )
        return pd.DataFrame(rows).sort_values("aic")


class DeclineAnalysis:
    """Fit and compare decline curve models for BSEE production data."""

    def __init__(self, forecast_periods: int = 10, economic_limit: float = 0.0):
        self._forecaster = ProductionForecaster()
        self._forecast_periods = forecast_periods
        self._economic_limit = economic_limit

    def fit_all_models(
        self,
        ts: ProductionTimeSeries,
        models: Optional[List[str]] = None,
    ) -> ModelComparison:
        """Fit all decline models to a production time series.

        Args:
            ts: ProductionTimeSeries from BseeDeclineAdapter.
            models: List of model types to fit. Defaults to all three.

        Returns:
            ModelComparison with fits, AIC scores, and best model selection.
        """
        if models is None:
            models = list(_MODEL_TYPES)

        series = pd.Series(ts.rates)
        fits: Dict[str, ModelFit] = {}

        for model_type in models:
            try:
                curve = self._forecaster.fit_decline_curve(series, model_type)
                predicted = curve.predict(list(range(len(ts.rates))))
                residuals = ts.rates - predicted
                n_params = self._count_params(model_type)
                aic = self._compute_aic(ts.rates, predicted, n_params)

                fits[model_type] = ModelFit(
                    curve=curve,
                    aic=aic,
                    n_params=n_params,
                    residuals=residuals,
                    predicted=predicted,
                )
                logger.info(
                    "%s fit: R²=%.4f, RMSE=%.2f, AIC=%.2f",
                    model_type,
                    curve.r_squared,
                    curve.rmse,
                    aic,
                )
            except Exception as e:
                logger.warning("Failed to fit %s model: %s", model_type, e)

        if not fits:
            raise ValueError("All model fits failed — check input data quality")

        best_model = min(fits, key=lambda k: fits[k].aic)

        return ModelComparison(
            field_name=ts.field_name,
            product_type=ts.product_type,
            fits=fits,
            best_model=best_model,
            best_fit=fits[best_model],
            data_points=ts.n_after_filter,
            time_span=len(ts.rates),
        )

    def forecast(
        self,
        comparison: ModelComparison,
        periods: Optional[int] = None,
        confidence_level: float = 0.95,
    ) -> ForecastResult:
        """Generate forecast using the best-fit model.

        Args:
            comparison: ModelComparison from fit_all_models.
            periods: Number of periods to forecast. Defaults to constructor value.
            confidence_level: Confidence level for intervals.

        Returns:
            ForecastResult with forecast values and confidence intervals.
        """
        if periods is None:
            periods = self._forecast_periods

        curve = comparison.best_fit.curve
        forecast_time = list(
            range(comparison.time_span, comparison.time_span + periods)
        )
        forecast_values = curve.predict(forecast_time)

        ci = self._bootstrap_confidence_intervals(
            comparison.best_fit, forecast_time, confidence_level
        )

        return ForecastResult(
            model_type=curve.model_type,
            forecast_values=forecast_values,
            confidence_intervals=ci,
            model_params=curve.parameters,
            accuracy_metrics={
                "r_squared": curve.r_squared,
                "rmse": curve.rmse,
                "aic": comparison.best_fit.aic,
            },
            forecast_periods=forecast_time,
        )

    def calculate_eur(
        self,
        comparison: ModelComparison,
        economic_limit: Optional[float] = None,
        max_periods: int = 1000,
    ) -> Dict[str, float]:
        """Calculate Estimated Ultimate Recovery for each model.

        EUR = cumulative production from time 0 to economic limit (or max periods).

        Returns:
            Dict mapping model name to EUR value.
        """
        if economic_limit is None:
            economic_limit = self._economic_limit

        eur_results = {}
        for name, fit in comparison.fits.items():
            cum = 0.0
            for t in range(max_periods):
                rate = fit.curve.predict([t])[0]
                if rate <= economic_limit:
                    break
                cum += rate
            eur_results[name] = cum

        return eur_results

    @staticmethod
    def _compute_aic(actual: np.ndarray, predicted: np.ndarray, n_params: int) -> float:
        """Compute Akaike Information Criterion.

        AIC = n * ln(RSS/n) + 2k
        where n = number of observations, k = number of parameters,
        RSS = residual sum of squares.
        """
        n = len(actual)
        rss = np.sum((actual - predicted) ** 2)

        if n <= 0:
            return float("inf")
        if rss <= 0:
            # Perfect fit — use a very small RSS to avoid log(0)
            return -float("inf")

        return n * np.log(rss / n) + 2 * n_params

    @staticmethod
    def _count_params(model_type: str) -> int:
        """Number of free parameters per model type."""
        if model_type == "hyperbolic":
            return 3  # qi, D, b
        return 2  # qi, D for exponential and harmonic

    def _bootstrap_confidence_intervals(
        self,
        fit: ModelFit,
        forecast_time: list,
        confidence_level: float,
        n_bootstrap: int = 200,
    ) -> Dict[str, np.ndarray]:
        """Bootstrap confidence intervals from residual resampling."""
        alpha = 1 - confidence_level
        forecasts = []

        base_forecast = fit.curve.predict(forecast_time)
        residual_std = np.std(fit.residuals)

        rng = np.random.default_rng(42)
        for _ in range(n_bootstrap):
            noise = rng.normal(0, residual_std, size=len(forecast_time))
            forecasts.append(np.maximum(0, base_forecast + noise))

        forecasts_array = np.array(forecasts)
        lower = np.percentile(forecasts_array, 100 * alpha / 2, axis=0)
        upper = np.percentile(forecasts_array, 100 * (1 - alpha / 2), axis=0)

        return {
            "lower_95": lower,
            "upper_95": upper,
        }
