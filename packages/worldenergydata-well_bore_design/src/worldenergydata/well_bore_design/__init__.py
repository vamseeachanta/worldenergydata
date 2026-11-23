"""Well bore design data models, hydraulic calculator, and decision framework."""

from worldenergydata.well_bore_design.decision_framework import (
    APPLICATION_MATRIX,
    BoreTypeDecision,
    BoreTypeRecommendation,
)
from worldenergydata.well_bore_design.hydraulics import WellBoreHydraulics
from worldenergydata.well_bore_design.schemas import (
    LARGE_BORE_MIN_BIT_SIZE_IN,
    SLIM_HOLE_MAX_BIT_SIZE_IN,
    BoreType,
    CasingString,
    EcdProfile,
    WellBoreDesign,
    bore_type_from_bit_size,
)

__all__ = [
    # schemas
    "BoreType",
    "CasingString",
    "WellBoreDesign",
    "EcdProfile",
    "bore_type_from_bit_size",
    "SLIM_HOLE_MAX_BIT_SIZE_IN",
    "LARGE_BORE_MIN_BIT_SIZE_IN",
    # hydraulics
    "WellBoreHydraulics",
    # decision framework
    "BoreTypeDecision",
    "BoreTypeRecommendation",
    "APPLICATION_MATRIX",
]
