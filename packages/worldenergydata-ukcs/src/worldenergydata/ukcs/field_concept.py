"""UKCS sparse or NSTA-enriched metadata -> FieldConcept normalizer.

Status, ownership and source evidence remain on the metadata dictionary because
they are not fields on the shared FieldConcept schema. Screening is preliminary.
"""

from __future__ import annotations

from typing import Any

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
        "operator": FieldMapEntry("operator"),
        "year_first_oil": FieldMapEntry("year_first_oil"),
        "data_source": FieldMapEntry("source"),
    }
)


def ukcs_field_to_concept(field_meta: dict[str, Any]):
    """Build a UK ``FieldConcept`` from sparse or enriched UKCS metadata."""
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "uk"  # basin priors key on "uk", not production region "ukcs"
    meta.setdefault("source", "NSTA")
    return to_field_concept(meta, _UK_MAPPING)


def uk_field_meta_mapping() -> FieldMetaMapping:
    """Return the UKCS FieldConcept mapping, including enriched metadata."""
    return _UK_MAPPING


def build_uk_field_concept(field_meta: dict[str, Any]):
    """Alias for the #717 reference-chain terminology."""
    return ukcs_field_to_concept(field_meta)


def screen_ukcs_field_metadata(field_meta: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic screening with explicit metadata evidence and limits.

    Coverage alone does not qualify an engineering recommendation. The metadata
    themes omit reservoir, host and commercial basis required for that decision.
    """
    from worldenergydata.field_development.recommendation import recommend

    concept = build_uk_field_concept(field_meta)
    coverage = {
        key: "available" if getattr(concept, key) is not None else "missing"
        for key in ("operator", "water_depth_m", "year_first_oil")
    }
    coverage.update(field_meta.get("metadata_coverage", {}))
    return {
        "field_concept": concept,
        "ranked_concepts": recommend(concept),
        "metadata_coverage": coverage,
        "metadata_provenance": field_meta.get("metadata_provenance", {}),
        "screening_label": "metadata_screening_only",
        "recommendation_ready": False,
    }
