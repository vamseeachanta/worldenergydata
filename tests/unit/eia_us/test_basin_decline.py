"""Tests for shale basin DCA — hyperbolic (b>1) with terminal decline switch."""

import numpy as np
import pytest

from worldenergydata.eia_us.analysis.basin_decline import (
    TERMINAL_B_FACTOR,
    HyperbolicDeclineModel,
    ShaleDeclineAnalyzer,
    ShaleDeclineResult,
    arps_hyperbolic,
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

    def test_terminal_and_pure_forecasts_remain_non_negative(self):
        """Both forecast options preserve nonnegative rates."""
        model_with_switch = HyperbolicDeclineModel(
            qi=5000.0, di=0.08, b=1.5, terminal_b=0.5
        )
        model_pure = HyperbolicDeclineModel(qi=5000.0, di=0.08, b=1.5, terminal_b=None)
        forecast_switch = model_with_switch.predict(120)
        forecast_pure = model_pure.predict(120)
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
        result = ShaleDeclineResult(
            basin="Bakken", model=model, r_squared=0.88, rmse=30.0
        )
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
        results = {
            name: analyzer.fit(data, basin=name) for name, data in basins.items()
        }
        assert len(results) == 2
        for name, res in results.items():
            assert res.r_squared >= 0.0


class TestTerminalDeclineCriterion:
    """Synthetic cases qualify equations and invariance, not basin reserves."""

    @pytest.mark.parametrize("b", [0.0, 0.5, 1.0, 1.5, 2.0])
    @pytest.mark.parametrize("short_horizon", [0, 1, 2, 24, 120, 240])
    def test_overlapping_forecasts_are_identical(self, b, short_horizon):
        model = HyperbolicDeclineModel(qi=1000.0, di=0.08, b=b)
        np.testing.assert_array_equal(
            model.predict(short_horizon), model.predict(360)[:short_horizon]
        )

    def test_fractional_switch_matches_independent_piecewise_equation(self):
        # D(t)=0.1/(1+0.2*t) reaches 0.04 at t=7.5 months.
        # q(7.5)=1000/sqrt(2.5); the exponential continues at 0.04/month.
        model = HyperbolicDeclineModel(
            qi=1000.0, di=0.1, b=2.0, terminal_decline_rate=0.04
        )
        t = np.arange(15, dtype=float)
        expected = np.empty_like(t)
        expected[:8] = 1000.0 / np.sqrt(1.0 + 0.2 * t[:8])
        expected[8:] = (1000.0 / np.sqrt(2.5)) * np.exp(-0.04 * (t[8:] - 7.5))
        np.testing.assert_allclose(model.predict(15), expected, rtol=1e-12)
        assert model.predict(15)[8] < 1000.0 / np.sqrt(2.6)

    def test_integer_switch_preserves_rate_and_nominal_decline(self):
        # qi=1000, Di=0.1, b=1 reaches D=0.05 at t=10, q=500.
        model = HyperbolicDeclineModel(
            qi=1000.0, di=0.1, b=1.0, terminal_decline_rate=0.05
        )
        rates = model.predict(14)
        assert rates[10] == pytest.approx(500.0)
        assert rates[11] == pytest.approx(500.0 * np.exp(-0.05))
        assert -np.log(rates[12] / rates[11]) == pytest.approx(0.05)
        # Sample the actual continuous switch helper on both sides of t=10.
        dt = 1e-4
        times = np.array([10.0 - dt, 10.0, 10.0 + dt])
        hyperbolic_rates = 1000.0 / (1.0 + 0.1 * times)
        joined_rates = model._apply_terminal_switch(times, hyperbolic_rates)
        slopes = np.diff(joined_rates) / dt
        np.testing.assert_allclose(slopes, [-25.0, -25.0], rtol=1e-5)

    def test_default_tail_has_effective_monthly_decline_of_0_8_percent(self):
        model = HyperbolicDeclineModel(qi=1000.0, di=0.1, b=2.0)
        rates = model.predict(120)
        assert 1.0 - rates[-1] / rates[-2] == pytest.approx(0.008)

    @pytest.mark.parametrize("di", [0.0, 0.004, 0.008])
    def test_initial_decline_below_limit_is_not_increased(self, di):
        model = HyperbolicDeclineModel(
            qi=1000.0, di=di, b=1.5, terminal_decline_rate=0.008
        )
        t = np.arange(24, dtype=float)
        np.testing.assert_allclose(model.predict(24), 1000.0 * np.exp(-di * t))

    @pytest.mark.parametrize(
        "disable",
        [
            {"terminal_b": None},
            {"terminal_decline_rate": None},
            {"terminal_b": None, "terminal_decline_rate": 0.04},
        ],
    )
    def test_terminal_switch_can_be_disabled(self, disable):
        model = HyperbolicDeclineModel(qi=1000.0, di=0.1, b=1.5, **disable)
        t = np.arange(240, dtype=float)
        expected = 1000.0 / (1.0 + 0.15 * t) ** (2.0 / 3.0)
        np.testing.assert_allclose(model.predict(240), expected, rtol=1e-12)

    @pytest.mark.parametrize("value", [-0.01, 0.0, np.nan, np.inf])
    def test_invalid_terminal_rate_is_rejected(self, value):
        with pytest.raises(ValueError, match="terminal_decline_rate"):
            HyperbolicDeclineModel(
                qi=1000.0, di=0.1, b=1.5, terminal_decline_rate=value
            )

    @pytest.mark.parametrize("parameter", ["qi", "di", "b"])
    @pytest.mark.parametrize("value", [-1.0, np.nan, np.inf])
    def test_invalid_model_parameters_are_rejected(self, parameter, value):
        parameters = dict(qi=1000.0, di=0.1, b=1.5)
        parameters[parameter] = value
        with pytest.raises(ValueError, match=parameter):
            HyperbolicDeclineModel(**parameters)

    def test_half_exponent_uses_rate_threshold(self):
        model = HyperbolicDeclineModel(
            qi=1000.0, di=0.1, b=0.5, terminal_decline_rate=0.04
        )
        # D(30)=0.04 and q(30)=1000/(1+0.05*30)^2=160.
        rates = model.predict(33)
        assert rates[30] == pytest.approx(160.0)
        assert rates[31] == pytest.approx(160.0 * np.exp(-0.04))

    @pytest.mark.parametrize("value", [-1.0, np.nan, np.inf])
    def test_invalid_legacy_terminal_b_is_rejected(self, value):
        with pytest.raises(ValueError, match="terminal_b"):
            HyperbolicDeclineModel(qi=1000.0, di=0.1, b=1.5, terminal_b=value)

    @pytest.mark.parametrize("horizon", [-1, 1.5, True, np.nan, np.inf])
    def test_invalid_horizon_is_rejected(self, horizon):
        model = HyperbolicDeclineModel(qi=1000.0, di=0.1, b=1.5)
        with pytest.raises(ValueError, match="n_months"):
            model.predict(horizon)

    def test_unreached_terminal_time_is_not_evaluated(self):
        # Tiny b puts the crossing far beyond the requested samples. Evaluating
        # q(ts) needlessly would overflow; preserve the pre-transition equation.
        model = HyperbolicDeclineModel(qi=1000.0, di=0.1, b=1e-18)
        expected = np.array([arps_hyperbolic(t, 1000.0, 0.1, 1e-18) for t in range(2)])
        np.testing.assert_array_equal(model.predict(2), expected)

    def test_default_tail_is_below_pure_hyperbolic(self):
        switched = HyperbolicDeclineModel(qi=1000.0, di=0.1, b=1.5).predict(360)
        pure = HyperbolicDeclineModel(
            qi=1000.0, di=0.1, b=1.5, terminal_b=None
        ).predict(360)
        np.testing.assert_array_equal(switched[:12], pure[:12])
        assert np.all(switched[120:] < pure[120:])

    def test_fitted_result_preserves_forecast_prefixes(self):
        result = ShaleDeclineAnalyzer().fit(make_synthetic_shale_production())
        np.testing.assert_array_equal(result.predict(120), result.predict(360)[:120])
        assert len(result.predict(np.int64(24))) == 24


@pytest.mark.parametrize(
    "b_min,b_max", [(-0.1, 3.0), (np.nan, 3.0), (0.0, np.inf), (1.0, 1.0), (2.0, 1.0)]
)
def test_fit_rejects_invalid_b_bounds_before_optimization(monkeypatch, b_min, b_max):
    from unittest.mock import Mock

    from worldenergydata.eia_us.analysis import basin_decline as decline

    optimizer = Mock(return_value=(np.array([1000.0, 0.1, 1.5]), None))
    monkeypatch.setattr(decline, "curve_fit", optimizer)
    with pytest.raises(ValueError, match="b_min|b_max"):
        ShaleDeclineAnalyzer().fit(
            make_synthetic_shale_production(), b_min=b_min, b_max=b_max
        )
    optimizer.assert_not_called()
