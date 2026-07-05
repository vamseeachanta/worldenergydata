"""Type curve matching for production analysis (Blasingame/Fetkovich)."""

from .blasingame import (
    blasingame_typecurve,
    match_blasingame,
    material_balance_time,
    normalized_rate,
    rate_integral,
    rate_integral_derivative,
)
from .fetkovich import (
    fetkovich_boundary,
    fetkovich_transient,
    fetkovich_typecurve,
    match_fetkovich,
)
from .models import MatchResult, ProductionData, ReservoirParams, TypeCurveSet

__all__ = [
    "blasingame_typecurve",
    "fetkovich_boundary",
    "fetkovich_transient",
    "fetkovich_typecurve",
    "match_blasingame",
    "match_fetkovich",
    "material_balance_time",
    "MatchResult",
    "normalized_rate",
    "ProductionData",
    "rate_integral",
    "rate_integral_derivative",
    "ReservoirParams",
    "TypeCurveSet",
]
