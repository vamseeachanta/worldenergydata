"""Independent hand calculations for synthetic NPV sensitivity inputs.

Assumed test inputs, not calibrated economic assumptions: an immediate outlay
of 100 at period 0 and a receipt of 110 at period 1. All other cash flow
components and optional emissions are zero. Rates are 0, 0.1 and 0.2.

Hand calculation: PV_t = CF_t / (1 + r)**t, so period-zero PV is always
-100 / (1 + r)**0 = -100 and total NPV is -100 + 110 / (1 + r).
The independent rational reference values are:

    r = 0:   PV_1 = 110;                 NPV = 10
    r = 0.1: PV_1 = 110 * 10 / 11 = 100; NPV = 0
    r = 0.2: PV_1 = 110 * 5 / 6 = 275/3; NPV = -25/3

Every numerical input and expected value below comes from this synthetic
example and its hand calculation, independently of the valuation code.
"""

from copy import deepcopy
from itertools import pairwise

import pytest

from worldenergydata.economics.dcf import CashFlowSchedule, calculate_npv

REFERENCE_CASES = (
    (0.0, [-100.0, 110.0], 10.0),
    (0.1, [-100.0, 100.0], 0.0),
    (0.2, [-100.0, 275.0 / 3.0], -25.0 / 3.0),
)


@pytest.fixture
def synthetic_schedule() -> CashFlowSchedule:
    """Use the assumed two-period inputs documented above."""
    return CashFlowSchedule(
        years=[0, 1],
        capex=[100.0, 0.0],
        revenue=[0.0, 110.0],
        opex=[0.0, 0.0],
        carbon_cost=[0.0, 0.0],
        emission_tco2_per_period=[0.0, 0.0],
    )


def test_npv_sensitivity_matches_hand_calculation(synthetic_schedule):
    """Check every discounted period, the total, and strict NPV decline."""
    npvs = []
    for rate, expected_periods, expected_npv in REFERENCE_CASES:
        result = calculate_npv(synthetic_schedule, discount_rate=rate)
        assert result.discounted_cash_flows == pytest.approx(expected_periods)
        assert result.npv == pytest.approx(expected_npv)
        npvs.append(result.npv)

    assert all(earlier > later for earlier, later in pairwise(npvs))


def test_npv_sensitivity_does_not_mutate_schedule(synthetic_schedule):
    """Compare every schedule field with a deep snapshot after each rate."""
    original = deepcopy(synthetic_schedule)
    for rate, _, _ in REFERENCE_CASES:
        calculate_npv(synthetic_schedule, discount_rate=rate)
        assert synthetic_schedule == original
