"""Estimate hull dimensions from rig type and water depth rating.

Generic dimensions are derived from industry averages for each hull form type.
Each estimate includes a confidence level indicating the data source quality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HullEstimate:
    """Estimated hull dimensions with confidence level."""

    loa_m: Optional[float] = None
    beam_m: Optional[float] = None
    draft_m: Optional[float] = None
    displacement_tonnes: Optional[float] = None
    confidence: str = "generic"  # "measured", "estimated", "generic"


# Industry-average hull dimensions by hull form type
# Sources: Offshore Magazine rig database, public ABS/DNV class records
_HULL_DEFAULTS: dict[str, HullEstimate] = {
    "drillship": HullEstimate(
        loa_m=228.0,
        beam_m=42.0,
        draft_m=12.0,
        displacement_tonnes=96000.0,
        confidence="generic",
    ),
    "semi_sub": HullEstimate(
        loa_m=104.0,
        beam_m=78.0,
        draft_m=21.0,
        displacement_tonnes=45000.0,
        confidence="generic",
    ),
    "jackup": HullEstimate(
        loa_m=70.0,
        beam_m=76.0,
        draft_m=5.5,
        displacement_tonnes=16000.0,
        confidence="generic",
    ),
    "barge": HullEstimate(
        loa_m=90.0,
        beam_m=27.0,
        draft_m=5.0,
        displacement_tonnes=12000.0,
        confidence="generic",
    ),
    "spar": HullEstimate(
        loa_m=None,
        beam_m=40.0,
        draft_m=198.0,
        displacement_tonnes=60000.0,
        confidence="generic",
    ),
}

# Water depth-based refinement for drillships
_DRILLSHIP_BY_DEPTH: list[tuple[float, HullEstimate]] = [
    # (max_water_depth_ft, estimate)
    (
        5000,
        HullEstimate(
            loa_m=190.0,
            beam_m=36.0,
            draft_m=10.0,
            displacement_tonnes=55000.0,
            confidence="estimated",
        ),
    ),
    (
        8000,
        HullEstimate(
            loa_m=228.0,
            beam_m=42.0,
            draft_m=12.0,
            displacement_tonnes=96000.0,
            confidence="estimated",
        ),
    ),
    (
        12000,
        HullEstimate(
            loa_m=238.0,
            beam_m=42.0,
            draft_m=12.0,
            displacement_tonnes=105000.0,
            confidence="estimated",
        ),
    ),
]

# Water depth-based refinement for semi-subs
_SEMI_SUB_BY_DEPTH: list[tuple[float, HullEstimate]] = [
    (
        3000,
        HullEstimate(
            loa_m=85.0,
            beam_m=67.0,
            draft_m=18.0,
            displacement_tonnes=30000.0,
            confidence="estimated",
        ),
    ),
    (
        7500,
        HullEstimate(
            loa_m=104.0,
            beam_m=78.0,
            draft_m=21.0,
            displacement_tonnes=45000.0,
            confidence="estimated",
        ),
    ),
    (
        12000,
        HullEstimate(
            loa_m=120.0,
            beam_m=90.0,
            draft_m=24.0,
            displacement_tonnes=55000.0,
            confidence="estimated",
        ),
    ),
]


def estimate_hull(
    hull_form_type: Optional[str],
    water_depth_ft: Optional[float] = None,
) -> Optional[HullEstimate]:
    """Estimate hull dimensions for a given hull form type.

    Uses water depth rating for refinement when available.
    Returns None if hull form type is unknown.
    """
    if not hull_form_type:
        return None

    form = str(hull_form_type).strip().lower()

    # Try depth-refined estimates first
    if water_depth_ft and water_depth_ft > 0:
        if form == "drillship":
            for max_depth, estimate in _DRILLSHIP_BY_DEPTH:
                if water_depth_ft <= max_depth:
                    return estimate
            return _DRILLSHIP_BY_DEPTH[-1][1]  # deepest bracket

        if form == "semi_sub":
            for max_depth, estimate in _SEMI_SUB_BY_DEPTH:
                if water_depth_ft <= max_depth:
                    return estimate
            return _SEMI_SUB_BY_DEPTH[-1][1]

    # Fallback to generic defaults
    return _HULL_DEFAULTS.get(form)


def populate_estimated_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing LOA_M, BEAM_M, DRAFT_M with type-based estimates.

    Adds DIMENSION_CONFIDENCE column: "measured" for original data,
    "estimated" for depth-refined estimates, "generic" for type averages.

    Only fills rows where ALL of LOA_M, BEAM_M, DRAFT_M are missing.

    Defensive against sparse-data input frames that may lack the dimension
    columns entirely (e.g., vendor-only spec-details fusion without BSEE
    WAR enrichment).
    """
    result = df.copy()

    # Sparse-data guard: ensure dimension columns exist before access (#408)
    for col in ("LOA_M", "BEAM_M", "DRAFT_M"):
        if col not in result.columns:
            result[col] = pd.NA

    if "DIMENSION_CONFIDENCE" not in result.columns:
        result["DIMENSION_CONFIDENCE"] = None

    # Mark existing dimensions as measured
    has_dims = (
        result["LOA_M"].notna() & result["BEAM_M"].notna() & result["DRAFT_M"].notna()
    )
    result.loc[
        has_dims & result["DIMENSION_CONFIDENCE"].isna(),
        "DIMENSION_CONFIDENCE",
    ] = "measured"

    # Estimate for rows missing all dimensions
    missing_all = (
        result["LOA_M"].isna() & result["BEAM_M"].isna() & result["DRAFT_M"].isna()
    )

    water_depth_col = None
    for col in ("WATER_DEPTH_RATING_FT", "MAX_WATER_DEPTH_FT"):
        if col in result.columns:
            water_depth_col = col
            break

    filled = 0
    for idx in result.index[missing_all]:
        hull_form = (
            result.at[idx, "HULL_FORM_TYPE"]
            if "HULL_FORM_TYPE" in result.columns
            else None
        )
        water_depth = result.at[idx, water_depth_col] if water_depth_col else None

        estimate = estimate_hull(hull_form, water_depth)
        if estimate:
            if estimate.loa_m is not None:
                result.at[idx, "LOA_M"] = estimate.loa_m
            if estimate.beam_m is not None:
                result.at[idx, "BEAM_M"] = estimate.beam_m
            if estimate.draft_m is not None:
                result.at[idx, "DRAFT_M"] = estimate.draft_m
            if (
                estimate.displacement_tonnes is not None
                and "DISPLACEMENT_TONNES" in result.columns
            ):
                result.at[idx, "DISPLACEMENT_TONNES"] = estimate.displacement_tonnes
            result.at[idx, "DIMENSION_CONFIDENCE"] = estimate.confidence
            filled += 1

    logger.info("Estimated dimensions for %d rigs", filled)

    # Refresh HULL_LIBRARY_REF now that LOA_M may have been filled
    if filled > 0 and "HULL_LIBRARY_REF" in result.columns:
        from worldenergydata.vessel_hull_models.rig_hulls.hull_form_mapper import (
            refresh_hull_library_refs,
        )

        result = refresh_hull_library_refs(result)

    return result
