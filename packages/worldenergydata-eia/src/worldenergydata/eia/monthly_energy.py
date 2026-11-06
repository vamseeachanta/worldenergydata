"""Total one caller-selected monthly energy series in declared MWh.

Record layout: EIA API Technical Documentation, APIv2 response data and January
2024 v2.1.6 string-value notes, https://www.eia.gov/opendata/documentation.php.
This narrow contract requires period, series, value and units on every row;
routes using other column names require explicit caller normalization.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from numbers import Real


def total_monthly_energy_mwh(records: Iterable[Mapping[str, object]]) -> float:
    """Sum supplied monthly energy amounts in MWh, without unit conversion.

    The arithmetic total is sum(value) for a single series, with unique YYYY-MM
    months and units exactly 'MWh'. Values may be API decimal strings or numbers.
    Missing, negative, nonfinite and duplicate observations are rejected.
    Nonzero inputs that underflow to zero during float conversion are rejected.
    The caller will select non-overlapping monthly energy amounts, not power,
    rates or stock snapshots. No missing month or observation is imputed.

    >>> total_monthly_energy_mwh([
    ...     dict(period="2024-01", series="example", value="125.5", units="MWh"),
    ...     dict(period="2024-02", series="example", value="74.25", units="MWh"),
    ... ])
    199.75
    """
    seen: set[str] = set()
    series_id = None
    values = []
    for record in records:
        if record.get("units") != "MWh":
            raise ValueError("every monthly energy observation must declare MWh")
        series = record.get("series")
        if not isinstance(series, str) or not series.strip():
            raise ValueError("a nonblank series identifier is required")
        if series_id is not None and series != series_id:
            raise ValueError("monthly energy observations must belong to one series")
        series_id = series
        period = record.get("period")
        if (
            not isinstance(period, str)
            or not re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", period)
            or period.startswith("0000")
        ):
            raise ValueError("period must be a valid YYYY-MM month")
        if period in seen:
            raise ValueError("duplicate monthly period")
        seen.add(period)
        value = record.get("value")
        if isinstance(value, bool) or not isinstance(value, (Real, str)):
            raise TypeError("value must be finite nonnegative monthly energy")
        exact_value = value
        if isinstance(value, str):
            try:
                exact_value = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError(
                    "value must be finite nonnegative monthly energy"
                ) from exc
            if not exact_value.is_finite():
                raise ValueError("value must be finite nonnegative monthly energy")
        if exact_value < 0:
            raise ValueError("value must be finite nonnegative monthly energy")
        try:
            number = float(value)
        except (ValueError, OverflowError) as exc:
            raise ValueError("value must be finite nonnegative monthly energy") from exc
        if not math.isfinite(number) or number < 0:
            raise ValueError("value must be finite nonnegative monthly energy")
        if number == 0 and exact_value != 0:
            raise ValueError("value must not underflow to zero")
        values.append(number)
    if not values:
        raise ValueError("no monthly energy observations supplied")
    try:
        total = math.fsum(values)
    except OverflowError as exc:
        raise ValueError("monthly energy total must be finite") from exc
    if not math.isfinite(total):
        raise ValueError("monthly energy total must be finite")
    return total
