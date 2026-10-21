"""Independent closed-form GoM benchmark, revision 1 (2026-10-21).

All production inputs are synthetic, in thousand bbl/day (kbd); tolerances are
chosen test inputs, not recommended acceptance limits. PEP 485 (2015),
"Symmetry" and "Behavior near zero", supports reference-scaled comparison
and explicit absolute tolerance near zero: https://peps.python.org/pep-0485/.
No fiscal constants or current-law claims are exercised here.
"""

import pytest

from worldenergydata.eia_us.analysis.us_fiscal import GoMCrosscheck


@pytest.mark.parametrize(
    "eia, reference, difference, fraction, accepted",
    [
        (105.0, 100.0, 5.0, 0.05, True),
        (95.0, 100.0, -5.0, 0.05, True),
        (106.0, 100.0, 6.0, 0.06, False),
        (94.0, 100.0, -6.0, 0.06, False),
    ],
)
def test_reference_scaled_hand_calculation(
    eia, reference, difference, fraction, accepted
):
    """Hand check: d = 105-100 = 5 or 95-100 = -5 kbd; |d|/100 = 0.05.

    At 106 or 94 kbd, |d| = 6 kbd and the fraction is 0.06. The synthetic
    caller-selected limit is 0.05 (5.0 %), inclusive at equality. The exact
    fractions are asserted directly; no numerical acceptance fudge is used.
    """
    result = GoMCrosscheck(tolerance_pct=0.05).compare(eia, reference)
    assert result["difference_kbd"] == difference
    assert result["pct_difference"] == fraction
    assert result["within_tolerance"] is accepted
    assert result["status"] == ("PASS" if accepted else "FAIL")
    assert result["relative_tolerance_fraction"] == 0.05


def test_issue_regression_nonzero_against_zero_is_not_evaluated():
    """40 bbl/day / 1000 = 0.04 kbd; d = 0.04-0 = 0.04 kbd.

    Unit basis: NIST SP 811 (2008), section 4, Table 5: kilo = 10**3.
    Relative error divides by zero and is undefined. PEP 485 (2015),
    "Behavior near zero": no nonzero value is small relative to zero.
    """
    for checker in (GoMCrosscheck(), GoMCrosscheck(tolerance_pct=0.05)):
        result = checker.compare(0.04, 0.0)
        assert result["difference_kbd"] == 0.04
        assert result["pct_difference"] is None
        assert result["within_tolerance"] is None
        assert result["status"] == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "absolute_tolerance, accepted", [(0.0, False), (0.03, False), (0.04, True)]
)
def test_zero_reference_uses_explicit_absolute_tolerance(absolute_tolerance, accepted):
    """Hand check: |0.04-0| = 0.04 kbd; compare with 0, 0.03, 0.04 kbd.

    All limits are synthetic caller choices; the boundary is inclusive.
    A large relative limit cannot authorize a comparison against zero.
    """
    result = GoMCrosscheck(
        tolerance_pct=2.0, absolute_tolerance_kbd=absolute_tolerance
    ).compare(0.04, 0.0)
    assert result["pct_difference"] is None
    assert result["within_tolerance"] is accepted
    assert result["status"] == ("PASS" if accepted else "FAIL")
    assert result["absolute_tolerance_kbd"] == absolute_tolerance


@pytest.mark.parametrize("production", [0.0, 100.0])
def test_exact_equality_needs_no_tolerance(production):
    """Hand check: x-x = 0 kbd, including zero/zero; exact equality passes.

    The relative difference remains undefined for zero/zero, rather than
    reporting an invented percentage. Synthetic nonzero input: 100 kbd.
    """
    result = GoMCrosscheck().compare(production, production)
    assert result["difference_kbd"] == 0.0
    assert result["pct_difference"] == (None if production == 0.0 else 0.0)
    assert result["within_tolerance"] is True
    assert result["status"] == "PASS"


def test_nonzero_reference_without_tolerance_is_not_evaluated():
    """Hand check: 105-100 = 5 kbd; 5/100 = 0.05; no limit was supplied."""
    result = GoMCrosscheck().compare(105.0, 100.0)
    assert result["pct_difference"] == 0.05
    assert result["within_tolerance"] is None
    assert result["status"] == "NOT_EVALUATED"


def test_absolute_tolerance_can_cover_nonzero_reference():
    """Hand check: |105-100| = 5 kbd <= supplied 5 kbd absolute limit."""
    result = GoMCrosscheck(absolute_tolerance_kbd=5.0).compare(105.0, 100.0)
    assert result["within_tolerance"] is True


def test_either_explicit_tolerance_can_pass():
    """Hand check: 5 kbd exceeds 4 kbd but 5/100 = 0.05 meets 0.05."""
    result = GoMCrosscheck(tolerance_pct=0.05, absolute_tolerance_kbd=4.0).compare(
        105.0, 100.0
    )
    assert result["within_tolerance"] is True


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("parameter", ["tolerance_pct", "absolute_tolerance_kbd"])
def test_invalid_tolerances_rejected(parameter, value):
    """Policy: tolerances must be finite and nonnegative; -1 is synthetic."""
    with pytest.raises(ValueError, match=parameter):
        GoMCrosscheck(**{parameter: value})


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("parameter", ["eia_production_kbd", "bsee_production_kbd"])
def test_invalid_production_rejected(parameter, value):
    """Policy: production rates must be finite and nonnegative."""
    inputs = {"eia_production_kbd": 0.0, "bsee_production_kbd": 0.0}
    inputs[parameter] = value
    with pytest.raises(ValueError, match=parameter):
        GoMCrosscheck().compare(**inputs)
