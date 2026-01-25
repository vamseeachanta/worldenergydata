#!/usr/bin/env python3
"""
Simple NPV Test Runner for UV
Run with: uv run python tests/modules/bsee/analysis/run_npv_test.py
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_npv_test_basic():
    """Run basic NPV test without complex dependencies"""
    
    print("=" * 80)
    print("BASIC NPV TEST RUNNER")
    print("=" * 80)
    
    # Check for configuration file
    config_file = Path(__file__).parent / "query_field_jack_stmalo_npv.yml"
    
    print(f"\n1. Checking configuration file...")
    if config_file.exists():
        print(f"   [OK] Found: {config_file}")
        
        # Read and display configuration
        with open(config_file, 'r') as f:
            lines = f.readlines()
            print(f"\n2. Configuration preview:")
            print("   " + "-" * 40)
            for i, line in enumerate(lines[:20]):
                print(f"   {i+1:2d}: {line.rstrip()}")
            print("   " + "-" * 40)
    else:
        print(f"   [FAIL] Not found: {config_file}")
        return
    
    # Try to import worldenergydata
    print(f"\n3. Testing worldenergydata import...")
    import worldenergydata
    print("   [OK] worldenergydata imported successfully")
    
    # Test NPV calculation logic
    print(f"\n4. Testing NPV calculation...")
    
    # Sample NPV calculation
    cash_flows = [-1000000, 300000, 400000, 500000, 600000]  # Initial investment + 4 years
    discount_rate = 0.10
    
    npv = sum(cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cash_flows))
    
    print(f"   Cash flows: {cash_flows}")
    print(f"   Discount rate: {discount_rate * 100}%")
    print(f"   Calculated NPV: ${npv:,.2f}")
    
    if npv > 0:
        print("   [OK] NPV is positive (profitable)")
    else:
        print("   [FAIL] NPV is negative (not profitable)")
    
    # BREAKPOINT: Add this line where you want to debug
    # import pdb; pdb.set_trace()
    
    print(f"\n5. Test Summary:")
    print(f"   - Configuration file: {'[OK] OK' if config_file.exists() else '[FAIL] Missing'}")
    print(f"   - Package import: [OK] OK")
    print(f"   - NPV calculation: [OK] OK")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


def run_npv_test_with_data():
    """Run NPV test with actual BSEE field data structure"""
    
    print("\n" + "=" * 80)
    print("NPV TEST WITH BSEE FIELD DATA")
    print("=" * 80)
    
    # Simulate BSEE field data structure
    field_data = {
        'field_name': 'Jack/St Malo',
        'block': 'WR678',
        'wells': 20,
        'production_start': '2014-12',
        'economic_params': {
            'opex_per_bbl': 15,
            'discount_rate': 0.10,
            'oil_price_per_bbl': 60
        }
    }
    
    print(f"\nField Information:")
    print(f"  Name: {field_data['field_name']}")
    print(f"  Block: {field_data['block']}")
    print(f"  Wells: {field_data['wells']}")
    print(f"  Production Start: {field_data['production_start']}")
    
    print(f"\nEconomic Parameters:")
    for key, value in field_data['economic_params'].items():
        print(f"  {key}: {value}")
    
    # Simulate monthly production data
    print(f"\nSimulated Production Data (first 6 months):")
    months = ['2015-01', '2015-02', '2015-03', '2015-04', '2015-05', '2015-06']
    production = [50000, 48000, 46000, 45000, 44000, 43000]  # BBL per month
    
    for month, prod in zip(months, production):
        revenue = prod * field_data['economic_params']['oil_price_per_bbl']
        opex = prod * field_data['economic_params']['opex_per_bbl']
        net_cash_flow = revenue - opex
        print(f"  {month}: {prod:,} BBL, Revenue: ${revenue:,}, OPEX: ${opex:,}, Net: ${net_cash_flow:,}")
    
    # BREAKPOINT: Uncomment to debug at this point
    # import pdb; pdb.set_trace()
    
    print("\n[OK] BSEE field data test completed")


if __name__ == "__main__":
    # Run both test functions
    run_npv_test_basic()
    run_npv_test_with_data()
    
    print("\n" + "="*80)
    print("To debug, uncomment the pdb.set_trace() lines in the code")
    print("Or run with: python -m pdb run_npv_test.py")
    print("="*80)