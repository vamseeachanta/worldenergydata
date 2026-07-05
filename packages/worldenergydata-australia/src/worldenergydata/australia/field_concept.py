"""Australia field metadata -> FieldConcept normalizer (#721).

Maps DataVic/NOPTA field metadata to a ``FieldConcept`` for concept screening,
reusing the F2 ``FieldMetaMapping`` (#715). ``water_depth_m`` comes from DataVic
``abswaterdepth`` (per-field). Shallow Gippsland shelf fields (Kingfish ~78 m,
Barracouta ~45 m) classify as ``dry`` via ``dev_system_from_water_depth_m``
(feet thresholds: <500 ft -> dry) despite being offshore — the chain derives
``dev_system`` from depth and does NOT hardcode "offshore == subsea".
"""

from __future__ import annotations

from typing import Any, Dict

from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    number_from,
    to_field_concept,
)

_AUSTRALIA_MAPPING = FieldMetaMapping(
    {
        "name": FieldMapEntry("field_name"),
        "operator": FieldMapEntry("operator"),
        "region": FieldMapEntry("region"),
        "water_depth_m": FieldMapEntry("water_depth_m", number_from),
        "data_source": FieldMapEntry("source"),
    }
)


def australia_field_to_concept(field_meta: Dict[str, Any]):
    """Build a sparse Australia ``FieldConcept`` from DataVic/NOPTA metadata."""
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "australia"
    meta.setdefault("source", "datavic")
    return to_field_concept(meta, _AUSTRALIA_MAPPING)


def australia_field_meta_mapping() -> FieldMetaMapping:
    """Return the Australia FieldConcept mapping."""
    return _AUSTRALIA_MAPPING


def build_australia_field_concept(field_meta: Dict[str, Any]):
    """Alias for the #721 reference-chain terminology."""
    return australia_field_to_concept(field_meta)
