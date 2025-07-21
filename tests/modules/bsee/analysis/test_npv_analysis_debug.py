"""
Enhanced NPV Analysis Test with Debugging Breakpoints
For testing the NPV user story implementation
"""
import pytest
import os
import sys
import pdb  # Python debugger for breakpoints
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from worldenergydata.engine import engine
from assetutilities.common.yml_utilities import ymlInput
ENGINE_AVAILABLE = True


def test_npv_analysis_with_breakpoints():
    """Test NPV analysis with debugging breakpoints"""
    
    # Test configuration
    input_file = 'query_field_jack_stmalo_npv.yml'
    test_dir = os.path.dirname(__file__)
    
    print("=" * 80)
    print("NPV ANALYSIS TEST - DEBUG MODE")
    print("=" * 80)
    
    # BREAKPOINT 1: Check file paths
    print(f"\nBREAKPOINT 1: Checking file paths")
    print(f"Test directory: {test_dir}")
    print(f"Input file: {input_file}")
    
    # Construct full path
    full_input_path = os.path.join(test_dir, input_file)
    print(f"Full input path: {full_input_path}")
    
    # Check if file exists
    if os.path.exists(full_input_path):
        print(f"[OK] Configuration file exists: {full_input_path}")
    else:
        print(f"[FAIL] Configuration file NOT found: {full_input_path}")
        pytest.skip("Configuration file not found")
    
    # BREAKPOINT 2: Read and inspect configuration
    print(f"\nBREAKPOINT 2: Reading configuration")
    try:
        with open(full_input_path, 'r') as f:
            config_content = f.read()
            print("Configuration preview (first 500 chars):")
            print("-" * 40)
            print(config_content[:500])
            print("-" * 40)
    except Exception as e:
        print(f"Error reading config: {e}")
        pytest.fail(f"Could not read configuration: {e}")
    
    # Uncomment to activate interactive debugger at this point
    # pdb.set_trace()  # <-- INTERACTIVE BREAKPOINT
    
    # BREAKPOINT 3: Test engine initialization
    print(f"\nBREAKPOINT 3: Testing engine initialization")
    
    # Check if engine is available
    if not ENGINE_AVAILABLE:
        print("[FAIL] Engine not available due to import errors")
        pytest.skip("Engine not available - dependencies missing")
    
    try:
        # Clear any command line arguments that might interfere
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]
        
        # Try to run the engine
        print("Attempting to run engine...")
        cfg = engine(full_input_path)
        
        # Restore original argv
        sys.argv = original_argv
        
        print("[OK] Engine executed successfully")
        
        # BREAKPOINT 4: Inspect results
        print(f"\nBREAKPOINT 4: Inspecting results")
        if cfg:
            print(f"Configuration type: {type(cfg)}")
            
            # Try to access NPV-related results
            if hasattr(cfg, 'results'):
                print("Results found in configuration")
                # pdb.set_trace()  # <-- INTERACTIVE BREAKPOINT for results inspection
            
            if isinstance(cfg, dict):
                print("Configuration keys:", list(cfg.keys())[:10])
                
                # Look for NPV-specific data
                npv_keys = [k for k in cfg.keys() if 'npv' in k.lower()]
                if npv_keys:
                    print(f"NPV-related keys found: {npv_keys}")
                    for key in npv_keys:
                        print(f"  {key}: {type(cfg[key])}")
    
    except Exception as e:
        print(f"[FAIL] Engine execution failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Engine execution failed: {e}")
    
    print("\n" + "=" * 80)
    print("NPV ANALYSIS TEST COMPLETED")
    print("=" * 80)


