"""Map operational rig types to hydrodynamic hull form types.

The distinction between RIG_TYPE (operational) and HULL_FORM_TYPE (hydrodynamic)
is intentional:
- RIG_TYPE: how the rig is operated (semi_submersible, drillship, jack_up, etc.)
- HULL_FORM_TYPE: hydrodynamic form for RAO/diffraction analysis (semi_sub, drillship, jackup, barge, spar)
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Operational RIG_TYPE -> hydrodynamic HULL_FORM_TYPE
_RIG_TYPE_TO_HULL_FORM: dict[str, str] = {
    "drillship": "drillship",
    "semi_submersible": "semi_sub",
    "jack_up": "jackup",
    "inland_barge": "barge",
    "submersible": "semi_sub",      # submersible rigs are semi-sub hull forms
    "tender_assisted": "semi_sub",  # tender-assisted drilling on semi-sub hulls
    "lift_boat": "jackup",          # lift boats are self-elevating (jackup family)
}

# These rig types don't have a meaningful offshore hull form
_NON_VESSEL_TYPES: frozenset[str] = frozenset({
    "platform_rig",
    "land_rig",
    "wireline_unit",
    "coil_tubing_unit",
    "snubbing_unit",
    "workover_rig",
    "pumping_unit",
    "support_vessel",
    "unknown",
})


def map_hull_form(rig_type: Optional[str]) -> Optional[str]:
    """Map a single RIG_TYPE to HULL_FORM_TYPE.

    Returns None for non-vessel types (platform rigs, land rigs, etc.)
    """
    if not rig_type or str(rig_type).lower() in ("nan", "none", ""):
        return None
    rig_type_lower = str(rig_type).strip().lower()
    if rig_type_lower in _NON_VESSEL_TYPES:
        return None
    form = _RIG_TYPE_TO_HULL_FORM.get(rig_type_lower)
    if form is None:
        logger.debug("No hull form mapping for rig type: %s", rig_type)
    return form


def populate_hull_forms(df: pd.DataFrame) -> pd.DataFrame:
    """Populate HULL_FORM_TYPE for all rigs in a DataFrame.

    Only fills rows where HULL_FORM_TYPE is currently empty/NaN,
    preserving values already set by XLS parser or other sources.

    Args:
        df: DataFrame with RIG_TYPE and HULL_FORM_TYPE columns.

    Returns:
        DataFrame with HULL_FORM_TYPE populated where possible.
    """
    result = df.copy()

    if "HULL_FORM_TYPE" not in result.columns:
        result["HULL_FORM_TYPE"] = None
    if "RIG_TYPE" not in result.columns:
        logger.warning("No RIG_TYPE column -- cannot populate hull forms")
        return result

    mask = result["HULL_FORM_TYPE"].isna() | (result["HULL_FORM_TYPE"] == "")
    mapped = result.loc[mask, "RIG_TYPE"].apply(map_hull_form)
    result.loc[mask, "HULL_FORM_TYPE"] = mapped

    populated = result["HULL_FORM_TYPE"].notna().sum()
    total = len(result)
    logger.info(
        "Hull form populated: %d/%d (%.1f%%)",
        populated,
        total,
        100 * populated / total if total else 0,
    )

    # Assign HULL_LIBRARY_REF for rigs with hull form and dimensions
    if "HULL_LIBRARY_REF" not in result.columns:
        result["HULL_LIBRARY_REF"] = None
    ref_mask = (
        result["HULL_FORM_TYPE"].notna()
        & result["HULL_LIBRARY_REF"].isna()
    )
    result.loc[ref_mask, "HULL_LIBRARY_REF"] = result.loc[ref_mask].apply(
        _make_hull_library_ref, axis=1,
    )

    return result


def _make_hull_library_ref(row: pd.Series) -> Optional[str]:
    """Generate a hull_library catalog reference key.

    Format: {hull_form}_{loa_bucket}m
    e.g. "semi_sub_100m", "drillship_230m", "jackup_70m"

    Returns None if hull form type is missing.
    """
    hull_form = row.get("HULL_FORM_TYPE")
    if not hull_form or str(hull_form) == "nan":
        return None
    loa = row.get("LOA_M")
    if loa and not pd.isna(loa) and float(loa) > 0:
        bucket = int(round(float(loa) / 10) * 10)
        return f"{hull_form}_{bucket}m"
    return f"{hull_form}_generic"
