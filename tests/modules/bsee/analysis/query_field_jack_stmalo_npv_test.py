import pytest
import os
import sys
import pandas as pd

import deepdiff
DEEPDIFF_AVAILABLE = True

from assetutilities.common.yml_utilities import ymlInput
from worldenergydata.engine import engine
ENGINE_AVAILABLE = True


def run_application(input_file, expected_result={}):
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    if not ENGINE_AVAILABLE:
        pytest.skip("Engine not available - dependencies missing")
    
    cfg = engine(input_file)


def get_valid_pytest_output_file(pytest_output_file):
    if pytest_output_file is not None and not os.path.isfile(
            pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__),
                                          pytest_output_file)
    return pytest_output_file

def test_application():

    input_file = 'query_field_jack_stmalo_npv.yml'

    pytest_output_file = None
    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})

    # Test NPV output files
    test_npv_output_files()


def test_npv_output_files():
    """Test that NPV output CSV files are generated and contain expected data."""
    
    # Define paths to expected NPV output files
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    npv_summary_file = os.path.join(results_dir, 'npv_summary_goa_jack_stmalo.csv')
    monthly_cashflows_file = os.path.join(results_dir, 'monthly_cashflows.csv')
    revenues_table_file = os.path.join(results_dir, 'revenues_table.csv')
    
    # Assert that NPV summary file exists
    assert os.path.exists(npv_summary_file), f"NPV summary file not found: {npv_summary_file}"
    
    # Assert that monthly cash flows file exists
    assert os.path.exists(monthly_cashflows_file), f"Monthly cash flows file not found: {monthly_cashflows_file}"
    
    # Assert that revenues table file exists (should already exist)
    assert os.path.exists(revenues_table_file), f"Revenues table file not found: {revenues_table_file}"
    
    # Read and validate NPV summary file
    npv_summary_df = pd.read_csv(npv_summary_file)
    
    # Assert NPV summary has expected columns
    expected_npv_columns = ['Field_Name', 'NPV_rate', 'Discount_Rate_Annual', 'Total_CAPEX_USD', 
                           'OPEX_per_BBL_USD', 'Total_Revenue_USD', 'Total_OPEX_USD', 
                           'Total_Net_Cash_Flow_USD', 'Analysis_Date', 'Notes']
    assert list(npv_summary_df.columns) == expected_npv_columns, f"NPV summary columns mismatch. Got: {list(npv_summary_df.columns)}"
    
    # Assert NPV summary has exactly one row (one analysis)
    assert len(npv_summary_df) == 1, f"Expected 1 row in NPV summary, got {len(npv_summary_df)}"
    
    # Assert field name is correct
    assert npv_summary_df['Field_Name'].iloc[0] == 'goa_jack_stmalo', f"Field name mismatch: {npv_summary_df['Field_Name'].iloc[0]}"
    
    # Assert NPV value is a number (not NaN)
    npv_value = npv_summary_df['NPV_rate'].iloc[0]
    assert pd.notna(npv_value), "NPV value should not be NaN"
    assert isinstance(npv_value, (int, float)), f"NPV value should be numeric, got {type(npv_value)}"
    
    # Assert discount rate is 0.10 (10% - Excel aligned)
    discount_rate = npv_summary_df['Discount_Rate_Annual'].iloc[0]
    assert discount_rate == 0.10, f"Expected discount rate 0.10, got {discount_rate}"
    
    # Assert total CAPEX is Excel-aligned (~$1.46B)
    total_capex = npv_summary_df['Total_CAPEX_USD'].iloc[0]
    assert total_capex > 0, f"Total CAPEX should be positive, got {total_capex}"
    assert abs(total_capex - 1460000000) < 100000000, f"Total CAPEX should be ~$1.46B for Excel alignment, got {total_capex}"  # ±$100M tolerance
    
    # Assert total revenue is positive
    total_revenue = npv_summary_df['Total_Revenue_USD'].iloc[0]
    assert total_revenue > 0, f"Total revenue should be positive, got {total_revenue}"
    
    # Read and validate monthly cash flows file
    monthly_cashflows_df = pd.read_csv(monthly_cashflows_file)
    
    # Assert monthly cash flows has expected columns
    expected_cashflow_columns = ['Month', 'Cash_Flow_USD', 'Description']
    assert list(monthly_cashflows_df.columns) == expected_cashflow_columns, f"Cash flows columns mismatch. Got: {list(monthly_cashflows_df.columns)}"
    
    # Assert first row is initial CAPEX (negative)
    first_row = monthly_cashflows_df.iloc[0]
    assert first_row['Month'] == 0, f"First month should be 0, got {first_row['Month']}"
    assert first_row['Cash_Flow_USD'] < 0, f"Initial CAPEX should be negative, got {first_row['Cash_Flow_USD']}"
    assert first_row['Description'] == 'Initial CAPEX (Excel-aligned)', f"First row description should be 'Initial CAPEX (Excel-aligned)', got {first_row['Description']}"
    
    # Assert subsequent rows are monthly cash flows
    monthly_rows = monthly_cashflows_df[monthly_cashflows_df['Month'] > 0]
    assert len(monthly_rows) > 0, "Should have monthly cash flow rows"
    
    # Assert all monthly cash flows have the correct description
    for _, row in monthly_rows.iterrows():
        assert row['Description'] == 'Monthly Net Cash Flow', f"Monthly row description should be 'Monthly Net Cash Flow', got {row['Description']}"
    
    # Read and validate revenues table file
    revenues_df = pd.read_csv(revenues_table_file)
    
    # Assert revenues table has expected columns
    expected_revenue_columns = ['Month', 'Monthly Oil Production', 'Avg Price (USD/bbl)', 'Revenue (USD)']
    assert list(revenues_df.columns) == expected_revenue_columns, f"Revenues columns mismatch. Got: {list(revenues_df.columns)}"
    
    # Assert revenues table has data rows
    assert len(revenues_df) > 1, "Revenues table should have at least one data row plus total row"
    
    print("✅ All NPV output file assertions passed successfully!")


if __name__ == "__main__":
    test_application()