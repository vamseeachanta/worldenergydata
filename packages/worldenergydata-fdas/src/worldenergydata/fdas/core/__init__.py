"""
FDAS Core Module

Core financial calculation and configuration functionality for field
development economic analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from .config import (
    DEFAULT_ASSUMPTIONS,
    AssumptionsManager,
    ConfigurationError,
    PriceDeckManager,
    classify_dev_system_by_depth,
    load_configuration,
    normalize_dev_system,
)
from .financial import (
    FinancialCalculationError,
    calculate_all_metrics,
    calculate_irr,
    calculate_npv,
    calculate_payback_period,
    calculate_trimmed_npv,
    excel_like_mirr,
    validate_cashflow_stream,
)

__all__ = [
    # Financial calculations
    "excel_like_mirr",
    "calculate_npv",
    "calculate_trimmed_npv",
    "calculate_irr",
    "calculate_payback_period",
    "validate_cashflow_stream",
    "calculate_all_metrics",
    "FinancialCalculationError",
    # Configuration management
    "normalize_dev_system",
    "classify_dev_system_by_depth",
    "AssumptionsManager",
    "PriceDeckManager",
    "ConfigurationError",
    "load_configuration",
    "DEFAULT_ASSUMPTIONS",
]
