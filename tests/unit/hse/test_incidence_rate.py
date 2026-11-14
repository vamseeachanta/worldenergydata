"""Value checks for the BLS exposure-normalized incidence rate.

Source: BLS, How To Compute Your Firm's Incidence Rate for Safety Management,
2025-03-10 revision, sections "How to compute incidence rates" and "An example":
https://www.bls.gov/iif/overview/compute-nonfatal-incidence-rates.htm
The normalization is also verified in Cal/OSHA, Brief Guide to Recordkeeping
Requirements, 2021 PDF revision, p. 5, Calculating Injury and Illness Incidence
Rates: https://www.dir.ca.gov/dosh/dosh_publications/RecKeepOverview.pdf
The normalization is 200,000 employee-hours. All example inputs are synthetic;
their independent arithmetic is given below.
"""

from fractions import Fraction

import numpy as np
import pytest

from worldenergydata.hse.incidence_rate import incidence_rate


@pytest.mark.parametrize("cases, expected", [(7, 3.5), (3, 1.5)])
def test_hand_calculated_case_subsets(cases, expected):
    """Synthetic hand calculation using the cited incidence-rate formula:
    7 * 200,000 / 400,000 = 3.5; 3 * 200,000 / 400,000 = 1.5.
    """
    assert incidence_rate(cases, 400_000) == expected


def test_synthetic_exposure_dataset():
    """Hand calculation using the cited BLS (2025) formula:

    Two disjoint groups in the same reporting period have (2 cases, 50,000 h)
    and (1 case, 100,000 h). Pooled exposure is 150,000 employee-hours and
    pooled cases are 3; 3 * 200,000 / 150,000 = 4.0 cases per 200,000 h.
    Averaging group rates would incorrectly give (8.0 + 2.0) / 2 = 5.0.
    All group values are synthetic inputs, not acceptance limits.
    """
    groups = [(2, 50_000), (1, 100_000)]
    cases = sum(count for count, _ in groups)
    employee_hours = sum(hours for _, hours in groups)

    assert incidence_rate(cases, employee_hours) == 4.0


def test_zero_cases_with_known_exposure():
    """BLS (2025) formula, synthetic: 0 * 200,000 / 50,000 = 0.0."""
    assert incidence_rate(0, 50_000) == 0.0


def test_fractional_employee_hours():
    """BLS (2025) formula, synthetic: 1 * 200,000 / 12,500.5
    = 400,000 / 25,001 cases per 200,000 employee-hours.
    """
    assert incidence_rate(1, 12_500.5) == pytest.approx(400_000 / 25_001)


@pytest.mark.parametrize(
    "count_type",
    [np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64],
)
def test_numpy_integral_case_count(count_type):
    """Synthetic: NumPy integer scalars retain 7 * 200,000 / 400,000 = 3.5."""
    rate = incidence_rate(count_type(7), 400_000)

    assert rate == 3.5
    assert type(rate) is float


def test_numpy_aggregated_case_count():
    """Synthetic: an integer array sum pools 4 + 3 cases before normalization."""
    cases = np.array([4, 3], dtype=np.int64).sum()

    assert incidence_rate(cases, 400_000) == 3.5


@pytest.mark.parametrize("count_type", [np.int64, np.uint64])
def test_numpy_zero_cases_with_known_exposure(count_type):
    """Synthetic: signed and unsigned zero counts retain a measured zero rate."""
    assert incidence_rate(count_type(0), 50_000) == 0.0


@pytest.mark.parametrize(
    "cases, expected",
    [(np.int64(2**63 - 1), 2.0**62), (np.uint64(2**64 - 1), 2.0**63)],
    ids=["signed-maximum", "unsigned-maximum"],
)
def test_numpy_large_counts_avoid_fixed_width_overflow(cases, expected):
    """Synthetic: count * 200,000 / 400,000 = count / 2.

    At each integer maximum, this rounds to the indicated float power of two.
    Multiplication must occur after conversion to an arbitrary-precision integer.
    """
    rate = incidence_rate(cases, 400_000)

    assert rate == expected
    assert type(rate) is float


@pytest.mark.parametrize("exposure_type", [np.float16, np.float32, np.float64])
def test_numpy_exposure_uses_builtin_float(exposure_type):
    """Synthetic: 1 * 200,000 / 40,000 = 5.0, including binary16 exposure."""
    rate = incidence_rate(1, exposure_type(40_000))

    assert rate == 5.0
    assert type(rate) is float


@pytest.mark.parametrize(
    "cases, expected",
    [(10**308, 2e5), (10**400, 2e97)],
    ids=["large-numerator", "count-beyond-float"],
)
def test_large_counts_preserve_finite_rates(cases, expected):
    """Synthetic: 10**n * 200,000 / 1e308 = 2 * 10**(n - 303).

    The integer numerator exceeds the float range, but these quotients do not.
    """
    assert incidence_rate(cases, 1e308) == pytest.approx(expected)


@pytest.mark.parametrize(
    "cases, hours",
    [(10**400, 1.0), (1, 5e-324)],
    ids=["large-count", "subnormal-hours"],
)
def test_unrepresentable_rate_raises_value_error(cases, hours):
    """Synthetic quotients exceed the finite float range, including tiny hours."""
    with pytest.raises(
        ValueError, match="rate cannot be represented as a finite float"
    ):
        incidence_rate(cases, hours)


@pytest.mark.parametrize(
    "cases",
    [
        -1,
        np.int64(-1),
        1.5,
        np.float64(7),
        True,
        False,
        np.bool_(True),
        np.bool_(False),
        "7",
        None,
    ],
)
def test_invalid_case_count(cases):
    """Counts must be nonnegative integers; these are API validation cases."""
    with pytest.raises(ValueError, match="incident_count"):
        incidence_rate(cases, 400_000)


@pytest.mark.parametrize("hours", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_unknown_or_invalid_exposure(hours):
    """A denominator must be finite and positive; zero is not a measured rate."""
    with pytest.raises(ValueError, match="hours_worked"):
        incidence_rate(7, hours)


@pytest.mark.parametrize(
    "hours",
    [10**400, Fraction(1, 10**400)],
    ids=["float-overflow", "float-underflow"],
)
def test_exposure_requires_positive_finite_float(hours):
    """Synthetic real exposures overflow float or round to zero on conversion."""
    with pytest.raises(ValueError, match="hours_worked"):
        incidence_rate(1, hours)


@pytest.mark.parametrize("hours", [True, False, "400000", None, 1j])
def test_invalid_exposure_type(hours):
    """Reject booleans and non-real exposure rather than silently coercing."""
    with pytest.raises(ValueError, match="hours_worked"):
        incidence_rate(7, hours)


def test_zero_cases_do_not_mask_missing_exposure():
    """Zero cases with zero exposure gives an undefined quotient, not zero."""
    with pytest.raises(ValueError, match="hours_worked"):
        incidence_rate(0, 0)
