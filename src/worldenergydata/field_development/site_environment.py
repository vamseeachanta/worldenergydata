"""Resolve supplied water-depth candidates without acquisition or inference.

The site-environment epic (issue 1090) requires source citation, vintage and
explicit unknowns, with documented precedence between source tiers. The ordered
``source_preference`` is caller policy, not a universal regional/global ranking.
The caller establishes the canonical field identifier and supplies normalized
depths in metres, positive down. No unit or vertical-datum conversion occurs.
Normalized numeric scalars are Python integers or floats; booleans are excluded.

Each candidate mapping declares ``depth_m``, ``units`` (``m``), ``source_id``,
``source_url`` (absolute HTTP/S), ``vintage`` (nonblank release/date text), and
``coverage`` (west, south, east, north in WGS84 geographic degrees). Coverage
uses closed, non-wrapping boxes, following ``terrain._validate_bbox``. Wrapped
antimeridian boxes are unqualified. The original selected mapping is retained,
including additional provenance; callers should not mutate it after selection.
This checks supplied declarations, not source authenticity or data freshness.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, TypeGuard
from urllib.parse import urlsplit

# Geographic degree limits: field_development.terrain._validate_bbox contract.
_LONGITUDE_LIMIT = 180.0
_LATITUDE_LIMIT = 90.0


@dataclass(frozen=True)
class DepthResolution:
    """Depth in metres plus unchanged candidate evidence, or an unknown reason."""

    field_id: str
    longitude: float
    latitude: float
    depth_m: float | None
    candidate: Mapping[str, Any] | None
    reason: str | None


def _has_text(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: object) -> TypeGuard[int | float]:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def _geographic_point(longitude: object, latitude: object) -> bool:
    return (
        _finite_number(longitude)
        and _finite_number(latitude)
        and -_LONGITUDE_LIMIT <= longitude <= _LONGITUDE_LIMIT
        and -_LATITUDE_LIMIT <= latitude <= _LATITUDE_LIMIT
    )


def _source_url(value: object) -> bool:
    if not _has_text(value) or any(character.isspace() for character in value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def _covers(coverage: object, longitude: float, latitude: float) -> bool:
    # Four bounds use the terrain._validate_bbox (west, south, east, north) form.
    if (
        not isinstance(coverage, (tuple, list))
        or len(coverage) != 4
        or not all(_finite_number(bound) for bound in coverage)
    ):
        return False
    west, south, east, north = coverage
    return (
        _geographic_point(west, south)
        and _geographic_point(east, north)
        and west < east
        and south < north
        and west <= longitude <= east
        and south <= latitude <= north
    )


def _qualified(candidate: Mapping[str, Any], longitude: float, latitude: float) -> bool:
    depth = candidate.get("depth_m")
    return (
        _finite_number(depth)
        # Issue 1090 scoped depth contract: nonnegative metres; zero is known.
        and depth >= 0
        and candidate.get("units") == "m"
        and _has_text(candidate.get("source_id"))
        and _source_url(candidate.get("source_url"))
        and _has_text(candidate.get("vintage"))
        and _covers(candidate.get("coverage"), longitude, latitude)
    )


def _source_order(source_preference: Sequence[str]) -> tuple[str, ...]:
    if isinstance(source_preference, (str, bytes)) or not isinstance(
        source_preference, Sequence
    ):
        raise ValueError("source_preference must be an ordered sequence of source ids")
    preference = tuple(source_preference)
    if not all(_has_text(source_id) for source_id in preference) or len(
        set(preference)
    ) != len(preference):
        raise ValueError("source_preference must contain distinct nonblank source ids")
    return preference


def resolve_depth(
    field_id: str,
    longitude: float,
    latitude: float,
    source_preference: Sequence[str],
    candidates: Iterable[Mapping[str, Any]],
) -> DepthResolution:
    """Select the first qualified preferred source covering the query point.

    Invalid candidate declarations are skipped. No qualifying candidate yields
    ``depth_m=None``, ``candidate=None`` and a nonempty reason, never zero.
    Invalid query arguments or duplicate candidates for any preferred source
    raise ``ValueError``, including duplicates that are unqualified or occur
    after a match. Unpreferred candidates do not affect selection.
    """
    if not _has_text(field_id):
        raise ValueError("field_id must be a nonblank canonical identifier")
    if not _geographic_point(longitude, latitude):
        raise ValueError("coordinates must be finite geographic longitude/latitude")
    preference = _source_order(source_preference)
    preferred = set(preference)
    by_source: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        source_id = candidate.get("source_id")
        if not isinstance(source_id, str) or source_id not in preferred:
            continue
        if source_id in by_source:
            raise ValueError(f"duplicate candidates for preferred source: {source_id}")
        by_source[source_id] = candidate

    for source_id in preference:
        selected = by_source.get(source_id)
        if selected is not None and _qualified(selected, longitude, latitude):
            return DepthResolution(
                field_id, longitude, latitude, selected["depth_m"], selected, None
            )
    return DepthResolution(
        field_id,
        longitude,
        latitude,
        None,
        None,
        "No qualified preferred depth candidate covers the point.",
    )
