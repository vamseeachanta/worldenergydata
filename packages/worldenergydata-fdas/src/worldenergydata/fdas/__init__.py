"""
FDAS (Field Development Analysis System) Module

Provides comprehensive financial analysis capabilities for deepwater field
development, including NPV/MIRR calculations, cashflow modeling, and
integration with BSEE data sources.

Features:
    - Excel-compatible MIRR (Modified Internal Rate of Return) calculations
    - NPV (Net Present Value) with customizable discount rates
    - IRR (Internal Rate of Return) for monthly and annual periods
    - Payback period analysis
    - Water depth-based development system classification
    - Integration with BSEE production data

Module Structure:
    core/               Core financial calculations
        financial.py    NPV, MIRR, IRR calculations
        config.py       Assumptions and price deck management
    adapters/           Data source adapters
        bsee_adapter.py Integration with BSEE data
        lease_mapping.py Lease-to-field mapping
    analysis/           Analysis engines
        cashflow.py     Cashflow modeling
    data/               Data loading and storage
    reports/            Report generation

Financial Functions:
    - calculate_npv: Net Present Value calculation
    - excel_like_mirr: Excel-compatible MIRR calculation
    - calculate_irr: Internal Rate of Return
    - calculate_all_metrics: All metrics in one call

Configuration:
    - AssumptionsManager: Manage development assumptions by system type
    - PriceDeckManager: Oil/gas price projections
    - classify_dev_system_by_depth: Classify by water depth

Example usage:
    from worldenergydata.fdas import (
        calculate_npv,
        excel_like_mirr,
        calculate_all_metrics,
        AssumptionsManager,
        BseeAdapter,
    )

    import numpy as np

    # Calculate NPV
    cashflows = np.array([-1000, 100, 200, 300, 400, 500])
    npv = calculate_npv(cashflows, discount_rate=0.10, period="monthly")

    # Calculate all metrics
    results = calculate_all_metrics(cashflows, discount_rate=0.10)
    logger.info(f"NPV: ${results['npv']:,.2f}")
    logger.info(f"MIRR: {results['mirr_annual']:.2%}")
    logger.info(f"Payback: {results['payback_years']:.1f} years")

CLI usage:
    worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300]"
    worldenergydata fdas calculate-mirr --cashflows "[-5000,1000,1500,2000]"
    worldenergydata fdas calculate-all --cashflows "[-1000,100,200,300,400,500]"
    worldenergydata fdas analyze --field "Thunder Horse" --discount-rate 0.10
    worldenergydata fdas classify 5000

Author: WorldEnergyData Team
Date: 2025-10-03
Version: 1.0.0
"""

from worldenergydata.common.logging import get_logger

from .adapters import (
    AdapterError,
    BseeAdapter,
    LeaseMapping,
)
from .core import (  # Financial functions; Configuration
    AssumptionsManager,
    ConfigurationError,
    FinancialCalculationError,
    PriceDeckManager,
    calculate_all_metrics,
    calculate_irr,
    calculate_npv,
    classify_dev_system_by_depth,
    excel_like_mirr,
)
from .fiscal import (  # Source-agnostic country fiscal-terms decks (#714)
    FiscalTerms,
    FiscalTermsNotFoundError,
    FiscalTermsValidationError,
    RoyaltyTerms,
    available_countries,
    get_fiscal_terms,
)

logger = get_logger(__name__)

__version__ = "1.0.0"

__all__ = [
    # Core financial
    "excel_like_mirr",
    "calculate_npv",
    "calculate_irr",
    "calculate_all_metrics",
    "FinancialCalculationError",
    # Configuration
    "AssumptionsManager",
    "PriceDeckManager",
    "classify_dev_system_by_depth",
    "ConfigurationError",
    # Adapters
    "BseeAdapter",
    "LeaseMapping",
    "AdapterError",
    # Fiscal terms (source-agnostic country decks, #714)
    "FiscalTerms",
    "RoyaltyTerms",
    "get_fiscal_terms",
    "available_countries",
    "FiscalTermsNotFoundError",
    "FiscalTermsValidationError",
    # Query API (issue #288)
    "economics",
    # Disclosure analytics (issue #338)
    "disclosure_analytics",
    # Metadata
    "__version__",
]


def __getattr__(name: str):
    """Lazy import of query API singletons (issue #288, #338)."""
    if name == "economics":
        from worldenergydata.fdas.api import economics

        return economics
    if name == "disclosure_analytics":
        from worldenergydata.fdas.api import disclosure_analytics

        return disclosure_analytics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
