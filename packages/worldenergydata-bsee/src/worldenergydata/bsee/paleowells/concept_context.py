"""Optional FieldConcept context from an explicit, caller-supplied era map.

Maps built by ``build_field_era_map`` represent dominant eras of joined paleo
wells, including nonproducing wells. Other supplied maps may have a different
derivation. No source discovery, loading or verification is performed here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from worldenergydata.bsee.paleowells.field_era import is_lower_tertiary
from worldenergydata.field_development.models import FieldConcept


@dataclass(frozen=True)
class GeologicalContextReceipt:
    """Mapping provenance, separate from the concept's original data source."""

    field_code: str
    source_reference: str
    geological_era: str
    mapping_method: str = "exact_field_code_lookup"
    limitation: str = (
        "Supplied field-level context; not proof of the producing reservoir's "
        "age or formation. Raw source and derivation not verified by this adapter."
    )
    source_derivation: str | None = None
    play_group: str | None = None
    play_group_rule: str = "no_play_supplied"


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def enrich_concept_context(
    concept: FieldConcept,
    *,
    field_code: str,
    field_era_map: Mapping[str, str | None],
    source_reference: str,
    source_derivation: str | None = None,
) -> tuple[FieldConcept, GeologicalContextReceipt | None]:
    """Return a revalidated concept and receipt, rejecting conflicting context.

    Field codes are matched exactly: identity normalization belongs to callers.
    Missing, null and explicit ``Unknown`` entries provide no update or receipt.
    Other nonblank era labels are retained without geological reclassification.
    A non-Lower-Tertiary era does not infer or clear a named play group.
    Optional source derivation is retained as supplied, without verification.
    """
    _require_text(field_code, "field_code")
    _require_text(source_reference, "source_reference")
    if source_derivation is not None:
        _require_text(source_derivation, "source_derivation")
    # Preserve which fields were supplied, while rerunning all model validators.
    payload = concept.model_dump(exclude_unset=True)
    validated = FieldConcept.model_validate(payload)
    era = field_era_map.get(field_code)
    if era is None or era == "Unknown":
        return validated, None
    _require_text(era, "matched era")

    updates = {"geological_era": era}
    lower_tertiary = is_lower_tertiary(era)
    play_rule = "no_play_supplied"
    if lower_tertiary:
        updates["play_group"] = "Lower Tertiary"
        play_rule = "lower_tertiary_era"
    elif validated.play_group is not None:
        play_rule = "retained_supplied_play"
    for attribute, value in updates.items():
        existing = getattr(validated, attribute)
        if existing is not None and existing != value:
            raise ValueError(f"conflicting {attribute} for explicit field code")
    result = FieldConcept.model_validate({**payload, **updates})
    receipt = GeologicalContextReceipt(
        field_code,
        source_reference,
        era,
        source_derivation=source_derivation,
        play_group=result.play_group,
        play_group_rule=play_rule,
    )
    if validated.play_group is not None and not lower_tertiary:
        receipt = replace(
            receipt,
            limitation=receipt.limitation
            + " A supplied play is retained for an era outside the Lower Tertiary "
            "grouping; era/play consistency is not verified.",
        )
    return result, receipt
