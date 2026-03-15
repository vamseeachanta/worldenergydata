#!/usr/bin/env python3
"""
Simple test to verify our refactored NPV analysis meets expectations
"""

import os

import pandas as pd


def test_refactored_npv():
    """Test that our refactored NPV analysis meets the requirements"""

    print("Testing Refactored NPV Analysis Results")
    print("=" * 50)

    results_dir = "tests/modules/bsee/analysis/results"
    npv_file = os.path.join(results_dir, "npv_summary.csv")

    if not os.path.exists(npv_file):
        print("❌ NPV summary file not found")
        return False

    df = pd.read_csv(npv_file)

    print("📊 Current Results:")
    print(f"  Field Name: {df['Field_Name'].iloc[0]}")
    print(f"  NPV: ${df['NPV_rate'].iloc[0]:,.2f}")
    print(f"  Discount Rate: {df['Discount_Rate_Annual'].iloc[0]*100}%")
    print(f"  CAPEX: ${df['Total_CAPEX_USD'].iloc[0]:,.0f}")
    print(f"  Total Revenue: ${df['Total_Revenue_USD'].iloc[0]:,.2f}")

    print("\n🧪 Running Tests:")

    # Test 1: Discount rate should be 8% (Excel-aligned)
    try:
        assert df["Discount_Rate_Annual"].iloc[0] == 0.08
        print("✅ Test 1: Discount rate is 8% (Excel-aligned)")
    except AssertionError:
        print(f"❌ Test 1: Expected 8%, got {df['Discount_Rate_Annual'].iloc[0]*100}%")
        return False

    # Test 2: CAPEX should be ~$1.46B (Excel-aligned)
    try:
        capex = df["Total_CAPEX_USD"].iloc[0]
        assert abs(capex - 1460000000) < 100000000  # ±$100M tolerance
        print("✅ Test 2: CAPEX is ~$1.46B (Excel-aligned)")
    except AssertionError:
        print(f"❌ Test 2: Expected ~$1.46B, got ${capex:,.0f}")
        return False

    # Test 3: NPV should be negative (realistic for this project)
    try:
        npv = df["NPV_rate"].iloc[0]
        assert npv < 0
        print("✅ Test 3: NPV is negative (realistic)")
    except AssertionError:
        print(f"❌ Test 3: Expected negative NPV, got ${npv:,.2f}")
        return False

    # Test 4: Field name should be correct
    try:
        field_name = df["Field_Name"].iloc[0]
        assert field_name == "goa_jack_stmalo"
        print("✅ Test 4: Field name is correct")
    except AssertionError:
        print(f"❌ Test 4: Expected 'goa_jack_stmalo', got '{field_name}'")
        return False

    # Test 5: Should have Notes column with Excel alignment info
    try:
        if "Notes" in df.columns:
            notes = df["Notes"].iloc[0]
            assert "Excel-aligned" in notes
            print("✅ Test 5: Notes indicate Excel alignment")
        else:
            print("⚠️  Test 5: Notes column missing (optional)")
    except AssertionError:
        print("❌ Test 5: Notes don't indicate Excel alignment")

    print(
        "\n🎉 All core tests passed! Manual analysis is now aligned with Excel approach."
    )
    return True


if __name__ == "__main__":
    test_refactored_npv()
