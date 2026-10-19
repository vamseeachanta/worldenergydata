"""Canada field metadata and supplied development wells -> FieldConcept.

Explicit metadata wins over the median non-null depth of linked wells, then
legacy defaults. Source markers distinguish supplied, aggregated and assumed
depths. No live source is contacted. Coordinates and UWIs stay on the well
records because FieldConcept has no corresponding fields.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from worldenergydata.canada.development_wells import (
    DevelopmentWell,
    summarize_field_wells,
)
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    number_from,
    to_field_concept,
)

# Representative water depth (m) per NL offshore field (C-NLOER / public record).
# Legacy fallback only: assumed, based on previous experience; not a measured
# result of development-well enrichment. Public source validation is deferred.
CANADA_WATER_DEPTH_M = {
    "hibernia": 80.0,
    "hebron": 93.0,
    "terra nova": 95.0,
    "white rose": 120.0,
    "north amethyst": 120.0,
}

_CANADA_MAPPING = FieldMetaMapping(
    {
        "name": FieldMapEntry("field_name"),
        "operator": FieldMapEntry("operator"),
        "region": FieldMapEntry("region"),
        "water_depth_m": FieldMapEntry("water_depth_m", number_from),
        "num_wells": FieldMapEntry("num_wells"),
        "data_source": FieldMapEntry("source"),
    }
)


def canada_field_to_concept(
    field_meta: dict[str, Any], *, development_wells: Iterable[DevelopmentWell] = ()
):
    """Build a concept; supplied well count is inventory, not producing wells.

    Caller-supplied depth and well count take precedence over well metadata.
    Legacy depths are retained for compatibility, labelled as defaults rather
    than measurements. Inputs are not mutated and field joins are exact after
    case/whitespace normalization.
    """
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "canada"
    meta.setdefault("source", "cnloer")
    summary = summarize_field_wells(meta.get("field_name", ""), development_wells)
    depth_source = "provided"
    if meta.get("water_depth_m") is None:
        meta["water_depth_m"] = summary.water_depth_m
        depth_source = (
            "development_wells_median"
            if summary.water_depth_m is not None
            else "unknown"
        )
    if meta.get("water_depth_m") is None:
        key = str(meta.get("field_name", "")).strip().lower()
        if key in CANADA_WATER_DEPTH_M:
            meta["water_depth_m"] = CANADA_WATER_DEPTH_M[key]
            depth_source = "legacy_default"
    if meta.get("num_wells") is None and summary.num_wells:
        meta["num_wells"] = summary.num_wells
    provenance = [str(meta.get("source") or "cnloer"), f"water_depth={depth_source}"]
    if summary.sources:
        provenance.append("development_wells_inventory=" + ",".join(summary.sources))
    meta["source"] = "; ".join(provenance)
    return to_field_concept(meta, _CANADA_MAPPING)


def canada_field_meta_mapping() -> FieldMetaMapping:
    """Return the Canada C-NLOER FieldConcept mapping."""
    return _CANADA_MAPPING


def build_canada_field_concept(
    field_meta: dict[str, Any], *, development_wells: Iterable[DevelopmentWell] = ()
):
    """Alias for the #719 reference-chain terminology."""
    return canada_field_to_concept(field_meta, development_wells=development_wells)
