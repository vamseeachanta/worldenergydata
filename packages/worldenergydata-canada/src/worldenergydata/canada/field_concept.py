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

from typing import Any, Dict

from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    number_from,
    to_field_concept,
)

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


def canada_field_to_concept(field_meta: Dict[str, Any]):
    """Build a sparse Canada ``FieldConcept`` from C-NLOER metadata."""
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "canada"
    meta.setdefault("source", "cnloer")
    if meta.get("water_depth_m") is None:
        key = str(meta.get("field_name", "")).strip().lower()
        if key in CANADA_WATER_DEPTH_M:
            meta["water_depth_m"] = CANADA_WATER_DEPTH_M[key]
    return to_field_concept(meta, _CANADA_MAPPING)


def canada_field_meta_mapping() -> FieldMetaMapping:
    """Return the Canada C-NLOER FieldConcept mapping."""
    return _CANADA_MAPPING


def build_canada_field_concept(field_meta: Dict[str, Any]):
    """Alias for the #719 reference-chain terminology."""
    return canada_field_to_concept(field_meta)
