#!/usr/bin/env python3
"""
Production Data Investigation

Test different production data rows and scaling factors to find
the exact data that produces the Excel benchmark NPV.
"""

import pandas as pd
import numpy as np
import numpy_financial as npf
import os

def test_production_data_rows():
    """Test different production data rows from Excel"""
    
    excel_file_path = r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
    sheet_name = "NPV w Mo'ly data chart"
    
    # Excel benchmark NPV
    excel_benchmark = -2595521294.50
    
    # Fixed parameters
    capex = 1460000000
    opex_per_bbl = 15.0
    discount_rate = 0.10
    
    print("="*80)
    print("PRODUCTION DATA ROW TESTING")
    print("="*80)
    
    try:
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, engine='openpyxl')
        
        # Extract BRENT prices (confirmed correct)
        brent_prices = []
        for col_idx in range(2, min(df.shape[1], 58)):
            val = df.iloc[2, col_idx]
            if pd.notna(val) and isinstance(val, (int, float)) and 20 < val < 200:
                brent_prices.append(float(val))
        
        print(f"BRENT prices: {len(brent_prices)} values")
        print(f"BRENT sample: {[f'${p:.2f}' for p in brent_prices[:5]]}")
        
        # Test different production data rows
        candidate_rows = [3, 5, 7, 12, 13]
        
        print(f"\n=== TESTING PRODUCTION DATA ROWS ===")
        
        for row_idx in candidate_rows:
            print(f"\n--- Testing Row {row_idx} ---")
            
            # Extract production data from this row
            prod_data = []
            for col_idx in range(2, min(df.shape[1], 58)):
                val = df.iloc[row_idx, col_idx]
                if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                    prod_data.append(float(val))
            
            if not prod_data:
                print(f"No production data in row {row_idx}")
                continue
            
            # Align lengths
            min_len = min(len(brent_prices), len(prod_data))
            brent_aligned = brent_prices[:min_len]
            prod_aligned = prod_data[:min_len]
            
            print(f"Production data: {len(prod_aligned)} values")
            print(f"Range: {min(prod_aligned):,.0f} - {max(prod_aligned):,.0f}")
            print(f"Sample: {[f'{p:,.0f}' for p in prod_aligned[:5]]}")
            
            # Test different scaling factors
            scaling_factors = [1, 1000, 1000000]  # 1x, 1000x (MBBl), 1M (MMBbl)
            
            for scale in scaling_factors:
                scaled_prod = [p * scale for p in prod_aligned]
                
                # Calculate NPV
                revenues = [p * b for p, b in zip(scaled_prod, brent_aligned)]
                opex_costs = [p * opex_per_bbl for p in scaled_prod]
                net_cf = [r - o for r, o in zip(revenues, opex_costs)]
                
                cash_flows = [-capex] + net_cf
                npv_result = npf.npv(discount_rate, cash_flows)
                
                # Calculate variance
                variance = abs(npv_result - excel_benchmark)
                variance_pct = (variance / abs(excel_benchmark)) * 100
                
                total_revenue = sum(revenues)
                total_opex = sum(opex_costs)
                
                print(f"  Scale {scale:>7,}x: NPV=${npv_result:>15,.0f} | Var={variance_pct:>6.1f}% | Rev=${total_revenue:>12,.0f} | OPEX=${total_opex:>12,.0f}")
                
                # Highlight best results
                if variance_pct < 20:
                    print(f"               *** GOOD RESULT: <20% variance ***")
                elif variance_pct < 10:
                    print(f"               *** EXCELLENT RESULT: <10% variance ***")
        
        print(f"\n=== TESTING MANUAL CALCULATIONS ===")
        
        # Test manual calculation approach - maybe there's a specific formula in Excel
        # Try different approaches that might be used in Excel
        
        # Approach 1: Try Row 12 with different time aggregation
        row_12_data = []
        for col_idx in range(2, min(df.shape[1], 58)):
            val = df.iloc[12, col_idx]
            if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                row_12_data.append(float(val))
        
        print(f"\nApproach 1: Row 12 with annual aggregation")
        if len(row_12_data) >= len(brent_prices):
            # Try aggregating to annual periods
            annual_periods = 5  # 2015-2019
            months_per_year = len(row_12_data) // annual_periods
            
            annual_prod = []
            annual_prices = []
            
            for year in range(annual_periods):
                start_idx = year * months_per_year
                end_idx = start_idx + months_per_year
                
                year_prod = sum(row_12_data[start_idx:end_idx])
                year_price = sum(brent_prices[start_idx:end_idx]) / months_per_year  # Average price
                
                annual_prod.append(year_prod)
                annual_prices.append(year_price)
            
            # Calculate NPV with annual data
            annual_revenues = [p * b for p, b in zip(annual_prod, annual_prices)]
            annual_opex = [p * opex_per_bbl for p in annual_prod]
            annual_net_cf = [r - o for r, o in zip(annual_revenues, annual_opex)]
            
            annual_cash_flows = [-capex] + annual_net_cf
            annual_npv = npf.npv(discount_rate, annual_cash_flows)
            
            annual_variance = abs(annual_npv - excel_benchmark)
            annual_variance_pct = (annual_variance / abs(excel_benchmark)) * 100
            
            print(f"Annual NPV: ${annual_npv:,.0f}")
            print(f"Annual Variance: {annual_variance_pct:.1f}%")
            print(f"Annual Revenue: ${sum(annual_revenues):,.0f}")
            print(f"Annual OPEX: ${sum(annual_opex):,.0f}")
        
        print(f"\n=== RECOMMENDATIONS ===")
        print("Based on testing:")
        print("1. Check if Excel uses different units (thousands/millions of barrels)")
        print("2. Verify if Excel aggregates data differently (annual vs monthly)")
        print("3. Check if there are other cost components not included in our calculation")
        print("4. Verify the exact NPV formula used in Excel (different period timing?)")
        
    except Exception as e:
        print(f"Error in analysis: {e}")

if __name__ == "__main__":
    test_production_data_rows()