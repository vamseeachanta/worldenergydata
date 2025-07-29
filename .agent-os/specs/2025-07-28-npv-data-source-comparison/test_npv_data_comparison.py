#!/usr/bin/env python3
"""
Test script to run NPV data comparison from project root.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from worldenergydata.modules.bsee.analysis.npv_data_comparison import main

if __name__ == "__main__":
    # Run with absolute path to Excel file
    excel_path = os.path.join(os.path.dirname(__file__), 'docs', 'modules', 'bsee', 'data', 'NPV_JStM-WELL-Production-Data-thru-2019.xlsx')
    
    # Check if file exists
    if os.path.exists(excel_path):
        print(f"Excel file found at: {excel_path}")
    else:
        print(f"Excel file not found at: {excel_path}")
        sys.exit(1)
    
    # Import and modify the main function to use our path
    from worldenergydata.modules.bsee.analysis.npv_data_comparison import NPVDataComparison
    
    print("=" * 80)
    print("NPV DATA SOURCE COMPARISON ANALYSIS")
    print("=" * 80)
    
    # Initialize comparison tool with explicit path
    comparison_tool = NPVDataComparison(excel_path)
    
    # Extract Excel data
    excel_data = comparison_tool.extract_excel_data()
    
    # Extract manual data (would be implemented to extract from BSEE)
    manual_data = comparison_tool.extract_manual_data()
    
    # Perform comparison
    comparison_results = comparison_tool.compare_data_sources(excel_data, manual_data)
    
    # Generate visualizations
    comparison_tool.generate_visual_comparison(excel_data)
    
    # Save report
    comparison_tool.save_comparison_report(comparison_results)
    
    # Print summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    if 'production_analysis' in comparison_results:
        prod = comparison_results['production_analysis']
        print(f"\nProduction Data (Excel):")
        print(f"  - Periods: {prod.get('count', 0)}")
        print(f"  - Average: {prod.get('average', 0):,.0f} BBL/period")
        print(f"  - Total: {prod.get('total', 0):,.0f} BBL")
        print(f"  - Coefficient of Variation: {prod.get('coefficient_of_variation', 0):.2%}")
    
    if 'price_analysis' in comparison_results:
        price = comparison_results['price_analysis']
        print(f"\nOil Price Data (Excel):")
        print(f"  - Average Price: ${price.get('average', 0):.2f}/BBL")
        print(f"  - Price Range: ${price.get('min', 0):.2f} - ${price.get('max', 0):.2f}/BBL")
        print(f"  - Volatility: {price.get('volatility', 0):.2%}")
    
    if 'revenue_potential' in comparison_results:
        rev = comparison_results['revenue_potential']
        print(f"\nRevenue Potential (Excel):")
        print(f"  - Total Revenue: ${rev.get('total_revenue', 0):,.0f}")
        print(f"  - Average per Period: ${rev.get('average_revenue_per_period', 0):,.0f}")
    
    print("\n" + "=" * 80)