"""Explicit monthly gas pricing in USD/Mcf, with no assumed price or HHV."""

import re
from datetime import date
from math import isfinite

import pandas as pd


def monthly_gas_revenue(
    production: pd.DataFrame, gas_prices: dict[str, float]
) -> tuple[dict[str, float], dict[str, float]]:
    """Return monthly Mcf and USD revenue; require one priced row per month.

    Prices share the oil deck's YYYY-MM keys and monthly time base. Each price
    is the supplied month's realized USD/Mcf value; escalation belongs in the
    caller's deck, as for oil. No USD/MMBtu conversion is performed.
    """
    if "MONTHLY_GAS_MCF" not in production:
        raise ValueError("Gas deck requires MONTHLY_GAS_MCF")
    if "YEAR_MONTH" not in production:
        raise ValueError("Gas deck requires YEAR_MONTH")
    months = production["YEAR_MONTH"].astype(str)
    for month in months:
        _validate_month(month)
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


def _validate_month(month: str) -> None:
    # YYYY-MM is the existing gas-deck API contract; date bounds come from
    # Python 3.11 datetime docs, date constructor and date.fromisoformat:
    # https://docs.python.org/3.11/library/datetime.html#datetime.date
    try:
        if (
            not isinstance(month, str)
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}", month) is None
        ):
            raise ValueError
        date.fromisoformat(f"{month}-01")
    except ValueError as exc:
        raise ValueError(
            f"Invalid production month {month!r}: expected calendar YYYY-MM"
        ) from exc


def _nonnegative_finite(value: float, label: str) -> float:
    # Boolean flags are not quantities; preserve the finite nonnegative domain
    # defined in docs/domains/field-development/gas-revenue.md at 648d6de4.
    if pd.api.types.is_bool(value):
        raise ValueError(f"Invalid {label}: expected finite nonnegative value")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid {label}: expected finite nonnegative value") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"Invalid {label}: expected finite nonnegative value")
    return number
