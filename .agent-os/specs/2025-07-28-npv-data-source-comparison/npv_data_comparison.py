#!/usr/bin/env python3
"""
NPV Data Source Comparison Tool
Compares manual analysis data with Excel benchmark data to identify discrepancies.
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))

from worldenergydata.modules.bsee.analysis.excel_data_extractor import ExcelDataExtractor
# from worldenergydata.modules.bsee.analysis.production_api12 import ProductionAPI12Analysis


class NPVDataComparison:
    """Compare NPV data sources between manual analysis and Excel benchmarks."""
    
    def __init__(self, excel_path: str = None):
        """Initialize the data comparison tool."""
        if excel_path is None:
            # Try to find the Excel file relative to project root
            current_file = os.path.abspath(__file__)
            # Go up to project root (worldenergydata/)
            project_root = current_file
            for _ in range(5):  # Go up 5 levels from analysis/npv_data_comparison.py
                project_root = os.path.dirname(project_root)
            excel_path = os.path.join(project_root, 'docs', 'modules', 'bsee', 'data', 'NPV_JStM-WELL-Production-Data-thru-2019.xlsx')
        
        self.excel_path = excel_path
        self.extractor = ExcelDataExtractor(excel_path)
        self.comparison_results = {}
        
    def extract_excel_data(self) -> Dict[str, List[float]]:
        """Extract production and price data from Excel."""
        print("Extracting Excel benchmark data...")
        
        # Extract data from specific rows
        production_data = self.extractor.extract_production_data(row_index=22)
        oil_prices = self.extractor.extract_oil_prices(row_index=4)
        
        # Get aligned data
        aligned = self.extractor.align_data(production_data, oil_prices)
        
        print(f"  - Extracted {len(production_data)} production data points")
        print(f"  - Extracted {len(oil_prices)} oil price data points")
        print(f"  - Aligned to {aligned['periods']} periods")
        
        return aligned
    
    def extract_manual_data(self, config_path: Optional[str] = None) -> Dict[str, List[float]]:
        """Extract production and price data from manual analysis system."""
        print("\nExtracting manual analysis data...")
        
        # For now, we'll simulate this with realistic data
        # In real implementation, this would extract from BSEE data sources
        
        # Note: This is where the actual manual data extraction would happen
        # using the existing ProductionAPI12Analysis class
        
        # Simulated data for comparison (this would be replaced with actual extraction)
        manual_production = []
        manual_prices = []
        
        print("  - Manual data extraction would be implemented here")
        print("  - Would use existing BSEE data extraction logic")
        
        return {
            'production': manual_production,
            'prices': manual_prices,
            'periods': 0
        }
    
    def compare_data_sources(self, excel_data: Dict, manual_data: Dict) -> Dict:
        """Perform detailed comparison between Excel and manual data."""
        print("\nComparing data sources...")
        
        if not manual_data['production']:
            print("  - No manual data available for comparison")
            print("  - Showing Excel data characteristics only")
            
            return self._analyze_single_source(excel_data)
        
        # Full comparison when both data sources are available
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'excel_source': self.excel_path,
            'production_comparison': self._compare_production(
                excel_data['production'], 
                manual_data['production']
            ),
            'price_comparison': self._compare_prices(
                excel_data['prices'],
                manual_data['prices']
            ),
            'data_alignment': self._check_alignment(excel_data, manual_data),
            'recommendations': []
        }
        
        # Generate recommendations based on findings
        comparison['recommendations'] = self._generate_recommendations(comparison)
        
        return comparison
    
    def _analyze_single_source(self, data: Dict) -> Dict:
        """Analyze characteristics of a single data source."""
        production = data['production']
        prices = data['prices']
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'source': 'Excel benchmark',
            'production_analysis': {
                'count': len(production),
                'total': sum(production),
                'average': np.mean(production) if production else 0,
                'std_dev': np.std(production) if production else 0,
                'min': min(production) if production else 0,
                'max': max(production) if production else 0,
                'range': max(production) - min(production) if production else 0,
                'coefficient_of_variation': np.std(production) / np.mean(production) if production and np.mean(production) > 0 else 0
            },
            'price_analysis': {
                'count': len(prices),
                'average': np.mean(prices) if prices else 0,
                'std_dev': np.std(prices) if prices else 0,
                'min': min(prices) if prices else 0,
                'max': max(prices) if prices else 0,
                'range': max(prices) - min(prices) if prices else 0,
                'volatility': np.std(prices) / np.mean(prices) if prices and np.mean(prices) > 0 else 0
            },
            'revenue_potential': {
                'total_revenue': sum(p * price for p, price in zip(production, prices)) if production and prices else 0,
                'average_revenue_per_period': np.mean([p * price for p, price in zip(production, prices)]) if production and prices else 0
            }
        }
        
        return analysis
    
    def _compare_production(self, excel_prod: List[float], manual_prod: List[float]) -> Dict:
        """Compare production data between sources."""
        if not manual_prod:
            return {'status': 'Manual data not available'}
        
        min_len = min(len(excel_prod), len(manual_prod))
        excel_aligned = excel_prod[:min_len]
        manual_aligned = manual_prod[:min_len]
        
        differences = [abs(e - m) for e, m in zip(excel_aligned, manual_aligned)]
        percent_differences = [abs(e - m) / e * 100 if e != 0 else 0 
                             for e, m in zip(excel_aligned, manual_aligned)]
        
        return {
            'periods_compared': min_len,
            'total_excel': sum(excel_aligned),
            'total_manual': sum(manual_aligned),
            'total_difference': abs(sum(excel_aligned) - sum(manual_aligned)),
            'total_difference_pct': abs(sum(excel_aligned) - sum(manual_aligned)) / sum(excel_aligned) * 100 if sum(excel_aligned) > 0 else 0,
            'average_difference': np.mean(differences),
            'average_difference_pct': np.mean(percent_differences),
            'max_difference': max(differences) if differences else 0,
            'max_difference_pct': max(percent_differences) if percent_differences else 0,
            'correlation': np.corrcoef(excel_aligned, manual_aligned)[0, 1] if min_len > 1 else 0
        }
    
    def _compare_prices(self, excel_prices: List[float], manual_prices: List[float]) -> Dict:
        """Compare oil price data between sources."""
        if not manual_prices:
            return {'status': 'Manual price data not available'}
        
        min_len = min(len(excel_prices), len(manual_prices))
        excel_aligned = excel_prices[:min_len]
        manual_aligned = manual_prices[:min_len]
        
        differences = [abs(e - m) for e, m in zip(excel_aligned, manual_aligned)]
        percent_differences = [abs(e - m) / e * 100 if e != 0 else 0 
                             for e, m in zip(excel_aligned, manual_aligned)]
        
        return {
            'periods_compared': min_len,
            'avg_excel_price': np.mean(excel_aligned),
            'avg_manual_price': np.mean(manual_aligned),
            'price_difference': abs(np.mean(excel_aligned) - np.mean(manual_aligned)),
            'price_difference_pct': abs(np.mean(excel_aligned) - np.mean(manual_aligned)) / np.mean(excel_aligned) * 100 if np.mean(excel_aligned) > 0 else 0,
            'max_price_difference': max(differences) if differences else 0,
            'correlation': np.corrcoef(excel_aligned, manual_aligned)[0, 1] if min_len > 1 else 0
        }
    
    def _check_alignment(self, excel_data: Dict, manual_data: Dict) -> Dict:
        """Check data alignment between sources."""
        return {
            'excel_periods': excel_data['periods'],
            'manual_periods': manual_data['periods'],
            'period_difference': abs(excel_data['periods'] - manual_data['periods']),
            'aligned': excel_data['periods'] == manual_data['periods']
        }
    
    def _generate_recommendations(self, comparison: Dict) -> List[str]:
        """Generate recommendations based on comparison results."""
        recommendations = []
        
        # Check production comparison
        if 'production_comparison' in comparison:
            prod_comp = comparison['production_comparison']
            if isinstance(prod_comp, dict) and 'average_difference_pct' in prod_comp:
                if prod_comp['average_difference_pct'] > 20:
                    recommendations.append(
                        f"Production data shows {prod_comp['average_difference_pct']:.1f}% average difference. "
                        "Investigate data source and scaling factors."
                    )
                if prod_comp.get('correlation', 0) < 0.8:
                    recommendations.append(
                        "Low correlation between production sources suggests different time periods or data issues."
                    )
        
        # Check price comparison
        if 'price_comparison' in comparison:
            price_comp = comparison['price_comparison']
            if isinstance(price_comp, dict) and 'price_difference_pct' in price_comp:
                if price_comp['price_difference_pct'] > 10:
                    recommendations.append(
                        f"Oil prices show {price_comp['price_difference_pct']:.1f}% difference. "
                        "Verify price source (BRENT vs WTI) and time period."
                    )
        
        # Check alignment
        if 'data_alignment' in comparison:
            if not comparison['data_alignment'].get('aligned', True):
                recommendations.append(
                    f"Data period mismatch: Excel has {comparison['data_alignment']['excel_periods']} periods, "
                    f"manual has {comparison['data_alignment']['manual_periods']} periods."
                )
        
        if not recommendations:
            recommendations.append("Data sources appear well-aligned.")
        
        return recommendations
    
    def generate_visual_comparison(self, excel_data: Dict, output_dir: str = "tests/modules/bsee/analysis/results"):
        """Generate visual comparisons of the data."""
        print("\nGenerating visual comparisons...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Production data visualization
        if excel_data['production']:
            plt.figure(figsize=(12, 6))
            periods = range(1, len(excel_data['production']) + 1)
            plt.plot(periods, excel_data['production'], 'b-', label='Excel Production', linewidth=2)
            plt.xlabel('Period (Month)')
            plt.ylabel('Production (BBL)')
            plt.title('Excel Benchmark Production Data')
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'excel_production_data.png'))
            plt.close()
        
        # Price data visualization
        if excel_data['prices']:
            plt.figure(figsize=(12, 6))
            periods = range(1, len(excel_data['prices']) + 1)
            plt.plot(periods, excel_data['prices'], 'g-', label='Excel Oil Prices (BRENT)', linewidth=2)
            plt.xlabel('Period (Month)')
            plt.ylabel('Oil Price (USD/BBL)')
            plt.title('Excel Benchmark Oil Price Data')
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'excel_oil_prices.png'))
            plt.close()
        
        # Revenue calculation visualization
        if excel_data['production'] and excel_data['prices']:
            revenues = [p * price for p, price in zip(excel_data['production'], excel_data['prices'])]
            plt.figure(figsize=(12, 6))
            periods = range(1, len(revenues) + 1)
            plt.bar(periods, revenues, color='purple', alpha=0.7)
            plt.xlabel('Period (Month)')
            plt.ylabel('Revenue (USD)')
            plt.title('Excel Benchmark Revenue Calculation')
            plt.grid(True, alpha=0.3, axis='y')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'excel_revenue_calculation.png'))
            plt.close()
        
        print(f"  - Visualizations saved to {output_dir}")
    
    def save_comparison_report(self, comparison: Dict, output_path: str = "tests/modules/bsee/analysis/results/npv_data_comparison_report.json"):
        """Save the comparison report to file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)
        
        print(f"\nComparison report saved to: {output_path}")
        
        # Also save as CSV for easy viewing
        csv_path = output_path.replace('.json', '.csv')
        self._save_summary_csv(comparison, csv_path)
    
    def _save_summary_csv(self, comparison: Dict, csv_path: str):
        """Save a summary of the comparison as CSV."""
        summary_data = []
        
        if isinstance(comparison.get('production_analysis'), dict):
            prod = comparison['production_analysis']
            summary_data.append({
                'Metric': 'Production Count',
                'Value': prod.get('count', 0),
                'Unit': 'periods'
            })
            summary_data.append({
                'Metric': 'Average Production',
                'Value': f"{prod.get('average', 0):,.0f}",
                'Unit': 'BBL/period'
            })
            summary_data.append({
                'Metric': 'Total Production',
                'Value': f"{prod.get('total', 0):,.0f}",
                'Unit': 'BBL'
            })
        
        if isinstance(comparison.get('price_analysis'), dict):
            price = comparison['price_analysis']
            summary_data.append({
                'Metric': 'Average Oil Price',
                'Value': f"{price.get('average', 0):.2f}",
                'Unit': 'USD/BBL'
            })
            summary_data.append({
                'Metric': 'Price Volatility',
                'Value': f"{price.get('volatility', 0):.2%}",
                'Unit': 'coefficient'
            })
        
        if isinstance(comparison.get('revenue_potential'), dict):
            rev = comparison['revenue_potential']
            summary_data.append({
                'Metric': 'Total Revenue Potential',
                'Value': f"{rev.get('total_revenue', 0):,.0f}",
                'Unit': 'USD'
            })
        
        if summary_data:
            df = pd.DataFrame(summary_data)
            df.to_csv(csv_path, index=False)
            print(f"Summary CSV saved to: {csv_path}")


def main():
    """Run the NPV data comparison analysis."""
    print("=" * 80)
    print("NPV DATA SOURCE COMPARISON ANALYSIS")
    print("=" * 80)
    
    # Initialize comparison tool
    comparison_tool = NPVDataComparison()
    
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


if __name__ == "__main__":
    main()