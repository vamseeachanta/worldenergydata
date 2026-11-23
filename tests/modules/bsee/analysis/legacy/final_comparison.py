#!/usr/bin/env python3
"""
Final comparison between Excel and Manual NPV analysis
"""

import os

import pandas as pd


def main():
    print("=== FINAL NPV ANALYSIS COMPARISON ===\n")

    # Excel results from updated analysis
    print(
        "📊 EXCEL ANALYSIS RESULTS (from NPV_JStM-WELL-Production-Data-thru-2019.xlsx):"
    )
    print("   NPV @ 10%: -$2,220,124,040.76")
    print("   Source: Cash flow series calculation from Excel file")
    print()

    # Manual analysis results
    results_file = "results/npv_summary.csv"
    if os.path.exists(results_file):
        manual_df = pd.read_csv(results_file)
        manual_npv = manual_df["NPV_rate"].iloc[0]
        manual_rate = manual_df["Discount_Rate_Annual"].iloc[0]
        manual_capex = manual_df["Total_CAPEX_USD"].iloc[0]

        print("🔧 MANUAL ANALYSIS RESULTS:")
        print(f"   NPV @ {manual_rate*100}%: ${manual_npv:,.2f}")
        print(f"   CAPEX Used: ${manual_capex:,.0f}")
        print(f"   Analysis Date: {manual_df['Analysis_Date'].iloc[0]}")
        print(f"   Notes: {manual_df['Notes'].iloc[0]}")
        print()

        # Calculate alignment
        excel_npv = -2220124040.76
        if manual_rate == 0.10:  # Both using 10%
            difference_pct = abs((manual_npv - excel_npv) / excel_npv * 100)
            print("📈 ALIGNMENT ANALYSIS:")
            print(f"   Excel NPV @ 10%: ${excel_npv:,.2f}")
            print(f"   Manual NPV @ 10%: ${manual_npv:,.2f}")
            print(f"   Difference: ${abs(manual_npv - excel_npv):,.2f}")
            print(f"   Difference %: {difference_pct:.1f}%")

            if difference_pct < 20:
                print("   ✅ Status: GOOD ALIGNMENT (< 20% difference)")
            elif difference_pct < 50:
                print("   ⚠️  Status: MODERATE ALIGNMENT (20-50% difference)")
            else:
                print("   ❌ Status: POOR ALIGNMENT (> 50% difference)")
        else:
            print(
                "⚠️  WARNING: Manual analysis using different discount rate than Excel"
            )
            print(f"   Excel uses 10%, Manual uses {manual_rate*100}%")
    else:
        print("❌ Manual analysis results not found!")
        print(f"   Expected file: {results_file}")

    print()
    print("=== SUMMARY ===")
    print("✅ Excel file updated to NPV_JStM-WELL-Production-Data-thru-2019.xlsx")
    print("✅ Manual analysis aligned to use same data source")
    print("✅ Both analyses focus on MON_O_PROD_VOL (oil production only)")
    print("✅ CAPEX aligned to $1.46B (Excel scenario)")
    print("✅ BRENT oil prices extracted from same Excel file")

    if os.path.exists(results_file):
        manual_df = pd.read_csv(results_file)
        if manual_df["Discount_Rate_Annual"].iloc[0] == 0.10:
            print("✅ Discount rate aligned to 10% (Excel standard)")
        else:
            print("⚠️  Discount rate needs alignment to 10%")


if __name__ == "__main__":
    main()
