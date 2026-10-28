"""Authoritative decline rate equations, independent of fitting and calendars.

Source: whitson manual, Decline Curve Analysis, sections 2.1.1–2.1.4,
web edition accessed 2026-10-19 (no publication year supplied):
https://manual.whitson.com/modules/well-performance/decline-curve-analysis/
Time and nominal decline must use reciprocal units. These equations do not
convert effective decline, select fitting bounds, or estimate recovery.
"""

import numpy as np


def exponential_rate(time, initial_rate: float, nominal_decline: float):
    """Return qi*exp(-D*t), manual section 2.1.1."""
    return initial_rate * np.exp(-nominal_decline * np.asarray(time, dtype=float))


def hyperbolic_rate(time, initial_rate: float, nominal_decline: float, b: float):
    """Return qi*(1+b*D*t)**(-1/b), including the exact exponential limit.

    The zero-exponent branch and unit coefficients follow manual section 2.1.
    log1p avoids cancellation when b*D*t is small, without a cutoff constant.
    """
    if b == 0:
        return exponential_rate(time, initial_rate, nominal_decline)
    time = np.asarray(time, dtype=float)
    return initial_rate * np.exp(-np.log1p(b * nominal_decline * time) / b)


def harmonic_rate(time, initial_rate: float, nominal_decline: float):
    """Return the b=1 special case, manual section 2.1.3."""
    return hyperbolic_rate(time, initial_rate, nominal_decline, b=1.0)
