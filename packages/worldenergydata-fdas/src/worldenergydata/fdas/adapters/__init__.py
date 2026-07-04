"""
FDAS Data Adapters Module

Provides adapters for translating between BSEE data structures and FDAS
financial analysis requirements.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from .bsee_adapter import (
    AdapterError,
    BseeAdapter,
    LeaseMapping,
    ProductionAdapter,
    WellDataAdapter,
)
from .contract import (  # F2 country adapter contract (#715)
    FDAS_PRODUCTION_COLUMNS,
    FdasContractError,
    FdasInputs,
    to_fdas_production,
)

# Note: field_concept_normalizer is intentionally NOT re-exported here — it
# imports field_development (root dist) at runtime; keeping it off the adapters
# package import path lets contract.py-only consumers stay field_development-free.
# Import it directly: from worldenergydata.fdas.adapters.field_concept_normalizer

__all__ = [
    "BseeAdapter",
    "LeaseMapping",
    "WellDataAdapter",
    "ProductionAdapter",
    "AdapterError",
    # F2 contract (#715)
    "to_fdas_production",
    "FDAS_PRODUCTION_COLUMNS",
    "FdasInputs",
    "FdasContractError",
]
