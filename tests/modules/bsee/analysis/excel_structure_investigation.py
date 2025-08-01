#!/usr/bin/env python3
"""
Excel Structure Investigation

Detailed analysis of the Excel NPV file to find the exact production data
used in the benchmark calculations.
"""

import pandas as pd
import numpy as np
import os

def investigate_excel_structure():
    """Investigate Excel file structure to find production data"""
    
    excel_file_path = r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
    sheet_name = "NPV w Mo'ly data chart"
    
    print("="*80)
    print("EXCEL STRUCTURE INVESTIGATION")
    print("="*80)
    
    try:
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, engine='openpyxl')
        print(f"Excel file shape: {df.shape}")
        print(f"Columns: {len(df.columns)}")
        print(f"Rows: {len(df)}")
        
        print(f"\n=== COLUMN ANALYSIS ===")
        for i, col in enumerate(df.columns):
            print(f"Column {i:2d}: {col}")
        
        print(f"\n=== ROW-BY-ROW ANALYSIS ===")
        for row_idx in range(min(20, len(df))):
            row_data = df.iloc[row_idx, :5].values  # First 5 columns
            row_desc = df.iloc[row_idx, 0] if pd.notna(df.iloc[row_idx, 0]) else "[empty]"
            print(f"Row {row_idx:2d}: {row_desc}")
            
            # Look for numeric data in this row
            numeric_data = []
            for col_idx in range(2, min(df.shape[1], 10)):  # Check columns 2-9
                val = df.iloc[row_idx, col_idx]
                if pd.notna(val) and isinstance(val, (int, float)):
                    numeric_data.append(f"{val:,.1f}")
            
            if numeric_data:
                print(f"         Data sample: {' | '.join(numeric_data)}")
        
        print(f"\n=== SPECIFIC ROW ANALYSIS ===")
        
        # Analyze BRENT prices (confirmed in row 2)
        brent_row = 2
        brent_data = []
        for col_idx in range(2, min(df.shape[1], 60)):
            val = df.iloc[brent_row, col_idx]
            if pd.notna(val) and isinstance(val, (int, float)) and 20 < val < 200:
                brent_data.append(val)
        
        print(f"Row {brent_row} (BRENT): {len(brent_data)} prices")
        print(f"BRENT range: ${min(brent_data):.2f} - ${max(brent_data):.2f}")
        print(f"BRENT sample: {[f'${p:.2f}' for p in brent_data[:5]]}")
        
        # Look for production data in other rows
        print(f"\n=== PRODUCTION DATA SEARCH ===")
        for row_idx in range(3, min(15, len(df))):
            row_label = str(df.iloc[row_idx, 0])[:50] if pd.notna(df.iloc[row_idx, 0]) else "[empty]"
            
            # Extract numeric data from this row
            numeric_vals = []
            for col_idx in range(2, min(df.shape[1], 60)):
                val = df.iloc[row_idx, col_idx]
                if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                    numeric_vals.append(val)
            
            if len(numeric_vals) > 20:  # Row has substantial data
                print(f"Row {row_idx:2d}: {row_label}")
                print(f"         {len(numeric_vals)} data points")
                print(f"         Range: {min(numeric_vals):,.1f} - {max(numeric_vals):,.1f}")
                print(f"         Sample: {[f'{v:,.0f}' for v in numeric_vals[:5]]}")
                
                # Calculate potential revenue with BRENT prices
                if len(numeric_vals) >= len(brent_data):
                    prod_sample = numeric_vals[:len(brent_data)]
                    revenue_sample = [p * b for p, b in zip(prod_sample[:5], brent_data[:5])]
                    total_revenue = sum(p * b for p, b in zip(prod_sample, brent_data))
                    print(f"         Revenue test: ${total_revenue:,.0f} total")
                    print(f"         Revenue sample: {[f'${r:,.0f}' for r in revenue_sample]}")
        
        print(f"\n=== SUMMARY STATISTICS ANALYSIS ===")
        
        # Look for cells that might contain summary statistics matching our benchmarks
        print("Searching for cells with values around our benchmark NPV...")
        target_npv = 2595521294.50  # Excel benchmark
        
        for row_idx in range(len(df)):
            for col_idx in range(len(df.columns)):
                val = df.iloc[row_idx, col_idx]
                if pd.notna(val) and isinstance(val, (int, float)):
                    if abs(abs(val) - target_npv) < target_npv * 0.1:  # Within 10%
                        print(f"Found potential NPV at Row {row_idx}, Col {col_idx}: {val:,.2f}")
        
        print(f"\n=== DATA EXTRACTION RECOMMENDATIONS ===")
        print("Based on analysis:")
        print("1. BRENT prices: Row 2, Columns 2-57 ✓ (confirmed)")
        print("2. Production data: Investigate rows 3-10 with substantial numeric data")
        print("3. Check if production data needs scaling (current values seem low)")
        print("4. Verify time period alignment between prices and production")
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")

if __name__ == "__main__":
    investigate_excel_structure()