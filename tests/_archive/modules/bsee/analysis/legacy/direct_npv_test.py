#!/usr/bin/env python3
"""
Direct NPV test to verify the current analysis
"""

import os
import sys

sys.path.insert(0, "../../../../")

from assetutilities.common.yml_utilities import ymlInput
from src.worldenergydata.bsee.analysis.production_api12 import Bsee_Production_API12


def main():
    print("=== DIRECT NPV CALCULATION TEST ===\n")

    # Load configuration
    print("📋 Loading configuration...")
    cfg = ymlInput("query_field_jack_stmalo_npv.yml")
    print(f"   Field: {cfg['meta'].get('label', 'Unknown')}")
    print(f"   Discount Rate: {cfg['economics']['cost']['discount_rate_annual']}")
    print(f"   OPEX per BBL: ${cfg['economics']['cost']['OPEX']}")
    print()

    # Initialize and run NPV calculation
    print("🔧 Running NPV calculation...")
    obj = Bsee_Production_API12()

    try:
        result = obj.perform_npv_calculation(cfg)
        print("   ✅ NPV calculation completed successfully")
        print()

        if result:
            print("📊 NPV RESULTS:")
            for key, value in result.items():
                if "npv" in key.lower():
                    print(f"   {key}: ${value:,.2f}")
                else:
                    print(f"   {key}: {value}")
            print()

        # Check if files were created
        results_dir = "results"
        npv_file = os.path.join(results_dir, "npv_summary.csv")
        cashflow_file = os.path.join(results_dir, "monthly_cashflows.csv")

        print("📁 CHECKING OUTPUT FILES:")
        if os.path.exists(npv_file):
            print(f"   ✅ NPV summary file created: {npv_file}")
            import pandas as pd

            df = pd.read_csv(npv_file)
            print(f"      NPV: ${df['NPV_rate'].iloc[0]:,.2f}")
            print(f"      Discount Rate: {df['Discount_Rate_Annual'].iloc[0]*100:.1f}%")
            print(f"      CAPEX: ${df['Total_CAPEX_USD'].iloc[0]:,.0f}")
        else:
            print(f"   ❌ NPV summary file not found: {npv_file}")

        if os.path.exists(cashflow_file):
            print(f"   ✅ Cash flows file created: {cashflow_file}")
        else:
            print(f"   ❌ Cash flows file not found: {cashflow_file}")

    except Exception as e:
        print(f"   ❌ Error during NPV calculation: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
