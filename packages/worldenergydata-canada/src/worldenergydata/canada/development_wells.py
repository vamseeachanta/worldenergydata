"""Offline development-well metadata for Canada FieldConcept enrichment.

Only caller-supplied ArcGIS JSON is read; this module performs no network or
cache I/O. Source-layer names, depth units and coordinate reference must be
verified by the caller. No default mapping asserts an unverified live schema.

Protocol reference: Esri, Query (Feature Service/Layer), JSON response syntax,
2026, https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from statistics import median
from typing import Any


class DevelopmentWellError(ValueError):
    """Malformed, incomplete or inconsistent supplied well metadata."""


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DevelopmentWellError(
            "Well identity, linkage and source require non-empty text"
        )
    return value.strip()


def _number(value: Any) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise DevelopmentWellError(
            "Well numeric attributes require a finite number or null"
        )
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise DevelopmentWellError(
            "Well numeric attributes require a finite number"
        ) from exc
    if not math.isfinite(result):
        raise DevelopmentWellError("Well numeric attributes require a finite number")
    return result


@dataclass(frozen=True)
class DevelopmentWell:
    """One UWI, explicitly linked field, metric depth and attribute coordinates.

    Coordinates are retained without reprojection; no CRS is inferred from the
    ArcGIS geometry. ``source`` identifies the caller's authorized input.
    """

    uwi: str
    field_name: str
    water_depth_m: float | None
    latitude: float | None
    longitude: float | None
    source: str

    def __post_init__(self) -> None:
        for name in ("uwi", "field_name", "source"):
            object.__setattr__(self, name, _text(getattr(self, name)))
        for name in ("water_depth_m", "latitude", "longitude"):
            object.__setattr__(self, name, _number(getattr(self, name)))
        # Source: field_development.models.FieldConcept.must_be_non_negative
        # (repository contract): water depth is a non-negative magnitude in m.
        if self.water_depth_m is not None and self.water_depth_m < 0:
            raise DevelopmentWellError("Water depth must be non-negative")


@dataclass(frozen=True)
class DevelopmentWellMapping:
    """Required attribute names; caller confirms depth in m and coordinate CRS.

    Field linkage must be supplied explicitly, never inferred from a well name.
    All mapped columns must exist; null depth/coordinates remain unknown.
    """

    uwi: str
    field_name: str
    water_depth_m: str
    latitude: str
    longitude: str

    def __post_init__(self) -> None:
        keys = [getattr(self, item.name) for item in fields(self)]
        for key in keys:
            _text(key)
        if len(set(keys)) != len(keys):
            raise DevelopmentWellError("Mapped attributes must be distinct")


def _unique_wells(wells: Iterable[DevelopmentWell]) -> tuple[DevelopmentWell, ...]:
    unique: dict[str, DevelopmentWell] = {}
    for well in wells:
        if well.uwi in unique and well != unique[well.uwi]:
            raise DevelopmentWellError(
                "Conflicting UWI records; resolve before enrichment"
            )
        unique[well.uwi] = well
    return tuple(unique.values())


def parse_development_wells(
    payload: Mapping[str, Any], *, mapping: DevelopmentWellMapping, source: str
) -> tuple[DevelopmentWell, ...]:
    """Parse a complete ArcGIS feature set using an explicit attribute mapping.

    Reject ArcGIS errors and transfer-limit responses rather than calculating
    a biased depth from a truncated page. A caller assembling pages must finish
    paging first. Exact duplicate UWIs collapse; conflicting duplicates raise.
    """
    source = _text(source)
    if not isinstance(payload, Mapping) or "error" in payload:
        raise DevelopmentWellError("Expected a successful ArcGIS feature response")
    # Esri Query JSON response syntax (2026): exceededTransferLimit=true
    # indicates more results, even when the features array is empty.
    if payload.get("exceededTransferLimit", False) is not False:
        raise DevelopmentWellError(
            "Incomplete ArcGIS response: transfer limit exceeded"
        )
    features = payload.get("features")
    if not isinstance(features, list):
        raise DevelopmentWellError("ArcGIS response requires a features array")
    wells = []
    for feature in features:
        attributes = feature.get("attributes") if isinstance(feature, Mapping) else None
        if not isinstance(attributes, Mapping):
            raise DevelopmentWellError("ArcGIS feature requires an attributes object")
        values = {}
        for item in fields(mapping):
            key = getattr(mapping, item.name)
            if key not in attributes:
                raise DevelopmentWellError("Missing mapped attribute in ArcGIS feature")
            values[item.name] = attributes[key]
        wells.append(DevelopmentWell(**values, source=source))
    return _unique_wells(wells)


@dataclass(frozen=True)
class FieldWellSummary:
    """Inventory count, median non-null depth and reproducible input identities.

    ``num_wells`` counts distinct linked UWIs, including null-depth records;
    it is not an estimate of producing or planned wells.
    """

    num_wells: int
    water_depth_m: float | None
    uwis: tuple[str, ...]
    sources: tuple[str, ...]


def summarize_field_wells(
    field_name: str, wells: Iterable[DevelopmentWell]
) -> FieldWellSummary:
    """Match a field exactly after case/whitespace normalization; no fuzzy join."""
    key = _text(field_name).casefold()
    linked = [
        well for well in _unique_wells(wells) if well.field_name.casefold() == key
    ]
    depths = [well.water_depth_m for well in linked if well.water_depth_m is not None]
    # NIST/SEMATECH e-Handbook, section 1.3.5.1, online edition read 2026:
    # https://www.itl.nist.gov/div898/handbook/eda/section3/eda351.htm#MEDIAN
    # Middle value for odd n; middle-pair mean for even n. Empty stays unknown.
    # Implemented by Python statistics.median (2026 documentation):
    # https://docs.python.org/3/library/statistics.html#statistics.median
    return FieldWellSummary(
        num_wells=len(linked),
        water_depth_m=median(depths) if depths else None,
        uwis=tuple(sorted(well.uwi for well in linked)),
        sources=tuple(sorted({well.source for well in linked})),
    )
