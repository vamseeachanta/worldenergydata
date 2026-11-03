"""Count caller-normalized completions by the dimensions in issue #1704."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date, datetime

from .activity import UNKNOWN, Parameters, depth_band


def _completion_year(value: object) -> int:
    message = "completion_date must be a date or an ISO calendar date (YYYY-MM-DD)"
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(message) from error
        if parsed.isoformat() != value:
            raise ValueError(message)
    elif isinstance(value, date) and not isinstance(value, datetime):
        parsed = value
    else:
        raise ValueError(message)
    return parsed.year


def annual_completion_counts(
    rows: Iterable[Mapping[str, object]],
    *,
    grain: str,
    source: str,
    parameters: Parameters,
) -> dict[str, object]:
    """Return observed year/area/depth cells with unit ``completions``.

    Each row declares a unique, nonblank string ``completion_id`` and a
    ``completion_date`` as a date object or an ISO calendar date. Datetimes,
    ambiguous strings and missing dates are rejected; years are never inferred.
    ``grain`` must be ``completion`` and ``source`` a nonblank provenance label.
    These declarations describe caller-established identities, not well counts
    or the potentially repeated completion listings consumed by ``analyse``.

    ``planning_area`` is a supplied label, never inferred from other fields.
    Missing or blank areas and missing/unusable ``water_depth_ft`` values retain
    the existing ``unknown`` label. Depth membership and labels use
    ``activity.depth_band`` with explicitly supplied ``Parameters``; boundaries
    are returned in feet. Extra row fields are ignored.

    Validation finishes before grouping. Cells are sorted by year, planning
    area and depth-band label; empty input has no cells. Inputs are not mutated.
    No durations, zero-filled strata or geographic mappings are produced.
    """
    if grain != "completion":
        raise ValueError("grain must be completion: unique completion identities")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a nonblank provenance label")
    if not isinstance(parameters, Parameters):
        raise ValueError("parameters must declare depth bins using Parameters")

    seen: set[str] = set()
    validated: list[tuple[int, str, str]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("completion rows must be mappings")
        identifier = row.get("completion_id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("completion_id must be a nonblank string")
        if identifier in seen:
            raise ValueError("duplicate completion_id")
        seen.add(identifier)
        year = _completion_year(row.get("completion_date"))
        area = row.get("planning_area")
        if area is not None and not isinstance(area, str):
            raise ValueError("planning_area must be a label or None")
        area = area.strip() if isinstance(area, str) else ""
        band = depth_band(row.get("water_depth_ft"), parameters)
        validated.append((year, area or UNKNOWN, band))

    counts = Counter(validated)
    return {
        "grain": grain,
        "source": source,
        "unit": "completions",
        "depth_edges_ft": list(parameters.depth_edges),
        "counts": [
            {
                "year": year,
                "planning_area": area,
                "water_depth_band": band,
                "count": counts[(year, area, band)],
            }
            for year, area, band in sorted(counts)
        ],
    }
