"""HSE Risk Index - Three-dimensional risk scoring framework."""

# CLI app for integration into parent CLI
from worldenergydata.safety_analysis.risk_index.cli import app as risk_index_app
from worldenergydata.safety_analysis.risk_index.config_loader import (
    RiskConfig,
    default_config,
    load_config,
)
from worldenergydata.safety_analysis.risk_index.dashboard import RiskDashboard
from worldenergydata.safety_analysis.risk_index.data_assembler import (
    DataAssembler,
)
from worldenergydata.safety_analysis.risk_index.methodology import (
    generate_methodology_html,
)
from worldenergydata.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    DimensionScore,
    RiskCategory,
)
from worldenergydata.safety_analysis.risk_index.normalizer import (
    NormalizationResult,
    normalize_to_scale,
    percentile_rank,
)
from worldenergydata.safety_analysis.risk_index.scorer import RiskScorer
from worldenergydata.safety_analysis.risk_index.slicer import RiskSlicer

__all__ = [
    "ActivityRiskScore",
    "CompositeScore",
    "DataAssembler",
    "DimensionScore",
    "NormalizationResult",
    "RiskCategory",
    "RiskConfig",
    "RiskDashboard",
    "RiskScorer",
    "RiskSlicer",
    "default_config",
    "generate_methodology_html",
    "load_config",
    "normalize_to_scale",
    "percentile_rank",
    "risk_index_app",
]
