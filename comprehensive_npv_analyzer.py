#!/usr/bin/env python3
"""
Comprehensive NPV Analysis for JStM WELL Production Data
Combines custom calculations with Excel data extraction for complete analysis.
"""

import pandas as pd
import numpy_financial as npf
import os
import json
from datetime import datetime
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class JStMNPVAnalyzer:
    def __init__(self):
        self.excel_file = r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
        self.results = {}
        
    def load_excel_data(self):
        """Load and analyze Excel data"""
        if not os.path.exists(self.excel_file):
            print(f"Warning: Excel file not found at {self.excel_file}")
            return None
            
        try:
            df = pd.read_excel(self.excel_file, sheet_name="NPV w Mo'ly data chart", engine='openpyxl')
            return df
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return None
    
    def extract_financial_metrics(self, df):
        """Extract financial metrics from Excel data"""
        if df is None:
            return {}, []
            
        # Find NPV values (large numbers)
        npv_values = []
        discount_rates = set()
        
        for col in df.columns:
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce').dropna()
                
                # NPV values (typically large, can be negative)
                potential_npv = numeric_col[(numeric_col.abs() > 1000000) & (numeric_col.abs() < 1e12)]
                npv_values.extend(potential_npv.tolist())
                
                # Discount rates (0-1 or 1-50 for percentages)
                rates_decimal = numeric_col[(numeric_col > 0) & (numeric_col < 1)]
                rates_percent = numeric_col[(numeric_col >= 1) & (numeric_col <= 50)]
                
                discount_rates.update(rates_decimal.tolist())
                discount_rates.update([r/100 for r in rates_percent.tolist()])
                
            except Exception:
                continue
        
        # Clean and sort discount rates
        clean_rates = sorted([r for r in discount_rates if 0.01 <= r <= 0.5])
        
        return {
            'npv_values': npv_values,
            'npv_count': len(npv_values),
            'positive_npv_count': len([v for v in npv_values if v > 0]),
            'negative_npv_count': len([v for v in npv_values if v < 0]),
            'max_npv': max(npv_values) if npv_values else 0,
            'min_npv': min(npv_values) if npv_values else 0,
            'avg_npv': np.mean(npv_values) if npv_values else 0
        }, clean_rates
    
    def create_cash_flow_scenarios(self):
        """Create multiple cash flow scenarios based on industry patterns"""
        scenarios = {
            'conservative': {
                'name': 'Conservative Case',
                'capex': -4300000000,  # $4.3B initial investment
                'cash_flows': [300000000, 350000000, 400000000, 450000000, 300000000, 200000000],
                'description': 'Lower production estimates, higher costs'
            },
            'base': {
                'name': 'Base Case', 
                'capex': -4300000000,
                'cash_flows': [400000000, 500000000, 600000000, 700000000, 500000000, 300000000],
                'description': 'Most likely scenario based on typical well performance'
            },
            'optimistic': {
                'name': 'Optimistic Case',
                'capex': -3800000000,  # Lower CAPEX
                'cash_flows': [500000000, 700000000, 850000000, 900000000, 700000000, 500000000],
                'description': 'Higher production rates, lower development costs'
            },
            'excel_based': {
                'name': 'Excel Data Derived',
                'capex': -4300000000,
                'cash_flows': [300000000, 350000000, 500000000, 850000000, 300000000],
                'description': 'Based on patterns observed in Excel file'
            }
        }
        return scenarios
    
    def calculate_scenario_npvs(self, scenarios, discount_rates):
        """Calculate NPV for all scenarios and discount rates"""
        results = {}
        
        for scenario_name, scenario_data in scenarios.items():
            full_cash_flows = [scenario_data['capex']] + scenario_data['cash_flows']
            scenario_results = []
            
            for rate in discount_rates:
                try:
                    npv = npf.npv(rate, full_cash_flows)
                    irr = npf.irr(full_cash_flows) if len(full_cash_flows) > 1 else None
                    
                    scenario_results.append({
                        'discount_rate': rate,
                        'npv': npv,
                        'irr': irr,
                        'cash_flows': full_cash_flows
                    })
                except Exception:
                    continue
            
            results[scenario_name] = {
                'info': scenario_data,
                'calculations': scenario_results
            }
        
        return results
    
    def perform_sensitivity_analysis(self, base_scenario, base_rate=0.10):
        """Perform sensitivity analysis on key variables"""
        base_cash_flows = [base_scenario['capex']] + base_scenario['cash_flows']
        base_npv = npf.npv(base_rate, base_cash_flows)
        
        sensitivity_results = {
            'base_npv': base_npv,
            'base_rate': base_rate,
            'sensitivities': {}
        }
        
        # Revenue sensitivity
        for change in [-0.3, -0.2, -0.1, 0.1, 0.2, 0.3]:
            adjusted_flows = [base_cash_flows[0]] + [cf * (1 + change) for cf in base_cash_flows[1:]]
            new_npv = npf.npv(base_rate, adjusted_flows)
            pct_change = ((new_npv - base_npv) / abs(base_npv) * 100) if base_npv != 0 else 0
            
            sensitivity_results['sensitivities'][f'revenue_{change:+.0%}'] = {
                'npv': new_npv,
                'npv_change_pct': pct_change,
                'description': f'Revenue {change:+.0%}'
            }
        
        # CAPEX sensitivity  
        for change in [-0.3, -0.2, -0.1, 0.1, 0.2, 0.3]:
            adjusted_flows = [base_cash_flows[0] * (1 + change)] + base_cash_flows[1:]
            new_npv = npf.npv(base_rate, adjusted_flows)
            pct_change = ((new_npv - base_npv) / abs(base_npv) * 100) if base_npv != 0 else 0
            
            sensitivity_results['sensitivities'][f'capex_{change:+.0%}'] = {
                'npv': new_npv,
                'npv_change_pct': pct_change,
                'description': f'CAPEX {change:+.0%}'
            }
        
        return sensitivity_results
    
    def generate_comprehensive_report(self):
        """Generate comprehensive analysis report"""
        print("="*80)
        print("COMPREHENSIVE NPV ANALYSIS - JStM WELL PRODUCTION DATA")
        print("="*80)
        
        # Load Excel data
        df = self.load_excel_data()
        excel_metrics, excel_rates = self.extract_financial_metrics(df)
        
        # Create scenarios
        scenarios = self.create_cash_flow_scenarios()
        
        # Use mix of excel rates and standard rates
        discount_rates = sorted(list(set(excel_rates[:10] + [0.05, 0.08, 0.10, 0.12, 0.15, 0.20])))
        
        print("\n1. EXCEL DATA ANALYSIS")
        print("-" * 40)
        if excel_metrics:
            print(f"NPV entries found: {excel_metrics['npv_count']}")
            print(f"Positive NPVs: {excel_metrics['positive_npv_count']} ({excel_metrics['positive_npv_count']/excel_metrics['npv_count']*100:.1f}%)")
            print(f"Negative NPVs: {excel_metrics['negative_npv_count']} ({excel_metrics['negative_npv_count']/excel_metrics['npv_count']*100:.1f}%)")
            print(f"Highest NPV: ${excel_metrics['max_npv']:,.0f}")
            print(f"Lowest NPV: ${excel_metrics['min_npv']:,.0f}")
            print(f"Average NPV: ${excel_metrics['avg_npv']:,.0f}")
        else:
            print("Unable to extract Excel data")
        
        # Calculate scenario NPVs
        scenario_results = self.calculate_scenario_npvs(scenarios, discount_rates)
        
        print("\n2. SCENARIO ANALYSIS")
        print("-" * 40)
        
        for scenario_name, results in scenario_results.items():
            print(f"\n{results['info']['name'].upper()}:")
            print(f"Description: {results['info']['description']}")
            print(f"CAPEX: ${results['info']['capex']:,.0f}")
            
            # Show NPV at key discount rates
            for calc in results['calculations']:
                if calc['discount_rate'] in [0.08, 0.10, 0.15]:
                    npv_status = "POSITIVE" if calc['npv'] > 0 else "NEGATIVE"
                    print(f"  NPV @ {calc['discount_rate']:.0%}: ${calc['npv']:>12,.0f} ({npv_status})")
                    if calc['irr'] and not np.isnan(calc['irr']):
                        print(f"  IRR: {calc['irr']:>19.1%}")
        
        # Sensitivity Analysis
        print("\n3. SENSITIVITY ANALYSIS (Base Case @ 10%)")
        print("-" * 40)
        base_scenario = scenarios['base']
        sensitivity = self.perform_sensitivity_analysis(base_scenario)
        
        print(f"Base NPV: ${sensitivity['base_npv']:,.0f}")
        print("\nRevenue Sensitivity:")
        for key, data in sensitivity['sensitivities'].items():
            if 'revenue' in key:
                print(f"  {data['description']:>12}: ${data['npv']:>15,.0f} ({data['npv_change_pct']:+.1f}%)")
        
        print("\nCAPEX Sensitivity:")
        for key, data in sensitivity['sensitivities'].items():
            if 'capex' in key:
                print(f"  {data['description']:>12}: ${data['npv']:>15,.0f} ({data['npv_change_pct']:+.1f}%)")
        
        # Save comprehensive results
        self.save_comprehensive_results(excel_metrics, scenario_results, sensitivity)
        
        print("\n4. FILES GENERATED")
        print("-" * 40)
        print("✓ comprehensive_npv_analysis.json")
        print("✓ comprehensive_npv_analysis.csv") 
        print("✓ npv_scenario_comparison.csv")
        
    def save_comprehensive_results(self, excel_metrics, scenario_results, sensitivity):
        """Save all results to files"""
        timestamp = datetime.now().isoformat()
        
        # Comprehensive JSON results
        comprehensive_data = {
            'analysis_date': timestamp,
            'project': 'JStM WELL Production Data',
            'excel_analysis': excel_metrics,
            'scenario_analysis': {},
            'sensitivity_analysis': sensitivity
        }
        
        # Process scenario results for JSON serialization
        for scenario_name, results in scenario_results.items():
            comprehensive_data['scenario_analysis'][scenario_name] = {
                'info': results['info'],
                'npv_calculations': [
                    {
                        'discount_rate': calc['discount_rate'],
                        'discount_rate_pct': f"{calc['discount_rate']:.1%}",
                        'npv': calc['npv'],
                        'npv_formatted': f"${calc['npv']:,.0f}",
                        'irr': calc['irr'] if calc['irr'] and not np.isnan(calc['irr']) else None,
                        'irr_formatted': f"{calc['irr']:.1%}" if calc['irr'] and not np.isnan(calc['irr']) else "N/A"
                    }
                    for calc in results['calculations']
                ]
            }
        
        # Save JSON
        with open('comprehensive_npv_analysis.json', 'w') as f:
            json.dump(comprehensive_data, f, indent=2, default=str)
        
        # Create scenario comparison CSV
        csv_data = []
        for scenario_name, results in scenario_results.items():
            for calc in results['calculations']:
                if calc['discount_rate'] in [0.08, 0.10, 0.15]:  # Key rates only
                    csv_data.append({
                        'Scenario': results['info']['name'],
                        'Discount_Rate': f"{calc['discount_rate']:.1%}",
                        'NPV': calc['npv'],
                        'IRR': calc['irr'] if calc['irr'] and not np.isnan(calc['irr']) else None,
                        'CAPEX': results['info']['capex'],
                        'Description': results['info']['description']
                    })
        
        df_scenarios = pd.DataFrame(csv_data)
        df_scenarios.to_csv('npv_scenario_comparison.csv', index=False)
        
        # Create comprehensive summary CSV
        summary_data = []
        if excel_metrics and excel_metrics.get('npv_count', 0) > 0:
            summary_data.append({
                'Analysis_Type': 'Excel Data Analysis',
                'NPV_Count': excel_metrics['npv_count'],
                'Avg_NPV': excel_metrics['avg_npv'],
                'Max_NPV': excel_metrics['max_npv'],
                'Min_NPV': excel_metrics['min_npv'],
                'Positive_Count': excel_metrics['positive_npv_count'],
                'Negative_Count': excel_metrics['negative_npv_count']
            })
        
        for scenario_name, results in scenario_results.items():
            npv_10pct = next((c['npv'] for c in results['calculations'] if abs(c['discount_rate'] - 0.10) < 0.001), None)
            if npv_10pct:
                summary_data.append({
                    'Analysis_Type': f"Scenario: {results['info']['name']}",
                    'NPV_at_10pct': npv_10pct,
                    'CAPEX': results['info']['capex'],
                    'Description': results['info']['description']
                })
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv('comprehensive_npv_analysis.csv', index=False)

def main():
    analyzer = JStMNPVAnalyzer()
    analyzer.generate_comprehensive_report()

if __name__ == "__main__":
    main()
