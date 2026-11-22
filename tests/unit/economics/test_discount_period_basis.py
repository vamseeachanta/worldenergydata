"""Independent arithmetic checks for the local annual discount-period convention.

Annual periods start at t=0; years are labels, not discount exponents, as
specified by CashFlowSchedule in worldenergydata.economics.dcf. This documents
that local contract only, without settling cross-engine or reference-date policy
or qualifying public economics.

Independent hand calculation (arbitrary arithmetic inputs, not assumptions):

    t    revenue    opex    capex    carbon_cost    net
    0          0      15       80              5   -100
    1        150      30        0             10    110
    2         10     100       20             11   -121

Net = revenue - opex - capex - carbon_cost. At r=0.1, discounted flows are
[-100 / 1.1**0, 110 / 1.1**1, -121 / 1.1**2] = [-100, 100, -100],
and their sum is NPV = -100. Calendar labels [2030, 2031, 2032] are arbitrary
consecutive labels for exactly these same three annual periods.

The absolute rounding budget is 32 * binary64 epsilon * 300, approximately
2.2e-12: 300 is the sum of absolute discounted flows; 32 conservatively allows
for subtraction, rate addition, powers, division and summation in this small
calculation. Relative tolerance is zero so pytest adds no default allowance.
"""

from copy import deepcopy
from sys import float_info

import pytest

from worldenergydata.economics.dcf import CashFlowSchedule, NPVResult, calculate_npv

DISCOUNT_RATE = 0.1
ABS_TOL = 32 * float_info.epsilon * 300


@pytest.fixture
def cash_flow_inputs():
    """Return fresh lists from the independent hand calculation above."""
    return {
        "years": [0, 1, 2],
        "capex": [80.0, 0.0, 20.0],
        "revenue": [0.0, 150.0, 10.0],
        "opex": [15.0, 30.0, 100.0],
        "carbon_cost": [5.0, 10.0, 11.0],
    }


def _assert_hand_calculation(result: NPVResult) -> None:
    """Check every returned component against the independent arithmetic."""
    assert result.net_cash_flows == pytest.approx(
        [-100.0, 110.0, -121.0], rel=0.0, abs=ABS_TOL
    )
    assert result.discounted_cash_flows == pytest.approx(
        [-100.0, 100.0, -100.0], rel=0.0, abs=ABS_TOL
    )
    assert result.npv == pytest.approx(-100.0, rel=0.0, abs=ABS_TOL)
    assert sum(result.discounted_cash_flows) == pytest.approx(
        -100.0, rel=0.0, abs=ABS_TOL
    )
    assert result.discount_rate == DISCOUNT_RATE


def test_discounted_loss_periods_match_hand_calculation(cash_flow_inputs):
    """Discount the final loss at t=2 and preserve all original input lists."""
    original_inputs = deepcopy(cash_flow_inputs)

    result = calculate_npv(CashFlowSchedule(**cash_flow_inputs), DISCOUNT_RATE)

    _assert_hand_calculation(result)
    assert cash_flow_inputs == original_inputs


def test_period_labels_do_not_rebase_discounting(cash_flow_inputs):
    """Consecutive calendar-year labels retain discount positions t=0, 1, 2."""
    original_inputs = deepcopy(cash_flow_inputs)
    calendar_inputs = deepcopy(cash_flow_inputs)
    calendar_inputs["years"] = [2030, 2031, 2032]
    original_calendar_inputs = deepcopy(calendar_inputs)

    indexed_result = calculate_npv(CashFlowSchedule(**cash_flow_inputs), DISCOUNT_RATE)
    calendar_result = calculate_npv(CashFlowSchedule(**calendar_inputs), DISCOUNT_RATE)

    _assert_hand_calculation(indexed_result)
    _assert_hand_calculation(calendar_result)
    assert calendar_result == indexed_result
    assert cash_flow_inputs == original_inputs
    assert calendar_inputs == original_calendar_inputs
