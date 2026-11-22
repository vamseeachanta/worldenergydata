"""Production-rate input contract for the fiscal helpers.

Source: issue #1292 (2026), missing-rate defect; docs/agent-pack.md, SF6.
The required domain is finite and nonnegative, in barrels per day.
Python 3.14 Library Reference, math.isfinite (2025), defines NaN and both
infinities as non-finite and explicitly includes zero as finite:
https://docs.python.org/3.14/library/math.html#math.isfinite

All monetary amounts and finite rates below are synthetic test inputs.
They establish input handling and arithmetic, not fiscal applicability.
"""

import pytest

from worldenergydata.west_africa.analysis import field_economics

# Source: input contract and math.isfinite reference above. Negative unit and
# fractional rates are synthetic sign checks; None represents missing input.
INVALID_RATES = [
    pytest.param(None, id="missing"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="positive-infinity"),
    pytest.param(float("-inf"), id="negative-infinity"),
    pytest.param(-1.0, id="negative-integer"),
    pytest.param(-0.5, id="negative-fraction"),
]


@pytest.mark.parametrize("rate", INVALID_RATES)
def test_profit_oil_split_rejects_invalid_rate(rate):
    """None is absent; NaN/infinities are not finite; negative rates < zero.

    Each therefore requires ValueError before any tier is selected. Zero USD
    is a synthetic amount: the rate contract also applies without profit oil.
    """
    with pytest.raises(ValueError, match="production_rate_bopd"):
        field_economics.calculate_profit_oil_split(
            profit_oil=0.0, production_rate_bopd=rate
        )


@pytest.mark.parametrize("rate", INVALID_RATES)
def test_psc_calculate_rejects_invalid_rate(rate):
    """The same domain applies through calculate, including zero cash flows.

    All amounts are synthetic zero USD; no fiscal coefficient is an oracle.
    """
    with pytest.raises(ValueError, match="production_rate_bopd"):
        field_economics.NigeriaDeepwaterPSC().calculate(
            gross_revenue=0.0,
            opex=0.0,
            capex=0.0,
            production_rate_bopd=rate,
        )


# Source: synthetic boundary examples for the contract above: zero, a positive
# fraction, and a large finite rate. There is no new upper acceptance limit.
@pytest.mark.parametrize("rate", [0.0, 0.5, 1_000_000_000.0])
def test_finite_nonnegative_rate_preserves_split_arithmetic(monkeypatch, rate):
    """Hand calculation using a synthetic tier, independent of fiscal tables.

    Assume profit oil = 8 USD and government share = 1/4 at all finite rates.
    Government = 8 * (1/4) = 2 USD; contractor = 8 * (3/4) = 6 USD.
    These binary-exact values require no rounding tolerance. The infinite tier
    ceiling is a synthetic open-ended band, not an accepted production rate.
    """
    # Source: the independent hand calculation in this test's docstring.
    monkeypatch.setattr(field_economics, "PROFIT_OIL_TIERS", [(float("inf"), 0.25)])

    result = field_economics.calculate_profit_oil_split(
        profit_oil=8.0, production_rate_bopd=rate
    )

    assert result == {"nnpc": 2.0, "contractor": 6.0}
