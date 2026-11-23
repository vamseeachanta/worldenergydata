"""
Production forecasting module for SODIR fields.

This module implements various forecasting methods for Norwegian petroleum production,
including decline curve analysis, time series models, and ensemble forecasting.
"""

import logging
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import optimize, stats
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class ForecastModel(Enum):
    """Available forecast models"""

    EXPONENTIAL = "exponential"
    HYPERBOLIC = "hyperbolic"
    HARMONIC = "harmonic"
    ARIMA = "arima"
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    MOVING_AVERAGE = "moving_average"


@dataclass
class DeclineCurve:
    """Decline curve parameters"""

    model_type: str
    initial_rate: float
    decline_rate: float
    b_factor: Optional[float] = None  # For hyperbolic decline
    r_squared: float = 0.0
    rmse: float = 0.0
    parameters: Dict[str, float] = field(default_factory=dict)

    def predict(self, time_periods: Union[int, List[int]]) -> np.ndarray:
        """Predict production for given time periods"""
        if isinstance(time_periods, int):
            time_periods = list(range(time_periods))

        predictions = []
        for t in time_periods:
            if self.model_type == "exponential":
                pred = self.initial_rate * np.exp(-self.decline_rate * t)
            elif self.model_type == "hyperbolic" and self.b_factor is not None:
                pred = self.initial_rate / (
                    (1 + self.b_factor * self.decline_rate * t) ** (1 / self.b_factor)
                )
            elif self.model_type == "harmonic":
                pred = self.initial_rate / (1 + self.decline_rate * t)
            else:
                pred = self.initial_rate * (1 - self.decline_rate * t)

            predictions.append(max(0, pred))  # Ensure non-negative

        return np.array(predictions)


@dataclass
class ForecastResult:
    """Results from production forecasting"""

    model_type: str
    forecast_values: np.ndarray
    confidence_intervals: Optional[Dict[str, np.ndarray]] = None
    model_params: Optional[Dict[str, Any]] = None
    accuracy_metrics: Optional[Dict[str, float]] = None
    forecast_periods: Optional[List[int]] = None

    def to_dataframe(self) -> pd.DataFrame:
        """Convert forecast to DataFrame"""
        df = pd.DataFrame(
            {
                "period": (
                    self.forecast_periods
                    if self.forecast_periods
                    else range(len(self.forecast_values))
                ),
                "forecast": self.forecast_values,
            }
        )

        if self.confidence_intervals:
            df["lower_95"] = self.confidence_intervals.get("lower_95", np.nan)
            df["upper_95"] = self.confidence_intervals.get("upper_95", np.nan)
            df["lower_80"] = self.confidence_intervals.get("lower_80", np.nan)
            df["upper_80"] = self.confidence_intervals.get("upper_80", np.nan)

        return df


