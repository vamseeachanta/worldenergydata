"""Illustrative examples with hand formulas and closed-form discount identities."""
import pytest

from worldenergydata.economics.scenario import (
    discounted_cash_flow_usd, net_cash_flow_usd, npv_usd, revenue_usd,
)


def test_revenue_and_signed_net_cash_flow():
    volumes, prices = (2000.0, 1000.0), (60.0, -20.0)
    revenue = revenue_usd(volumes, prices)
    assert revenue == (2000 * 60, 1000 * -20)
    assert net_cash_flow_usd(revenue, (30000.0, 0.0), (2000.0, 1000.0)) == (
        2000 * 60 - 30000 - 2000, 1000 * -20 - 1000)


@pytest.mark.parametrize('offset', [0, 1, 3])
def test_annuity_identity_and_discount_origin(offset):
    payment, rate, count = 2000.0, 0.08, 7
    # Ordinary annuity is at t=1..n. Shift all times by offset-1.
    expected = payment * (1 - (1 + rate) ** -count) / rate
    expected *= (1 + rate) ** (1 - offset)
    flows = (payment,) * count
    assert npv_usd(flows, rate, offset) == pytest.approx(expected)
    discounted = discounted_cash_flow_usd(flows, rate, offset)
    assert discounted[0] == pytest.approx(payment / (1 + rate) ** offset)
    assert sum(discounted) == pytest.approx(expected)


def test_zero_rate_and_single_payment_limits():
    flows = (-2000.0, 800.0, 900.0, 700.0)
    assert npv_usd(flows, 0.0, 1) == -2000 + 800 + 900 + 700
    assert discounted_cash_flow_usd(flows, 0.0, 0) == flows
    assert npv_usd((800.0,), -0.2, 2) == pytest.approx(800 / 0.8 ** 2)
    assert npv_usd((), 0.08, 0) == 0.0


@pytest.mark.parametrize('rate', [-1.0, float('nan'), float('inf')])
def test_invalid_discount_rate(rate):
    with pytest.raises(ValueError):
        npv_usd((100.0,), rate, 1)


def test_nonfinite_values_and_mismatched_horizons_fail():
    with pytest.raises(ValueError):
        revenue_usd((100.0,), (60.0, 60.0))
    with pytest.raises(ValueError):
        net_cash_flow_usd((100.0,), (0.0,), (float('nan'),))
    with pytest.raises(ValueError):
        npv_usd((100.0,), 0.08, -1)
