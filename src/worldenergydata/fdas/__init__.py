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
    print(f"NPV: ${results['npv']:,.2f}")
    print(f"MIRR: {results['mirr_annual']:.2%}")
    print(f"Payback: {results['payback_years']:.1f} years")

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
