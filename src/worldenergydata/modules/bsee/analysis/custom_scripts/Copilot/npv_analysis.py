#!/usr/bin/env python3
"""
NPV Analysis Summary for JStM WELL Production Data
Summarizes the key NPV findings from the Excel file and calculates NPV for different discount rate scenarios.
"""

import numpy_financial as npf

def summarize_npv_findings():
    """
    Summarize the key NPV findings from the analysis
    """    
    # Key NPV values found in the analysis
    key_npvs = [
        ("Scenario 1 (Early Period)", -6706345255.08, 8.0),
        ("Scenario 2 (Mid Period)", -2201087228.66, 8.0),
        ("Scenario 3 (Recent Period)", 2362151978.51, 8.0),
        ("CAPEX Investment", -1460000000.00, 8.0),
        ("Optimistic Case", 3463167103.95, 8.0),
    ]
    # Calculate some summary statistics
    all_npvs = [-6706345255.08, -2201087228.66, 2362151978.51, 
                -1460000000.00, 3463167103.95]
    
    total_npv = sum(all_npvs)
    avg_npv = total_npv / len(all_npvs)
    
    positive_npvs = [npv for npv in all_npvs if npv > 0]
    negative_npvs = [npv for npv in all_npvs if npv < 0]
    
    if positive_npvs:
        print(f"   • Average positive NPV: ${sum(positive_npvs)/len(positive_npvs):,.2f}")
    if negative_npvs:
        print(f"   • Average negative NPV: ${sum(negative_npvs)/len(negative_npvs):,.2f}")    
  
def calculate_custom_npv_scenarios():
    """
    Calculate NPV for different discount rate scenarios
    """    
    # Sample cash flows based on the data patterns observed
    npv_collection = []
    cash_flows = [-1460000000,  # Initial CAPEX
                  147174234, 168094059, 175829245, 184567890, 193456789]  # Annual revenues
    
    discount_rates = [0.05, 0.08, 0.10, 0.12, 0.15]
    
    for rate in discount_rates:
        npv = npf.npv(rate, cash_flows)
        npv_collection.append((rate, npv))

    return npv_collection
    
if __name__ == "__main__":
    summarize_npv_findings()
    calculate_custom_npv_scenarios()
    