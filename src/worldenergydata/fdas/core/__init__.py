"""
FDAS Core Module

Core financial calculation and configuration functionality for field
development economic analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from .financial import (
    excel_like_mirr,
    calculate_npv,
    calculate_trimmed_npv,
    calculate_irr,
    calculate_payback_period,
    validate_cashflow_stream,
    calculate_all_metrics,
    FinancialCalculationError,
)

from .config import (
    normalize_dev_system,
    classify_dev_system_by_depth,
    AssumptionsManager,
    PriceDeckManager,
    ConfigurationError,
    load_configuration,
    DEFAULT_ASSUMPTIONS,
)

__all__ = [
    # Financial calculations
    'excel_like_mirr',
    'calculate_npv',
    'calculate_trimmed_npv',
    'calculate_irr',
    'calculate_payback_period',
    'validate_cashflow_stream',
    'calculate_all_metrics',
    'FinancialCalculationError',

    # Configuration management
    'normalize_dev_system',
    'classify_dev_system_by_depth',
    'AssumptionsManager',
    'PriceDeckManager',
    'ConfigurationError',
    'load_configuration',
    'DEFAULT_ASSUMPTIONS',
]
