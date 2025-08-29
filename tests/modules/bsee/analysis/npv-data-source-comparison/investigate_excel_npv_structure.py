#!/usr/bin/env python3
"""
Investigate Excel NPV structure to find correct data rows
"""

import pandas as pd
import numpy as np
import os

def investigate_excel_structure():
    """Deep investigation of Excel file structure"""
    
    excel_file_path = r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
    sheet_name = "NPV w Mo'ly data chart"
    
    print("="*80)
    print("EXCEL NPV STRUCTURE INVESTIGATION")
    print("="*80)
    
    try:
        # Read Excel with all data
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, engine='openpyxl')
        
        print(f"Excel shape: {df.shape}")
        print(f"\nColumn headers (first row):")
        for col_idx in range(min(10, df.shape[1])):
            print(f"  Col {col_idx}: {df.iloc[0, col_idx]}")
        
        print(f"\nRow labels (first column) - ALL ROWS:")
        for row_idx in range(df.shape[0]):
            label = df.iloc[row_idx, 0]
            if pd.notna(label):
                # Get sample values
                sample_vals = []
                for col in range(2, min(5, df.shape[1])):
                    val = df.iloc[row_idx, col]
                    if pd.notna(val):
                        if isinstance(val, (int, float)):
                            sample_vals.append(f"{val:,.2f}")
                        else:
                            sample_vals.append(str(val))
                
                print(f"  Row {row_idx:2d}: {str(label)[:50]:<50} -> {sample_vals}")
        
        # Now let's look for specific patterns
        print("\n" + "="*80)
        print("SEARCHING FOR KEY DATA PATTERNS")
        print("="*80)
        
        # Look for BRENT or oil price patterns
        print("\nSearching for oil price data...")
        for row_idx in range(df.shape[0]):
            # Check all cells in the row for BRENT or price indicators
            for col_idx in range(df.shape[1]):
                cell_val = df.iloc[row_idx, col_idx]
                if pd.notna(cell_val) and isinstance(cell_val, str):
                    if any(keyword in str(cell_val).upper() for keyword in ['BRENT', 'OIL PRICE', 'PRICE', 'WTI']):
                        print(f"  Found price indicator at Row {row_idx}, Col {col_idx}: {cell_val}")
                        # Show the data in this row
                        data_vals = []
                        for c in range(2, min(10, df.shape[1])):
                            v = df.iloc[row_idx, c]
                            if pd.notna(v) and isinstance(v, (int, float)):
                                data_vals.append(f"{v:.2f}")
                        if data_vals:
                            print(f"    Data: {data_vals}")
        
        # Look for production totals
        print("\nSearching for production total rows...")
        for row_idx in range(df.shape[0]):
            label = df.iloc[row_idx, 0]
            if pd.notna(label):
                label_str = str(label).upper()
                if any(keyword in label_str for keyword in ['TOTAL', 'JSM', 'PRODUCTION', 'BBL', 'MONTHLY']):
                    # Get data range
                    data_vals = []
                    for c in range(2, min(10, df.shape[1])):
                        v = df.iloc[row_idx, c]
                        if pd.notna(v) and isinstance(v, (int, float)):
                            data_vals.append(v)
                    if data_vals:
                        print(f"  Row {row_idx}: {label} -> Min: {min(data_vals):,.0f}, Max: {max(data_vals):,.0f}, Avg: {np.mean(data_vals):,.0f}")
        
        # Check specific rows that we know about
        print("\n" + "="*80)
        print("CHECKING SPECIFIC ROWS")
        print("="*80)
        
        # Row 2 - Previously thought to be BRENT
        print("\nRow 2 (suspected BRENT):")
        row_2_data = []
        for c in range(2, min(20, df.shape[1])):
            v = df.iloc[2, c]
            if pd.notna(v):
                row_2_data.append(f"{v}")
        print(f"  Data: {row_2_data}")
        
        # Row 4 - Currently set as oil_prices
        print("\nRow 4 (current oil_prices):")
        row_4_data = []
        for c in range(2, min(20, df.shape[1])):
            v = df.iloc[4, c]
            if pd.notna(v):
                row_4_data.append(f"{v}")
        print(f"  Data: {row_4_data}")
        
        # Row 22 - JSM Total production
        print("\nRow 22 (JSM Total):")
        row_22_data = []
        for c in range(2, min(20, df.shape[1])):
            v = df.iloc[22, c]
            if pd.notna(v) and isinstance(v, (int, float)):
                row_22_data.append(f"{v:,.0f}")
        print(f"  Data: {row_22_data}")
        
        # Look at the second sheet if exists
        print("\n" + "="*80)
        print("CHECKING OTHER SHEETS")
        print("="*80)
        
        # Get all sheet names
        xl_file = pd.ExcelFile(excel_file_path)
        print(f"Available sheets: {xl_file.sheet_names}")
        
        # Check if there's a data sheet with oil prices
        for sheet in xl_file.sheet_names:
            if any(keyword in sheet.upper() for keyword in ['PRICE', 'BRENT', 'DATA', 'INPUT']):
                print(f"\nChecking sheet: {sheet}")
                df_sheet = pd.read_excel(excel_file_path, sheet_name=sheet, engine='openpyxl')
                print(f"  Shape: {df_sheet.shape}")
                # Look for price data
                for row in range(min(10, df_sheet.shape[0])):
                    for col in range(min(5, df_sheet.shape[1])):
                        val = df_sheet.iloc[row, col]
                        if pd.notna(val) and isinstance(val, str):
                            if any(kw in str(val).upper() for kw in ['BRENT', 'PRICE', 'OIL']):
                                print(f"  Found: Row {row}, Col {col}: {val}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_excel_structure()