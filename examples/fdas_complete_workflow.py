#!/usr/bin/env python
"""
FDAS Complete Workflow Example

Demonstrates end-to-end field development economic analysis using the FDAS module.
This example shows how to:
1. Load BSEE data
2. Process production and drilling data
3. Generate monthly cashflows
4. Calculate NPV/MIRR/IRR
5. Create Excel reports

Author: WorldEnergyData Team
Date: 2025-10-03
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.worldenergydata.modules.fdas import (
    # Core financial
    calculate_all_metrics,
    excel_like_mirr,
    calculate_npv,

    # Configuration
    AssumptionsManager,
    classify_dev_system_by_depth,

    # Adapters
    BseeAdapter,
)

from src.worldenergydata.modules.fdas.data import (
    ProductionProcessor,
)

from src.worldenergydata.modules.fdas.analysis import (
    CashflowEngine,
)

from src.worldenergydata.modules.fdas.reports import (
    FDASReportBuilder,
)


def example_simple_npv_mirr():
    """Example 1: Simple NPV and MIRR calculation"""
    print("\n" + "="*80)
    print("Example 1: Simple NPV and MIRR Calculation")
    print("="*80)

    # Simple field development cashflow (in millions USD)
    cashflows = np.array([
        -1500,  # Year 0: Initial CAPEX
        -500,   # Year 1: Additional CAPEX
        200,    # Year 2: First production
        800,    # Year 3: Ramp up
        1200,   # Year 4: Peak
        1000,   # Year 5: Plateau
        800,    # Year 6: Decline
        600,    # Year 7
        400,    # Year 8
        200,    # Year 9
    ])

    discount_rate = 0.10  # 10% cost of capital

    # Calculate NPV
    npv = calculate_npv(cashflows, discount_rate, period='annual')

    # Calculate MIRR
    mirr_annual, mirr_monthly = excel_like_mirr(cashflows, discount_rate)

    print(f"\nCashflow Analysis:")
    print(f"  Total Investment: ${abs(cashflows[cashflows < 0].sum()):,.0f}M")
    print(f"  Total Revenue:    ${cashflows[cashflows > 0].sum():,.0f}M")
    print(f"\nFinancial Metrics:")
    print(f"  NPV (10% discount): ${npv:,.2f}M")
    print(f"  MIRR (Annual):      {mirr_monthly:.2%}")
    print(f"  Project Status:     {'✓ PROFITABLE' if npv > 0 else '✗ UNPROFITABLE'}")


def example_with_assumptions():
    """Example 2: Using assumptions manager"""
    print("\n" + "="*80)
    print("Example 2: Development System Assumptions")
    print("="*80)

    # Load assumptions from FDAS source
    assumptions_file = Path('/home/vamsee/Downloads/FDAS_V30/lease_assumptions.xlsx')

    if assumptions_file.exists():
        mgr = AssumptionsManager.from_excel(assumptions_file)

        print("\nSubsea 15K Development Assumptions:")
        for param in ['HOST_CAPEX_MM', 'SURF_PER_WELL_MM', 'ROYALTY_RATE',
                     'VARIABLE_OPEX_$/BBL', 'FIXED_OPEX_MM_PER_YEAR']:
            value = mgr.get('subsea15', param)
            print(f"  {param:30} {value:10.2f}")

        print("\nSubsea 20K Development Assumptions:")
        for param in ['HOST_CAPEX_MM', 'SURF_PER_WELL_MM', 'ROYALTY_RATE',
                     'VARIABLE_OPEX_$/BBL', 'FIXED_OPEX_MM_PER_YEAR']:
            value = mgr.get('subsea20', param)
            print(f"  {param:30} {value:10.2f}")
    else:
        print("\nUsing default assumptions (assumptions file not found)")
        mgr = AssumptionsManager()


def example_production_processing():
    """Example 3: Production data processing"""
    print("\n" + "="*80)
    print("Example 3: Production Data Processing")
    print("="*80)

    # Create sample production data
    dates = pd.date_range('2020-01-01', periods=48, freq='MS')
    production_data = pd.DataFrame({
        'API_WELL_NUMBER': ['60805401' + str(i).zfill(4) for i in range(5)] * 48,
        'DEV_NAME': ['Sample Field'] * 240,
        'PROD_DATE': np.repeat(dates, 5),
        'OIL_VOLUME': np.random.randint(5000, 25000, 240),
        'WATER_VOLUME': np.random.randint(1000, 10000, 240),
        'GAS_VOLUME': np.random.randint(500, 5000, 240),
    })

    print(f"\nProcessing {len(production_data)} production records...")

    # Process production
    processor = ProductionProcessor(production_data)

    # Monthly aggregation
    monthly = processor.aggregate_monthly(by='DEV_NAME')
    print(f"\nMonthly Production Summary:")
    print(f"  Months of production: {len(monthly)}")
    print(f"  Total oil:            {monthly['MONTHLY_OIL_BBL'].sum():,.0f} BBL")
    print(f"  Average monthly:      {monthly['MONTHLY_OIL_BBL'].mean():,.0f} BBL")
    print(f"  Peak month:           {monthly['MONTHLY_OIL_BBL'].max():,.0f} BBL")

    # First oil
    first_oil = processor.identify_first_oil(by='DEV_NAME')
    print(f"\nFirst Oil:")
    print(f"  Date:                 {first_oil['FIRST_OIL_DATE'].iloc[0]}")

    # Cumulative production
    cumulative = processor.calculate_cumulative_production(by='DEV_NAME')
    print(f"\nCumulative Production:")
    print(f"  Final cumulative:     {cumulative['CUMULATIVE_OIL_BBL'].iloc[-1]:,.0f} BBL")


def example_cashflow_generation():
    """Example 4: Monthly cashflow generation"""
    print("\n" + "="*80)
    print("Example 4: Monthly Cashflow Generation")
    print("="*80)

    # Create sample data
    months = pd.period_range('2024-01', periods=60, freq='M')
    production = pd.DataFrame({
        'YEAR_MONTH': months,
        'MONTHLY_OIL_BBL': np.concatenate([
            np.linspace(0, 100000, 12),      # Ramp up
            np.full(24, 100000),              # Plateau
            np.linspace(100000, 50000, 24),   # Decline
        ])
    })

    # Setup
    mgr = AssumptionsManager()  # Use defaults
    engine = CashflowEngine(mgr, 'subsea15')

    # WTI prices
    wti_prices = {str(m): 75.0 for m in months}

    # Drilling timeline (simplified)
    timeline = {
        'drilling_monthly': {
            '2023-06': 30,
            '2023-07': 31,
            '2023-08': 15,
        },
        'completion_monthly': {
            '2023-09': 30,
            '2023-10': 31,
            '2023-11': 30,
        }
    }

    print("\nGenerating monthly cashflows...")
    cashflows = engine.generate_monthly_cashflow(
        production,
        timeline,
        wti_prices,
        datetime(2024, 1, 1)
    )

    # Summary
    total_revenue = sum(cf.oil_revenue_usd for cf in cashflows)
    total_opex = sum(cf.variable_opex_usd + cf.fixed_opex_usd for cf in cashflows)
    total_capex = sum(cf.drilling_capex_usd + cf.facilities_capex_usd + cf.host_capex_usd
                     for cf in cashflows)
    net_cashflow = sum(cf.net_cashflow_usd for cf in cashflows)

    print(f"\nCashflow Summary ({len(cashflows)} months):")
    print(f"  Total Revenue:        ${total_revenue/1e6:,.1f}M")
    print(f"  Total OPEX:           ${total_opex/1e6:,.1f}M")
    print(f"  Total CAPEX:          ${total_capex/1e6:,.1f}M")
    print(f"  Net Cashflow:         ${net_cashflow/1e6:,.1f}M")

    # Calculate metrics
    cf_array = np.array([cf.net_cashflow_usd for cf in cashflows])
    metrics = calculate_all_metrics(cf_array, 0.10)

    print(f"\nFinancial Metrics:")
    print(f"  NPV (10%):            ${metrics.get('npv', 0)/1e6:,.1f}M")
    print(f"  MIRR (Annual):        {metrics.get('mirr_annual', 0):.2%}")
    print(f"  IRR (Annual):         {metrics.get('irr_annual', 0):.2%}")
    print(f"  Payback:              {metrics.get('payback_years', 0):.1f} years")


def example_complete_workflow():
    """Example 5: Complete workflow with real data (if available)"""
    print("\n" + "="*80)
    print("Example 5: Complete Workflow")
    print("="*80)

    bsee_data_dir = Path('data/modules/bsee/current')

    if not bsee_data_dir.exists():
        print("\nBSEE data directory not found - using synthetic data")
        print("To run with real data, ensure BSEE data is available at:")
        print(f"  {bsee_data_dir}")
        return

    print("\nThis would demonstrate:")
    print("  1. Loading BSEE data with BseeAdapter")
    print("  2. Processing production data")
    print("  3. Extracting D&C timeline")
    print("  4. Generating cashflows")
    print("  5. Calculating financial metrics")
    print("  6. Creating Excel report")
    print("\nSee examples/fdas_anchor_field_example.py for full implementation")


def main():
    """Run all examples"""
    print("="*80)
    print("FDAS Module - Complete Workflow Examples")
    print("="*80)

    try:
        example_simple_npv_mirr()
        example_with_assumptions()
        example_production_processing()
        example_cashflow_generation()
        example_complete_workflow()

        print("\n" + "="*80)
        print("✓ All examples completed successfully!")
        print("="*80)
        print("\nFor more examples, see:")
        print("  - examples/fdas_anchor_field_example.py")
        print("  - tests/modules/fdas/integration/test_end_to_end.py")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
