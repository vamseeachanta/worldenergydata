"""Pure annual duration summaries of prepared well rows (see #1686).

The caller declares the year, water-depth band and full day-basis label. This
module neither classifies bands nor selects a basis, assigns years, refreshes
sources or authorizes publication. Each distinct well has equal weight within
its year/band/basis cell. Calendar and rig durations are summarized independently.

Quantile definition
-------------------
For sorted valid observations x of size n, use zero-based rank r = (n - 1) * p,
with linear interpolation between floor(r) and ceil(r). The quartiles use
p = 1/4, 1/2 and 3/4. These fractions define the statistical contract, rather
than source-derived constants. For the independent hand case [2, 4, 6, 8],
the ranks are 0.75, 1.5 and 2.25, giving 3.5, 5 and 6.5 days respectively.
A singleton has the same value at all three ranks; an empty metric has null
quartiles and a valid count of zero. No rounding or quantization is applied.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from fractions import Fraction
from math import floor, isfinite
from numbers import Integral, Rational, Real
from typing import Any

_REQUIRED = (
    "year",
    "water_depth_band",
    "basis",
    "well_id",
    "calendar_days",
    "rig_days",
)


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{field} must be an integer")
    return int(value)


def _label(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value


def _duration(value: object, field: str) -> float | None:
    if value is None:
        return None
    message = f"{field} must be finite nonnegative real days or None"
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(message)
    try:
        days = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(message) from exc
    if not isfinite(days) or days < 0:
        raise ValueError(message)
    # Canonicalize signed zero so duplicate order cannot change serialized output.
    return 0.0 if days == 0 else days


def _exact_duration(value: Real | None) -> Fraction | None:
    if value is None:
        return None
    if isinstance(value, Rational):
        return Fraction(int(value.numerator), int(value.denominator))
    return Fraction(*value.as_integer_ratio())


def _metric(values: Iterable[float | None]) -> dict[str, int | float | None]:
    ordered = sorted(value for value in values if value is not None)

    def quantile(probability: float) -> float | None:
        if not ordered:
            return None
        rank = (len(ordered) - 1) * probability
        lower = floor(rank)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = rank - lower
        # Nonnegative endpoints make this difference safe even at large magnitudes.
        return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction

    return {
        "valid_count": len(ordered),
        "q1": quantile(0.25),
        "median": quantile(0.5),
        "q3": quantile(0.75),
    }


def annual_duration_summary(
    rows: Iterable[Mapping[str, object]],
    min_cell_size: int,
    *,
    year_floor: int | None = None,
    year_floor_caveat: str | None = None,
    quantization_caveat: str | None = None,
) -> dict[str, Any]:
    """Return ``cells`` and ``metadata`` without changing input rows.

    Every row must explicitly contain ``year`` (integer), ``water_depth_band``,
    ``basis`` and ``well_id`` (nonempty strings), plus ``calendar_days`` and
    ``rig_days``. Durations accept finite nonnegative real numbers representable
    as floats, or ``None`` for unknown. NaN, infinities, negative values, booleans
    and numeric strings are rejected with ValueError, rather than dropped or
    treated as missing. Adapters must explicitly convert other null sentinels.
    Labels are opaque and retained verbatim; extra row fields are ignored.

    Duplicate identity is (year, basis, well_id). Identical consumed band and
    duration values count once, including nulls. Exact rational representations
    of the original scalars are compared; disagreements raise ValueError. Thus a
    well cannot occupy two bands under the same annual basis. The same well may
    appear in different years or under different bases.

    Cells are sorted by (year, water_depth_band, basis). ``well_count`` counts
    distinct wells including wells with unknown durations. ``small_cell`` means
    well_count < min_cell_size, where the caller must supply a positive integer.
    Small cells remain in the result with their metrics; they are not suppressed
    or published. Each metric has its own ``valid_count``, ``q1``, ``median`` and
    ``q3``; the absence of observations never becomes a zero-day measurement.

    The optional year floor and caveat strings are declarations preserved as
    metadata only: they do not filter rows or infer historical completeness.
    No floor or quantization caveat is invented when absent, and
    ``source_completeness`` remains ``not_established``. The caller remains
    responsible for population coverage, well-identifier grain and eligibility.
    """
    threshold = _integer(min_cell_size, "min_cell_size")
    if threshold <= 0:
        raise ValueError("min_cell_size must be a positive integer")
    if year_floor is not None:
        year_floor = _integer(year_floor, "year_floor")
    for name, caveat in (
        ("year_floor_caveat", year_floor_caveat),
        ("quantization_caveat", quantization_caveat),
    ):
        if caveat is not None and not isinstance(caveat, str):
            raise ValueError(f"{name} must be a string or None")

    seen: dict[tuple[int, str, str], tuple[str, Fraction | None, Fraction | None]] = {}
    groups: dict[tuple[int, str, str], list[tuple[float | None, float | None]]] = {}
    for row in rows:
        for field in _REQUIRED:
            if field not in row:
                raise ValueError(f"missing required field: {field}")
        year = _integer(row["year"], "year")
        band = _label(row["water_depth_band"], "water_depth_band")
        basis = _label(row["basis"], "basis")
        well_id = _label(row["well_id"], "well_id")
        calendar = _duration(row["calendar_days"], "calendar_days")
        rig = _duration(row["rig_days"], "rig_days")
        identity = (year, basis, well_id)
        observation = (
            band,
            _exact_duration(row["calendar_days"]),
            _exact_duration(row["rig_days"]),
        )
        if identity in seen:
            if seen[identity] != observation:
                raise ValueError("conflicting duplicate well row within year and basis")
            continue
        seen[identity] = observation
        groups.setdefault((year, band, basis), []).append((calendar, rig))

    cells = []
    for (year, band, basis), observations in sorted(groups.items()):
        cells.append(
            {
                "year": year,
                "water_depth_band": band,
                "basis": basis,
                "well_count": len(observations),
                "small_cell": len(observations) < threshold,
                "calendar_days": _metric(calendar for calendar, _ in observations),
                "rig_days": _metric(rig for _, rig in observations),
            }
        )
    return {
        "cells": cells,
        "metadata": {
            "min_cell_size": threshold,
            "quantile_method": "linear: rank = (n - 1) * p",
            "year_floor": year_floor,
            "year_floor_caveat": year_floor_caveat,
            "quantization_caveat": quantization_caveat,
            "source_completeness": "not_established",
        },
    }
