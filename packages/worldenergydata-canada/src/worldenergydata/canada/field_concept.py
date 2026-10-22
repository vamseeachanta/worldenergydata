"""Canada C-NLOER field metadata -> FieldConcept normalizer (#719).

Maps sparse C-NLOER offshore field metadata to a ``FieldConcept`` for concept
screening, reusing the F2 ``FieldMetaMapping`` (#715). Water depth (metres) comes
from the C-NLOER ArcGIS Development-Wells layer (a metadata-enrichment follow-on);
the fixture carries a representative depth per field.

Grand Banks fields are SHALLOW (iceberg zone): Hibernia ~80 m, Hebron ~93 m,
Terra Nova ~95 m, White Rose ~120 m. Via ``dev_system_from_water_depth_m`` these
convert to ~262-394 ft, all below the 500 ft ``dry`` cutoff — correct for the
GBS dry-tree fields (Hibernia, Hebron); a known simplification for the FPSO+subsea
fields (Terra Nova/White Rose/North Amethyst), refined in a follow-on.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from worldenergydata.canada.development_wells import (
    DevelopmentWell,
    development_wells_manifest,
    summarize_water_depth,
)
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    number_from,
    to_field_concept,
)
from worldenergydata.field_development.models import FieldConcept

# Representative water depth (m) per NL offshore field (C-NLOER / public record).
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
        "data_source": FieldMapEntry("source"),
    }
)


def canada_field_to_concept(
    field_meta: dict[str, Any], *, wells: Iterable[DevelopmentWell] | None = None
) -> FieldConcept:
    """Build a concept, optionally using caller-qualified linked well depths.

    Omitted wells retain legacy output. Explicit wells enable provenance even
    when no measured median is available; fallback constants remain unchanged.
    """
    meta = (
        _canada_field_metadata(field_meta)
        if wells is None
        else enrich_canada_field_metadata(field_meta, wells)
    )
    return to_field_concept(meta, _CANADA_MAPPING)


def _canada_field_metadata(field_meta: dict[str, Any]) -> dict[str, Any]:
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "canada"
    meta.setdefault("source", "cnloer")
    if meta.get("water_depth_m") is None:
        key = str(meta.get("field_name", "")).strip().lower()
        if key in CANADA_WATER_DEPTH_M:
            meta["water_depth_m"] = CANADA_WATER_DEPTH_M[key]
    return meta


def enrich_canada_field_metadata(
    field_meta: dict[str, Any], wells: Iterable[DevelopmentWell]
) -> dict[str, Any]:
    """Return metadata and evidence without mutating inputs or accessing a source.

    A linked median takes precedence over field metadata. Without contributors,
    the supplied depth, existing representative default, or missing value is
    retained in that order. Measurement authenticity remains NOT_EVALUATED;
    measured_median describes the caller's record basis, not verified source data.
    """
    meta = _canada_field_metadata(field_meta)
    records = list(wells)
    field_name = meta.get("field_name")
    if not isinstance(field_name, str):
        raise TypeError("field_name must be supplied for well enrichment")
    summary = summarize_water_depth(field_name, records)
    manifest = development_wells_manifest(records)
    if summary.water_depth_m is not None:
        meta["water_depth_m"] = summary.water_depth_m
        origin = "measured_median"
    elif field_meta.get("water_depth_m") is not None:
        origin = "provided"
    else:
        origin = "default" if meta.get("water_depth_m") is not None else "missing"
    meta["water_depth_provenance"] = {
        "origin": origin,
        "depth_datum": summary.depth_datum,
        "contributing_uwis": list(summary.contributing_uwis),
        "sources": list(summary.sources),
        "linked_well_count": summary.linked_well_count,
        "manifest": manifest,
        "measurement_status": "NOT_EVALUATED",
    }
    meta["source"] = (
        f"{meta.get('source') or 'cnloer'}; water_depth_m={origin}; "
        f"development_wells_sha256={manifest['sha256']}; "
        "measurement_status=NOT_EVALUATED"
    )
    return meta


def canada_field_meta_mapping() -> FieldMetaMapping:
    """Return the Canada C-NLOER FieldConcept mapping."""
    return _CANADA_MAPPING


def build_canada_field_concept(
    field_meta: dict[str, Any], *, wells: Iterable[DevelopmentWell] | None = None
) -> FieldConcept:
    """Alias for the #719 reference-chain terminology."""
    return canada_field_to_concept(field_meta, wells=wells)
