"""Annual enforcement counts from normalized INC category observations.

Source shape and action vocabulary: BSEEINCSImporter._normalize_row in
hse/importers/bsee_incs_importer.py. Each category carries its own inc_count;
the number of normalized rows is not the number of INCs (issue 1683).
"""

from collections.abc import Iterable, Mapping
from datetime import date
from numbers import Integral
from typing import Literal, TypedDict

_ACTIONS = frozenset({"warning", "comp_shutin", "fac_shutin"})


class AnnualINCCount(TypedDict):
    """Aggregate-only output schema; count is measured in INCs."""

    year: int
    action: str
    count: int
    unit: Literal["INCs"]


def _incident_year(value: object) -> int:
    """Require a valid normalized calendar date, including datetime values."""
    if not isinstance(value, date):
        raise ValueError("incident_date must be a valid date or datetime")
    try:
        # Reconstruction also rejects missing date sentinels such as NaT.
        return date(value.year, value.month, value.day).year
    except (TypeError, ValueError) as error:
        raise ValueError("incident_date must be a valid date or datetime") from error


def annual_inc_counts(rows: Iterable[Mapping[str, object]]) -> list[AnnualINCCount]:
    """Sum supplied category counts by incident calendar year and action.

    Required inputs are incident_date (date or datetime), violation_type
    (warning, comp_shutin or fac_shutin) and inc_count (nonnegative integer).
    Booleans, strings and floats are not normalized counts. Zero is permitted
    by the nonnegative count contract in issue 1683.

    Results contain only year, action, count and unit, sorted by year then
    action. Only observed pairs are emitted, including explicit zero counts;
    absent pairs do not establish zero INCs or complete annual coverage.
    Datetimes retain their supplied calendar year without timezone conversion.
    Inputs are neither mutated nor deduplicated. No source identifiers or text
    are carried into the output.

    Raises:
        TypeError: rows is not an iterable of normalized mappings.
        ValueError: A row is not a mapping or has missing/invalid fields.
    """
    if isinstance(rows, (str, bytes, Mapping)):
        raise TypeError("rows must be an iterable of normalized mappings")
    totals: dict[tuple[int, str], int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each row must be a mapping")
        year = _incident_year(row.get("incident_date"))
        action = row.get("violation_type")
        if not isinstance(action, str) or action not in _ACTIONS:
            raise ValueError(
                "violation_type must be warning, comp_shutin or fac_shutin"
            )
        count = row.get("inc_count")
        if isinstance(count, bool) or not isinstance(count, Integral) or count < 0:
            raise ValueError(
                "inc_count must be a nonnegative integer, excluding booleans"
            )
        key = (year, action)
        totals[key] = totals.get(key, 0) + int(count)
    return [
        {"year": year, "action": action, "count": count, "unit": "INCs"}
        for (year, action), count in sorted(totals.items())
    ]
