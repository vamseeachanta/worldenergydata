"""Spain CORES field metadata to FieldConcept normalizer (#763)."""

from __future__ import annotations

from typing import Any, Dict

from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    number_from,
    to_field_concept,
)


def _title_name(value: Any) -> str:
    return str(value).strip().title()


_SPAIN_MAPPING = FieldMetaMapping(
    {
        "name": FieldMapEntry("field_name", _title_name),
        "region": FieldMapEntry("region"),
        "water_depth_m": FieldMapEntry("water_depth_m", number_from),
        "data_source": FieldMapEntry("source"),
    }
)


def spain_field_to_concept(field_meta: Dict[str, Any]):
    """Build a sparse Spain ``FieldConcept`` from CORES metadata."""
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "spain"
    meta.setdefault("source", "CORES")
    if _is_onshore(meta) and meta.get("water_depth_m") is None:
        meta["water_depth_m"] = 0.0
    return to_field_concept(meta, _SPAIN_MAPPING)


def spain_field_meta_mapping() -> FieldMetaMapping:
    """Return the Spain sparse FieldConcept mapping."""
    return _SPAIN_MAPPING


def build_spain_field_concept(field_meta: Dict[str, Any]):
    """Alias for the #763 reference-chain terminology."""
    return spain_field_to_concept(field_meta)


def _is_onshore(meta: Dict[str, Any]) -> bool:
    env = str(meta.get("environment") or meta.get("environment_type") or "").lower()
    return env in {"onshore", "land", "terra"}
