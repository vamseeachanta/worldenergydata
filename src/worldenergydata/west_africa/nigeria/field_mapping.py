"""
Nigeria crude blend name to field and operator mapping.

Maps NUPRC blend/stream names to their primary field(s) and operators.
Blend names in NUPRC reports identify crude export terminals/blends,
not individual fields — one blend typically aggregates several fields.

Deepwater threshold: water depth >= 300m (standard industry definition).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

DEEPWATER_THRESHOLD_M = 300


@dataclass
class FieldInfo:
    """Metadata for a Nigeria oil field linked to a NUPRC blend."""

    field_name: str
    operator: str
    water_depth_m: int
    blend_name: str
    status: Optional[str] = None

    @property
    def is_deepwater(self) -> bool:
        """Return True if water depth >= 300m (deepwater threshold)."""
        return self.water_depth_m >= DEEPWATER_THRESHOLD_M

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FieldInfo):
            return NotImplemented
        return (
            self.field_name == other.field_name
            and self.operator == other.operator
            and self.blend_name == other.blend_name
        )


# Manual seed mapping: NUPRC blend name → primary field and operator.
# Multiple fields can share a blend (terminal aggregation); this maps
# to the dominant deepwater field where applicable.
BLEND_TO_FIELD_MAP: dict = {
    "BONNY LIGHT": FieldInfo(
        field_name="Bonny Terminal (multi-field blend)",
        operator="Shell Nigeria",
        water_depth_m=0,
        blend_name="BONNY LIGHT",
        status="Producing",
    ),
    "ESCRAVOS": FieldInfo(
        field_name="Escravos Terminal (multi-field blend)",
        operator="Chevron Nigeria",
        water_depth_m=0,
        blend_name="ESCRAVOS",
        status="Producing",
    ),
    "FORCADOS": FieldInfo(
        field_name="Forcados Terminal (multi-field blend)",
        operator="Shell Nigeria",
        water_depth_m=0,
        blend_name="FORCADOS",
        status="Producing",
    ),
    "QUAT IBOE": FieldInfo(
        field_name="Qua Iboe Terminal (multi-field blend)",
        operator="ExxonMobil Nigeria",
        water_depth_m=0,
        blend_name="QUAT IBOE",
        status="Producing",
    ),
    "BRASS RIVER": FieldInfo(
        field_name="Brass Terminal (multi-field blend)",
        operator="Agip Nigeria",
        water_depth_m=0,
        blend_name="BRASS RIVER",
        status="Producing",
    ),
    "AGBAMI": FieldInfo(
        field_name="Agbami",
        operator="Chevron Nigeria",
        water_depth_m=1440,
        blend_name="AGBAMI",
        status="Producing",
    ),
    "ERHA": FieldInfo(
        field_name="Erha",
        operator="ExxonMobil Nigeria",
        water_depth_m=1000,
        blend_name="ERHA",
        status="Producing",
    ),
    "BONGA": FieldInfo(
        field_name="Bonga",
        operator="Shell Nigeria",
        water_depth_m=1000,
        blend_name="BONGA",
        status="Producing",
    ),
    "EGINA": FieldInfo(
        field_name="Egina",
        operator="TotalEnergies Nigeria",
        water_depth_m=1500,
        blend_name="EGINA",
        status="Producing",
    ),
    "UKPOKITI": FieldInfo(
        field_name="Ukpokiti",
        operator="Chevron Nigeria",
        water_depth_m=600,
        blend_name="UKPOKITI",
        status="Producing",
    ),
}


def lookup_field(blend_name: Optional[str]) -> Optional[FieldInfo]:
    """
    Look up FieldInfo for a NUPRC blend name (case-insensitive).

    Args:
        blend_name: Blend/stream name as it appears in NUPRC reports.

    Returns:
        FieldInfo if found, None otherwise.
    """
    if not blend_name:
        return None
    key = str(blend_name).strip().upper()
    return BLEND_TO_FIELD_MAP.get(key)


def lookup_operator(blend_name: Optional[str]) -> Optional[str]:
    """
    Look up the primary operator for a NUPRC blend name.

    Args:
        blend_name: Blend/stream name as it appears in NUPRC reports.

    Returns:
        Operator name string if found, None otherwise.
    """
    field_info = lookup_field(blend_name)
    if field_info is None:
        return None
    return field_info.operator


def resolve_blend(blend_name: Optional[str]) -> Optional[FieldInfo]:
    """
    Attempt to resolve a blend name to FieldInfo, including partial matches.

    Exact match is tried first. For partial matches, returns None if
    ambiguous (multiple candidates) to avoid incorrect mappings.

    Args:
        blend_name: Blend name to resolve (may be abbreviated).

    Returns:
        FieldInfo on unambiguous match, None otherwise.
    """
    if not blend_name:
        return None

    normalised = str(blend_name).strip().upper()

    # Exact match
    if normalised in BLEND_TO_FIELD_MAP:
        return BLEND_TO_FIELD_MAP[normalised]

    # Partial match — only return if exactly one candidate
    candidates = [
        fi for key, fi in BLEND_TO_FIELD_MAP.items()
        if normalised in key or key in normalised
    ]
    if len(candidates) == 1:
        return candidates[0]

    # Ambiguous or no match
    return None
