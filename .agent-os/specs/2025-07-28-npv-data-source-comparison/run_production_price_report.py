#!/usr/bin/env python3
"""
Script to run production and prices differences report from project root.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    # Set up paths
    excel_path = os.path.join(os.path.dirname(__file__), 'docs', 'modules', 'bsee', 'data', 'NPV_JStM-WELL-Production-Data-thru-2019.xlsx')
    
    # Check if file exists
    if not os.path.exists(excel_path):
        print(f"Excel file not found at: {excel_path}")
        sys.exit(1)
    
    # Import and run report generator
    from worldenergydata.modules.bsee.analysis.production_price_differences_report import ProductionPriceDifferencesReport
    
    # Generate report with explicit path
    report_generator = ProductionPriceDifferencesReport(excel_path=excel_path)
    comprehensive_report = report_generator.generate_complete_report()