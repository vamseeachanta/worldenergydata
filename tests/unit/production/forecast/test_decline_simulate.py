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


@pytest.mark.parametrize("unit", ["D", "ns"])
@pytest.mark.parametrize("name", ["qi", "Di", "economic_limit", "b", "months"])
def test_rejects_duration_in_numeric_field(name, unit):
    params = dict(model="harmonic", b=1, months=1)
    params[name] = np.timedelta64(1, unit)
    with pytest.raises(ValueError, match=rf"^{name} must be "):
        _simulate(**params)


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


def test_rejects_exact_fraction_limit_below_floor_before_rounding():
    limit = Fraction(2**54 - 1, 2**54)
    assert limit < 1 and float(limit) == 1.0
    with pytest.raises(ValueError, match="economic_limit must be at least 1"):
        _simulate(economic_limit=limit)


@pytest.mark.parametrize(
    "model,b",
    [
        ("harmonic", Fraction(2**54 + 1, 2**54)),
        ("harmonic", Fraction(2**54 - 1, 2**54)),
        ("exponential", Fraction(1, 2**1075)),
        ("exponential", Fraction(-1, 2**1075)),
    ],
)
def test_rejects_exact_fraction_exponent_before_rounding(model, b):
    assert float(b) == (1.0 if model == "harmonic" else 0.0)
    with pytest.raises(ValueError, match="b is inconsistent with model"):
        _simulate(model=model, b=b)


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


@pytest.mark.parametrize(
    "model,b", [("harmonic", 1), ("hyperbolic", 1), ("hyperbolic", 2)]
)
@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_profile_preserves_rates_when_decline_times_month_overflows(model, b):
    result = _simulate(
        qi=1e308, Di=1e308, b=b, model=model, economic_limit=1e307, months=3
    )
    # For b=1, q(t) = 1 / (t + 1e-308), giving 1, 1/2 and 1/3.
    # For b=2, q(t) = 1e154 / sqrt(2*t + 1e-308) at the same inputs.
    if b == 1:
        rates = [1.0, 0.5, 1 / 3]
        cumulative = [1.0, 1.5, 11 / 6]
    else:
        rates = [1e154 / math.sqrt(2), 5e153, 1e154 / math.sqrt(6)]
        cumulative = np.cumsum(rates)
    np.testing.assert_allclose(
        result.forecast_df["rate_bbl"], rates, rtol=1e-12, atol=0
    )
    np.testing.assert_allclose(
        result.forecast_df["cumulative_bbl"], cumulative, rtol=1e-12, atol=0
    )
    pd.testing.assert_frame_equal(
        result.forecast_df, ArpsDeclineCurve().forecast(result, months=3)
    )


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_profile_preserves_subnormal_rates_after_scaling():
    # q(t) = 1e308 / (1 + 0.5e308*t)**2 rounds to 4e-308/t**2.
    result = _simulate(
        qi=1e308, Di=1e308, b=0.5, model="hyperbolic", economic_limit=1e307, months=2
    )
    np.testing.assert_allclose(
        result.forecast_df["rate_bbl"], [4e-308, 1e-308], rtol=1e-12, atol=0
    )
    np.testing.assert_allclose(
        result.forecast_df["cumulative_bbl"], [4e-308, 5e-308], rtol=1e-12, atol=0
    )


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_exponential_eur_preserves_representable_recovery():
    # Synthetic recovery is finite even though qi / Di overflows.
    with localcontext() as context:
        context.prec = 80
        expected = float((Decimal("1e308") - Decimal("9e307")) / Decimal("0.5"))
    assert math.isfinite(expected)
    assert expected == pytest.approx(2e307)
    result = _simulate(qi=1e308, Di=0.5, economic_limit=9e307, months=1)
    assert result.eur_bbl == pytest.approx(expected, rel=1e-14)


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


