"""Explicit monthly gas pricing in USD/Mcf, with no assumed price or HHV."""

from math import isfinite
from typing import Dict, Tuple

import pandas as pd


def monthly_gas_revenue(
    production: pd.DataFrame, gas_prices: Dict[str, float]
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return monthly Mcf and USD revenue; require one priced row per month.

    Prices share the oil deck's YYYY-MM keys and monthly time base. Each price
    is the supplied month's realized USD/Mcf value; escalation belongs in the
    caller's deck, as for oil. No USD/MMBtu conversion is performed.
    """
    if "MONTHLY_GAS_MCF" not in production:
        raise ValueError("Gas deck requires MONTHLY_GAS_MCF")
    months = production["YEAR_MONTH"].astype(str)
    if months.duplicated().any():
        raise ValueError("Duplicate production months in gas-enabled cashflow")
    volumes, revenues = {}, {}
    for month, raw_volume in zip(months, production["MONTHLY_GAS_MCF"]):
        volume = _nonnegative_finite(raw_volume, f"gas volume for {month}")
        if month not in gas_prices:
            raise ValueError(f"Missing gas price in USD/Mcf for {month}")
        price = _nonnegative_finite(gas_prices[month], f"gas price for {month}")
        revenue = volume * price
        if not isfinite(revenue):
            raise ValueError(f"Non-finite gas revenue for {month}")
        volumes[month] = volume
        revenues[month] = revenue
    return volumes, revenues


def _nonnegative_finite(value: float, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}: expected finite nonnegative value") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"Invalid {label}: expected finite nonnegative value")
    return number
