"""
FDAS Data Processing Module

Handles production aggregation, D&C timeline extraction, and data
preparation for financial analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from .production import (
    ProductionProcessor,
    aggregate_monthly_production,
    identify_first_oil_date,
    ProductionProcessingError,
)

from .drilling import (
    DrillingTimelineExtractor,
    CompletionActivityClassifier,
    calculate_drilling_days,
    DrillingDataError,
)

__all__ = [
    # Production processing
    'ProductionProcessor',
    'aggregate_monthly_production',
    'identify_first_oil_date',
    'ProductionProcessingError',

    # Drilling & completion
    'DrillingTimelineExtractor',
    'CompletionActivityClassifier',
    'calculate_drilling_days',
    'DrillingDataError',
]