@pytest.mark.parametrize(
    "model,b",
    [("exponential", 0.0), ("harmonic", 1.0), ("hyperbolic", 0.5), ("hyperbolic", 1.0)],
)
@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_eur_preserves_adjacent_initial_and_limit_rates(model, b):
    # Use the exact binary inputs in an independent 100-digit closed form.
    qi = np.nextafter(1000.0, np.inf)
    decline = 1e-14
    with localcontext() as context:
        context.prec = 100
        initial = Decimal.from_float(float(qi))
        limit = Decimal(1000)
        nominal = Decimal.from_float(decline)
        exponent = Decimal.from_float(b)
        if b == 0:
            expected = (initial - limit) / nominal
        elif b == 1:
            expected = initial / nominal * (initial / limit).ln()
        else:
            expected = (
                initial
                / nominal
                * (((exponent - 1) * (initial / limit).ln()).exp() - 1)
                / (exponent - 1)
            )
    result = _simulate(
        qi=qi, Di=decline, b=b, model=model, economic_limit=1000.0, months=1
    )
    assert result.eur_bbl == pytest.approx(float(expected), rel=1e-14)


@pytest.mark.parametrize(
    "qi,limit",
    [
        (1000 + Fraction(1, 2**45), 1000),
        (1000, 1000 - Fraction(1, 2**45)),
        (np.uint64(2**63 + 1), float(2**63)),
        (2**63 + 1, np.float64(2**63)),
    ],
)
def test_rejects_positive_recovery_erased_by_rate_rounding(qi, limit):
    # In the first two cases, (qi - limit) / Di = 2**-45 / 2**-45 = 1 bbl.
    assert float(qi) == float(limit)
    with pytest.raises(ValueError, match=r"qi.*economic_limit.*precision"):
        _simulate(qi=qi, Di=2**-45, economic_limit=limit, months=1)


@pytest.mark.parametrize(
    "model,b",
    [("exponential", 0), ("harmonic", 1), ("hyperbolic", 0.5), ("hyperbolic", 1)],
)
def test_eur_across_float_rounding_midpoint(model, b):
    limit = 1000 + Fraction(1, 2**44)
    qi = limit + Fraction(1, 2**60)
    assert float(qi) - float(limit) == 2**-43
    # Exact exponential EUR = 2**-60 / 2**-60 = 1 bbl. For the other
    # exponents the relative correction is smaller than (qi - limit) / limit.
    result = _simulate(
        qi=qi, Di=2**-60, b=b, model=model, economic_limit=limit, months=1
    )
    assert result.eur_bbl == pytest.approx(1.0, rel=1e-14, abs=0)


@pytest.mark.parametrize(
    "qi,limit",
    [
        (1000 + Fraction(3, 2**45), 1000.0),
        (np.float64(1000), 1000 - Fraction(3, 2**45)),
    ],
)
def test_eur_preserves_difference_of_fraction_and_float(qi, limit):
    # (3 * 2**-45 bbl/month) / (2**-45 per month) = 3 bbl.
    result = _simulate(qi=qi, Di=2**-45, economic_limit=limit, months=1)
    assert result.eur_bbl == 3.0


@pytest.mark.parametrize(
    "model,b", [("exponential", 0), ("harmonic", 1), ("hyperbolic", 0.5)]
)
def test_midpoint_gap_smaller_than_a_float_keeps_representable_eur(model, b):
    limit = 1000 + Fraction(1, 2**44)
    qi = limit + Fraction(1, 2**1075)
    # The gap divided by the decline is 2**-1075 / 2**-1074 = 0.5 bbl.
    # The relative correction for these exponents is less than 2**-1075.
    result = _simulate(
        qi=qi, Di=2**-1074, b=b, model=model, economic_limit=limit, months=1
    )
    assert result.eur_bbl == 0.5


