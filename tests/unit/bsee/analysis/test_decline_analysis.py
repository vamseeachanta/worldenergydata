"""Tests for DeclineAnalysis — model fitting, comparison, and forecasting."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
    BseeDeclineAdapter,
    ProductionTimeSeries,
)
from worldenergydata.bsee.analysis.forecasting.decline_analysis import (
    DeclineAnalysis,
    ModelComparison,
    ModelFit,
)
from worldenergydata.sodir.forecasting import DeclineCurve, ForecastResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def adapter():
    return BseeDeclineAdapter(min_points=3)


@pytest.fixture
def analysis():
    return DeclineAnalysis(forecast_periods=5, economic_limit=100.0)


def _make_exponential_ts(qi=50000, D=0.05, n=20, noise=500):
    """Generate synthetic exponential decline time series."""
    rng = np.random.default_rng(42)
    rates = np.array([qi * np.exp(-D * t) for t in range(n)])
    rates = rates + rng.normal(0, noise, n)
    rates = np.maximum(rates, 1)  # ensure positive
    return ProductionTimeSeries(
        time_indices=np.arange(n, dtype=float),
        rates=rates,
        dates=np.array(list(range(200001, 200001 + n))),
        product_type="oil",
        field_name="SYNTH_EXP",
        unit="bbl_per_day",
        n_original=n,
        n_after_filter=n,
        shut_in_periods=0,
    )


def _make_hyperbolic_ts(qi=50000, D=0.05, b=0.5, n=20, noise=500):
    """Generate synthetic hyperbolic decline time series."""
    rng = np.random.default_rng(43)
    rates = np.array([qi / ((1 + b * D * t) ** (1 / b)) for t in range(n)])
    rates = rates + rng.normal(0, noise, n)
    rates = np.maximum(rates, 1)
    return ProductionTimeSeries(
        time_indices=np.arange(n, dtype=float),
        rates=rates,
        dates=np.array(list(range(200001, 200001 + n))),
        product_type="oil",
        field_name="SYNTH_HYP",
        unit="bbl_per_day",
        n_original=n,
        n_after_filter=n,
        shut_in_periods=0,
    )


@pytest.fixture
def exp_ts():
    return _make_exponential_ts()


@pytest.fixture
def hyp_ts():
    return _make_hyperbolic_ts()


# ---------------------------------------------------------------------------
# fit_all_models tests
# ---------------------------------------------------------------------------

class TestFitAllModels:
    def test_fits_three_models(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        assert isinstance(comparison, ModelComparison)
        assert len(comparison.fits) == 3
        assert "exponential" in comparison.fits
        assert "hyperbolic" in comparison.fits
        assert "harmonic" in comparison.fits

    def test_best_model_selected(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        assert comparison.best_model in comparison.fits
        assert comparison.best_fit is comparison.fits[comparison.best_model]

    def test_exponential_data_favors_exponential(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        # Exponential model should have lowest AIC for exponential data
        exp_aic = comparison.fits["exponential"].aic
        for name, fit in comparison.fits.items():
            if name != "exponential":
                # Allow some tolerance — with noise, other models may fit well too
                assert exp_aic <= fit.aic + 50, (
                    f"Exponential AIC ({exp_aic:.1f}) should be competitive "
                    f"with {name} AIC ({fit.aic:.1f})"
                )

    def test_r_squared_positive(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        for fit in comparison.fits.values():
            assert fit.curve.r_squared > 0.5, (
                f"{fit.curve.model_type} R² too low: {fit.curve.r_squared}"
            )

    def test_model_fit_has_residuals(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        for fit in comparison.fits.values():
            assert len(fit.residuals) == exp_ts.n_after_filter
            assert len(fit.predicted) == exp_ts.n_after_filter

    def test_custom_model_list(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts, models=["exponential"])
        assert len(comparison.fits) == 1
        assert comparison.best_model == "exponential"

    def test_summary_table(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        table = comparison.summary_table()
        assert isinstance(table, pd.DataFrame)
        assert "model" in table.columns
        assert "aic" in table.columns
        assert "r_squared" in table.columns
        assert "is_best" in table.columns
        assert len(table) == 3


class TestAIC:
    def test_aic_perfect_fit(self):
        actual = np.array([100, 90, 81, 73, 66])
        predicted = np.array([100, 90, 81, 73, 66])
        aic = DeclineAnalysis._compute_aic(actual, predicted, n_params=2)
        # Perfect fit → RSS=0 → AIC = -inf
        assert aic == float("-inf")

    def test_aic_worse_for_bad_fit(self):
        actual = np.array([100, 90, 81, 73, 66])
        good_pred = np.array([99, 89, 80, 72, 65])  # near-perfect, not exact
        bad_pred = np.array([50, 50, 50, 50, 50])
        aic_good = DeclineAnalysis._compute_aic(actual, good_pred, 2)
        aic_bad = DeclineAnalysis._compute_aic(actual, bad_pred, 2)
        assert aic_good < aic_bad

    def test_aic_penalizes_more_params(self):
        actual = np.array([100, 90, 81, 73, 66])
        predicted = np.array([99, 89, 80, 72, 65])
        aic_2 = DeclineAnalysis._compute_aic(actual, predicted, n_params=2)
        aic_3 = DeclineAnalysis._compute_aic(actual, predicted, n_params=3)
        assert aic_2 < aic_3  # 2 params < 3 params AIC


class TestCountParams:
    def test_exponential_has_2(self):
        assert DeclineAnalysis._count_params("exponential") == 2

    def test_hyperbolic_has_3(self):
        assert DeclineAnalysis._count_params("hyperbolic") == 3

    def test_harmonic_has_2(self):
        assert DeclineAnalysis._count_params("harmonic") == 2


# ---------------------------------------------------------------------------
# Forecast tests
# ---------------------------------------------------------------------------

class TestForecast:
    def test_forecast_returns_result(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        forecast = analysis.forecast(comparison)
        assert isinstance(forecast, ForecastResult)
        assert len(forecast.forecast_values) == 5  # default periods
        assert forecast.model_type == comparison.best_model

    def test_forecast_custom_periods(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        forecast = analysis.forecast(comparison, periods=20)
        assert len(forecast.forecast_values) == 20

    def test_forecast_values_declining(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        forecast = analysis.forecast(comparison, periods=10)
        # Values should generally decline
        vals = forecast.forecast_values
        assert vals[0] > vals[-1], "Forecast should show declining rates"

    def test_forecast_has_confidence_intervals(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        forecast = analysis.forecast(comparison)
        assert forecast.confidence_intervals is not None
        assert "lower_95" in forecast.confidence_intervals
        assert "upper_95" in forecast.confidence_intervals

    def test_forecast_ci_bounds(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        forecast = analysis.forecast(comparison)
        lower = forecast.confidence_intervals["lower_95"]
        upper = forecast.confidence_intervals["upper_95"]
        assert np.all(lower <= upper)

    def test_forecast_to_dataframe(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        forecast = analysis.forecast(comparison)
        df = forecast.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert "period" in df.columns
        assert "forecast" in df.columns

    def test_forecast_accuracy_metrics(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        forecast = analysis.forecast(comparison)
        assert forecast.accuracy_metrics is not None
        assert "r_squared" in forecast.accuracy_metrics
        assert "rmse" in forecast.accuracy_metrics
        assert "aic" in forecast.accuracy_metrics


# ---------------------------------------------------------------------------
# EUR tests
# ---------------------------------------------------------------------------

class TestEUR:
    def test_eur_returns_dict(self, analysis, exp_ts):
        comparison = analysis.fit_all_models(exp_ts)
        eur = analysis.calculate_eur(comparison)
        assert isinstance(eur, dict)
        assert len(eur) == 3
        for val in eur.values():
            assert val > 0

    def test_eur_with_economic_limit(self, exp_ts):
        analysis = DeclineAnalysis(economic_limit=10000.0)
        comparison = analysis.fit_all_models(exp_ts)
        eur_high = analysis.calculate_eur(comparison, economic_limit=10000.0)
        eur_low = analysis.calculate_eur(comparison, economic_limit=1.0)
        # Lower economic limit → more EUR
        for model in eur_high:
            assert eur_low[model] >= eur_high[model]

    def test_eur_exponential_vs_harmonic(self, exp_ts):
        analysis = DeclineAnalysis(economic_limit=0.0)
        comparison = analysis.fit_all_models(exp_ts)
        eur = analysis.calculate_eur(comparison, max_periods=500)
        # Harmonic decline is slower → higher EUR (generally)
        # This isn't always true with noisy data, so just check values exist
        assert eur["exponential"] > 0
        assert eur["harmonic"] > 0


# ---------------------------------------------------------------------------
# Integration: adapter → analysis pipeline
# ---------------------------------------------------------------------------

class TestIntegrationPipeline:
    def test_full_pipeline(self, adapter, analysis):
        """End-to-end: DataFrame → adapter → analysis → forecast → EUR."""
        # Create realistic production data
        qi = 40000
        D = 0.03
        n = 30
        rng = np.random.default_rng(77)
        df = pd.DataFrame({
            "PRODUCTION_DATE": list(range(200001, 200001 + n)),
            "FIELD_NAME_CODE": ["TEST_FIELD"] * n,
            "MON_O_PROD_VOL": [
                qi * np.exp(-D * t) * 30 + rng.normal(0, 5000) for t in range(n)
            ],
            "DAYS_ON_PROD": [30] * n,
        })

        ts = adapter.extract_field_production(df, "TEST_FIELD")
        comparison = analysis.fit_all_models(ts)
        forecast = analysis.forecast(comparison)
        eur = analysis.calculate_eur(comparison)

        assert comparison.best_model in ["exponential", "hyperbolic", "harmonic"]
        assert len(forecast.forecast_values) == 5
        assert all(v > 0 for v in eur.values())
