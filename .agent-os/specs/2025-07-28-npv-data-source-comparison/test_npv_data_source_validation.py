"""
Tests for NPV data source validation and comparison.
This module compares Excel benchmark data with manual analysis data sources.
"""

import pytest
import pandas as pd
import numpy as np
import numpy_financial as npf
import os
import sys
from typing import Dict, List, Tuple

# Add src to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from worldenergydata.modules.bsee.analysis.excel_data_extractor import ExcelDataExtractor


class TestNPVDataSourceValidation:
    """Test suite for validating NPV data sources."""
    
    @pytest.fixture
    def excel_extractor(self):
        """Create Excel data extractor."""
        excel_path = r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
        return ExcelDataExtractor(excel_path)
    
    @pytest.fixture
    def excel_data(self, excel_extractor):
        """Extract Excel benchmark data."""
        production = excel_extractor.extract_production_data(row_index=22)
        prices = excel_extractor.extract_oil_prices(row_index=4)
        return excel_extractor.align_data(production, prices)
    
    def test_excel_data_characteristics(self, excel_data):
        """Test Excel data characteristics match expected values."""
        # From our analysis:
        # - 55 periods of data
        # - Average production: 33,938 BBL/period
        # - Average price: $56.60/BBL
        
        assert excel_data['periods'] == 55, f"Expected 55 periods, got {excel_data['periods']}"
        
        avg_production = np.mean(excel_data['production'])
        assert 33000 < avg_production < 35000, f"Average production {avg_production:.0f} outside expected range"
        
        avg_price = np.mean(excel_data['prices'])
        assert 55 < avg_price < 58, f"Average price ${avg_price:.2f} outside expected range"
        
        # Total revenue should be around $106M
        revenues = [p * price for p, price in zip(excel_data['production'], excel_data['prices'])]
        total_revenue = sum(revenues)
        assert 105_000_000 < total_revenue < 107_000_000, f"Total revenue ${total_revenue:,.0f} outside expected range"
        
        print(f"Excel Data Validation:")
        print(f"  - Periods: {excel_data['periods']}")
        print(f"  - Avg Production: {avg_production:,.0f} BBL/period")
        print(f"  - Avg Price: ${avg_price:.2f}/BBL")
        print(f"  - Total Revenue: ${total_revenue:,.0f}")
    
    def test_npv_calculation_with_excel_data(self, excel_data):
        """Test NPV calculation using Excel data."""
        # Use same parameters as the spec
        capex = 1460000000  # $1.46B
        opex_per_bbl = 15.00  # $15/BBL from YAML config
        discount_rate = 0.10  # 10%
        
        # Calculate cash flows
        cash_flows = []
        for prod, price in zip(excel_data['production'], excel_data['prices']):
            revenue = prod * price
            opex = prod * opex_per_bbl
            net_cf = revenue - opex
            cash_flows.append(net_cf)
        
        # NPV calculation with CAPEX at period 0
        all_cash_flows = [-capex] + cash_flows
        npv = npf.npv(discount_rate, all_cash_flows)
        
        print(f"\nNPV Calculation with Excel Data:")
        print(f"  - CAPEX: ${capex:,.0f}")
        print(f"  - OPEX per BBL: ${opex_per_bbl:.2f}")
        print(f"  - Discount Rate: {discount_rate:.1%}")
        print(f"  - Number of Periods: {len(cash_flows)}")
        print(f"  - Total Net Cash Flow: ${sum(cash_flows):,.0f}")
        print(f"  - NPV Result: ${npv:,.2f}")
        
        # The calculated NPV shows significant variance from Excel benchmark
        # This helps us identify the source of discrepancy
        print(f"  - Variance from Excel benchmark (~-$2.6B): ${npv - (-2600000000):,.0f}")
        print(f"  - Percentage difference: {abs(npv - (-2600000000)) / 2600000000 * 100:.1f}%")
        
        return npv
    
    def test_production_data_scale_analysis(self, excel_data):
        """Analyze production data scale to identify potential differences."""
        production = excel_data['production']
        
        # Check if production values might be daily vs monthly
        daily_to_monthly_factor = 30  # Approximate days per month
        
        # If these are daily values, monthly would be ~30x higher
        avg_prod = np.mean(production)
        monthly_estimate = avg_prod * daily_to_monthly_factor
        
        print(f"\nProduction Scale Analysis:")
        print(f"  - Average Production (as-is): {avg_prod:,.0f} BBL")
        print(f"  - If daily, monthly would be: {monthly_estimate:,.0f} BBL")
        print(f"  - Min Production: {min(production):,.0f} BBL")
        print(f"  - Max Production: {max(production):,.0f} BBL")
        
        # Check if values are reasonable for daily production
        # Typical deepwater wells produce 5,000-50,000 BBL/day
        assert all(5000 < p < 60000 for p in production), "Some production values outside typical daily range"
        
        # This suggests the Excel data is likely daily production
        return 'daily'
    
    def test_cash_flow_component_breakdown(self, excel_data):
        """Break down cash flow components for detailed analysis."""
        capex = 1460000000
        opex_per_bbl = 15.00
        
        components = {
            'periods': [],
            'production': [],
            'prices': [],
            'revenue': [],
            'opex': [],
            'net_cash_flow': []
        }
        
        for i, (prod, price) in enumerate(zip(excel_data['production'], excel_data['prices'])):
            revenue = prod * price
            opex = prod * opex_per_bbl
            net_cf = revenue - opex
            
            components['periods'].append(i + 1)
            components['production'].append(prod)
            components['prices'].append(price)
            components['revenue'].append(revenue)
            components['opex'].append(opex)
            components['net_cash_flow'].append(net_cf)
        
        # Create DataFrame for analysis
        df = pd.DataFrame(components)
        
        # Save detailed breakdown
        output_path = "tests/modules/bsee/analysis/results/excel_cash_flow_breakdown.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        
        print(f"\nCash Flow Component Breakdown:")
        print(f"  - Total Revenue: ${df['revenue'].sum():,.0f}")
        print(f"  - Total OPEX: ${df['opex'].sum():,.0f}")
        print(f"  - Total Net Cash Flow: ${df['net_cash_flow'].sum():,.0f}")
        print(f"  - Average Net CF per Period: ${df['net_cash_flow'].mean():,.0f}")
        print(f"  - Cash flow breakdown saved to: {output_path}")
        
        # First 5 periods
        print("\nFirst 5 Periods:")
        print(df.head().to_string(index=False))
        
        return df
    
    def test_npv_sensitivity_to_data_frequency(self, excel_data):
        """Test NPV sensitivity to daily vs monthly data interpretation."""
        capex = 1460000000
        opex_per_bbl = 15.00
        discount_rate = 0.10
        
        # Scenario 1: Data as daily production (55 days)
        daily_cash_flows = []
        for prod, price in zip(excel_data['production'], excel_data['prices']):
            revenue = prod * price
            opex = prod * opex_per_bbl
            daily_cash_flows.append(revenue - opex)
        
        # Convert daily discount rate (approximate)
        daily_rate = (1 + discount_rate) ** (1/365) - 1
        npv_daily = npf.npv(daily_rate, [-capex] + daily_cash_flows)
        
        # Scenario 2: Data as monthly production (55 months)
        monthly_rate = (1 + discount_rate) ** (1/12) - 1
        npv_monthly = npf.npv(monthly_rate, [-capex] + daily_cash_flows)
        
        # Scenario 3: Convert daily to monthly (aggregate by 30-day periods)
        monthly_aggregated = []
        for i in range(0, len(daily_cash_flows), 30):
            month_total = sum(daily_cash_flows[i:i+30])
            monthly_aggregated.append(month_total)
        
        if monthly_aggregated:
            npv_aggregated = npf.npv(monthly_rate, [-capex] + monthly_aggregated)
        else:
            npv_aggregated = 0
        
        print(f"\nNPV Sensitivity to Data Frequency:")
        print(f"  - NPV (Daily interpretation): ${npv_daily:,.2f}")
        print(f"  - NPV (Monthly interpretation): ${npv_monthly:,.2f}")
        print(f"  - NPV (Daily aggregated to monthly): ${npv_aggregated:,.2f}")
        print(f"  - Difference (Monthly vs Daily): ${npv_monthly - npv_daily:,.2f}")
        
        return {
            'daily': npv_daily,
            'monthly': npv_monthly,
            'aggregated': npv_aggregated
        }
    
    def test_identify_data_source_discrepancies(self, excel_data):
        """Identify specific discrepancies that could cause NPV variance."""
        issues = []
        
        # Check 1: Data period coverage
        if excel_data['periods'] != 60:
            issues.append(f"Period mismatch: Excel has {excel_data['periods']} periods, expected 60 months (5 years)")
        
        # Check 2: Production scale
        avg_prod = np.mean(excel_data['production'])
        if avg_prod < 100000:  # If less than 100k, likely daily not monthly
            issues.append(f"Production scale suggests daily data ({avg_prod:.0f} BBL/day), not monthly")
        
        # Check 3: Price consistency
        price_cv = np.std(excel_data['prices']) / np.mean(excel_data['prices'])
        if price_cv > 0.5:
            issues.append(f"High price volatility (CV={price_cv:.2%}) may indicate data quality issues")
        
        # Check 4: Revenue scale for deepwater field
        total_prod = sum(excel_data['production'])
        total_revenue = sum(p * price for p, price in zip(excel_data['production'], excel_data['prices']))
        if total_revenue < 1_000_000_000:  # Less than $1B over project life
            issues.append(f"Total revenue ${total_revenue:,.0f} seems low for major deepwater field")
        
        print(f"\nIdentified Data Source Discrepancies:")
        if issues:
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("  - No major discrepancies identified")
        
        # Recommendations
        print(f"\nRecommendations for NPV Alignment:")
        print(f"  1. Verify if Excel data represents daily or monthly production")
        print(f"  2. Ensure manual analysis uses same time period aggregation")
        print(f"  3. Confirm OPEX calculation uses same production values")
        print(f"  4. Check if additional months of data exist beyond period 55")
        
        return issues


