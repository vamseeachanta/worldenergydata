"""
FDAS Data Processing Module

Handles production aggregation, D&C timeline extraction, and data
preparation for financial analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from .drilling import (
    CompletionActivityClassifier,
    DrillingDataError,
    DrillingTimelineExtractor,
    calculate_drilling_days,
)
from .production import (
    ProductionProcessingError,
    ProductionProcessor,
    aggregate_monthly_production,
    identify_first_oil_date,
)

__all__ = [
    # Production processing
    "ProductionProcessor",
    "aggregate_monthly_production",
    "identify_first_oil_date",
    "ProductionProcessingError",
    # Drilling & completion
    "DrillingTimelineExtractor",
    "CompletionActivityClassifier",
    "calculate_drilling_days",
    "DrillingDataError",
]