def test_npv_calculation_direct():
    """Test NPV calculation directly without full engine"""
    
    print("\n" + "=" * 80)
    print("DIRECT NPV CALCULATION TEST")
    print("=" * 80)
    
    # Mock data for NPV calculation
    mock_data = {
        'cash_flows': [-1000000,  # Initial investment
                       300000,     # Year 1
                       400000,     # Year 2
                       500000,     # Year 3
                       600000],    # Year 4
        'discount_rate': 0.10,     # 10% discount rate
        'field_name': 'Test Field'
    }
    
    print(f"\nTest data:")
    print(f"  Field: {mock_data['field_name']}")
    print(f"  Cash flows: {mock_data['cash_flows']}")
    print(f"  Discount rate: {mock_data['discount_rate'] * 100}%")
    
    # Simple NPV calculation
    def calculate_npv(cash_flows, discount_rate):
        """Calculate NPV using basic formula"""
        npv = 0
        for t, cash_flow in enumerate(cash_flows):
            npv += cash_flow / ((1 + discount_rate) ** t)
        return npv
    
    # Calculate NPV
    npv_value = calculate_npv(mock_data['cash_flows'], mock_data['discount_rate'])
    
    print(f"\nCalculated NPV: ${npv_value:,.2f}")
    
    # Assertions
    assert npv_value > 0, f"NPV should be positive for this test case, got {npv_value}"
    
    # BREAKPOINT: Inspect NPV calculation
    # pdb.set_trace()  # <-- INTERACTIVE BREAKPOINT
    
    print("[OK] Direct NPV calculation test passed")


def test_npv_analysis_components():
    """Test individual components of NPV analysis"""
    
    print("\n" + "=" * 80)
    print("NPV COMPONENTS TEST")
    print("=" * 80)
    
    # Test 1: Production data processing
    print("\nTest 1: Production data simulation")
    production_data = {
        'month': ['2020-01', '2020-02', '2020-03'],
        'oil_production_bbl': [10000, 12000, 11000],
        'gas_production_mcf': [5000, 6000, 5500]
    }
    print(f"  Production months: {production_data['month']}")
    print(f"  Oil production: {production_data['oil_production_bbl']}")
    
    # Test 2: Economic parameters
    print("\nTest 2: Economic parameters")
    economic_params = {
        'oil_price_per_bbl': 60,
        'gas_price_per_mcf': 3,
        'opex_per_bbl': 15,
        'discount_rate': 0.10
    }
    for key, value in economic_params.items():
        print(f"  {key}: {value}")
    
    # Test 3: Revenue calculation
    print("\nTest 3: Revenue calculation")
    total_oil_revenue = sum(production_data['oil_production_bbl']) * economic_params['oil_price_per_bbl']
    total_gas_revenue = sum(production_data['gas_production_mcf']) * economic_params['gas_price_per_mcf']
    total_revenue = total_oil_revenue + total_gas_revenue
    
    print(f"  Total oil revenue: ${total_oil_revenue:,}")
    print(f"  Total gas revenue: ${total_gas_revenue:,}")
    print(f"  Total revenue: ${total_revenue:,}")
    
    # BREAKPOINT: Inspect component calculations
    # pdb.set_trace()  # <-- INTERACTIVE BREAKPOINT
    
    assert total_revenue > 0, "Total revenue should be positive"
    print("\n[OK] NPV components test passed")


if __name__ == "__main__":
    # Run tests with different options
    import argparse
    
    parser = argparse.ArgumentParser(description='NPV Analysis Test Suite')
    parser.add_argument('--debug', action='store_true', help='Enable interactive debugging')
    parser.add_argument('--test', choices=['all', 'engine', 'direct', 'components'], 
                        default='all', help='Which test to run')
    
    args = parser.parse_args()
    
    # Enable interactive debugging if requested
    if args.debug:
        print("DEBUG MODE ENABLED - Breakpoints will pause execution")
        # Uncomment breakpoints in the code above
    
    # Run selected tests
    if args.test in ['all', 'engine']:
        test_npv_analysis_with_breakpoints()
    
    if args.test in ['all', 'direct']:
        test_npv_calculation_direct()
    
    if args.test in ['all', 'components']:
        test_npv_analysis_components()
    
    print("\nAll selected tests completed!")