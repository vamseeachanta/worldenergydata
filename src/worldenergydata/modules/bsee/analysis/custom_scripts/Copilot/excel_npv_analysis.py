#!/usr/bin/env python3
"""
NPV Analysis for JStM WELL Production Data
Reads the Excel file and calculates NPV from the data within it
"""

import pandas as pd
import numpy_financial as npf
import os

def read_excel_with_detailed_analysis(file_path):
    """
    Read Excel file and perform detailed analysis of each sheet
    """
    try:
        xl_file = pd.ExcelFile(file_path)
        print(f"Available sheets: {xl_file.sheet_names}")
        
        sheets_analysis = {}
        for sheet_name in xl_file.sheet_names:
            
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
            
            # Clean the dataframe
            df = df.dropna(how='all')  # Remove completely empty rows
            df = df.dropna(axis=1, how='all')  # Remove completely empty columns
            
            # Look for numerical data
            numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            print(f"Numerical columns: {numerical_cols[:10]}...")  # Show first 10
            
            # Scan for potential financial keywords in the data
            financial_keywords = ['npv', 'irr', 'discount', 'rate', 'cost', 'capex', 'opex', 
                                'revenue', 'price', 'brent', 'oil', 'production', 'barrel', 
                                'investment', 'cash', 'flow', 'million', 'billion']
            
            # Check cell values for financial data
            financial_data_found = []
            for idx, row in df.iterrows():
                for col in df.columns:
                    cell_value = str(row[col]).lower() if pd.notna(row[col]) else ''
                    for keyword in financial_keywords:
                        if keyword in cell_value:
                            financial_data_found.append({
                                'row': idx,
                                'col': col,
                                'value': row[col],
                                'keyword': keyword
                            })
            
            if financial_data_found:
                print(f"Found {len(financial_data_found)} cells with financial keywords:")
                for item in financial_data_found[:10]:  # Show first 10
                    print(f"  Row {item['row']}, Col {item['col']}: {item['value']} (keyword: {item['keyword']})")
            
            # Look for NPV or discount rate values
            npv_data = []
            rate_data = []
            
            for col in df.columns:
                try:
                    numeric_col = pd.to_numeric(df[col], errors='coerce')
                    
                    # Look for NPV values (typically large numbers, could be negative)
                    potential_npv = numeric_col[(numeric_col.abs() > 1000000) & (numeric_col.abs() < 1e12)]
                    if not potential_npv.empty:
                        for val in potential_npv.dropna():
                            npv_data.append({'column': col, 'value': val, 'type': 'Large NPV-like value'})
                    
                    # Look for discount rates (between 0 and 1 or small percentages)
                    potential_rates = numeric_col[(numeric_col > 0) & (numeric_col < 1)]
                    if not potential_rates.empty:
                        for val in potential_rates.dropna():
                            rate_data.append({'column': col, 'value': val, 'type': 'Decimal rate'})
                    
                    # Look for percentage rates (between 1 and 50)
                    potential_pct_rates = numeric_col[(numeric_col >= 1) & (numeric_col <= 50)]
                    if not potential_pct_rates.empty:
                        for val in potential_pct_rates.dropna():
                            rate_data.append({'column': col, 'value': val, 'type': 'Percentage rate'})
                
                except Exception:
                    continue
            
            display_df = df.iloc[:5, :min(10, len(df.columns))]
            non_empty_cols = []
            for col in display_df.columns:
                if not display_df[col].isna().all():
                    non_empty_cols.append(col)
            
            if non_empty_cols:
                print(display_df[non_empty_cols[:5]].to_string())
            
            sheets_analysis[sheet_name] = {
                'dataframe': df,
                'financial_data': financial_data_found,
                'npv_data': npv_data,
                'rate_data': rate_data,
                'numerical_columns': numerical_cols
            }
        
        return sheets_analysis
    
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None
        

def extract_npv_from_sheets(sheets_analysis):
    """
    Extract NPV calculations from the analyzed sheets
    """
    npv_results = {}
    
    for sheet_name, analysis in sheets_analysis.items():
        print(f"\n{'='*50}")
        print(f"NPV EXTRACTION FROM SHEET: {sheet_name}")
        print(f"{'='*50}")
        
        df = analysis['dataframe']
        npv_data = analysis['npv_data']
        rate_data = analysis['rate_data']
        
        # Look for explicit NPV values in the data
        if npv_data:
            print("Found potential NPV values:")
            for npv_item in npv_data:
                print(f"  NPV: ${npv_item['value']:,.2f} (from column: {npv_item['column']})")
        
        # Look for discount rates
        discount_rate = 0.08  # Default
        if rate_data:
            print("Found potential discount rates:")
            for rate_item in rate_data:
                rate_val = rate_item['value']
                if rate_item['type'] == 'Percentage rate':
                    rate_val = rate_val / 100
                print(f"  Rate: {rate_val:.4f} ({rate_val*100:.2f}%) from column: {rate_item['column']}")
                discount_rate = rate_val  # Use the last found rate
        
        # Try to find cash flow data for NPV calculation
        cash_flows = []
        
        # Look for time series data that could represent cash flows
        for col in df.columns:
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce').dropna()
                
                # Check if this could be a cash flow series
                if len(numeric_col) > 3:  # At least 4 data points
                    # Check for mix of positive and negative values (typical for cash flows)
                    pos_count = (numeric_col > 0).sum()
                    neg_count = (numeric_col < 0).sum()
                    
                    if pos_count > 0 and neg_count > 0:
                        cash_flows.append({
                            'column': col,
                            'values': numeric_col.tolist(),
                            'positive_count': pos_count,
                            'negative_count': neg_count
                        })
            except Exception:
                continue
        
        if cash_flows:
            print(f"\nFound {len(cash_flows)} potential cash flow series:")
            for i, cf in enumerate(cash_flows[:3]):  # Show first 3
                print(f"  Series {i+1} (Column: {cf['column']}): {len(cf['values'])} periods")
                print(f"    Sample values: {cf['values'][:5]}...")
                
                # Calculate NPV for this series
                try:
                    npv_calc = npf.npv(discount_rate, cf['values'])
                    print(f"    Calculated NPV @ {discount_rate*100:.1f}%: ${npv_calc:,.2f}")
                    
                    npv_results[f"{sheet_name}_series_{i+1}"] = {
                        'npv': npv_calc,
                        'discount_rate': discount_rate,
                        'cash_flows': cf['values'],
                        'source_column': cf['column']
                    }
                except Exception as e:
                    print(f"    Error calculating NPV: {e}")
        
        # If we found explicit NPV values, record them
        if npv_data:
            for i, npv_item in enumerate(npv_data):
                npv_results[f"{sheet_name}_explicit_npv_{i+1}"] = {
                    'npv': npv_item['value'],
                    'discount_rate': discount_rate,
                    'source_column': npv_item['column'],
                    'note': 'Explicit NPV value found in data'
                }
    
    return npv_results

def main():
    file_path = r"docs\modules\bsee\data\JStM-WELL-Production-Data-thru-2019.xlsx"
    
    print(f"Reading Excel file: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return
    
    # Analyze the Excel file in detail
    sheets_analysis = read_excel_with_detailed_analysis(file_path)
    
    if sheets_analysis is None:
        print("Failed to read Excel file")
        return
    
    # Extract NPV data
    npv_results = extract_npv_from_sheets(sheets_analysis)

if __name__ == "__main__":
    main()
