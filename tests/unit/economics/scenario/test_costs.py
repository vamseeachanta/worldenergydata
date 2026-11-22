"""Illustrative cost examples; all expected values use independent arithmetic."""

import pytest

from worldenergydata.economics.scenario import (
    activity_cost_usd,
    cost_breakdown,
    expenditure_profile_usd,
)
from worldenergydata.economics.scenario_inputs import CostBreakdown, Expenditure


def test_engineering_and_contingency_bases_are_explicit():
    result = cost_breakdown(CostBreakdown((2000.0, 3000.0), 0.2, 0.25, True))
    assert result.base_usd == pytest.approx(2000 + 3000)
    assert result.engineering_usd == pytest.approx((2000 + 3000) * 0.2)
    assert result.contingency_usd == pytest.approx((2000 + 3000) * (1 + 0.2) * 0.25)
    assert result.total_usd == pytest.approx((2000 + 3000) * (1 + 0.2) * (1 + 0.25))
    separate = cost_breakdown(CostBreakdown((2000.0, 3000.0), 0.2, 0.25, False))
    assert separate.total_usd == pytest.approx(5000 * (1 + 0.2 + 0.25))
    assert cost_breakdown(CostBreakdown((), 0.0, 0.0, False)).total_usd == 0


def test_activity_cost_rounding_and_schedule_rollup():
    # 5 days * 250 USD/day = 1250 USD: half increment rounds upward.
    assert activity_cost_usd(5.0, 250.0, 100.0) == 1300.0
    assert activity_cost_usd(5.0, 250.0, 0.0) == 1250.0
    events = (
        Expenditure(1, "capital", 2000.0),
        Expenditure(1, "capital", 3000.0),
        Expenditure(2, "operating", 500.0),
    )
    assert expenditure_profile_usd(events, 3, "capital") == (0, 2000 + 3000, 0)
    assert expenditure_profile_usd(events, 3, "operating") == (0, 0, 500)
    with pytest.raises(ValueError):
        expenditure_profile_usd(events, 2, "capital")


@pytest.mark.parametrize("args", [(-1, 10, 0), (1, float("inf"), 0), (1, 10, -1)])
def test_activity_rejects_invalid_inputs(args):
    with pytest.raises(ValueError):
        activity_cost_usd(*args)


def test_expenditure_and_breakdown_validation():
    with pytest.raises(ValueError):
        Expenditure(0, "unclassified", 100.0)
    with pytest.raises(ValueError):
        CostBreakdown((100.0,), 0.2, 0.25, 1)


def test_cost_rollup_rejects_numerical_overflow():
    # Numerical limit probe, not an illustrative estimate.
    with pytest.raises(ValueError):
        cost_breakdown(CostBreakdown((1e308, 1e308), 0.2, 0.25, True))


def test_fractional_day_activity_cost_rounds_decimal_half_up():
    # 0.29 days * 25000 USD/day = 7250 USD: the half increment rounds up.
    assert activity_cost_usd(0.29, 25000.0, 100.0) == 7300.0