class ProductionForecaster:
    """Main production forecasting class"""

    def __init__(self):
        """Initialize forecaster"""
        self.models = {}
        self.historical_data = None

    def fit_decline_curve(
        self, production_data: pd.Series, model_type: str = "exponential"
    ) -> DeclineCurve:
        """
        Fit decline curve to production data.

        Args:
            production_data: Historical production series
            model_type: Type of decline curve

        Returns:
            DeclineCurve with fitted parameters
        """
        # Remove NaN and zero values
        clean_data = production_data.dropna()
        clean_data = clean_data[clean_data > 0]

        if len(clean_data) < 3:
            raise ValueError("Insufficient data for decline curve fitting")

        # Time indices
        time = np.arange(len(clean_data))
        values = clean_data.values

        # Initial parameter guess
        initial_rate = values[0]

        if model_type == "exponential":
            params = self._fit_exponential_decline(time, values, initial_rate)
        elif model_type == "hyperbolic":
            params = self._fit_hyperbolic_decline(time, values, initial_rate)
        elif model_type == "harmonic":
            params = self._fit_harmonic_decline(time, values, initial_rate)
        else:
            params = self._fit_linear_decline(time, values, initial_rate)

        return params

    def _fit_exponential_decline(
        self, time: np.ndarray, production: np.ndarray, initial_rate: float
    ) -> DeclineCurve:
        """Fit exponential decline curve: q(t) = qi * exp(-D*t)"""

        def exponential(t, qi, D):
            return qi * np.exp(-D * t)

        try:
            # Fit curve
            popt, pcov = optimize.curve_fit(
                exponential,
                time,
                production,
                p0=[initial_rate, 0.1],
                bounds=([0, 0], [np.inf, 1]),
            )

            qi, D = popt

            # Calculate R-squared
            predictions = exponential(time, qi, D)
            r_squared = self._calculate_r_squared(production, predictions)
            rmse = np.sqrt(mean_squared_error(production, predictions))

            return DeclineCurve(
                model_type="exponential",
                initial_rate=qi,
                decline_rate=D,
                r_squared=r_squared,
                rmse=rmse,
                parameters={"qi": qi, "D": D},
            )

        except Exception as e:
            logger.error(f"Failed to fit exponential decline: {e}")
            # Return simple estimate
            return DeclineCurve(
                model_type="exponential",
                initial_rate=initial_rate,
                decline_rate=0.1,
                r_squared=0,
                rmse=float("inf"),
            )

    def _fit_hyperbolic_decline(
        self, time: np.ndarray, production: np.ndarray, initial_rate: float
    ) -> DeclineCurve:
        """Fit hyperbolic decline curve: q(t) = qi / (1 + b*D*t)^(1/b)"""

        def hyperbolic(t, qi, D, b):
            return qi / ((1 + b * D * t) ** (1 / b))

        try:
            # Fit curve
            popt, pcov = optimize.curve_fit(
                hyperbolic,
                time,
                production,
                p0=[initial_rate, 0.1, 0.5],
                bounds=([0, 0, 0], [np.inf, 1, 1]),
            )

            qi, D, b = popt

            # Calculate R-squared
            predictions = hyperbolic(time, qi, D, b)
            r_squared = self._calculate_r_squared(production, predictions)
            rmse = np.sqrt(mean_squared_error(production, predictions))

            return DeclineCurve(
                model_type="hyperbolic",
                initial_rate=qi,
                decline_rate=D,
                b_factor=b,
                r_squared=r_squared,
                rmse=rmse,
                parameters={"qi": qi, "D": D, "b": b},
            )

        except Exception as e:
            logger.error(f"Failed to fit hyperbolic decline: {e}")
            # Fall back to exponential
            return self._fit_exponential_decline(time, production, initial_rate)

    def _fit_harmonic_decline(
        self, time: np.ndarray, production: np.ndarray, initial_rate: float
    ) -> DeclineCurve:
        """Fit harmonic decline curve: q(t) = qi / (1 + D*t)"""

        def harmonic(t, qi, D):
            return qi / (1 + D * t)

        try:
            # Fit curve
            popt, pcov = optimize.curve_fit(
                harmonic,
                time,
                production,
                p0=[initial_rate, 0.1],
                bounds=([0, 0], [np.inf, 1]),
            )

            qi, D = popt

            # Calculate R-squared
            predictions = harmonic(time, qi, D)
            r_squared = self._calculate_r_squared(production, predictions)
            rmse = np.sqrt(mean_squared_error(production, predictions))

            return DeclineCurve(
                model_type="harmonic",
                initial_rate=qi,
                decline_rate=D,
                r_squared=r_squared,
                rmse=rmse,
                parameters={"qi": qi, "D": D},
            )

        except Exception as e:
            logger.error(f"Failed to fit harmonic decline: {e}")
            return self._fit_exponential_decline(time, production, initial_rate)

    def _fit_linear_decline(
        self, time: np.ndarray, production: np.ndarray, initial_rate: float
    ) -> DeclineCurve:
        """Fit linear decline: q(t) = qi - D*t"""
        # Simple linear regression
        slope, intercept = np.polyfit(time, production, 1)

        # Calculate R-squared
        predictions = intercept + slope * time
        r_squared = self._calculate_r_squared(production, predictions)
        rmse = np.sqrt(mean_squared_error(production, predictions))

        return DeclineCurve(
            model_type="linear",
            initial_rate=intercept,
            decline_rate=-slope / intercept if intercept != 0 else 0,
            r_squared=r_squared,
            rmse=rmse,
            parameters={"intercept": intercept, "slope": slope},
        )

    def _calculate_r_squared(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        """Calculate R-squared value"""
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)

        if ss_tot == 0:
            return 0

        return 1 - (ss_res / ss_tot)

    def forecast_production(
        self,
        historical_data: pd.DataFrame,
        forecast_years: int = 10,
        method: str = "decline_curve",
        confidence_level: float = 0.95,
    ) -> ForecastResult:
        """
        Generate production forecast.

        Args:
            historical_data: Historical production data
            forecast_years: Number of years to forecast
            method: Forecasting method
            confidence_level: Confidence level for intervals

        Returns:
            ForecastResult with predictions
        """
        self.historical_data = historical_data

        # Prepare production data
        if "oil_production" in historical_data.columns:
            production = historical_data["oil_production"]
        elif "gas_production" in historical_data.columns:
            production = historical_data["gas_production"]
        elif "production_boe" in historical_data.columns:
            production = historical_data["production_boe"]
        else:
            production = historical_data.iloc[:, 0]  # Use first column

        # Apply forecasting method
        if method == "decline_curve":
            forecast = self._forecast_with_decline_curve(production, forecast_years)
        elif method == "moving_average":
            forecast = self._forecast_with_moving_average(production, forecast_years)
        elif method == "polynomial":
            forecast = self._forecast_with_polynomial(production, forecast_years)
        else:
            # Default to exponential decline
            forecast = self._forecast_with_decline_curve(
                production, forecast_years, "exponential"
            )

        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(
            production, forecast, confidence_level
        )

        # Calculate accuracy metrics on historical fit
        if len(production) > forecast_years:
            train = production[:-forecast_years]
            test = production[-forecast_years:]

            # Fit model on training data
            temp_forecast = self._forecast_with_decline_curve(train, forecast_years)

            accuracy_metrics = {
                "mape": mean_absolute_percentage_error(
                    test[: len(temp_forecast)], temp_forecast[: len(test)]
                ),
                "rmse": np.sqrt(
                    mean_squared_error(
                        test[: len(temp_forecast)], temp_forecast[: len(test)]
                    )
                ),
            }
        else:
            accuracy_metrics = None

        return ForecastResult(
            model_type=method,
            forecast_values=forecast,
            confidence_intervals=confidence_intervals,
            model_params={"method": method, "forecast_years": forecast_years},
            accuracy_metrics=accuracy_metrics,
            forecast_periods=list(
                range(len(production), len(production) + forecast_years)
            ),
        )

    def _forecast_with_decline_curve(
        self,
        production: pd.Series,
        forecast_years: int,
        curve_type: str = "exponential",
    ) -> np.ndarray:
        """Forecast using decline curve analysis"""
        # Fit decline curve
        decline_curve = self.fit_decline_curve(production, curve_type)

        # Generate forecast
        forecast = decline_curve.predict(forecast_years)

        return forecast

    def _forecast_with_moving_average(
        self, production: pd.Series, forecast_years: int, window: int = 3
    ) -> np.ndarray:
        """Forecast using moving average"""
        # Calculate moving average
        ma = production.rolling(window=window, min_periods=1).mean()

        # Simple trend extrapolation
        trend = (ma.iloc[-1] - ma.iloc[-window]) / window if len(ma) >= window else 0

        # Generate forecast
        last_value = ma.iloc[-1]
        forecast = []
        for i in range(forecast_years):
            next_value = max(0, last_value + trend * i)
            forecast.append(next_value)

        return np.array(forecast)

    def _forecast_with_polynomial(
        self, production: pd.Series, forecast_years: int, degree: int = 2
    ) -> np.ndarray:
        """Forecast using polynomial regression"""
        # Time indices
        time = np.arange(len(production))

        # Fit polynomial
        coeffs = np.polyfit(time, production.values, degree)
        poly = np.poly1d(coeffs)

        # Generate forecast
        future_time = np.arange(len(production), len(production) + forecast_years)
        forecast = poly(future_time)

        # Ensure non-negative
        forecast = np.maximum(0, forecast)

        return forecast

    def _calculate_confidence_intervals(
        self, historical: pd.Series, forecast: np.ndarray, confidence_level: float
    ) -> Dict[str, np.ndarray]:
        """Calculate confidence intervals for forecast"""
        # Calculate historical variance
        if len(historical) > 1:
            std_error = historical.std()
        else:
            std_error = 0.1 * np.mean(forecast)

        # Z-scores for confidence levels
        z_95 = stats.norm.ppf((1 + 0.95) / 2)
        z_80 = stats.norm.ppf((1 + 0.80) / 2)

        # Calculate intervals (simplified - increases with time)
        time_factor = np.sqrt(np.arange(1, len(forecast) + 1))

        intervals = {
            "lower_95": forecast - z_95 * std_error * time_factor,
            "upper_95": forecast + z_95 * std_error * time_factor,
            "lower_80": forecast - z_80 * std_error * time_factor,
            "upper_80": forecast + z_80 * std_error * time_factor,
        }

        # Ensure non-negative
        for key in intervals:
            if "lower" in key:
                intervals[key] = np.maximum(0, intervals[key])

        return intervals

    def ensemble_forecast(
        self,
        historical_data: pd.DataFrame,
        models: List[str] = None,
        forecast_years: int = 10,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Create ensemble forecast using multiple models.

        Args:
            historical_data: Historical production data
            models: List of models to use
            forecast_years: Forecast horizon
            weights: Model weights (optional)

        Returns:
            Dictionary with ensemble results
        """
        if models is None:
            models = ["exponential", "hyperbolic", "moving_average"]

        # Generate forecasts from each model
        forecasts = {}
        model_objects = {}

        for model in models:
            try:
                if model in ["exponential", "hyperbolic", "harmonic"]:
                    result = self.forecast_production(
                        historical_data, forecast_years, "decline_curve"
                    )
                    # Re-fit with specific curve type
                    production = (
                        historical_data.iloc[:, 0]
                        if historical_data.shape[1] > 0
                        else historical_data
                    )
                    decline = self.fit_decline_curve(production, model)
                    forecasts[model] = decline.predict(forecast_years)
                    model_objects[model] = decline
                else:
                    result = self.forecast_production(
                        historical_data, forecast_years, model
                    )
                    forecasts[model] = result.forecast_values
                    model_objects[model] = result

            except Exception as e:
                logger.warning(f"Failed to generate {model} forecast: {e}")
                continue

        if not forecasts:
            raise ValueError("No models successfully generated forecasts")

        # Calculate weights if not provided
        if weights is None:
            # Equal weights
            weights = {model: 1.0 / len(forecasts) for model in forecasts}

        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        # Calculate ensemble mean
        ensemble_mean = np.zeros(forecast_years)
        for model, forecast in forecasts.items():
            weight = weights.get(model, 0)
            ensemble_mean += weight * forecast

        # Calculate ensemble variance (simplified)
        ensemble_std = np.zeros(forecast_years)
        for model, forecast in forecasts.items():
            weight = weights.get(model, 0)
            ensemble_std += weight * (forecast - ensemble_mean) ** 2
        ensemble_std = np.sqrt(ensemble_std)

        return {
            "ensemble_mean": ensemble_mean,
            "ensemble_std": ensemble_std,
            "individual_forecasts": forecasts,
            "model_weights": weights,
            "models": model_objects,
        }

    def validate_forecast(
        self, forecast: np.ndarray, actual: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Validate forecast against actual data.

        Args:
            forecast: Forecast values
            actual: Actual production values

        Returns:
            Dictionary with validation metrics
        """
        # Ensure same length
        min_len = min(len(forecast), len(actual))
        forecast = forecast[:min_len]

        if isinstance(actual, pd.DataFrame):
            actual = actual.iloc[:min_len, 0].values
        else:
            actual = actual[:min_len]

        # Calculate metrics
        metrics = {
            "mape": mean_absolute_percentage_error(actual, forecast) * 100,
            "rmse": np.sqrt(mean_squared_error(actual, forecast)),
            "mae": np.mean(np.abs(actual - forecast)),
            "r_squared": self._calculate_r_squared(actual, forecast),
        }

        # Calculate directional accuracy
        if len(actual) > 1:
            actual_direction = np.diff(actual) > 0
            forecast_direction = np.diff(forecast) > 0
            metrics["directional_accuracy"] = np.mean(
                actual_direction == forecast_direction
            )

        return metrics

    def scenario_forecast(
        self,
        historical_data: pd.DataFrame,
        scenarios: Dict[str, Dict[str, float]],
        forecast_years: int = 10,
    ) -> Dict[str, ForecastResult]:
        """
        Generate scenario-based forecasts.

        Args:
            historical_data: Historical production
            scenarios: Dictionary of scenarios with parameters
            forecast_years: Forecast horizon

        Returns:
            Dictionary of ForecastResult for each scenario
        """
        scenario_results = {}

        for scenario_name, params in scenarios.items():
            # Adjust historical data based on scenario
            adjusted_data = historical_data.copy()

            # Apply decline factor if specified
            if "decline_factor" in params:
                factor = params["decline_factor"]
                if "oil_production" in adjusted_data:
                    adjusted_data["oil_production"] *= factor
                if "gas_production" in adjusted_data:
                    adjusted_data["gas_production"] *= factor

            # Generate forecast for scenario
            result = self.forecast_production(
                adjusted_data,
                forecast_years,
                method=params.get("method", "decline_curve"),
            )

            scenario_results[scenario_name] = result

        return scenario_results

    def calculate_eur(
        self,
        production_profile: pd.Series,
        decline_curve: Optional[DeclineCurve] = None,
        economic_limit: float = 0.0,
    ) -> float:
        """
        Calculate Estimated Ultimate Recovery (EUR).

        Args:
            production_profile: Historical production
            decline_curve: Fitted decline curve (optional)
            economic_limit: Economic production limit

        Returns:
            EUR value
        """
        # Calculate historical cumulative
        historical_cumulative = production_profile.sum()

        if decline_curve is None:
            # Fit decline curve if not provided
            decline_curve = self.fit_decline_curve(production_profile)

        # Calculate future production until economic limit
        future_production = 0
        year = 0
        max_years = 50  # Maximum forecast horizon

        while year < max_years:
            annual_production = decline_curve.predict([year])[0]

            if annual_production <= economic_limit:
                break

            future_production += annual_production
            year += 1

        # Total EUR
        eur = historical_cumulative + future_production

        return eur
