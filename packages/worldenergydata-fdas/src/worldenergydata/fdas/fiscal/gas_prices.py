"""Normalize a supplied Australian gas marker to the FDAS USD/Mcf contract.

No market prices, gas heating values or exchange rates are supplied by this
module. Callers select the delivery location, observation period and gross/net
heating-value basis appropriate to their production volumes.
"""

from collections.abc import Mapping
from math import isfinite
from numbers import Real


def au_gas_prices_usd_per_mcf(
    prices_aud_per_gj: Mapping[str, float],
    *,
    gj_per_mcf: Mapping[str, float],
    usd_per_aud: Mapping[str, float],
) -> dict[str, float]:
    """Convert monthly AUD/GJ prices using explicit monthly heat content and FX.

    The three mappings must have identical YYYY-MM keys. FX is USD per AUD,
    never its reciprocal. Inputs must be real numbers, excluding bool, and
    finite. Prices may be zero; heat content and FX must be positive.
    No escalation or averaging is applied.

    Equation: P[USD/Mcf] = P[AUD/GJ] * H[GJ/Mcf] * X[USD/AUD].
    Basis: BIPM, The International System of Units, ninth edition (2019),
    section 5.4.1, quantity calculus (algebra of quantities):
    https://www.bipm.org/documents/20126/41483022/SI-Brochure-9.pdf
    This is dimensional cancellation, with no empirical conversion constant.
    """
    months = set(prices_aud_per_gj)
    if set(gj_per_mcf) != months or set(usd_per_aud) != months:
        raise ValueError("Gas price, heating value and FX months must match")
    converted = {}
    for month, raw_price in prices_aud_per_gj.items():
        price = _finite_input(raw_price, "gas price", positive=False)
        heat = _finite_input(gj_per_mcf[month], "GJ/Mcf", positive=True)
        fx = _finite_input(usd_per_aud[month], "USD/AUD", positive=True)
        converted_price = price * heat * fx
        if not isfinite(converted_price):
            raise ValueError("Converted gas price must be finite")
        converted[month] = converted_price
    return converted


def _finite_input(value: float, label: str, *, positive: bool) -> float:
    try:
        if not isinstance(value, Real) or isinstance(value, bool):
            raise TypeError
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be finite and numeric") from exc
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    # Zero is the algebraic boundary, not an empirical acceptance limit.
    if positive and number <= 0:
        raise ValueError(f"{label} must be finite and positive")
    if number < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return number
