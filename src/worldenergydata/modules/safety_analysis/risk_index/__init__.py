"""HSE Risk Index - Three-dimensional risk scoring framework."""

# CLI app for integration into parent CLI
from worldenergydata.modules.safety_analysis.risk_index.cli import app as risk_index_app
from worldenergydata.modules.safety_analysis.risk_index.dashboard import RiskDashboard
from worldenergydata.modules.safety_analysis.risk_index.data_assembler import (
    DataAssembler,
)
from worldenergydata.modules.safety_analysis.risk_index.methodology import (
    generate_methodology_html,
)
from worldenergydata.modules.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    DimensionScore,
    RiskCategory,
)
from worldenergydata.modules.safety_analysis.risk_index.normalizer import (
    NormalizationResult,
    normalize_to_scale,
    percentile_rank,
)
from worldenergydata.modules.safety_analysis.risk_index.scorer import RiskScorer

__all__ = [
    "ActivityRiskScore",
    "CompositeScore",
    "DataAssembler",
    "DimensionScore",
    "NormalizationResult",
    "RiskCategory",
    "RiskDashboard",
    "RiskScorer",
    "generate_methodology_html",
    "normalize_to_scale",
    "percentile_rank",
    "risk_index_app",
]
