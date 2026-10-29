"""Independent synthetic arithmetic for production crosschecks (issue #1607).

The unit convention is 1 kbd = 1,000 bbl/day. Hand calculations:
40 / 1,000 = 0.04 kbd; a relative difference from zero is undefined.
1,100 / 1,000 = 1.1 kbd; against 1.0 kbd the signed difference is
0.1 kbd and the absolute relative difference is 0.1 (10 percent).
These arbitrary inputs provide arithmetic examples, not production assumptions.
"""

from math import nextafter, ulp

import pytest

from worldenergydata.eia_us.analysis.us_fiscal import GoMCrosscheck


@pytest.mark.parametrize("tolerance_fraction", [0.05, 1.0])
def test_nonzero_against_zero_is_indeterminate(tolerance_fraction):
    """Neither a 5 percent nor a 100 percent relative limit defines division by zero."""
    result = GoMCrosscheck(tolerance_pct=tolerance_fraction).compare(
        eia_production_kbd=40.0 / 1_000.0,
        bsee_production_kbd=0.0,
    )

    assert result["eia_kbd"] == 0.04
    assert result["bsee_kbd"] == 0.0
    assert result["difference_kbd"] == 0.04
    assert result["pct_difference"] is None
    assert result["within_tolerance"] is None


def test_zero_against_zero_agrees():
    """Exact zero kbd equality agrees even at a zero dimensionless tolerance."""
    result = GoMCrosscheck(tolerance_pct=0.0).compare(0.0, 0.0)

    assert result == {
        "eia_kbd": 0.0,
        "bsee_kbd": 0.0,
        "difference_kbd": 0.0,
        "pct_difference": 0.0,
        "within_tolerance": True,
    }


@pytest.mark.parametrize(
    ("tolerance_fraction", "expected_agreement"),
    [(0.09, False), (0.11, True)],
)
def test_nonzero_reference_hand_arithmetic(tolerance_fraction, expected_agreement):
    """The hand-calculated 10 percent error lies between 9 and 11 percent."""
    result = GoMCrosscheck(tolerance_pct=tolerance_fraction).compare(
        eia_production_kbd=1_100.0 / 1_000.0,
        bsee_production_kbd=1.0,
    )

    # Decimal 1.1 is not binary-exact. Four ULPs at 1.1 conservatively cover
    # conversion and subtraction rounding: this bound is in kbd for the
    # difference, dimensionless after division by the exact 1.0 kbd reference.
    rounding_bound = 4 * ulp(1.1)
    assert set(result) == {
        "eia_kbd",
        "bsee_kbd",
        "difference_kbd",
        "pct_difference",
        "within_tolerance",
    }
    assert result["eia_kbd"] == 1.1
    assert result["bsee_kbd"] == 1.0
    assert result["difference_kbd"] == pytest.approx(0.1, rel=0, abs=rounding_bound)
    # The existing pct_difference API returns a fraction, not percentage points.
    assert result["pct_difference"] == pytest.approx(0.1, rel=0, abs=rounding_bound)
    assert result["within_tolerance"] is expected_agreement


@pytest.mark.parametrize(
    ("tolerance_fraction", "expected_agreement"),
    [
        (nextafter(0.125, 0.0), False),
        (0.125, True),
        (nextafter(0.125, 1.0), True),
    ],
)
def test_relative_tolerance_boundary_is_inclusive(
    tolerance_fraction, expected_agreement
):
    """(1.125 - 1) / 1 = 1/8, exactly binary-representable, or 12.5 percent.

    Check dimensionless limits one representable float below, at, and above
    the boundary without a fuzzy assertion on the boolean decision.
    """
    result = GoMCrosscheck(tolerance_pct=tolerance_fraction).compare(1.125, 1.0)

    assert result["difference_kbd"] == 0.125
    assert result["pct_difference"] == 0.125
    assert result["within_tolerance"] is expected_agreement
