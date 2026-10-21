"""Exposure-normalized HSE incidence rates using the BLS convention."""

from math import isfinite
from numbers import Integral, Real
from operator import index

# BLS, How To Compute Your Firm's Incidence Rate for Safety Management,
# 2025-03-10 revision, "How to compute incidence rates": normalization hours.
# https://www.bls.gov/iif/overview/compute-nonfatal-incidence-rates.htm
_BASE_HOURS = 200_000


def incidence_rate(incident_count: int, hours_worked: float) -> float:
    """Return cases per 200,000 employee-hours, using the cited BLS formula.

    ``incident_count`` is a nonnegative integer count of the selected cases.
    ``hours_worked`` is finite, positive actual employee-hours for the same
    population and reporting period, excluding paid nonwork time. The caller
    must classify cases and supply matching exposure; incident records alone
    do not establish exposure. Pool counts and hours before calling when
    combining disjoint groups, rather than averaging their individual rates.
    Integral counts are normalized to built-in integers before arithmetic.
    Exposure is normalized to a finite, positive built-in float before use.

    BLS (2025 revision, "How to compute incidence rates") defines this base as
    the annual hours of 100 full-time employees. Applying its nonfatal injury
    and illness convention requires the corresponding recordable case count.
    This calculation supplies no acceptance threshold or compliance decision.

    Raises:
        ValueError: The count or exposure is invalid, exposure is not a finite
            positive float after conversion, or the rate is not a finite float.
            Missing or zero exposure must not be interpreted as a zero rate.
    """
    if (
        isinstance(incident_count, bool)
        or not isinstance(incident_count, Integral)
        or incident_count < 0
    ):
        raise ValueError("incident_count must be a nonnegative integer")
    incident_count = index(incident_count)
    if (
        isinstance(hours_worked, bool)
        or not isinstance(hours_worked, Real)
        or hours_worked <= 0
    ):
        raise ValueError("hours_worked must be finite, positive employee-hours")
    try:
        hours_worked = float(hours_worked)
    except (OverflowError, ValueError) as exc:
        raise ValueError(
            "hours_worked must be finite, positive employee-hours"
        ) from exc
    if not isfinite(hours_worked) or hours_worked <= 0:
        raise ValueError("hours_worked must be finite, positive employee-hours")
    # BLS (2025), "How to compute incidence rates": cases * base / hours.
    # Keep intermediates as integers so only the final quotient is rounded.
    hours_numerator, hours_denominator = hours_worked.as_integer_ratio()
    try:
        return incident_count * _BASE_HOURS * hours_denominator / hours_numerator
    except OverflowError as exc:
        raise ValueError(
            "incidence rate cannot be represented as a finite float"
        ) from exc
