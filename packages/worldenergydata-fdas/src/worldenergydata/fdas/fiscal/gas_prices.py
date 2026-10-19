"""Explicit Australian gas-price normalization for the USD/Mcf cashflow seam."""

import re
from collections.abc import Mapping
from datetime import datetime
from math import isfinite
from numbers import Real


def convert_australia_gas_prices(
    prices_aud_per_gj: Mapping[str, float],
    *,
    usd_per_aud: Mapping[str, float],
    gj_per_mcf: Mapping[str, float],
) -> dict[str, float]:
    """Convert supplied monthly AUD/GJ quotes to realized USD/Mcf prices.

    The caller selects and qualifies the market series, monthly aggregation,
    exchange rates and gas energy content at the production volume's reference
    conditions. No hub, heating value, FX rate or transport adjustment is assumed.
    This function does not fetch or qualify market data.

    Equation: (AUD/GJ) * (USD/AUD) * (GJ/Mcf) = USD/Mcf, by unit
    cancellation; NIST SP 811 (2008), section 7.11, quantity equations:
    https://www.nist.gov/pml/special-publication-811/nist-guide-si-chapter-7-rules-and-style-conventions-expressing-values
    """
    series = {
        "prices_aud_per_gj": prices_aud_per_gj,
        "usd_per_aud": usd_per_aud,
        "gj_per_mcf": gj_per_mcf,
    }
    for label, values in series.items():
        if not isinstance(values, Mapping):
            raise TypeError(f"{label}: expected a monthly mapping")
        if set(values) != set(prices_aud_per_gj):
            raise ValueError(f"{label}: months must match prices_aud_per_gj exactly")
    converted = {}
    for month, raw_price in prices_aud_per_gj.items():
        if not isinstance(month, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", month):
            raise ValueError("Price month must be YYYY-MM")
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError as exc:
            raise ValueError("Price month must be a valid YYYY-MM") from exc
        price = _number(raw_price, "prices_aud_per_gj", positive=False)
        fx = _number(usd_per_aud[month], "usd_per_aud", positive=True)
        energy = _number(gj_per_mcf[month], "gj_per_mcf", positive=True)
        result = price * fx * energy
        if not isfinite(result):
            raise ValueError(f"Non-finite converted gas price for {month}")
        converted[month] = result
    return converted


def _number(value: float, label: str, *, positive: bool) -> float:
    # Bounds define this conversion contract, not market or gas-property limits.
    # Nonnegative prices match analysis.gas_revenue; conversion factors are positive.
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label}: expected a finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{label}: expected a finite number") from exc
    if not isfinite(number) or number < 0 or (positive and number == 0):
        raise ValueError(
            f"{label}: expected a finite {'positive' if positive else 'nonnegative'} number"
        )
    return number