@pytest.mark.parametrize(
    "gap_multiple,b",
    [
        (1.0, math.nextafter(1.0, 0.0)),
        (1.5, math.nextafter(1.0, 0.0)),
        (2.5, math.nextafter(1.0, 2.0)),
    ],
)
def test_normal_relative_gap_preserves_eur_near_harmonic_exponent(gap_multiple, b):
    limit = 1 + Fraction(1, 2**53)
    decline = gap_multiple * 2.0**-1022
    qi = limit * (1 + Fraction(decline))
    # Integrate the Whitson manual's decline rate (Decline Curve Analysis,
    # web ed. 2026-10-19, §2.1) and expand for relative gap r = Di:
    # EUR = limit * (1 + b*r/2 + O(r**2)), just above the rounding midpoint.
    result = _simulate(
        qi=qi, Di=decline, b=b, model="hyperbolic", economic_limit=limit, months=1
    )
    assert result.eur_bbl == math.nextafter(1.0, 2.0)


@pytest.mark.parametrize(
    "decline,expected",
    [(2**-1024, math.expm1(0.5) / 0.5), (2**51, 2**-1074)],
)
def test_subnormal_relative_gap_retains_hyperbolic_exponent_effect(decline, expected):
    limit = 1 + Fraction(1, 2**53)
    qi = limit + Fraction(1, 2**1024)
    # (b-1)*log(qi/limit) is 0.5 to one ulp. The gap divided by Di is
    # 1 or 2**-1075. Multiplying by expm1(0.5)/0.5 before rounding makes
    # the second recovery round up to the smallest positive float.
    result = _simulate(
        qi=qi,
        Di=decline,
        b=2**1023,
        model="hyperbolic",
        economic_limit=limit,
        months=1,
    )
    assert result.eur_bbl == pytest.approx(expected, rel=1e-14, abs=0)


@pytest.mark.parametrize("qi", [Fraction(1000), 1000 - Fraction(1, 2**45)])
def test_exact_rate_at_or_below_rounded_cutoff_retains_zero_eur(qi):
    assert float(qi) == 1000.0
    assert _simulate(qi=qi, economic_limit=1000).eur_bbl == 0.0


@pytest.mark.parametrize("b", [np.nextafter(0.0, 1.0), 1e-320, 1e-310])
@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_hyperbolic_profile_preserves_subnormal_exponent(b):
    # Synthetic closed form at 400 digits retains even the smallest exponent.
    with localcontext() as context:
        context.prec = 400
        exponent = Decimal.from_float(float(b))
        nominal = Decimal.from_float(0.1)
        expected_rates = [
            float(Decimal(1000) * (-(1 + exponent * nominal * t).ln() / exponent).exp())
            for t in range(1, 13)
        ]
    result = _simulate(model="hyperbolic", b=b)
    np.testing.assert_allclose(
        result.forecast_df["rate_bbl"], expected_rates, rtol=1e-13, atol=0
    )
    np.testing.assert_allclose(
        result.forecast_df["cumulative_bbl"],
        np.cumsum(expected_rates),
        rtol=1e-13,
        atol=0,
    )
    pd.testing.assert_frame_equal(
        result.forecast_df, ArpsDeclineCurve().forecast(result, months=12)
    )


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_exponential_profile_scales_before_decay_underflows():
    # Synthetic rate remains representable although exp(-750) rounds to zero.
    with localcontext() as context:
        context.prec = 100
        expected = float(Decimal.from_float(1e300) * Decimal(-750).exp())
    result = _simulate(qi=1e300, Di=750.0, economic_limit=1.0, months=1)
    assert result.forecast_df["rate_bbl"].iloc[0] == pytest.approx(
        expected, rel=1e-12, abs=0
    )
    assert result.forecast_df["cumulative_bbl"].iloc[0] == pytest.approx(
        expected, rel=1e-12, abs=0
    )
    pd.testing.assert_frame_equal(
        result.forecast_df, ArpsDeclineCurve().forecast(result, months=1)
    )
