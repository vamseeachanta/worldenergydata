"""Synthetic checks for deterministic Arps simulation without curve fitting."""

import math

import numpy as np
import pandas as pd
import pytest

from worldenergydata.production.forecast.decline import ArpsDeclineCurve, ForecastResult


def _simulate(**overrides):
    params = dict(
        qi=1000.0,
        Di=0.1,
        b=0.0,
        model="exponential",
        economic_limit=100.0,
        months=12,
    )
    params.update(overrides)
    return ArpsDeclineCurve().simulate(**params)


@pytest.mark.parametrize(
    "model,b,expected_eur",
    [
        ("exponential", 0.0, 9000.0),
        ("harmonic", 1.0, 10000.0 * math.log(10.0)),
        ("hyperbolic", 0.5, 20000.0 * (1.0 - math.sqrt(0.1))),
        ("hyperbolic", 1.0, 10000.0 * math.log(10.0)),
        ("hyperbolic", 2.0, 10000.0 * (10.0 - 1.0)),
    ],
)
def test_simulate_closed_forms_and_legacy_profile(model, b, expected_eur):
    result = _simulate(model=model, b=b)
    assert isinstance(result, ForecastResult)
    assert (result.qi, result.Di, result.b, result.model) == (1000.0, 0.1, b, model)
    assert result.eur_bbl == pytest.approx(expected_eur)
    assert math.isnan(result.r_squared)
    assert result.lower_ci is None
    assert result.upper_ci is None

    months = np.arange(1, 13)
    if model == "exponential":
        expected_rates = 1000.0 * np.exp(-0.1 * months)
    elif model == "harmonic":
        expected_rates = 1000.0 / (1.0 + 0.1 * months)
    else:
        expected_rates = 1000.0 / (1.0 + b * 0.1 * months) ** (1.0 / b)
    expected = pd.DataFrame(
        {
            "month": months,
            "rate_bbl": expected_rates,
            "cumulative_bbl": np.cumsum(expected_rates),
        }
    )
    pd.testing.assert_frame_equal(result.forecast_df, expected)
    pd.testing.assert_frame_equal(
        result.forecast_df, ArpsDeclineCurve().forecast(result, months=12)
    )


@pytest.mark.parametrize("months", [1, 60, np.int64(7)])
def test_simulate_requested_horizon_and_repeatability(months):
    first = _simulate(months=months)
    second = _simulate(months=months)
    assert len(first.forecast_df) == months
    assert first.forecast_df["month"].tolist() == list(range(1, months + 1))
    assert first.eur_bbl == second.eur_bbl
    pd.testing.assert_frame_equal(first.forecast_df, second.forecast_df)


@pytest.mark.parametrize(
    "model,b", [("exponential", 0), ("harmonic", 1), ("hyperbolic", 0.5)]
)
@pytest.mark.parametrize("economic_limit", [1000.0, 1100.0])
def test_economic_limit_at_or_above_initial_rate_keeps_profile(
    model, b, economic_limit
):
    result = _simulate(model=model, b=b, economic_limit=economic_limit)
    assert result.eur_bbl == 0.0
    assert len(result.forecast_df) == 12
    assert (result.forecast_df["rate_bbl"] > 0).all()


def test_profile_continues_below_economic_limit():
    result = _simulate(economic_limit=900.0, months=3)
    assert result.eur_bbl == pytest.approx(1000.0)
    assert result.forecast_df["rate_bbl"].iloc[-1] < 900.0
    assert len(result.forecast_df) == 3


def test_one_barrel_per_month_limit_is_supported():
    assert _simulate(economic_limit=1.0).eur_bbl == pytest.approx(9990.0)


@pytest.mark.parametrize("name", ["qi", "Di", "economic_limit"])
@pytest.mark.parametrize(
    "value", [0.0, -1.0, math.nan, math.inf, -math.inf, "100", None]
)
def test_rejects_invalid_rate_decline_and_limit(name, value):
    with pytest.raises(ValueError, match=name):
        _simulate(**{name: value})


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -1.0, "0", None])
def test_rejects_invalid_exponent(value):
    with pytest.raises(ValueError, match="b"):
        _simulate(b=value)


@pytest.mark.parametrize(
    "model,b", [("exponential", 0.5), ("harmonic", 0.5), ("hyperbolic", 0.0)]
)
def test_rejects_model_inconsistent_exponent(model, b):
    with pytest.raises(ValueError, match="b"):
        _simulate(model=model, b=b)


@pytest.mark.parametrize("model", ["invalid", "Exponential", "", None, []])
def test_rejects_unknown_model(model):
    with pytest.raises(ValueError, match="model"):
        _simulate(model=model)


@pytest.mark.parametrize(
    "months", [True, False, 0, -1, 1.5, 12.0, math.nan, math.inf, "12", None]
)
def test_rejects_invalid_months(months):
    with pytest.raises(ValueError, match="months"):
        _simulate(months=months)


@pytest.mark.parametrize("economic_limit", [0.1, 0.99])
def test_rejects_limit_below_one_barrel_per_month(economic_limit):
    with pytest.raises(ValueError, match="economic_limit"):
        _simulate(economic_limit=economic_limit)
