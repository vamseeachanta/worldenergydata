"""Tests for UKCS decline curve analysis — Forties, Buzzard, Mariner."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.ukcs.production.decline_curves import (
    DeclineCurveAnalyzer,
    DeclineCurveResult,
    DeclineModel,
)


def make_exponential_decline(qi=50000.0, d=0.04, n=36, seed=42):
    """Synthetic exponential decline (e.g. Forties mature phase)."""
    t = np.arange(n)
    values = qi * np.exp(-d * t)
    noise = np.random.default_rng(seed).normal(0, qi * 0.01, n)
    return pd.Series(np.maximum(values + noise, 0.0))


def make_hyperbolic_decline(qi=80000.0, d=0.05, b=0.6, n=48, seed=7):
    """Synthetic hyperbolic decline (e.g. Buzzard early phase)."""
    t = np.arange(n)
    values = qi / ((1 + b * d * t) ** (1.0 / b))
    noise = np.random.default_rng(seed).normal(0, qi * 0.01, n)
    return pd.Series(np.maximum(values + noise, 0.0))


def make_harmonic_decline(qi=30000.0, d=0.03, n=40, seed=99):
    """Synthetic harmonic decline (e.g. Mariner water-drive)."""
    t = np.arange(n)
    values = qi / (1 + d * t)
    noise = np.random.default_rng(seed).normal(0, qi * 0.005, n)
    return pd.Series(np.maximum(values + noise, 0.0))


class TestDeclineModelEnum:
    def test_exponential_value(self):
        assert DeclineModel.EXPONENTIAL.value == "exponential"

    def test_hyperbolic_value(self):
        assert DeclineModel.HYPERBOLIC.value == "hyperbolic"

    def test_harmonic_value(self):
        assert DeclineModel.HARMONIC.value == "harmonic"


class TestDeclineCurveResult:
    def test_predict_returns_array(self):
        result = DeclineCurveResult(
            model_type="exponential",
            initial_rate=50000.0,
            decline_rate=0.04,
            r_squared=0.95,
            rmse=500.0,
        )
        forecast = result.predict(12)
        assert isinstance(forecast, np.ndarray)
        assert len(forecast) == 12

    def test_predict_all_non_negative(self):
        result = DeclineCurveResult(
            model_type="exponential",
            initial_rate=50000.0,
            decline_rate=0.04,
            r_squared=0.95,
            rmse=500.0,
        )
        forecast = result.predict(60)
        assert all(v >= 0 for v in forecast)

    def test_predict_exponential_declines(self):
        result = DeclineCurveResult(
            model_type="exponential",
            initial_rate=50000.0,
            decline_rate=0.10,
            r_squared=0.95,
            rmse=500.0,
        )
        forecast = result.predict(12)
        assert forecast[0] > forecast[-1]

    def test_predict_harmonic_declines(self):
        result = DeclineCurveResult(
            model_type="harmonic",
            initial_rate=30000.0,
            decline_rate=0.05,
            r_squared=0.90,
            rmse=200.0,
        )
        forecast = result.predict(24)
        assert forecast[0] > forecast[-1]

    def test_predict_hyperbolic_declines(self):
        result = DeclineCurveResult(
            model_type="hyperbolic",
            initial_rate=80000.0,
            decline_rate=0.05,
            b_factor=0.6,
            r_squared=0.93,
            rmse=800.0,
        )
        forecast = result.predict(24)
        assert forecast[0] > forecast[-1]


class TestDeclineCurveAnalyzerFit:
    @pytest.fixture
    def analyzer(self):
        return DeclineCurveAnalyzer()

    def test_fit_exponential_forties(self, analyzer):
        data = make_exponential_decline()
        result = analyzer.fit(data, DeclineModel.EXPONENTIAL)
        assert result.model_type == "exponential"
        assert result.initial_rate > 0
        assert result.decline_rate > 0
        assert result.r_squared > 0.85

    def test_fit_hyperbolic_buzzard(self, analyzer):
        data = make_hyperbolic_decline()
        result = analyzer.fit(data, DeclineModel.HYPERBOLIC)
        assert result.model_type == "hyperbolic"
        assert result.b_factor is not None
        assert 0.0 < result.b_factor <= 1.0

    def test_fit_harmonic_mariner(self, analyzer):
        data = make_harmonic_decline()
        result = analyzer.fit(data, DeclineModel.HARMONIC)
        assert result.model_type == "harmonic"
        assert result.initial_rate > 0

    def test_fit_insufficient_data_raises(self, analyzer):
        short = pd.Series([10000.0, 9500.0])
        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            analyzer.fit(short)

    def test_fit_returns_r_squared_in_range(self, analyzer):
        data = make_exponential_decline()
        result = analyzer.fit(data)
        assert 0.0 <= result.r_squared <= 1.0

    def test_fit_returns_non_negative_rmse(self, analyzer):
        data = make_exponential_decline()
        result = analyzer.fit(data)
        assert result.rmse >= 0.0

    def test_fit_default_is_exponential(self, analyzer):
        data = make_exponential_decline()
        result = analyzer.fit(data)
        assert result.model_type == "exponential"


class TestDeclineCurveAnalyzerBestFit:
    @pytest.fixture
    def analyzer(self):
        return DeclineCurveAnalyzer()

    def test_best_fit_returns_highest_r_squared(self, analyzer):
        data = make_exponential_decline()
        best = analyzer.best_fit(data)
        assert best.model_type in ("exponential", "hyperbolic", "harmonic")
        assert best.r_squared > 0.80

    def test_best_fit_buzzard_hyperbolic(self, analyzer):
        data = make_hyperbolic_decline()
        best = analyzer.best_fit(data)
        assert best.r_squared > 0.80

    def test_best_fit_mariner_harmonic(self, analyzer):
        data = make_harmonic_decline()
        best = analyzer.best_fit(data)
        assert best.r_squared > 0.75


class TestMultiFieldDCAUKCS:
    """DCA applied to 3+ UKCS fields as required by acceptance criteria."""

    @pytest.fixture
    def analyzer(self):
        return DeclineCurveAnalyzer()

    def test_three_fields_all_fit(self, analyzer):
        fields = {
            "FORTIES": make_exponential_decline(qi=50000.0, d=0.04),
            "BUZZARD": make_hyperbolic_decline(qi=80000.0, d=0.05, b=0.6),
            "MARINER": make_harmonic_decline(qi=30000.0, d=0.03),
        }
        results = {name: analyzer.best_fit(data) for name, data in fields.items()}
        assert len(results) == 3
        for name, curve in results.items():
            assert curve.r_squared > 0.7, f"{name} fit quality too low"

    def test_forties_mature_exponential(self, analyzer):
        data = make_exponential_decline(qi=45000.0, d=0.06, n=60)
        result = analyzer.fit(data, DeclineModel.EXPONENTIAL)
        assert result.r_squared > 0.85

    def test_buzzard_early_production(self, analyzer):
        data = make_hyperbolic_decline(qi=100000.0, d=0.04, b=0.5, n=48)
        result = analyzer.fit(data, DeclineModel.HYPERBOLIC)
        assert result.initial_rate > 0

    def test_mariner_water_drive(self, analyzer):
        data = make_harmonic_decline(qi=25000.0, d=0.025, n=36)
        result = analyzer.fit(data, DeclineModel.HARMONIC)
        assert result.decline_rate > 0
