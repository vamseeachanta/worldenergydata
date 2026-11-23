"""
FieldConcept metadata normalizer (F2, #715).

Maps a country regulator's field-metadata dict → a ``field_development.models.
FieldConcept`` for concept screening. Generalizes the US-GoM ``field_development.
subseaiq.load_subseaiq_fields`` mapping so any country can supply its own column
map — but, per adversarial review (B2), a **declarative rename-map is not enough**:
``subseaiq`` embeds real transform logic (fluid-type priority, regex year
parsing, comma-stripped floats, and a many-facilities→one-concept reduction). So
``FieldMetaMapping`` carries **per-field transform callables**, and the concept
reduction is a dedicated function — no logic is lost.

Placement note: this lives in the fdas member but imports ``field_development``
(root distribution) at runtime. That is the established namespace pattern here
(the bsee member likewise imports root ``engine``/``analysis`` at runtime without
declaring them — root is always installed alongside members). It is NOT declared
in ``worldenergydata-fdas`` deps, which would create a member→root workspace
cycle. ``contract.py`` stays a pure leaf (no field_development import); the
FieldConcept side is isolated here.

Author: WorldEnergyData Team
Issue:  https://github.com/vamseeachanta/worldenergydata/issues/715
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

# Runtime imports resolved via the shared worldenergydata namespace (root dist).
from worldenergydata.field_development.enums import ConceptType, FluidType
from worldenergydata.field_development.loader import load_concept
from worldenergydata.field_development.models import FieldConcept

from ..core.config import classify_dev_system_by_depth

_M_TO_FT = 3.280839895


# --- reusable transforms (ported from subseaiq, generalized) ---------------


def identity(v: Any) -> Any:
    return v


def number_from(v: Any) -> Optional[float]:
    """Comma-stripped float coercion (subseaiq ``_float``)."""
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def year_from(v: Any) -> Optional[int]:
    """Extract a 4-digit year from free text (subseaiq ``_year``)."""
    m = re.search(r"(19|20)\d{2}", str(v or ""))
    return int(m.group(0)) if m else None


def fluid_from_reserve_type(v: Any) -> Optional[FluidType]:
    """Reserve-type string → FluidType, oil-primary for mixed (subseaiq)."""
    s = (str(v) if v is not None else "").lower()
    if "condensate" in s:
        return FluidType.CONDENSATE
    if "oil" in s and "gas" in s:
        return FluidType.OIL  # oil-primary for mixed
    if "oil" in s:
        return FluidType.OIL
    if "gas" in s:
        return FluidType.GAS
    return None


def dev_system_from_water_depth_m(water_depth_m: Any) -> str:
    """Water depth in METERS → FDAS dev-system vocab {dry,subsea15,subsea20,unknown}.

    FieldConcept stores meters; the FDAS classifier thresholds are in FEET, so we
    convert before classifying (the ft-vs-m mismatch the review pinned).
    """
    m = number_from(water_depth_m)
    if m is None:
        return "unknown"
    return classify_dev_system_by_depth(m * _M_TO_FT)


# Concept-reduction priority (mirrors subseaiq ``_CONCEPT_PRIORITY``): a
# subsea-tieback facility means the field is produced VIA tieback, so it wins over
# the host's own type.
DEFAULT_CONCEPT_PRIORITY = (
    ConceptType.SUBSEA_TIEBACK,
    ConceptType.FPSO,
    ConceptType.SPAR,
    ConceptType.TLP,
    ConceptType.SEMISUB_FPS,
    ConceptType.FIXED_JACKET,
    ConceptType.FLNG,
    ConceptType.COMPLIANT_TOWER,
)


def reduce_concept_type(
    concept_types: Iterable[ConceptType],
    *,
    priority: tuple = DEFAULT_CONCEPT_PRIORITY,
) -> Optional[ConceptType]:
    """Reduce a field's several facility concepts to one by priority.

    Preserves subseaiq's many-facilities→one-concept rule (subsea-tieback wins).
    A pure function over already-mapped ConceptTypes so it stays decoupled from
    any country's host-type vocabulary. Unknown/absent → None.
    """
    ranked = [(priority.index(ct), ct) for ct in concept_types if ct in priority]
    if not ranked:
        return None
    return min(ranked, key=lambda t: t[0])[1]


# --- the mapping ------------------------------------------------------------


@dataclass(frozen=True)
class FieldMapEntry:
    """One regulator-column → FieldConcept-field rule.

    ``source_key`` is the regulator dict key; ``transform`` coerces/derives the
    value (default passthrough). A ``None`` transform result is dropped (the
    field stays unset — FieldConcept requires only ``name``).
    """

    source_key: str
    transform: Callable[[Any], Any] = identity


class FieldMetaMapping:
    """A country's regulator-metadata → FieldConcept field map (with callables).

    Validated at construction against ``FieldConcept`` fields so a typo'd target
    fails loudly rather than silently dropping (FieldConcept is ``extra=forbid``).
    """

    def __init__(self, entries: Dict[str, FieldMapEntry]):
        unknown = set(entries) - set(FieldConcept.model_fields)
        if unknown:
            raise ValueError(
                f"FieldMetaMapping targets not on FieldConcept: {sorted(unknown)}"
            )
        self._entries = dict(entries)

    def apply(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for target, entry in self._entries.items():
            val = entry.transform(meta.get(entry.source_key))
            if val is not None:
                out[target] = val
        return out


def to_field_concept(meta: Dict[str, Any], mapping: FieldMetaMapping) -> FieldConcept:
    """Build a validated FieldConcept from a regulator metadata dict.

    Applies ``mapping`` (per-field callables) then routes through
    ``field_development.loader.load_concept`` (Pydantic validation, ``extra=
    forbid``). Raises if the result is not a valid FieldConcept (e.g. missing
    ``name``, out-of-range magnitudes).
    """
    return load_concept(mapping.apply(meta))
