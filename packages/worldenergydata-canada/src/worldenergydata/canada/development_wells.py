"""Offline, caller-normalized development-well water-depth evidence.

This is not an ArcGIS parser or a source-qualification check. Source attributes,
units, datum and field linkage must be established by the caller before records
are constructed. No network access or persistence is performed here.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from fractions import Fraction
from statistics import median


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty, trimmed string")


@dataclass(frozen=True)
class DevelopmentWell:
    """One explicitly linked well, with nullable depth and caller-declared basis.

    Only metre inputs are supported; no source unit or datum is inferred. UWI
    is treated as an opaque identifier, without onshore survey-format parsing.
    A source reference records lineage, not verification or permission to reuse.
    """

    uwi: str
    field_name: str
    water_depth_m: float | None
    depth_unit: str
    depth_datum: str
    source: str

    def __post_init__(self) -> None:
        for name in ("uwi", "field_name", "depth_datum", "source"):
            _identifier(getattr(self, name), name)
        if self.depth_unit != "m":
            raise ValueError("depth_unit must be explicitly supplied as 'm'")
        depth = self.water_depth_m
        if depth is not None:
            # Nonnegative physical magnitude: FieldConcept.must_be_non_negative,
            # src/worldenergydata/field_development/models.py (schema 1.0.0).
            if isinstance(depth, bool) or not isinstance(depth, (int, float)):
                raise ValueError("water depth must be finite and nonnegative or None")
            try:
                depth = float(depth)
            except OverflowError as error:
                raise ValueError(
                    "water depth must be finite and nonnegative or None"
                ) from error
            if not math.isfinite(depth) or depth < 0:
                raise ValueError("water depth must be finite and nonnegative or None")
            object.__setattr__(self, "water_depth_m", depth)


@dataclass(frozen=True)
class WaterDepthSummary:
    """Arithmetic evidence only; measurement qualification is not established."""

    field_name: str
    water_depth_m: float | None
    depth_datum: str | None
    linked_well_count: int
    contributing_uwis: tuple[str, ...]
    sources: tuple[str, ...]


def _validated_wells(wells: Iterable[DevelopmentWell]) -> list[DevelopmentWell]:
    records = list(wells)
    identifiers = set()
    for record in records:
        if not isinstance(record, DevelopmentWell):
            raise TypeError("wells must contain normalized DevelopmentWell records")
        if record.uwi in identifiers:
            raise ValueError(
                "duplicate well identifier; resolve records before enrichment"
            )
        identifiers.add(record.uwi)
    return records


def summarize_water_depth(
    field_name: str, wells: Iterable[DevelopmentWell]
) -> WaterDepthSummary:
    """Median of non-null depths with exact caller-supplied field linkage.

    Duplicate identifiers and mixed contributing datums are refused. Null depths
    count as linked records but never as measurements. An empty sample has no
    depth, datum or contributing source; it does not produce a zero depth.
    """
    _identifier(field_name, "field_name")
    records = _validated_wells(wells)
    linked = [record for record in records if record.field_name == field_name]
    measured = [record for record in linked if record.water_depth_m is not None]
    datums = {record.depth_datum for record in measured}
    if len(datums) > 1:
        raise ValueError("contributing depths must use the same datum")
    # Python 3.11 Library Reference (retrieved 2026), statistics.median: middle value for
    # odd samples; arithmetic mean of the middle two for even samples.
    # https://docs.python.org/3.11/library/statistics.html#statistics.median
    # Exact fractions avoid overflow and dependence on ambient Decimal context.
    depths = [
        Fraction(record.water_depth_m)
        for record in measured
        if record.water_depth_m is not None
    ]
    return WaterDepthSummary(
        field_name=field_name,
        water_depth_m=float(median(depths)) if depths else None,
        depth_datum=next(iter(datums)) if datums else None,
        linked_well_count=len(linked),
        contributing_uwis=tuple(sorted(record.uwi for record in measured)),
        sources=tuple(sorted({record.source for record in measured})),
    )


def development_wells_manifest(wells: Iterable[DevelopmentWell]) -> dict:
    """Return a reproducible digest of normalized inputs, without storing rows.

    Schema version 1 hashes UTF-8 JSON of all records sorted by unique UWI, with
    sorted keys, compact separators, unescaped Unicode and no nonfinite numbers.
    Nulls, linkage, units, datum and source participate in the digest. The digest
    establishes input identity only, not source authenticity or data readiness.
    """
    records = _validated_wells(wells)
    payload = json.dumps(
        [asdict(record) for record in sorted(records, key=lambda record: record.uwi)],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return {
        "schema_version": "1",
        "record_count": len(records),
        "depth_unit": "m",
        "sources": sorted({record.source for record in records}),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
