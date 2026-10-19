"""Hand calculations using the cited decline equations, without fitting."""

import numpy as np
import pytest

from worldenergydata.common.decline import (
    exponential_rate,
    harmonic_rate,
    hyperbolic_rate,
)


def test_exponential_half_life():
    """Synthetic qi=100, D=ln(2), t=[0,1,2]: q=[100,50,25].

    Manual, Decline Curve Analysis, section 2.1.1 (accessed 2026-10-19):
    q=qi*exp(-D*t); exp(-ln(2)*t)=2**(-t).
    """
    np.testing.assert_allclose(
        exponential_rate([0, 1, 2], 100, np.log(2)), [100, 50, 25]
    )


@pytest.mark.parametrize("b", [0.5, 1, 2])
def test_hyperbolic_hand_calculation(b):
    """Synthetic qi=100, D=1, t=2/b: base=1+b*1*2/b=3.

    Manual section 2.1 (accessed 2026-10-19), q=qi*(1+b*D*t)**(-1/b).
    b=.5 gives 100/9, b=1 gives 100/3, b=2 gives 100/sqrt(3).
    """
    expected = {0.5: 100 / 9, 1: 100 / 3, 2: 100 / np.sqrt(3)}[b]
    assert hyperbolic_rate(2 / b, 100, 1, b) == pytest.approx(expected)


def test_exponential_and_harmonic_limits():
    """At t=1, qi=100, D=1: b=0 -> 100/e; b=1 -> 100/2=50.

    Manual sections 2.1.1 and 2.1.3 (accessed 2026-10-19).
    """
    assert hyperbolic_rate(1, 100, 1, 0) == pytest.approx(100 / np.e)
    assert harmonic_rate(1, 100, 1) == 50


def test_zero_decline_and_empty_times():
    """D=0 makes each equation q=qi; an empty time array stays empty."""
    for model in (exponential_rate, harmonic_rate):
        np.testing.assert_array_equal(model([0, 1], 100, 0), [100, 100])
        assert model([], 100, 0).size == 0
    np.testing.assert_array_equal(hyperbolic_rate([0, 1], 100, 0, 0.5), [100, 100])
