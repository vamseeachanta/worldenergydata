"""
FDAS (Field Development Analysis System) Module

Provides comprehensive financial analysis capabilities for deepwater field
development, including NPV/MIRR calculations, cashflow modeling, and
integration with BSEE data sources.

Author: WorldEnergyData Team
Date: 2025-10-03
Version: 1.0.0
"""

from .core import (
    # Financial functions
    excel_like_mirr,
    calculate_npv,
    calculate_irr,
    calculate_all_metrics,
    FinancialCalculationError,

    # Configuration
    AssumptionsManager,
    PriceDeckManager,
    classify_dev_system_by_depth,
    ConfigurationError,
)

from .adapters import (
    BseeAdapter,
    LeaseMapping,
    AdapterError,
)

__version__ = '1.0.0'

__all__ = [
    # Core financial
    'excel_like_mirr',
    'calculate_npv',
    'calculate_irr',
    'calculate_all_metrics',
    'FinancialCalculationError',

    # Configuration
    'AssumptionsManager',
    'PriceDeckManager',
    'classify_dev_system_by_depth',
    'ConfigurationError',

    # Adapters
    'BseeAdapter',
    'LeaseMapping',
    'AdapterError',

    # Metadata
    '__version__',
]
