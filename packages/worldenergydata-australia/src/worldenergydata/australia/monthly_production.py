"""Total caller-normalized monthly gas volumes; no live production feed.

EIA Glossary, entries Mcf and MMcf, defines thousand and million cubic feet:
https://www.eia.gov/tools/glossary/index.php?id=M
The registry's MMscf-to-Mcf factor is reused; reference conditions are unchanged.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from numbers import Real

from worldenergydata.common.units import convert


def total_monthly_gas_mcf(records: Iterable[Mapping[str, object]]) -> float:
    """Sum one gas series with unique YYYY-MM periods and gas_mmscf values.

    Inputs are finite nonnegative numbers in million standard cubic feet per
    month, at the same caller-established reference conditions. Output is the
    supplied months' total in thousand standard cubic feet (Mcf), not a rate.
    Per the cited EIA definitions, 10**6 / 10**3 = 1000 Mcf per MMscf.
    Missing months are not filled and an empty series is not reported as zero.
    Nonzero inputs that underflow to zero during float conversion are rejected.
    This contract does not qualify GBB units or connect field production feeds.

    >>> total_monthly_gas_mcf([
    ...     {"period": "2024-01", "gas_mmscf": 1.25},
    ...     {"period": "2024-02", "gas_mmscf": 2.5},
    ... ])
    3750.0
    """
    seen: set[str] = set()
    volumes = []
    for record in records:
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
        value = record.get("gas_mmscf")
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError("gas_mmscf must be a finite nonnegative number")
        if value < 0:
            raise ValueError("gas_mmscf must be a finite nonnegative number")
        try:
            number = float(value)
        except OverflowError as exc:
            raise ValueError("gas_mmscf must be finite") from exc
        if not math.isfinite(number) or number < 0:
            raise ValueError("gas_mmscf must be a finite nonnegative number")
        if number == 0 and value != 0:
            raise ValueError("gas_mmscf must not underflow to zero")
        volumes.append(convert(number, "mmscf", "mcf"))
    if not volumes:
        raise ValueError("no monthly gas observations supplied")
    try:
        total = math.fsum(volumes)
    except OverflowError as exc:
        raise ValueError("converted gas total must be finite") from exc
    if not math.isfinite(total):
        raise ValueError("converted gas total must be finite")
    return total
