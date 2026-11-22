"""Synthetic checks for anonymous peer quartiles; no incident data is used.

Issue #425 supplies the minimum cell size of ten. Expected quartiles below
come from independent hand calculations using zero-based rank (n - 1) * p
and linear interpolation, including both endpoints.
"""

import sys
from fractions import Fraction

import pytest

from worldenergydata.hse.peer_quartiles import peer_quartiles


def test_min_cell_size():
    """Issue #425: nine rates are suppressed, ten rates are eligible."""
    assert peer_quartiles(range(9)) is None
    assert peer_quartiles(range(10)) is not None


def test_inclusive_quartiles_match_hand_case():
    """For sorted 0..9, ranks are 9*p = 2.25, 4.5, 6.75.

    Adjacent rates differ by one, so interpolation yields those same values.
    """
    assert peer_quartiles(range(10)) == {
        "q1": 2.25,
        "median": 4.5,
        "q3": 6.75,
    }


def test_nonlinear_rates_match_hand_case():
    """Squares of 0..11: ranks 11*p = 2.75, 5.5, 8.25.

    Q1 = 4 + .75*(9-4) = 7.75; median = 25 + .5*(36-25) = 30.5;
    Q3 = 64 + .25*(81-64) = 68.25. These are synthetic inputs.
    """
    assert peer_quartiles(value**2 for value in range(12)) == {
        "q1": 7.75,
        "median": 30.5,
        "q3": 68.25,
    }


def test_permutation_invariance():
    """Reversing or rotating synthetic 0..9 preserves the hand-case values."""
    expected = {"q1": 2.25, "median": 4.5, "q3": 6.75}
    assert peer_quartiles(reversed(range(10))) == expected
    assert peer_quartiles([*range(5, 10), *range(5)]) == expected


@pytest.mark.parametrize("rate", [0.0, 7.0, sys.float_info.max])
def test_all_equal_values(rate):
    """Interpolation of equal endpoints returns that value, even at float max."""
    assert peer_quartiles([rate] * 10) == {
        "q1": rate,
        "median": rate,
        "q3": rate,
    }


@pytest.mark.parametrize("size", [0, 1, 9])
def test_below_threshold_group(size):
    """Empty, singleton and boundary cells are below the #425 minimum."""
    assert peer_quartiles([0.0] * size) is None


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        float("nan"),
        float("inf"),
        -float("inf"),
        -1,
        True,
        False,
        "1",
        1j,
        10**400,
        -Fraction(1, 10**400),
    ],
    ids=[
        "missing",
        "nan",
        "positive-infinity",
        "negative-infinity",
        "negative",
        "true",
        "false",
        "string",
        "complex",
        "float-overflow",
        "negative-underflow",
    ],
)
@pytest.mark.parametrize("valid_size", [0, 9, 10])
def test_invalid_rates_rejected(invalid, valid_size):
    """Reject invalid members even in suppressed cells or after ten valid ones.

    Synthetic 10**400 exceeds float range; its negative reciprocal rounds to
    negative zero, so nonnegativity must also be checked before conversion.
    """
    with pytest.raises(ValueError, match="rates must"):
        peer_quartiles([0.0] * valid_size + [invalid])


@pytest.mark.parametrize("rates", [None, 1.0])
def test_missing_or_noniterable_group_rejected(rates):
    """An absent group cannot be interpreted as an empty group."""
    with pytest.raises(ValueError, match="rates must"):
        peer_quartiles(rates)


def test_output_contains_no_members():
    """The complete output schema contains only the hand-case quartiles."""
    result = peer_quartiles(range(10))

    assert type(result) is dict
    assert set(result) == {"q1", "median", "q3"}
    assert all(type(value) is float for value in result.values())
    assert result == {"q1": 2.25, "median": 4.5, "q3": 6.75}
