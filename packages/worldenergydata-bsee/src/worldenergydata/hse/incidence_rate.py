"""Exposure-normalized HSE incidence rates using the BLS convention."""

from math import isfinite
from numbers import Real

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

    BLS (2025 revision, "How to compute incidence rates") defines this base as
    the annual hours of 100 full-time employees. Applying its nonfatal injury
    and illness convention requires the corresponding recordable case count.
    This calculation supplies no acceptance threshold or compliance decision.

    Raises:
        ValueError: The count or exposure is invalid, or the rate cannot be
            represented as a finite float. Missing or zero exposure must not
            be interpreted as a zero incidence rate.
    """
    if (
        isinstance(incident_count, bool)
        or not isinstance(incident_count, int)
        or incident_count < 0
    ):
        raise ValueError("incident_count must be a nonnegative integer")
    if (
        isinstance(hours_worked, bool)
        or not isinstance(hours_worked, Real)
        or not isfinite(hours_worked)
        or hours_worked <= 0
    ):
        raise ValueError("hours_worked must be finite, positive employee-hours")

    # BLS (2025), "How to compute incidence rates": cases * base / hours.
    rate = incident_count * _BASE_HOURS / hours_worked
    if not isfinite(rate):
        raise ValueError("incidence rate cannot be represented as a finite float")
    return rate
