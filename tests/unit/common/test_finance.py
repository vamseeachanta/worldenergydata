"""Independent examples for the shared time-zero discounting convention."""

import numpy as np
import pytest

from worldenergydata.common.finance import discounted_cash_flows, net_present_value


def test_published_npv_example():
    """NumPy Financial 1.0.0, npv Examples (2019), rounds to five decimals.

    https://raw.githubusercontent.com/numpy/numpy-financial/v1.0.0/numpy_financial/_financial.py
    Inputs: rate=.08; flows=[-40000, 5000, 8000, 12000, 30000].
    Published answer=3065.22267, with half a last-place rounding allowance.
    """
    assert net_present_value([-40000, 5000, 8000, 12000, 30000], 0.08) == (
        pytest.approx(3065.22267, rel=0, abs=0.000005)
    )


def test_discounted_components_and_time_zero():
    """Hand calculation: [-100,121]/[1,1.1]=[-100,110]; sum=10.

    Synthetic inputs; NumPy Financial 1.0.0 npv Notes defines the equation.
    """
    np.testing.assert_allclose(discounted_cash_flows([-100, 121], 0.1), [-100, 110])
    assert net_present_value([-100, 121], 0.1) == pytest.approx(10)


@pytest.mark.parametrize("rate", [0, 0.1, -0.5])
def test_empty_and_single_flow(rate):
    """Empty sum=0; a single time-zero flow=-100 for every chosen rate."""
    assert net_present_value([], rate) == 0
    assert net_present_value([-100], rate) == -100


def test_leading_zero_is_a_period():
    """Hand calculation at r=1: [0,-100,400] -> 0-50+100=50."""
    assert net_present_value([0, -100, 400], 1) == 50
