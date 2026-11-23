"""Tests for SODIR production forecasting module."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.sodir.forecasting import (
    DeclineCurve,
    ForecastModel,
    ForecastResult,
    ProductionForecaster,
)


class TestForecastModel:
    """Tests for ForecastModel enum."""

    def test_exponential_value(self):
        assert ForecastModel.EXPONENTIAL.value == "exponential"

    def test_hyperbolic_value(self):
        assert ForecastModel.HYPERBOLIC.value == "hyperbolic"

    def test_harmonic_value(self):
        assert ForecastModel.HARMONIC.value == "harmonic"

    def test_all_models_defined(self):
        expected = {
            "exponential",
            "hyperbolic",
            "harmonic",
            "arima",
            "linear",
            "polynomial",
            "moving_average",
        }
        actual = {m.value for m in ForecastModel}
        assert actual == expected


class TestDeclineCurve:
    """Tests for DeclineCurve dataclass."""

    def test_exponential_predict(self):
        dc = DeclineCurve(
            model_type="exponential",
            initial_rate=1000.0,
            decline_rate=0.1,
        )
        predictions = dc.predict(5)
        assert len(predictions) == 5
        assert predictions[0] == pytest.approx(1000.0, rel=1e-3)
        assert predictions[1] < predictions[0]

    def test_exponential_predict_list(self):
        dc = DeclineCurve(
            model_type="exponential",
            initial_rate=1000.0,
            decline_rate=0.1,
        )
        predictions = dc.predict([0, 1, 2])
        assert len(predictions) == 3

    def test_hyperbolic_predict(self):
        dc = DeclineCurve(
            model_type="hyperbolic",
            initial_rate=1000.0,
            decline_rate=0.1,
            b_factor=0.5,
        )
        predictions = dc.predict(5)
        assert len(predictions) == 5
        assert predictions[0] == pytest.approx(1000.0, rel=1e-3)
        assert all(p >= 0 for p in predictions)

    def test_harmonic_predict(self):
        dc = DeclineCurve(
            model_type="harmonic",
            initial_rate=1000.0,
            decline_rate=0.1,
        )
        predictions = dc.predict(5)
        assert len(predictions) == 5
        assert predictions[0] == pytest.approx(1000.0, rel=1e-3)

    def test_linear_predict(self):
        dc = DeclineCurve(
            model_type="linear",
            initial_rate=1000.0,
            decline_rate=0.1,
        )
        predictions = dc.predict(5)
        assert len(predictions) == 5

    def test_predictions_non_negative(self):
        dc = DeclineCurve(
            model_type="exponential",
            initial_rate=10.0,
            decline_rate=0.9,
        )
        predictions = dc.predict(100)
        assert all(p >= 0 for p in predictions)


class TestForecastResult:
    """Tests for ForecastResult dataclass."""

    def test_to_dataframe_basic(self):
        result = ForecastResult(
            model_type="exponential",
            forecast_values=np.array([100, 90, 80]),
        )
        df = result.to_dataframe()
        assert len(df) == 3
        assert "period" in df.columns
        assert "forecast" in df.columns

    def test_to_dataframe_with_periods(self):
        result = ForecastResult(
            model_type="exponential",
            forecast_values=np.array([100, 90, 80]),
            forecast_periods=[10, 11, 12],
        )
        df = result.to_dataframe()
        assert list(df["period"]) == [10, 11, 12]

    def test_to_dataframe_with_confidence_intervals(self):
        result = ForecastResult(
            model_type="exponential",
            forecast_values=np.array([100, 90, 80]),
            confidence_intervals={
                "lower_95": np.array([90, 80, 70]),
                "upper_95": np.array([110, 100, 90]),
            },
        )
        df = result.to_dataframe()
        assert "lower_95" in df.columns
        assert "upper_95" in df.columns


class TestProductionForecaster:
    """Tests for ProductionForecaster."""

    def setup_method(self):
        self.forecaster = ProductionForecaster()

    def _make_declining_production(self, n=20, initial=1000.0, decline=0.05):
        """Create synthetic declining production data."""
        time = np.arange(n)
        production = initial * np.exp(-decline * time)
        noise = np.random.default_rng(42).normal(0, initial * 0.02, n)
        return pd.Series(production + noise)

    def test_fit_exponential_decline(self):
        production = self._make_declining_production()
        dc = self.forecaster.fit_decline_curve(production, "exponential")
        assert dc.model_type == "exponential"
        assert dc.initial_rate > 0
        assert dc.decline_rate > 0
        assert dc.r_squared > 0.8

    def test_fit_hyperbolic_decline(self):
        production = self._make_declining_production()
        dc = self.forecaster.fit_decline_curve(production, "hyperbolic")
        assert dc.model_type == "hyperbolic"
        assert dc.b_factor is not None

    def test_fit_harmonic_decline(self):
        production = self._make_declining_production()
        dc = self.forecaster.fit_decline_curve(production, "harmonic")
        assert dc.model_type == "harmonic"

    def test_fit_linear_decline(self):
        production = self._make_declining_production()
        dc = self.forecaster.fit_decline_curve(production, "linear")
        assert dc.model_type == "linear"

    def test_fit_insufficient_data_raises(self):
        production = pd.Series([100, 200])
        with pytest.raises(ValueError, match="Insufficient data"):
            self.forecaster.fit_decline_curve(production)

    def test_forecast_production_decline_curve(self):
        data = pd.DataFrame({"oil_production": self._make_declining_production()})
        result = self.forecaster.forecast_production(data, forecast_years=5)
        assert result.model_type == "decline_curve"
        assert len(result.forecast_values) == 5

    def test_forecast_production_moving_average(self):
        data = pd.DataFrame({"oil_production": self._make_declining_production()})
        result = self.forecaster.forecast_production(
            data, forecast_years=5, method="moving_average"
        )
        assert result.model_type == "moving_average"
        assert len(result.forecast_values) == 5

    def test_forecast_production_polynomial(self):
        data = pd.DataFrame({"oil_production": self._make_declining_production()})
        result = self.forecaster.forecast_production(
            data, forecast_years=5, method="polynomial"
        )
        assert result.model_type == "polynomial"
        assert len(result.forecast_values) == 5

    def test_forecast_production_gas_column(self):
        data = pd.DataFrame({"gas_production": self._make_declining_production()})
        result = self.forecaster.forecast_production(data, forecast_years=5)
        assert len(result.forecast_values) == 5

    def test_forecast_production_boe_column(self):
        data = pd.DataFrame({"production_boe": self._make_declining_production()})
        result = self.forecaster.forecast_production(data, forecast_years=5)
        assert len(result.forecast_values) == 5

    def test_forecast_production_default_column(self):
        data = pd.DataFrame({"some_column": self._make_declining_production()})
        result = self.forecaster.forecast_production(data, forecast_years=5)
        assert len(result.forecast_values) == 5

    def test_forecast_has_confidence_intervals(self):
        data = pd.DataFrame({"oil_production": self._make_declining_production()})
        result = self.forecaster.forecast_production(data, forecast_years=5)
        assert result.confidence_intervals is not None
        assert "lower_95" in result.confidence_intervals
        assert "upper_95" in result.confidence_intervals

    def test_forecast_has_periods(self):
        n = 20
        data = pd.DataFrame({"oil_production": self._make_declining_production(n=n)})
        result = self.forecaster.forecast_production(data, forecast_years=5)
        assert result.forecast_periods == [20, 21, 22, 23, 24]

    def test_validate_forecast(self):
        forecast = np.array([100, 90, 80, 70, 60])
        actual = pd.DataFrame({"production": [98, 88, 82, 72, 58]})
        metrics = self.forecaster.validate_forecast(forecast, actual)
        assert "mape" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r_squared" in metrics
        assert "directional_accuracy" in metrics

    def test_calculate_eur(self):
        production = self._make_declining_production()
        eur = self.forecaster.calculate_eur(production)
        assert eur > production.sum()

    def test_calculate_eur_with_economic_limit(self):
        production = self._make_declining_production()
        eur_no_limit = self.forecaster.calculate_eur(production, economic_limit=0)
        eur_with_limit = self.forecaster.calculate_eur(production, economic_limit=500)
        assert eur_with_limit <= eur_no_limit

    def test_r_squared_calculation(self):
        actual = np.array([100, 90, 80, 70, 60])
        predicted = np.array([100, 90, 80, 70, 60])
        r2 = self.forecaster._calculate_r_squared(actual, predicted)
        assert r2 == pytest.approx(1.0)

    def test_r_squared_zero_variance(self):
        actual = np.array([100, 100, 100])
        predicted = np.array([100, 100, 100])
        r2 = self.forecaster._calculate_r_squared(actual, predicted)
        assert r2 == 0  # ss_tot is 0


class TestEnsembleForecast:
    """Tests for ensemble_forecast method."""

    def _make_declining(self, n=20, initial=1000.0, decline=0.05):
        time = np.arange(n)
        production = initial * np.exp(-decline * time)
        noise = np.random.default_rng(42).normal(0, initial * 0.02, n)
        return pd.Series(production + noise)

    def test_default_models(self):
        forecaster = ProductionForecaster()
        data = pd.DataFrame({"oil_production": self._make_declining()})
        result = forecaster.ensemble_forecast(data, forecast_years=5)
        assert "ensemble_mean" in result
        assert "ensemble_std" in result
        assert "individual_forecasts" in result
        assert "model_weights" in result
        assert len(result["ensemble_mean"]) == 5

    def test_custom_models(self):
        forecaster = ProductionForecaster()
        data = pd.DataFrame({"oil_production": self._make_declining()})
        result = forecaster.ensemble_forecast(
            data, models=["exponential", "moving_average"], forecast_years=3
        )
        assert len(result["individual_forecasts"]) == 2
        assert len(result["ensemble_mean"]) == 3

    def test_custom_weights(self):
        forecaster = ProductionForecaster()
        data = pd.DataFrame({"oil_production": self._make_declining()})
        weights = {"exponential": 0.7, "moving_average": 0.3}
        result = forecaster.ensemble_forecast(
            data,
            models=["exponential", "moving_average"],
            forecast_years=3,
            weights=weights,
        )
        assert (
            result["model_weights"]["exponential"]
            > result["model_weights"]["moving_average"]
        )


class TestScenarioForecast:
    """Tests for scenario_forecast method."""

    def _make_declining(self, n=20, initial=1000.0, decline=0.05):
        time = np.arange(n)
        production = initial * np.exp(-decline * time)
        return pd.Series(production)

    def test_basic_scenarios(self):
        forecaster = ProductionForecaster()
        data = pd.DataFrame({"oil_production": self._make_declining()})
        scenarios = {
            "optimistic": {"decline_factor": 1.2},
            "pessimistic": {"decline_factor": 0.8},
        }
        results = forecaster.scenario_forecast(data, scenarios, forecast_years=5)
        assert "optimistic" in results
        assert "pessimistic" in results
        assert len(results["optimistic"].forecast_values) == 5

    def test_scenario_with_method(self):
        forecaster = ProductionForecaster()
        data = pd.DataFrame({"oil_production": self._make_declining()})
        scenarios = {
            "base": {"method": "moving_average"},
        }
        results = forecaster.scenario_forecast(data, scenarios, forecast_years=3)
        assert "base" in results
        assert results["base"].model_type == "moving_average"


class TestDeclineCurveFitErrorPaths:
    """Tests for error/fallback paths in decline curve fitting."""

    def test_fit_hyperbolic_bad_data_falls_back(self):
        """When hyperbolic fit fails, should fall back to exponential."""
        forecaster = ProductionForecaster()
        # Create data that's difficult to fit hyperbolically
        # (constant values can cause curve_fit issues)
        production = pd.Series([1.0] * 10 + [0.5] * 10)
        dc = forecaster.fit_decline_curve(production, "hyperbolic")
        # Should return something (either hyperbolic or exponential fallback)
        assert dc is not None
        assert dc.initial_rate > 0

    def test_fit_harmonic_bad_data_falls_back(self):
        """When harmonic fit fails, should fall back to exponential."""
        forecaster = ProductionForecaster()
        production = pd.Series([1.0] * 10 + [0.5] * 10)
        dc = forecaster.fit_decline_curve(production, "harmonic")
        assert dc is not None
        assert dc.initial_rate > 0
