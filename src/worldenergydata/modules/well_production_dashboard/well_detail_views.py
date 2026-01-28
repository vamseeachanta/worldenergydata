"""
Well Detail Views Component.

Provides detailed well visualizations with production charts, economic metrics,
decline curves, and verification status integration.

This module re-exports all components from the split modules for backward
compatibility. New code should import directly from the specific modules:

- views_utils: WellDetailConfig, ChartQualityIndicator, PLOTLY_AVAILABLE
- views_production: ProductionChartBuilder
- views_decline: DeclineCurveAnalyzer
- views_financial: EconomicMetricsCalculator
- views_verification: VerificationStatusBadge, AuditTrailLink
- views_main: WellDetailView
"""

# Re-export from views_utils
from .views_utils import (
    PLOTLY_AVAILABLE,
    ChartQualityIndicator,
    WellDetailConfig,
    logger,
)

# Re-export from views_production
from .views_production import ProductionChartBuilder

# Re-export from views_decline
from .views_decline import DeclineCurveAnalyzer

# Re-export from views_financial
from .views_financial import EconomicMetricsCalculator

# Re-export from views_verification
from .views_verification import AuditTrailLink, VerificationStatusBadge

# Re-export from views_main
from .views_main import WellDetailView

# Export all public names for backward compatibility
__all__ = [
    # Utils
    "PLOTLY_AVAILABLE",
    "logger",
    "WellDetailConfig",
    "ChartQualityIndicator",
    # Production
    "ProductionChartBuilder",
    # Decline
    "DeclineCurveAnalyzer",
    # Financial
    "EconomicMetricsCalculator",
    # Verification
    "VerificationStatusBadge",
    "AuditTrailLink",
    # Main view
    "WellDetailView",
]
