"""Tests for decline curve analysis applied to Brazilian pre-salt fields."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.brazil_anp.production.decline_curves import (
    DeclineCurveAnalyzer,
    DeclineModel,
)


def make_exponential_data(qi=100000.0, d=0.05, n=36):
    """Generate synthetic exponential decline data."""
    t = np.arange(n)
    production = qi * np.exp(-d * t)
    noise = np.random.default_rng(42).normal(0, qi * 0.01, n)
    return pd.Series(production + noise)


def make_plateau_then_decline(qi=150000.0, plateau_months=12, d=0.03, n=48):
    """Generate plateau + decline data (like Lula)."""
    production = []
    for t in range(n):
        if t < plateau_months:
            production.append(qi + np.random.default_rng(42 + t).normal(0, qi * 0.01))
        else:
            t_decline = t - plateau_months
            production.append(
                qi * np.exp(-d * t_decline)
                + np.random.default_rng(42 + t).normal(0, qi * 0.01)
            )
    return pd.Series(production)


def make_mature_decline(qi=80000.0, d=0.08, n=60):
    """Generate mature decline data (like Marlim)."""
    t = np.arange(n)
    production = qi * np.exp(-d * t)
    noise = np.random.default_rng(99).normal(0, qi * 0.005, n)
    return pd.Series(np.maximum(production + noise, 100))


class TestDeclineModel:
    def test_exponential_enum(self):
        assert DeclineModel.EXPONENTIAL.value == "exponential"

    def test_hyperbolic_enum(self):
        assert DeclineModel.HYPERBOLIC.value == "hyperbolic"

    def test_harmonic_enum(self):
        assert DeclineModel.HARMONIC.value == "harmonic"


class TestDeclineCurveAnalyzerFit:
    @pytest.fixture
    def analyzer(self):
        return DeclineCurveAnalyzer()

    def test_fit_exponential(self, analyzer):
        data = make_exponential_data()
        result = analyzer.fit(data, model=DeclineModel.EXPONENTIAL)
        assert result.model_type == "exponential"
        assert result.initial_rate > 0
        assert result.decline_rate > 0
        assert result.r_squared > 0.9

    def test_fit_hyperbolic(self, analyzer):
        data = make_exponential_data()
        result = analyzer.fit(data, model=DeclineModel.HYPERBOLIC)
        assert result.model_type == "hyperbolic"
        assert result.initial_rate > 0
        assert result.b_factor is not None

    def test_fit_harmonic(self, analyzer):
        data = make_exponential_data()
        result = analyzer.fit(data, model=DeclineModel.HARMONIC)
        assert result.model_type == "harmonic"
        assert result.initial_rate > 0

    def test_insufficient_data_raises(self, analyzer):
        short = pd.Series([100.0, 90.0])
        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            analyzer.fit(short)

    def test_fit_returns_r_squared(self, analyzer):
        data = make_exponential_data()
        result = analyzer.fit(data)
        assert 0.0 <= result.r_squared <= 1.0

    def test_fit_returns_rmse(self, analyzer):
        data = make_exponential_data()
        result = analyzer.fit(data)
        assert result.rmse >= 0.0


class TestDeclineCurveAnalyzerPredict:
    @pytest.fixture
    def analyzer(self):
        return DeclineCurveAnalyzer()

    def test_predict_future(self, analyzer):
        data = make_exponential_data()
        curve = analyzer.fit(data)
        forecast = curve.predict(12)
        assert len(forecast) == 12
        assert all(v >= 0 for v in forecast)

    def test_predict_declining(self, analyzer):
        data = make_exponential_data()
        curve = analyzer.fit(data)
        forecast = curve.predict(12)
        assert forecast[0] > forecast[-1]


class TestDeclineCurveAnalyzerBestFit:
    @pytest.fixture
    def analyzer(self):
        return DeclineCurveAnalyzer()

    def test_best_fit_selects_highest_r_squared(self, analyzer):
        data = make_exponential_data()
        best = analyzer.best_fit(data)
        assert best.model_type in ("exponential", "hyperbolic", "harmonic")
        assert best.r_squared > 0.8

    def test_best_fit_on_mature_field(self, analyzer):
        data = make_mature_decline()
        best = analyzer.best_fit(data)
        assert best.r_squared > 0.7

    def test_best_fit_on_plateau_data(self, analyzer):
        data = make_plateau_then_decline()
        best = analyzer.best_fit(data)
        assert best.initial_rate > 0


class TestMultiFieldDCA:
    @pytest.fixture
    def analyzer(self):
        return DeclineCurveAnalyzer()

    def test_fit_multiple_fields(self, analyzer):
        fields = {
            "LULA": make_plateau_then_decline(),
            "BUZIOS": make_exponential_data(qi=120000),
            "MARLIM": make_mature_decline(),
        }
        results = {}
        for name, data in fields.items():
            results[name] = analyzer.best_fit(data)

        assert len(results) == 3
        for name, curve in results.items():
            assert curve.r_squared > 0.5, f"{name} fit too poor"
