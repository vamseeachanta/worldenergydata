"""UKCS field-metadata -> FieldConcept normalizer (#717).

The current UK NSTA production slice has sparse metadata. The mapping therefore
populates only fields that are defensible from the approved fixture/source path:
name, UK basin-region key, optional water depth, and source label. The concept
screening output is a wiring proof, not a published UK field recommendation.
"""

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


_UK_MAPPING = FieldMetaMapping(
    {
        "name": FieldMapEntry("field_name", _title_name),
        "region": FieldMapEntry("region"),
        "water_depth_m": FieldMapEntry("water_depth_m", number_from),
        "data_source": FieldMapEntry("source"),
    }
)


def ukcs_field_to_concept(field_meta: Dict[str, Any]):
    """Build a sparse UK ``FieldConcept`` from approved UKCS metadata."""
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "uk"  # basin priors key on "uk", not production region "ukcs"
    meta.setdefault("source", "NSTA")
    return to_field_concept(meta, _UK_MAPPING)


def uk_field_meta_mapping() -> FieldMetaMapping:
    """Return the UKCS sparse FieldConcept mapping."""
    return _UK_MAPPING


def build_uk_field_concept(field_meta: Dict[str, Any]):
    """Alias for the #717 reference-chain terminology."""
    return ukcs_field_to_concept(field_meta)
