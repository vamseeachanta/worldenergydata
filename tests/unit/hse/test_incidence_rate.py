"""Value checks for the BLS exposure-normalized incidence rate.

Source: BLS, How To Compute Your Firm's Incidence Rate for Safety Management,
2025-03-10 revision, sections "How to compute incidence rates" and "An example":
https://www.bls.gov/iif/overview/compute-nonfatal-incidence-rates.htm
The normalization is 200,000 employee-hours. Test data not taken from the
published example are synthetic; their independent arithmetic is given below.
"""

import pytest

from worldenergydata.hse.incidence_rate import incidence_rate


@pytest.mark.parametrize("cases, expected", [(7, 3.5), (3, 1.5)])
def test_bls_published_examples(cases, expected):
    """BLS (2025), "An example": 7 cases / 400,000 h gives 3.5;
    its DART subset has 3 cases / 400,000 h and gives 1.5 per 200,000 h.
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


@pytest.mark.parametrize("cases", [-1, 1.5, True, False, "7", None])
def test_invalid_case_count(cases):
    """Counts must be nonnegative integers; these are API validation cases."""
    with pytest.raises(ValueError, match="incident_count"):
        incidence_rate(cases, 400_000)


@pytest.mark.parametrize("hours", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_unknown_or_invalid_exposure(hours):
    """A denominator must be finite and positive; zero is not a measured rate."""
    with pytest.raises(ValueError, match="hours_worked"):
        incidence_rate(7, hours)


@pytest.mark.parametrize("hours", [True, False, "400000", None, 1j])
def test_invalid_exposure_type(hours):
    """Reject booleans and non-real exposure rather than silently coercing."""
    with pytest.raises(ValueError, match="hours_worked"):
        incidence_rate(7, hours)


def test_zero_cases_do_not_mask_missing_exposure():
    """Zero cases with zero exposure gives an undefined quotient, not zero."""
    with pytest.raises(ValueError, match="hours_worked"):
        incidence_rate(0, 0)