def test_comprehensive_npv_validation():
    """Run comprehensive NPV data validation."""
    print("\n" + "="*80)
    print("COMPREHENSIVE NPV DATA SOURCE VALIDATION")
    print("="*80)
    
    # Create test instance
    test = TestNPVDataSourceValidation()
    
    # Create data manually (not using fixtures)
    excel_path = r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
    extractor = ExcelDataExtractor(excel_path)
    
    # Extract data
    production = extractor.extract_production_data(row_index=22)
    prices = extractor.extract_oil_prices(row_index=4)
    excel_data = extractor.align_data(production, prices)
    
    # Run all test methods
    print("\n1. Excel Data Characteristics:")
    test.test_excel_data_characteristics(excel_data)
    
    print("\n2. NPV Calculation with Excel Data:")
    npv_result = test.test_npv_calculation_with_excel_data(excel_data)
    
    print("\n3. Production Scale Analysis:")
    scale = test.test_production_data_scale_analysis(excel_data)
    
    print("\n4. Cash Flow Component Breakdown:")
    breakdown = test.test_cash_flow_component_breakdown(excel_data)
    
    print("\n5. NPV Sensitivity Analysis:")
    sensitivity = test.test_npv_sensitivity_to_data_frequency(excel_data)
    
    print("\n6. Data Source Discrepancy Analysis:")
    issues = test.test_identify_data_source_discrepancies(excel_data)
    
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    # Run as standalone script
    test_comprehensive_npv_validation()
    
    # Or run with pytest
    # pytest.main([__file__, "-v"])