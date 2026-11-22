"""Deterministic fit-contract checks using independent hand calculations.

Synthetic parameters are chosen for simple algebra, not as basin estimates.
Only the existing forecast suite exercises parameter estimation; these tests
inject optimizer outcomes and make no fitting-quality or live-data claim.
"""

from math import sqrt
from unittest.mock import Mock

import numpy as np
import pytest

from worldenergydata.eia_us.analysis import basin_decline as decline


@pytest.mark.parametrize("failure_type", [RuntimeError, ValueError])
def test_optimizer_failure_is_explicit(monkeypatch, failure_type):
    """Both formerly handled failures must escape as a documented fit error."""
    failure = failure_type("injected optimizer failure")
    optimizer = Mock(side_effect=failure)
    monkeypatch.setattr(decline, "curve_fit", optimizer)
    # Six observations meet the existing minimum; rates are arbitrary fixtures.
    production = np.array([6.0, 5.0, 4.0, 3.0, 2.0, 1.0])

    with pytest.raises(decline.DeclineFitError, match="fit failed") as caught:
        decline.ShaleDeclineAnalyzer().fit(production)

    assert caught.value.__cause__ is failure
    optimizer.assert_called_once()


def test_fit_diagnostics_use_fitted_objective(monkeypatch):
    """qi=12, di=1/2, b=2 gives q(t)=12/sqrt(1+t), by substitution."""
    parameters = np.array([12.0, 0.5, 2.0])
    times = np.arange(6, dtype=float)  # Existing minimum, months zero through five.
    expected_rates = np.array([12.0 / sqrt(1.0 + t) for t in times])
    # Hand calculation: SSE = 1+1+4+4+0+0 = 10; MSE = 10/6 = 5/3.
    expected_residuals = np.array([1.0, -1.0, 2.0, -2.0, 0.0, 0.0])
    production = expected_rates + expected_residuals
    objective = Mock(wraps=decline.arps_hyperbolic)
    optimizer = Mock(return_value=(parameters, None))
    analyzer = decline.ShaleDeclineAnalyzer()
    diagnostics = Mock(wraps=analyzer._r_squared)
    forecast = Mock(side_effect=AssertionError("forecast used for diagnostics"))
    monkeypatch.setattr(decline, "arps_hyperbolic", objective)
    monkeypatch.setattr(decline, "curve_fit", optimizer)
    monkeypatch.setattr(decline.HyperbolicDeclineModel, "predict", forecast)
    monkeypatch.setattr(analyzer, "_r_squared", diagnostics)

    result = analyzer.fit(production)

    optimizer.assert_called_once()
    fitted_objective, fitted_times, fitted_observations = optimizer.call_args.args
    assert fitted_objective is objective
    np.testing.assert_array_equal(fitted_times, times)
    np.testing.assert_array_equal(fitted_observations, production)
    objective.assert_called_once()
    diagnostic_times, *diagnostic_parameters = objective.call_args.args
    np.testing.assert_array_equal(diagnostic_times, fitted_times)
    np.testing.assert_array_equal(diagnostic_parameters, parameters)
    np.testing.assert_array_equal(
        [result.model.qi, result.model.di, result.model.b], parameters
    )
    diagnostics.assert_called_once()
    observed, predicted = diagnostics.call_args.args
    np.testing.assert_array_equal(observed, production)
    # Square roots and residual subtraction incur floating-point roundoff;
    # 1e-12 allows those operations while remaining far below fixture residuals.
    np.testing.assert_allclose(predicted, expected_rates, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(
        observed - predicted, expected_residuals, rtol=1e-12, atol=1e-12
    )
    assert result.rmse == pytest.approx(sqrt(5.0 / 3.0), rel=1e-12, abs=1e-12)
    forecast.assert_not_called()


def test_negative_r_squared_matches_hand_calculation(monkeypatch):
    """For [1,2,3] vs [3,2,1]: mean=2, SST=2, SSE=8, R²=-3."""
    observed = np.array([1.0, 2.0, 3.0])
    predicted = np.array([3.0, 2.0, 1.0])
    analyzer = decline.ShaleDeclineAnalyzer()
    assert analyzer._r_squared(observed, predicted) == -3.0

    # Repeat the hand example twice to meet the existing six-month minimum:
    # SST=4, SSE=16, R²=1-16/4=-3, RMSE=sqrt(16/6)=sqrt(8/3) bopd.
    # Inject both the objective and its optimizer result to isolate arithmetic.
    production_bopd = np.tile(observed, 2)
    objective_rates_bopd = np.tile(predicted, 2)
    monkeypatch.setattr(
        decline, "curve_fit", Mock(return_value=(np.array([3.0, 0.5, 1.0]), None))
    )
    monkeypatch.setattr(
        decline, "arps_hyperbolic", Mock(return_value=objective_rates_bopd)
    )
    result = analyzer.fit(production_bopd)

    assert result.r_squared == -3.0
    # A square root is rounded in binary floating point; allow 1e-12 relative
    # error rather than requiring bitwise identity with the independent sqrt.
    assert result.rmse == pytest.approx(sqrt(8.0 / 3.0), rel=1e-12)


@pytest.mark.parametrize("exact_match", [True, False])
def test_constant_observation_r_squared_preserves_convention(exact_match):
    """SST=0 is undefined; retain the existing 1 if exact, otherwise 0 rule."""
    # Constant [2,2,2] has mean 2 and SST=0; [1,1,1] has nonzero SSE=3.
    observed = np.array([2.0, 2.0, 2.0])
    predicted = observed.copy() if exact_match else np.array([1.0, 1.0, 1.0])
    expected = 1.0 if exact_match else 0.0
    assert decline.ShaleDeclineAnalyzer._r_squared(observed, predicted) == expected
