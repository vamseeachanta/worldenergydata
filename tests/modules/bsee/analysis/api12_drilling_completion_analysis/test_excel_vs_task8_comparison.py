#!/usr/bin/env python3
"""
Excel vs Task 8 DataFrame Comparison

This script compares the Excel-derived economics data with the Task 8 DataFrame
to identify variances and document methodology differences.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from loguru import logger


class ExcelVsTask8Comparison:
    """Compare Excel economics data with Task 8 programmatic calculations"""
    
    def __init__(self):
        self.excel_csv_path = r"results\jack_st_malo_excel_economics_20250730_130153.csv"
        self.task8_csv_path = r"tests\modules\bsee\analysis\results\jack_st_malo_monthly_economics_test_20250729_113950.csv"
        self.output_folder = "results"
        
    def load_dataframes(self):
        """Load both CSV files into DataFrames"""
        logger.info("Loading CSV files for comparison...")
        
        # Load Excel-derived data
        df_excel = pd.read_csv(self.excel_csv_path)
        logger.info(f"Excel CSV loaded: {len(df_excel)} rows, {len(df_excel.columns)} columns")
        
        # Load Task 8 data
        df_task8 = pd.read_csv(self.task8_csv_path)
        logger.info(f"Task 8 CSV loaded: {len(df_task8)} rows, {len(df_task8.columns)} columns")
        
        return df_excel, df_task8
    
    def align_dataframes(self, df_excel, df_task8):
        """Align DataFrames for comparison by reordering columns and matching periods"""
        
        # Get common columns
        excel_cols = set(df_excel.columns)
        task8_cols = set(df_task8.columns)
        common_cols = excel_cols.intersection(task8_cols)
        
        logger.info(f"Common columns: {len(common_cols)}")
        logger.info(f"Excel-only columns: {excel_cols - task8_cols}")
        logger.info(f"Task8-only columns: {task8_cols - excel_cols}")
        
        # Align to common columns and same order
        column_order = sorted(list(common_cols))
        df_excel_aligned = df_excel[column_order].copy()
        df_task8_aligned = df_task8[column_order].copy()
        
        # Limit to same number of rows (minimum)
        min_rows = min(len(df_excel_aligned), len(df_task8_aligned))
        df_excel_aligned = df_excel_aligned.iloc[:min_rows]
        df_task8_aligned = df_task8_aligned.iloc[:min_rows]
        
        logger.info(f"Aligned DataFrames to {min_rows} rows and {len(column_order)} columns")
        
        return df_excel_aligned, df_task8_aligned, column_order
    
    def calculate_variances(self, df_excel, df_task8, columns):
        """Calculate variances between Excel and Task 8 data"""
        
        variance_results = {}
        
        for col in columns:
            if col == 'Month-Year':
                continue  # Skip text columns
                
            try:
                # Convert to numeric if needed
                excel_vals = pd.to_numeric(df_excel[col], errors='coerce')
                task8_vals = pd.to_numeric(df_task8[col], errors='coerce')
                
                # Calculate variances
                absolute_diff = excel_vals - task8_vals
                percent_diff = (absolute_diff / task8_vals * 100).replace([np.inf, -np.inf], np.nan)
                
                variance_results[col] = {
                    'excel_sum': excel_vals.sum(),
                    'task8_sum': task8_vals.sum(),
                    'absolute_diff_sum': absolute_diff.sum(),
                    'absolute_diff_mean': absolute_diff.mean(),
                    'percent_diff_mean': percent_diff.mean(),
                    'max_absolute_diff': absolute_diff.abs().max(),
                    'max_percent_diff': percent_diff.abs().max()
                }
                
            except Exception as e:
                logger.warning(f"Could not calculate variance for {col}: {e}")
                
        return variance_results
    
    def create_comparison_report(self, df_excel, df_task8, variance_results):
        """Create a detailed comparison report"""
        
        report_lines = []
        report_lines.append("# Excel vs Task 8 DataFrame Comparison Report")
        report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("\n## Overview")
        report_lines.append(f"- Excel data periods: {len(df_excel)}")
        report_lines.append(f"- Task 8 data periods: {len(df_task8)}")
        report_lines.append(f"- Compared columns: {len(variance_results)}")
        
        # Key metrics comparison
        report_lines.append("\n## Key Metrics Comparison")
        report_lines.append("\n| Metric | Excel Total | Task 8 Total | Absolute Diff | % Diff |")
        report_lines.append("|--------|-------------|--------------|---------------|---------|")
        
        key_metrics = ['Monthly_production_BBL', 'Oil_sales', 'OPEX_monthly', 'CAPEX_monthly']
        
        for metric in key_metrics:
            if metric in variance_results:
                var = variance_results[metric]
                excel_total = var['excel_sum']
                task8_total = var['task8_sum']
                abs_diff = var['absolute_diff_sum']
                pct_diff = (abs_diff / task8_total * 100) if task8_total != 0 else 0
                
                report_lines.append(f"| {metric} | {excel_total:,.2f} | {task8_total:,.2f} | {abs_diff:,.2f} | {pct_diff:.2f}% |")
        
        # Production data analysis
        report_lines.append("\n## Production Data Analysis")
        
        if 'Monthly_production_BBL' in variance_results:
            prod_var = variance_results['Monthly_production_BBL']
            report_lines.append(f"\n### Production Totals")
            report_lines.append(f"- Excel: {prod_var['excel_sum']:,.0f} BBL")
            report_lines.append(f"- Task 8: {prod_var['task8_sum']:,.0f} BBL")
            report_lines.append(f"- Difference: {prod_var['absolute_diff_sum']:,.0f} BBL ({prod_var['absolute_diff_sum']/prod_var['task8_sum']*100:.1f}%)")
            
            # Check if Excel data is daily vs monthly
            excel_avg_prod = prod_var['excel_sum'] / len(df_excel)
            task8_avg_prod = prod_var['task8_sum'] / len(df_task8)
            
            report_lines.append(f"\n### Production Scale Analysis")
            report_lines.append(f"- Excel average per period: {excel_avg_prod:,.0f} BBL")
            report_lines.append(f"- Task 8 average per period: {task8_avg_prod:,.0f} BBL")
            report_lines.append(f"- Scale factor: {task8_avg_prod/excel_avg_prod:.2f}x")
            
            if excel_avg_prod < 200000:  # Likely daily data
                report_lines.append("\n**Note:** Excel data appears to be DAILY production values")
                report_lines.append(f"- If multiplied by 30.4: {excel_avg_prod * 30.4:,.0f} BBL/month")
        
        # Oil price comparison
        report_lines.append("\n## Oil Price Analysis")
        
        if 'Oil_price_USD' in df_excel.columns and 'Oil_price_USD' in df_task8.columns:
            excel_prices = pd.to_numeric(df_excel['Oil_price_USD'], errors='coerce')
            task8_prices = pd.to_numeric(df_task8['Oil_price_USD'], errors='coerce')
            
            report_lines.append(f"\n### Price Statistics")
            report_lines.append(f"- Excel average: ${excel_prices.mean():.2f}/BBL")
            report_lines.append(f"- Task 8 average: ${task8_prices.mean():.2f}/BBL")
            report_lines.append(f"- Price difference: ${abs(excel_prices.mean() - task8_prices.mean()):.2f}/BBL")
            
        # Time period analysis
        report_lines.append("\n## Time Period Analysis")
        
        if 'Month-Year' in df_excel.columns:
            report_lines.append(f"\n### Excel Time Coverage")
            report_lines.append(f"- First period: {df_excel['Month-Year'].iloc[0]}")
            report_lines.append(f"- Last period: {df_excel['Month-Year'].iloc[-1]}")
            report_lines.append(f"- Total periods: {len(df_excel)}")
            
        if 'Month-Year' in df_task8.columns:
            report_lines.append(f"\n### Task 8 Time Coverage")
            report_lines.append(f"- First period: {df_task8['Month-Year'].iloc[0]}")
            report_lines.append(f"- Last period: {df_task8['Month-Year'].iloc[-1]}")
            report_lines.append(f"- Total periods: {len(df_task8)}")
            
        # Methodology differences
        report_lines.append("\n## Methodology Differences")
        report_lines.append("\n### Data Sources")
        report_lines.append("- **Excel**: Direct extraction from NPV_JStM-WELL-Production-Data-thru-2019.xlsx")
        report_lines.append("  - Production: Row 22 (JSM Total AVGMoly)")
        report_lines.append("  - Oil Prices: Row 2 (BRENT prices)")
        report_lines.append("  - Well Count: Row 27")
        report_lines.append("  - CAPEX: Row 32")
        report_lines.append("\n- **Task 8**: Programmatic calculation from BSEE database")
        report_lines.append("  - Production: Aggregated from individual well data")
        report_lines.append("  - Oil Prices: External price data source")
        report_lines.append("  - Well Count: Calculated from active wells")
        report_lines.append("  - CAPEX: Fixed allocation over project life")
        
        report_lines.append("\n### Key Differences Identified")
        report_lines.append("1. **Production Data Scale**: Excel may contain daily values while Task 8 uses monthly")
        report_lines.append("2. **Time Period Coverage**: Different start/end dates between sources")
        report_lines.append("3. **Price Data Source**: Excel uses embedded BRENT prices, Task 8 may use different source")
        report_lines.append("4. **Calculation Methods**: Excel uses fixed formulas, Task 8 uses dynamic calculations")
        
        # Recommendations
        report_lines.append("\n## Recommendations for Alignment")
        report_lines.append("\n1. **Verify Production Units**: Confirm if Excel data is daily or monthly")
        report_lines.append("2. **Align Time Periods**: Ensure both analyses cover the same date range")
        report_lines.append("3. **Standardize Price Source**: Use consistent oil price data")
        report_lines.append("4. **Document Assumptions**: Clearly state all calculation assumptions")
        report_lines.append("5. **Scale Factor Application**: If Excel is daily, apply 30.4x multiplier for monthly comparison")
        
        return "\n".join(report_lines)
    
    def save_comparison_results(self, report, df_excel, df_task8, variance_results):
        """Save comparison results to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save markdown report
        report_path = os.path.join(self.output_folder, f"excel_vs_task8_comparison_{timestamp}.md")
        with open(report_path, 'w') as f:
            f.write(report)
        logger.info(f"Saved comparison report to: {report_path}")
        
        # Save variance summary CSV
        variance_df = pd.DataFrame(variance_results).T
        variance_path = os.path.join(self.output_folder, f"excel_vs_task8_variance_{timestamp}.csv")
        variance_df.to_csv(variance_path)
        logger.info(f"Saved variance summary to: {variance_path}")
        
        # Save side-by-side comparison CSV (first 10 rows)
        comparison_df = pd.DataFrame()
        for col in sorted(set(df_excel.columns).intersection(set(df_task8.columns))):
            if col != 'Month-Year':
                comparison_df[f"{col}_Excel"] = df_excel[col].iloc[:10]
                comparison_df[f"{col}_Task8"] = df_task8[col].iloc[:10]
            else:
                comparison_df[col] = df_excel[col].iloc[:10]
                
        comparison_path = os.path.join(self.output_folder, f"excel_vs_task8_sidebyside_{timestamp}.csv")
        comparison_df.to_csv(comparison_path, index=False)
        logger.info(f"Saved side-by-side comparison to: {comparison_path}")
        
        return report_path, variance_path, comparison_path
    
    def run_comparison(self):
        """Main comparison process"""
        logger.info("Starting Excel vs Task 8 comparison...")
        
        # Load data
        df_excel, df_task8 = self.load_dataframes()
        
        # Align DataFrames
        df_excel_aligned, df_task8_aligned, columns = self.align_dataframes(df_excel, df_task8)
        
        # Calculate variances
        variance_results = self.calculate_variances(df_excel_aligned, df_task8_aligned, columns)
        
        # Create report
        report = self.create_comparison_report(df_excel, df_task8, variance_results)
        
        # Save results
        report_path, variance_path, comparison_path = self.save_comparison_results(
            report, df_excel, df_task8, variance_results
        )
        
        # Print summary
        print("\n=== COMPARISON SUMMARY ===")
        print(f"Excel periods: {len(df_excel)}")
        print(f"Task 8 periods: {len(df_task8)}")
        
        if 'Monthly_production_BBL' in variance_results:
            prod_var = variance_results['Monthly_production_BBL']
            print(f"\nProduction Totals:")
            print(f"  Excel: {prod_var['excel_sum']:,.0f} BBL")
            print(f"  Task 8: {prod_var['task8_sum']:,.0f} BBL")
            print(f"  Variance: {abs(prod_var['absolute_diff_sum']/prod_var['task8_sum']*100):.1f}%")
            
        return report_path


def test_excel_vs_task8_comparison():
    """Test the comparison functionality"""
    
    comparator = ExcelVsTask8Comparison()
    report_path = comparator.run_comparison()
    
    print(f"\n+ Comparison complete!")
    print(f"   Report saved to: {report_path}")
    
    return report_path


if __name__ == "__main__":
    test_excel_vs_task8_comparison()