#!/usr/bin/env python3
"""
Debug script to examine the Excel file and extract exactly what data should be used
"""

import pandas as pd
import numpy as np

def analyze_excel_file():
    """Analyze the Excel file to understand its structure and data"""
    file_path = r"docs\modules\bsee\data\JStM-WELL-Production-Data-thru-2019.xlsx"
    
    print("=== EXCEL FILE ANALYSIS ===")
    
    # Read the Excel file
    excel_file = pd.ExcelFile(file_path)
    print(f"Available sheets: {excel_file.sheet_names}")
    
    # Read the main NPV sheet
    df = pd.read_excel(file_path, sheet_name="NPV w Mo'ly data chart", engine='openpyxl')
    print(f"\nDataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)[:10]}...")
    
    # Look for the key data we need
    print("\n=== SEARCHING FOR OIL PRODUCTION DATA ===")
    
    # Search for monthly oil production values
    for i in range(min(20, df.shape[0])):
        for j, col in enumerate(df.columns):
            cell_val = df.iloc[i, j]
            if pd.notna(cell_val) and isinstance(cell_val, (int, float)):
                if 10000 < cell_val < 1000000:  # Likely production values in barrels
                    print(f"Row {i}, Col '{col}': {cell_val:,.0f} (potential production)")
    
    print("\n=== SEARCHING FOR REVENUE/PRICE DATA ===")
    
    # Search for revenue or price information
    for i in range(min(20, df.shape[0])):
        for j, col in enumerate(df.columns):
            cell_val = df.iloc[i, j]
            if pd.notna(cell_val):
                cell_str = str(cell_val).lower()
                if any(keyword in cell_str for keyword in ['revenue', 'price', 'brent', '$']):
                    print(f"Row {i}, Col '{col}': {cell_val}")
    
    print("\n=== SEARCHING FOR CAPEX/COST DATA ===")
    
    # Search for CAPEX information
    for i in range(min(20, df.shape[0])):
        for j, col in enumerate(df.columns):
            cell_val = df.iloc[i, j]
            if pd.notna(cell_val):
                cell_str = str(cell_val).lower()
                if any(keyword in cell_str for keyword in ['capex', 'cost', 'investment', 'facility']):
                    print(f"Row {i}, Col '{col}': {cell_val}")
    
    print("\n=== EXAMINING COLUMN HEADERS ===")
    
    # Print column headers with their indices
    for i, col in enumerate(df.columns):
        print(f"Col {i}: '{col}'")
        if i > 15:  # Limit output
            print("... (truncated)")
            break
    
    print("\n=== EXAMINING FIRST FEW ROWS OF DATA ===")
    
    # Print first few rows
    for i in range(min(5, df.shape[0])):
        print(f"\nRow {i}:")
        for j in range(min(10, df.shape[1])):
            cell_val = df.iloc[i, j]
            if pd.notna(cell_val):
                print(f"  Col {j} ({df.columns[j]}): {cell_val}")

if __name__ == "__main__":
    analyze_excel_file()
