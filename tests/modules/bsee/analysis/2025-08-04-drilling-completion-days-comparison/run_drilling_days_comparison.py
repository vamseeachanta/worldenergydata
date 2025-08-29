#!/usr/bin/env python3
"""
Simple script to demonstrate the drilling days comparison functionality.

This script runs the comparison test and generates a markdown report
showing the differences between the two drilling days calculation methods.
"""

import os
import sys
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from drilling_days_comparison_test import DrillingDaysComparisonTest

def main():
    """
    Main function to run the drilling days comparison and generate report.
    """
    print("=" * 60)
    print("DRILLING DAYS COMPARISON DEMONSTRATION")
    print("=" * 60)
    print()
    
    try:
        # Initialize the comparison test framework
        print("1. Initializing comparison test framework...")
        comparison_test = DrillingDaysComparisonTest()
        
        # Run the full comparison with markdown report generation
        print("2. Running comparison between both methods...")
        print("   This may take a few minutes to execute both analysis methods...")
        print()
        
        results = comparison_test.run_full_comparison_with_report()
        
        if not results.get('success', False):
            print(f"❌ Comparison failed: {results.get('error', 'Unknown error')}")
            return
        
        # Display results
        print("3. ✅ Comparison completed successfully!")
        print()
        
        # Summary information
        summary = results.get('summary', {})
        print("📊 COMPARISON SUMMARY:")
        print(f"   • Method 1 (Lease Number): {summary.get('method1_records', 0)} records")
        print(f"   • Method 2 (API12 Number): {summary.get('method2_records', 0)} records")
        print()
        
        # Report information
        report_path = results.get('markdown_report_path')
        if report_path:
            print(f"📄 MARKDOWN REPORT GENERATED:")
            print(f"   • File: {report_path}")
            print(f"   • Size: {os.path.getsize(report_path)} bytes")
            print()
            
            # Show preview of the report
            print("📋 REPORT PREVIEW:")
            print("-" * 50)
            
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                preview_lines = lines[:25]  # First 25 lines
                
                for line in preview_lines:
                    print(line.rstrip())
                
                if len(lines) > 25:
                    print("... (report continues)")
            
            print("-" * 50)
            print()
        
        # Comparison statistics
        comparison_df = results.get('comparison_df')
        if comparison_df is not None and len(comparison_df) > 0:
            status_counts = comparison_df['status'].value_counts()
            print("📈 COMPARISON STATISTICS:")
            for status, count in status_counts.items():
                status_desc = {
                    'OK': 'Within acceptable thresholds',
                    'REVIEW': 'Exceeding thresholds, require review',
                    'ERROR': 'Missing data or calculation errors'
                }.get(status, 'Unknown status')
                print(f"   • {status}: {count} records ({status_desc})")
            print()
        
        print("🎯 KEY DELIVERABLE ACHIEVED:")
        print("   ✓ Both drilling days methods executed successfully")
        print("   ✓ Output files compared and analyzed")
        print("   ✓ Markdown comparison table generated")
        print("   ✓ Key columns compared: API12, drilling days, completion days")
        print("   ✓ Discrepancies identified and flagged")
        print()
        
        print("=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during comparison: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()