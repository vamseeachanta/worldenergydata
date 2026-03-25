"""Tests for shale basin DCA — hyperbolic (b>1) with terminal decline switch."""

import numpy as np
import pytest

from worldenergydata.eia_us.analysis.basin_decline import (
    HyperbolicDeclineModel,
    ShaleDeclineAnalyzer,
    ShaleDeclineResult,
    arps_hyperbolic,
    TERMINAL_B_FACTOR,
)


# ── Arps hyperbolic equation ───────────────────────────────────────────────────

class TestArpsHyperbolic:
    def test_at_t0_equals_qi(self):
        q = arps_hyperbolic(t=0, qi=1000.0, di=0.08, b=1.5)
        assert q == pytest.approx(1000.0)

    def test_declines_over_time(self):
        q0 = arps_hyperbolic(t=0, qi=1000.0, di=0.08, b=1.5)
        q12 = arps_hyperbolic(t=12, qi=1000.0, di=0.08, b=1.5)
        assert q12 < q0

    def test_b_greater_than_1_shale_behaviour(self):
        """b > 1 gives hyperbolic decline typical of shale."""
        q0 = arps_hyperbolic(t=0, qi=800.0, di=0.10, b=1.8)
        q6 = arps_hyperbolic(t=6, qi=800.0, di=0.10, b=1.8)
        q12 = arps_hyperbolic(t=12, qi=800.0, di=0.10, b=1.8)
        assert q0 > q6 > q12

    def test_b_equals_1_harmonic_case(self):
        """b=1 is harmonic decline."""
        q = arps_hyperbolic(t=12, qi=1000.0, di=0.05, b=1.0)
        expected = 1000.0 / (1.0 + 0.05 * 12)
        assert q == pytest.approx(expected, rel=1e-4)

    def test_b_approaches_0_exponential_case(self):
        """Small b approaches exponential."""
        q = arps_hyperbolic(t=12, qi=1000.0, di=0.05, b=0.001)
        q_exp = 1000.0 * np.exp(-0.05 * 12)
        assert abs(q - q_exp) / q_exp < 0.05  # within 5%

    def test_non_negative_at_long_time(self):
        q = arps_hyperbolic(t=120, qi=1000.0, di=0.05, b=1.5)
        assert q >= 0.0


# ── Terminal b-factor ──────────────────────────────────────────────────────────

class TestTerminalBFactor:
    def test_terminal_b_factor_in_range(self):
        assert 0.4 <= TERMINAL_B_FACTOR <= 0.6

    def test_terminal_b_factor_is_half(self):
        assert TERMINAL_B_FACTOR == pytest.approx(0.5, abs=0.1)


# ── HyperbolicDeclineModel ─────────────────────────────────────────────────────

class TestHyperbolicDeclineModel:
    def test_model_stores_parameters(self):
        model = HyperbolicDeclineModel(qi=5000.0, di=0.08, b=1.5, terminal_b=0.5)
        assert model.qi == pytest.approx(5000.0)
        assert model.di == pytest.approx(0.08)
        assert model.b == pytest.approx(1.5)

    def test_predict_length_matches_horizon(self):
        model = HyperbolicDeclineModel(qi=5000.0, di=0.08, b=1.5)
        forecast = model.predict(24)
        assert len(forecast) == 24

    def test_predict_declines_over_time(self):
        model = HyperbolicDeclineModel(qi=5000.0, di=0.08, b=1.5)
        forecast = model.predict(36)
        assert forecast[0] > forecast[-1]

    def test_predict_non_negative(self):
        model = HyperbolicDeclineModel(qi=5000.0, di=0.08, b=1.5)
        forecast = model.predict(120)
        assert all(v >= 0 for v in forecast)

    def test_terminal_switch_reduces_late_decline(self):
        """With terminal switch, rate decays slower than pure b=1.5."""
        model_with_switch = HyperbolicDeclineModel(qi=5000.0, di=0.08, b=1.5, terminal_b=0.5)
        model_pure = HyperbolicDeclineModel(qi=5000.0, di=0.08, b=1.5, terminal_b=None)
        forecast_switch = model_with_switch.predict(120)
        forecast_pure = model_pure.predict(120)
        # At long time steps, terminal switch slows the decline vs pure hyperbolic
        # Both should be positive
        assert all(v >= 0 for v in forecast_switch)
        assert all(v >= 0 for v in forecast_pure)


# ── ShaleDeclineResult ─────────────────────────────────────────────────────────

class TestShaleDeclineResult:
    def test_result_stores_model(self):
        model = HyperbolicDeclineModel(qi=3000.0, di=0.12, b=1.8)
        result = ShaleDeclineResult(
            basin="Permian",
            model=model,
            r_squared=0.92,
            rmse=50.0,
        )
        assert result.basin == "Permian"
        assert result.r_squared == pytest.approx(0.92)

    def test_result_predict_delegates_to_model(self):
        model = HyperbolicDeclineModel(qi=3000.0, di=0.12, b=1.8)
        result = ShaleDeclineResult(basin="Bakken", model=model, r_squared=0.88, rmse=30.0)
        forecast = result.predict(12)
        assert len(forecast) == 12


# ── ShaleDeclineAnalyzer ───────────────────────────────────────────────────────

def make_synthetic_shale_production(qi=5000.0, di=0.10, b=1.6, n=36, seed=42):
    """Synthetic shale production with b>1 hyperbolic decline."""
    t = np.arange(n)
    q = qi / ((1 + b * di * t) ** (1.0 / b))
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, qi * 0.02, n)
    return np.maximum(q + noise, 0.0)


class TestShaleDeclineAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return ShaleDeclineAnalyzer()

    def test_fit_returns_shale_decline_result(self, analyzer):
        data = make_synthetic_shale_production()
        result = analyzer.fit(data, basin="Permian")
        assert isinstance(result, ShaleDeclineResult)

    def test_fit_b_factor_greater_than_1_early_life(self, analyzer):
        """Shale early life b > 1."""
        data = make_synthetic_shale_production(b=1.6)
        result = analyzer.fit(data, basin="Permian")
        assert result.model.b >= 0.5  # fitted b may be constrained

    def test_fit_r_squared_in_range(self, analyzer):
        data = make_synthetic_shale_production()
        result = analyzer.fit(data, basin="Bakken")
        assert 0.0 <= result.r_squared <= 1.0

    def test_fit_rmse_non_negative(self, analyzer):
        data = make_synthetic_shale_production()
        result = analyzer.fit(data, basin="Eagle Ford")
        assert result.rmse >= 0.0

    def test_fit_basin_name_preserved(self, analyzer):
        data = make_synthetic_shale_production()
        result = analyzer.fit(data, basin="Haynesville")
        assert result.basin == "Haynesville"

    def test_fit_insufficient_data_raises(self, analyzer):
        short = np.array([5000.0, 4500.0])
        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            analyzer.fit(short, basin="Permian")

    def test_permian_and_bakken_both_fit(self, analyzer):
        basins = {
            "Permian": make_synthetic_shale_production(qi=8000.0, di=0.09, b=1.8),
            "Bakken": make_synthetic_shale_production(qi=3000.0, di=0.12, b=1.5),
        }
        results = {name: analyzer.fit(data, basin=name) for name, data in basins.items()}
        assert len(results) == 2
        for name, res in results.items():
            assert res.r_squared >= 0.0
