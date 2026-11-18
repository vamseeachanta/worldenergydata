"""Synthetic checks for deterministic Arps simulation without curve fitting."""

import math
from decimal import Decimal, localcontext
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from scipy.integrate import quad

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


@pytest.mark.parametrize(
    "name,value",
    [
        ("qi", Fraction(1000)),
        ("Di", Fraction(1, 10)),
        ("economic_limit", Fraction(100)),
        ("b", Fraction(1, 2)),
    ],
)
def test_simulate_accepts_fraction_parameters(name, value):
    params = dict(model="hyperbolic", b=0.5)
    params[name] = value
    result = _simulate(**params)
    expected = _simulate(model="hyperbolic", b=0.5)
    assert (result.qi, result.Di, result.b) == (expected.qi, expected.Di, expected.b)
    assert all(type(v) is float for v in (result.qi, result.Di, result.b))
    assert result.eur_bbl == expected.eur_bbl
    pd.testing.assert_frame_equal(result.forecast_df, expected.forecast_df)


@pytest.mark.parametrize("name", ["qi", "Di", "economic_limit", "b"])
@pytest.mark.parametrize(
    "value", [10**400, Fraction(10**400)], ids=["integer", "fraction"]
)
def test_rejects_real_conversion_overflow(name, value):
    with pytest.raises(ValueError, match=rf"^{name} must be finite"):
        _simulate(**{name: value})


@pytest.mark.parametrize(
    "qi,b,economic_limit",
    [
        (100000.0, 64.0, 99999.0),
        (1000.0, 1.0 - 5e-7, 100.0),
        (1000.0, 1.0, 100.0),
        (1000.0, 1.0 + 5e-7, 100.0),
    ],
)
def test_hyperbolic_eur_matches_integrated_rate(qi, b, economic_limit):
    decline = 0.1
    end_month = math.expm1(b * math.log(qi / economic_limit)) / (b * decline)
    expected, _ = quad(
        lambda t: qi / (1.0 + b * decline * t) ** (1.0 / b), 0.0, end_month
    )
    result = _simulate(
        qi=qi,
        Di=decline,
        b=b,
        model="hyperbolic",
        economic_limit=economic_limit,
        months=1,
    )
    assert math.isfinite(result.eur_bbl)
    assert result.eur_bbl == pytest.approx(expected, rel=1e-10)


@pytest.mark.parametrize(
    "qi,decline,b",
    [
        (65000.0, 0.1, 64.0),
        (10.0, 1.0, 310.0),
        (10.0, 1.0, 22.0),
        (10.0, 1.0, 23.0),
    ],
)
@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_hyperbolic_eur_avoids_intermediate_overflow(qi, decline, b):
    # Synthetic parameters; evaluate the closed form independently at 80 digits.
    # The last two cases straddle the log-space branch at x = 50.
    with localcontext() as context:
        context.prec = 80
        initial_rate = Decimal(str(qi))
        nominal_decline = Decimal(str(decline))
        exponent = Decimal(str(b))
        expected = float(
            (initial_rate / nominal_decline)
            * (initial_rate ** (exponent - 1) - 1)
            / (exponent - 1)
        )

    result = _simulate(
        qi=qi,
        Di=decline,
        b=b,
        model="hyperbolic",
        economic_limit=1.0,
        months=3,
    )
    assert math.isfinite(result.eur_bbl)
    assert result.eur_bbl == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize(
    "qi,decline,b,model",
    [
        (10.0, 1.0, 311.0, "hyperbolic"),
        (1e6, 1e-3, 60.0, "hyperbolic"),
        (1e6, 1e-303, 0.0, "exponential"),
        (1e6, 1e-303, 1.0, "harmonic"),
    ],
)
@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_simulate_rejects_eur_beyond_float_range(qi, decline, b, model):
    # Synthetic cases with true recovery above the floating-point range.
    with pytest.raises(
        ValueError, match="^EUR is not representable in floating point$"
    ):
        _simulate(
            qi=qi,
            Di=decline,
            b=b,
            model=model,
            economic_limit=1.0,
            months=1,
        )


@pytest.mark.parametrize("model", ["harmonic", "hyperbolic"])
@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_simulate_rejects_nonfinite_profile_with_finite_eur(model):
    # Synthetic rates keep EUR finite but overflow the cumulative sample sum.
    with pytest.raises(
        ValueError, match="^Profile is not representable in floating point$"
    ):
        _simulate(
            qi=5e307,
            Di=1.0,
            b=1.0,
            model=model,
            economic_limit=2.5e307,
            months=100,
        )


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_simulate_preserves_finite_profile_near_cumulative_overflow():
    result = _simulate(
        qi=5e307,
        Di=1.0,
        b=1.0,
        model="harmonic",
        economic_limit=2.5e307,
        months=54,
    )
    assert result.eur_bbl == pytest.approx(5e307 * math.log(2.0))
    assert np.isfinite(result.forecast_df.to_numpy()).all()
    expected_rates = 5e307 / (1.0 + np.arange(1, 55))
    np.testing.assert_allclose(result.forecast_df["rate_bbl"], expected_rates)
    np.testing.assert_allclose(
        result.forecast_df["cumulative_bbl"], np.cumsum(expected_rates)
    )


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_simulate_accepts_finite_profile_after_intermediate_overflow():
    result = _simulate(Di=1e308, months=3)
    assert result.eur_bbl == pytest.approx(9e-306, rel=1e-12, abs=0.0)
    np.testing.assert_array_equal(result.forecast_df["rate_bbl"], 0.0)
    np.testing.assert_array_equal(result.forecast_df["cumulative_bbl"], 0.0)


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_simulate_reports_unrepresentable_eur_intermediate():
    # The exact recovery is finite; the existing helper's qi / Di is not.
    with localcontext() as context:
        context.prec = 80
        expected = float((Decimal("1e308") - Decimal("9e307")) / Decimal("0.5"))
    assert math.isfinite(expected)
    assert expected == pytest.approx(2e307)
    with pytest.raises(
        ValueError, match="^EUR is not representable in floating point$"
    ):
        _simulate(qi=1e308, Di=0.5, economic_limit=9e307, months=1)


def test_hyperbolic_approaches_exponential_as_exponent_tends_to_zero():
    exponential = _simulate(months=60)
    hyperbolic = _simulate(model="hyperbolic", b=1e-9, months=60)
    assert hyperbolic.eur_bbl == pytest.approx(exponential.eur_bbl, rel=1e-8)
    np.testing.assert_allclose(
        hyperbolic.forecast_df["rate_bbl"],
        exponential.forecast_df["rate_bbl"],
        # The leading relative correction b * (Di*t)**2 / 2 is 1.8e-8 at t=60.
        rtol=2e-8,
        atol=0.0,
    )
