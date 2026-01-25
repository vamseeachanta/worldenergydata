"""
Report generation module for API12 drilling completion analysis.

This module provides functions to generate comprehensive analysis reports
comparing the lease-based and API12-based drilling completion methodologies.
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple
import math


def generate_executive_summary(comparison_data: pd.DataFrame, methodology_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate executive summary of the analysis.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        methodology_data (Dict[str, Any]): Methodology information
        
    Returns:
        Dict[str, Any]: Executive summary data
    """
    total_wells = len(comparison_data)
    fields = comparison_data['field_name'].unique().tolist()
    
    # Calculate key statistics
    avg_drilling_diff = comparison_data['drilling_diff'].mean()
    avg_completion_diff = comparison_data['completion_diff'].mean()
    max_total_diff = comparison_data['total_diff'].max()
    min_total_diff = comparison_data['total_diff'].min()
    
    # Identify wells with significant differences
    high_diff_wells = comparison_data[comparison_data['total_diff'] > 100]
    
    key_findings = [
        f"Analyzed {total_wells} wells across {len(fields)} fields",
        f"Average drilling days difference: {avg_drilling_diff:.1f} days",
        f"Average completion days difference: {avg_completion_diff:.1f} days",
        f"Maximum total difference: {max_total_diff:.0f} days (well {comparison_data.loc[comparison_data['total_diff'].idxmax(), 'well_name']})",
        f"Minimum total difference: {min_total_diff:.0f} days (well {comparison_data.loc[comparison_data['total_diff'].idxmin(), 'well_name']})",
        f"{len(high_diff_wells)} wells show differences greater than 100 days"
    ]
    
    return {
        'total_wells_analyzed': total_wells,
        'fields_analyzed': fields,
        'average_drilling_difference': float(avg_drilling_diff),
        'average_completion_difference': float(avg_completion_diff),
        'maximum_difference': float(max_total_diff),
        'minimum_difference': float(min_total_diff),
        'high_difference_wells_count': len(high_diff_wells),
        'methodology_comparison': {
            'lease_method': methodology_data.get('lease_method', {}).get('approach', 'Timeline-based analysis'),
            'api12_method': methodology_data.get('api12_method', {}).get('approach', 'Milestone-based analysis')
        },
        'key_findings': key_findings
    }


def analyze_calculation_differences(comparison_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze calculation differences between the two methods.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        
    Returns:
        Dict[str, Any]: Analysis of calculation differences
    """
    drilling_diffs = comparison_data['drilling_diff'].dropna()
    completion_diffs = comparison_data['completion_diff'].dropna()
    total_diffs = comparison_data['total_diff'].dropna()
    
    # Find extreme cases
    max_drilling_idx = drilling_diffs.idxmax()
    min_drilling_idx = drilling_diffs.idxmin()
    max_completion_idx = completion_diffs.idxmax()
    min_completion_idx = completion_diffs.idxmin()
    
    extreme_cases = {
        'highest_drilling_diff': {
            'api12': int(comparison_data.loc[max_drilling_idx, 'API12']),
            'well_name': comparison_data.loc[max_drilling_idx, 'well_name'],
            'field': comparison_data.loc[max_drilling_idx, 'field_name'],
            'diff': float(drilling_diffs.max())
        },
        'lowest_drilling_diff': {
            'api12': int(comparison_data.loc[min_drilling_idx, 'API12']),
            'well_name': comparison_data.loc[min_drilling_idx, 'well_name'],
            'field': comparison_data.loc[min_drilling_idx, 'field_name'],
            'diff': float(drilling_diffs.min())
        },
        'highest_completion_diff': {
            'api12': int(comparison_data.loc[max_completion_idx, 'API12']),
            'well_name': comparison_data.loc[max_completion_idx, 'well_name'],
            'field': comparison_data.loc[max_completion_idx, 'field_name'],
            'diff': float(completion_diffs.max())
        },
        'lowest_completion_diff': {
            'api12': int(comparison_data.loc[min_completion_idx, 'API12']),
            'well_name': comparison_data.loc[min_completion_idx, 'well_name'],
            'field': comparison_data.loc[min_completion_idx, 'field_name'],
            'diff': float(completion_diffs.min())
        }
    }
    
    # Statistical analysis
    statistical_summary = {
        'drilling_differences': {
            'mean': float(drilling_diffs.mean()),
            'median': float(drilling_diffs.median()),
            'std': float(drilling_diffs.std()),
            'min': float(drilling_diffs.min()),
            'max': float(drilling_diffs.max()),
            'q25': float(drilling_diffs.quantile(0.25)),
            'q75': float(drilling_diffs.quantile(0.75))
        },
        'completion_differences': {
            'mean': float(completion_diffs.mean()),
            'median': float(completion_diffs.median()),
            'std': float(completion_diffs.std()),
            'min': float(completion_diffs.min()),
            'max': float(completion_diffs.max()),
            'q25': float(completion_diffs.quantile(0.25)),
            'q75': float(completion_diffs.quantile(0.75))
        },
        'total_differences': {
            'mean': float(total_diffs.mean()),
            'median': float(total_diffs.median()),
            'std': float(total_diffs.std()),
            'min': float(total_diffs.min()),
            'max': float(total_diffs.max()),
            'q25': float(total_diffs.quantile(0.25)),
            'q75': float(total_diffs.quantile(0.75))
        }
    }
    
    return {
        'drilling_differences': drilling_diffs.tolist(),
        'completion_differences': completion_diffs.tolist(),
        'extreme_cases': extreme_cases,
        'statistical_summary': statistical_summary
    }


def generate_field_analysis(comparison_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate field-by-field analysis.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        
    Returns:
        Dict[str, Any]: Field analysis data
    """
    field_analysis = {}
    
    for field in comparison_data['field_name'].unique():
        field_data = comparison_data[comparison_data['field_name'] == field]
        
        wells_details = []
        for _, row in field_data.iterrows():
            wells_details.append({
                'api12': int(row['API12']),
                'well_name': row['well_name'],
                'drilling_diff': float(row['drilling_diff']),
                'completion_diff': float(row['completion_diff']),
                'total_diff': float(row['total_diff'])
            })
        
        field_analysis[field] = {
            'wells_count': len(field_data),
            'average_drilling_diff': float(field_data['drilling_diff'].mean()),
            'average_completion_diff': float(field_data['completion_diff'].mean()),
            'average_total_diff': float(field_data['total_diff'].mean()),
            'max_drilling_diff': float(field_data['drilling_diff'].max()),
            'min_drilling_diff': float(field_data['drilling_diff'].min()),
            'max_completion_diff': float(field_data['completion_diff'].max()),
            'min_completion_diff': float(field_data['completion_diff'].min()),
            'wells_details': wells_details
        }
    
    return field_analysis


def identify_root_causes(comparison_data: pd.DataFrame, methodology_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify root causes for calculation differences.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        methodology_data (Dict[str, Any]): Methodology information
        
    Returns:
        Dict[str, Any]: Root cause analysis
    """
    # Analyze patterns in differences
    high_drilling_diffs = comparison_data[comparison_data['drilling_diff'].abs() > 50]
    high_completion_diffs = comparison_data[comparison_data['completion_diff'].abs() > 30]
    
    primary_factors = [
        "Timeline Reconstruction Methods: Lease method uses raw WAR start/end dates vs API12 method uses milestone phase durations",
        "Gap Handling Philosophy: Lease method applies fixed thresholds (300 days drilling, 8 days completion) vs API12 method uses framework-determined logic",
        "Data Source Granularity: Lease method processes individual WAR records vs API12 method uses aggregated milestone data",
        "Drilling Interruption Treatment: Lease method explicitly handles gaps and restarts timeline vs API12 method may aggregate interrupted periods"
    ]
    
    methodology_impacts = [
        f"Gap-based vs Milestone-based: {len(high_drilling_diffs)} wells show drilling differences >50 days, likely due to different gap handling",
        f"Timeline Reconstruction: Wells with complex drilling histories show larger differences due to timeline calculation methods",
        f"Data Processing: Framework integration in API12 method may smooth out drilling interruptions captured in lease method",
        f"Completion Calculation: {len(high_completion_diffs)} wells show completion differences >30 days due to different post-TD analysis methods"
    ]
    
    data_quality_factors = [
        "WAR Data Completeness: Missing or incomplete WAR records affect lease method calculations",
        "Milestone Accuracy: WellRigDays framework accuracy depends on milestone calculation quality",
        "Date Precision: Different date handling between methods may introduce systematic differences",
        "Activity Classification: Different categorization of drilling vs completion activities"
    ]
    
    recommendations = [
        "Validate gap thresholds against actual drilling histories for representative wells",
        "Compare milestone calculation logic in WellRigDays against raw WAR timeline analysis",
        "Analyze data source completeness for both WAR records and milestone data",
        "Review timeline reconstruction accuracy for wells with extreme differences",
        "Develop hybrid approach combining WAR granularity with milestone framework benefits",
        "Implement configurable gap thresholds based on well-specific characteristics"
    ]
    
    return {
        'primary_factors': primary_factors,
        'methodology_impacts': methodology_impacts,
        'data_quality_factors': data_quality_factors,
        'recommendations': recommendations,
        'high_difference_analysis': {
            'drilling_outliers': len(high_drilling_diffs),
            'completion_outliers': len(high_completion_diffs),
            'fields_most_affected': comparison_data.groupby('field_name')['total_diff'].mean().nlargest(3).index.tolist()
        }
    }


def generate_statistical_analysis(comparison_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate comprehensive statistical analysis.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        
    Returns:
        Dict[str, Any]: Statistical analysis results
    """
    def calculate_stats(series: pd.Series) -> Dict[str, float]:
        """Calculate statistical measures for a series."""
        return {
            'mean': float(series.mean()),
            'median': float(series.median()),
            'std': float(series.std()),
            'min': float(series.min()),
            'max': float(series.max()),
            'q25': float(series.quantile(0.25)),
            'q75': float(series.quantile(0.75)),
            'iqr': float(series.quantile(0.75) - series.quantile(0.25)),
            'skewness': float(series.skew()),
            'kurtosis': float(series.kurtosis())
        }
    
    return {
        'drilling_differences': calculate_stats(comparison_data['drilling_diff']),
        'completion_differences': calculate_stats(comparison_data['completion_diff']),
        'total_differences': calculate_stats(comparison_data['total_diff'])
    }


def create_comparison_tables(comparison_data: pd.DataFrame) -> Dict[str, str]:
    """
    Create markdown tables for comparison.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        
    Returns:
        Dict[str, str]: Dictionary of markdown tables
    """
    # Enhanced methodology comparison table with more detail
    methodology_table = """
| Aspect | Lease Method | API12 Method |
|--------|--------------|--------------|
| **Data Sources** | WAR binary files (mv_war_main.bin, mv_war_boreholes_view.bin, mv_war_main_prop.bin), CSV lease data | Structured well data + WellRigDays framework |
| **Timeline Construction** | Raw start/end dates with gap analysis | Aggregated milestone phases |
| **Drilling Calculation** | (TD_DATE - ADJUSTED_SPUD_DATE) - early_days with 300-day gap threshold | Milestone-based DRL phases through WellRigDays |
| **Completion Calculation** | Post-TD WAR analysis (8-day threshold) | Milestone completion phases |
| **Gap Handling** | Fixed thresholds (300 days, 8 days) | Framework-determined logic |
| **Output Format** | Single Excel file with timestamp | Multiple CSV files + visualizations |
| **Architecture** | Monolithic DrillingCompletionDays class | Framework integration WellAPI12 class |
| **Data Granularity** | Individual WAR record level | Aggregated phase level |
| **Processing Logic** | Sequential timeline analysis | Framework-based phase aggregation |
| **Date Handling** | Direct date arithmetic | WellRigDays date processing |
| **Validation** | WAR data completeness checks | Framework validation |
| **Performance** | O(n*m) complexity | O(n) + framework overhead |
"""
    
    # Well details table
    well_table_rows = []
    well_table_rows.append("| API12 | Field | Well | Lease Drill | API12 Drill | Drill Diff | Lease Comp | API12 Comp | Comp Diff | Total Diff |")
    well_table_rows.append("|-------|-------|------|-------------|-------------|------------|------------|------------|-----------|------------|")
    
    for _, row in comparison_data.iterrows():
        well_table_rows.append(
            f"| {int(row['API12'])} | {row['field_name']} | {row['well_name']} | "
            f"{int(row['lease_drilling_days'])} | {int(row['api12_drilling_days'])} | {int(row['drilling_diff'])} | "
            f"{int(row['lease_completion_days'])} | {int(row['api12_completion_days'])} | {int(row['completion_diff'])} | {int(row['total_diff'])} |"
        )
    
    well_details_table = "\n".join(well_table_rows)
    
    # Field summary table
    field_summary = comparison_data.groupby('field_name').agg({
        'drilling_diff': ['mean', 'min', 'max'],
        'completion_diff': ['mean', 'min', 'max'],
        'total_diff': ['mean', 'min', 'max'],
        'API12': 'count'
    }).round(1)
    
    field_table_rows = []
    field_table_rows.append("| Field | Wells | Avg Drill Diff | Min Drill | Max Drill | Avg Comp Diff | Min Comp | Max Comp | Avg Total Diff |")
    field_table_rows.append("|-------|-------|----------------|-----------|-----------|---------------|----------|----------|----------------|")
    
    for field in field_summary.index:
        field_table_rows.append(
            f"| {field} | {int(field_summary.loc[field, ('API12', 'count')])} | "
            f"{field_summary.loc[field, ('drilling_diff', 'mean')]:.1f} | "
            f"{field_summary.loc[field, ('drilling_diff', 'min')]:.0f} | "
            f"{field_summary.loc[field, ('drilling_diff', 'max')]:.0f} | "
            f"{field_summary.loc[field, ('completion_diff', 'mean')]:.1f} | "
            f"{field_summary.loc[field, ('completion_diff', 'min')]:.0f} | "
            f"{field_summary.loc[field, ('completion_diff', 'max')]:.0f} | "
            f"{field_summary.loc[field, ('total_diff', 'mean')]:.1f} |"
        )
    
    field_summary_table = "\n".join(field_table_rows)
    
    # Extreme cases table
    max_total_idx = comparison_data['total_diff'].idxmax()
    min_total_idx = comparison_data['total_diff'].idxmin()
    max_drill_idx = comparison_data['drilling_diff'].idxmax()
    min_drill_idx = comparison_data['drilling_diff'].idxmin()
    
    extreme_cases_table = f"""
| Case | API12 | Field | Well | Lease Drill | API12 Drill | Drill Diff | Lease Comp | API12 Comp | Comp Diff | Total Diff |
|------|-------|-------|------|-------------|-------------|------------|------------|------------|-----------|------------|
| Highest Total Diff | {int(comparison_data.loc[max_total_idx, 'API12'])} | {comparison_data.loc[max_total_idx, 'field_name']} | {comparison_data.loc[max_total_idx, 'well_name']} | {int(comparison_data.loc[max_total_idx, 'lease_drilling_days'])} | {int(comparison_data.loc[max_total_idx, 'api12_drilling_days'])} | {int(comparison_data.loc[max_total_idx, 'drilling_diff'])} | {int(comparison_data.loc[max_total_idx, 'lease_completion_days'])} | {int(comparison_data.loc[max_total_idx, 'api12_completion_days'])} | {int(comparison_data.loc[max_total_idx, 'completion_diff'])} | {int(comparison_data.loc[max_total_idx, 'total_diff'])} |
| Lowest Total Diff | {int(comparison_data.loc[min_total_idx, 'API12'])} | {comparison_data.loc[min_total_idx, 'field_name']} | {comparison_data.loc[min_total_idx, 'well_name']} | {int(comparison_data.loc[min_total_idx, 'lease_drilling_days'])} | {int(comparison_data.loc[min_total_idx, 'api12_drilling_days'])} | {int(comparison_data.loc[min_total_idx, 'drilling_diff'])} | {int(comparison_data.loc[min_total_idx, 'lease_completion_days'])} | {int(comparison_data.loc[min_total_idx, 'api12_completion_days'])} | {int(comparison_data.loc[min_total_idx, 'completion_diff'])} | {int(comparison_data.loc[min_total_idx, 'total_diff'])} |
| Highest Drill Diff | {int(comparison_data.loc[max_drill_idx, 'API12'])} | {comparison_data.loc[max_drill_idx, 'field_name']} | {comparison_data.loc[max_drill_idx, 'well_name']} | {int(comparison_data.loc[max_drill_idx, 'lease_drilling_days'])} | {int(comparison_data.loc[max_drill_idx, 'api12_drilling_days'])} | {int(comparison_data.loc[max_drill_idx, 'drilling_diff'])} | {int(comparison_data.loc[max_drill_idx, 'lease_completion_days'])} | {int(comparison_data.loc[max_drill_idx, 'api12_completion_days'])} | {int(comparison_data.loc[max_drill_idx, 'completion_diff'])} | {int(comparison_data.loc[max_drill_idx, 'total_diff'])} |
| Lowest Drill Diff | {int(comparison_data.loc[min_drill_idx, 'API12'])} | {comparison_data.loc[min_drill_idx, 'field_name']} | {comparison_data.loc[min_drill_idx, 'well_name']} | {int(comparison_data.loc[min_drill_idx, 'lease_drilling_days'])} | {int(comparison_data.loc[min_drill_idx, 'api12_drilling_days'])} | {int(comparison_data.loc[min_drill_idx, 'drilling_diff'])} | {int(comparison_data.loc[min_drill_idx, 'lease_completion_days'])} | {int(comparison_data.loc[min_drill_idx, 'api12_completion_days'])} | {int(comparison_data.loc[min_drill_idx, 'completion_diff'])} | {int(comparison_data.loc[min_drill_idx, 'total_diff'])} |
"""
    
    return {
        'methodology_comparison': methodology_table,
        'well_details_table': well_details_table,
        'field_summary_table': field_summary_table,
        'extreme_cases_table': extreme_cases_table
    }


def generate_recommendations(comparison_data: pd.DataFrame, methodology_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Generate actionable recommendations based on analysis.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        methodology_data (Dict[str, Any]): Methodology information
        
    Returns:
        Dict[str, List[str]]: Categorized recommendations
    """
    high_diff_count = len(comparison_data[comparison_data['total_diff'] > 100])
    
    immediate_actions = [
        f"Investigate the {high_diff_count} wells with differences >100 days to understand specific causes",
        "Focus on Stones field wells (showing highest differences) for detailed timeline analysis",
        "Validate milestone calculation logic in WellRigDays framework against known drilling histories",
        "Compare gap threshold appropriateness (300 days drilling, 8 days completion) against actual field data"
    ]
    
    methodology_improvements = [
        "Develop hybrid approach combining WAR data granularity with milestone framework benefits",
        "Implement configurable gap thresholds based on field-specific or well-specific characteristics",
        "Add data quality indicators to identify wells where method differences may be due to data issues",
        "Create validation framework to cross-check both methods against external drilling timeline data"
    ]
    
    validation_steps = [
        "Select 10-15 wells across different fields for detailed manual timeline validation",
        "Compare both methods against operator-reported drilling and completion timelines",
        "Analyze correlation between data completeness and calculation accuracy",
        "Validate WellRigDays milestone logic against raw WAR data for representative wells"
    ]
    
    future_research = [
        "Investigate machine learning approaches for improved timeline reconstruction",
        "Study field-specific patterns in methodology differences",
        "Develop uncertainty quantification for both calculation methods",
        "Research optimal gap thresholds based on drilling technology and field characteristics"
    ]
    
    return {
        'immediate_actions': immediate_actions,
        'methodology_improvements': methodology_improvements,
        'validation_steps': validation_steps,
        'future_research': future_research
    }


def generate_methodology_comparison_table() -> str:
    """
    Generate detailed methodology comparison table.
    
    Returns:
        str: Markdown table comparing methodologies
    """
    return """
| Aspect | Lease Method | API12 Method |
|--------|--------------|--------------|
| **Data Sources** | WAR binary files (mv_war_main.bin, mv_war_boreholes_view.bin, mv_war_main_prop.bin), CSV lease data | Structured well data + WellRigDays framework integration |
| **Primary Approach** | Timeline-based analysis with gap handling | Milestone-based phase calculation |
| **Drilling Days Logic** | (TD_DATE - ADJUSTED_SPUD_DATE) - early_days with 300-day gap threshold | WellRigDays framework using milestone DRL phases |
| **Completion Days Logic** | Post-TD WAR analysis with 8-day gap threshold for activity segments | Milestone completion phase extraction from framework |
| **Gap Handling** | Fixed thresholds: 300 days for drilling interruptions, 8 days for completion | Framework-determined milestone logic |
| **Timeline Construction** | Raw WAR start/end dates with custom gap analysis | Aggregated milestone phase durations |
| **Data Granularity** | Individual WAR record level with start/end timestamps | Aggregated milestone phase level |
| **Architecture** | Monolithic DrillingCompletionDays class (7 functions) | Framework integration WellAPI12 class (20 functions) |
| **File Processing** | Direct pickle file loading + CSV processing | Framework-based data access through specialized classes |
| **Output Format** | Single Excel file with timestamp | Multiple CSV files + visualization support |
| **Complexity** | O(n*m) where n=wells, m=WAR records per well | O(n) well processing + WellRigDays overhead |
| **Business Rules** | Explicit gap thresholds and timeline restart logic | WellRigDays framework validation and milestone accuracy |
| **Strengths** | Direct WAR data access, comprehensive gap analysis | Specialized framework, multi-well analysis, visualization |
| **Limitations** | Dependent on WAR data quality, fixed thresholds | Dependent on WellRigDays implementation, framework complexity |
"""


def calculate_accuracy_metrics(comparison_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate accuracy metrics comparing the two methods.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        
    Returns:
        Dict[str, Any]: Accuracy metrics
    """
    lease_drilling = comparison_data['lease_drilling_days']
    api12_drilling = comparison_data['api12_drilling_days']
    lease_completion = comparison_data['lease_completion_days']
    api12_completion = comparison_data['api12_completion_days']
    
    # Drilling accuracy metrics
    drilling_mae = np.mean(np.abs(lease_drilling - api12_drilling))
    drilling_rmse = np.sqrt(np.mean((lease_drilling - api12_drilling)**2))
    drilling_corr = np.corrcoef(lease_drilling, api12_drilling)[0, 1]
    
    # Completion accuracy metrics
    completion_mae = np.mean(np.abs(lease_completion - api12_completion))
    completion_rmse = np.sqrt(np.mean((lease_completion - api12_completion)**2))
    completion_corr = np.corrcoef(lease_completion, api12_completion)[0, 1]
    
    # Distribution analysis
    drilling_diffs = comparison_data['drilling_diff']
    completion_diffs = comparison_data['completion_diff']
    
    # Outlier analysis (using IQR method)
    def identify_outliers(series):
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return series[(series < lower_bound) | (series > upper_bound)]
    
    drilling_outliers = identify_outliers(drilling_diffs)
    completion_outliers = identify_outliers(completion_diffs)
    
    return {
        'agreement_statistics': {
            'drilling_mae': float(drilling_mae),
            'drilling_rmse': float(drilling_rmse),
            'drilling_correlation': float(drilling_corr),
            'completion_mae': float(completion_mae),
            'completion_rmse': float(completion_rmse),
            'completion_correlation': float(completion_corr),
            'mean_absolute_error': float(np.mean(np.abs(comparison_data['total_diff']))),
            'root_mean_squared_error': float(np.sqrt(np.mean(comparison_data['total_diff']**2))),
            'correlation_coefficient': float(np.corrcoef(
                lease_drilling + lease_completion, 
                api12_drilling + api12_completion
            )[0, 1])
        },
        'difference_distribution': {
            'drilling_diff_range': [float(drilling_diffs.min()), float(drilling_diffs.max())],
            'completion_diff_range': [float(completion_diffs.min()), float(completion_diffs.max())],
            'total_diff_range': [float(comparison_data['total_diff'].min()), float(comparison_data['total_diff'].max())]
        },
        'outlier_analysis': {
            'drilling_outliers': len(drilling_outliers),
            'completion_outliers': len(completion_outliers),
            'drilling_outlier_wells': drilling_outliers.index.tolist(),
            'completion_outlier_wells': completion_outliers.index.tolist()
        }
    }


def compile_comprehensive_report(comparison_data: pd.DataFrame, methodology_data: Dict[str, Any]) -> str:
    """
    Compile comprehensive markdown report.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        methodology_data (Dict[str, Any]): Methodology information
        
    Returns:
        str: Complete markdown report
    """
    # Generate all analysis components
    exec_summary = generate_executive_summary(comparison_data, methodology_data)
    calc_diffs = analyze_calculation_differences(comparison_data)
    field_analysis = generate_field_analysis(comparison_data)
    root_causes = identify_root_causes(comparison_data, methodology_data)
    statistical_analysis = generate_statistical_analysis(comparison_data)
    tables = create_comparison_tables(comparison_data)
    enhanced_tables = create_enhanced_tables(comparison_data)
    methodology_tables = create_methodology_documentation_tables()
    recommendations = generate_recommendations(comparison_data, methodology_data)
    accuracy_metrics = calculate_accuracy_metrics(comparison_data)
    
    # Compile report
    report = f"""# Root Cause Analysis Report: API12 Drilling Completion Days Comparison

**Analysis Date**: {datetime.now().strftime('%B %d, %Y')}  
**Purpose**: Comprehensive analysis comparing lease-based and API12-based drilling completion day calculation methodologies  
**Dataset**: {exec_summary['total_wells_analyzed']} wells across {len(exec_summary['fields_analyzed'])} fields

## Executive Summary

This comprehensive analysis compares two different approaches to calculating drilling and completion days in BSEE oil and gas well data:

1. **Lease Method**: Timeline-based analysis using raw WAR (Well Activity Reports) data with gap thresholds
2. **API12 Method**: Milestone-based analysis using WellRigDays framework integration

### Key Findings

{chr(10).join(f'• {finding}' for finding in exec_summary['key_findings'])}

### Statistical Overview

- **Average Drilling Difference**: {exec_summary['average_drilling_difference']:.1f} days
- **Average Completion Difference**: {exec_summary['average_completion_difference']:.1f} days  
- **Maximum Total Difference**: {exec_summary['maximum_difference']:.0f} days
- **Minimum Total Difference**: {exec_summary['minimum_difference']:.0f} days
- **Wells with >100 days difference**: {exec_summary['high_difference_wells_count']}

## Methodology Comparison

### High-Level Comparison
{tables['methodology_comparison']}

### Data Flow Process
{methodology_tables['data_flow_table']}

### Algorithm Complexity
{methodology_tables['algorithm_table']}

### Business Rules Implementation
{methodology_tables['business_rules_table']}

### Error Handling Strategies
{methodology_tables['error_handling_table']}

## Statistical Analysis

### Distribution Analysis
{enhanced_tables['distribution_table']}

### Percentile Analysis
{enhanced_tables['percentile_table']}

### Drilling Days Differences
- **Mean**: {statistical_analysis['drilling_differences']['mean']:.2f} days
- **Median**: {statistical_analysis['drilling_differences']['median']:.2f} days
- **Standard Deviation**: {statistical_analysis['drilling_differences']['std']:.2f} days
- **Range**: {statistical_analysis['drilling_differences']['min']:.0f} to {statistical_analysis['drilling_differences']['max']:.0f} days
- **Interquartile Range**: {statistical_analysis['drilling_differences']['q25']:.1f} to {statistical_analysis['drilling_differences']['q75']:.1f} days

### Completion Days Differences
- **Mean**: {statistical_analysis['completion_differences']['mean']:.2f} days
- **Median**: {statistical_analysis['completion_differences']['median']:.2f} days
- **Standard Deviation**: {statistical_analysis['completion_differences']['std']:.2f} days
- **Range**: {statistical_analysis['completion_differences']['min']:.0f} to {statistical_analysis['completion_differences']['max']:.0f} days
- **Interquartile Range**: {statistical_analysis['completion_differences']['q25']:.1f} to {statistical_analysis['completion_differences']['q75']:.1f} days

### Agreement Metrics
- **Mean Absolute Error**: {accuracy_metrics['agreement_statistics']['mean_absolute_error']:.2f} days
- **Root Mean Squared Error**: {accuracy_metrics['agreement_statistics']['root_mean_squared_error']:.2f} days
- **Correlation Coefficient**: {accuracy_metrics['agreement_statistics']['correlation_coefficient']:.3f}
- **Drilling Correlation**: {accuracy_metrics['agreement_statistics']['drilling_correlation']:.3f}
- **Completion Correlation**: {accuracy_metrics['agreement_statistics']['completion_correlation']:.3f}

### Correlation Analysis
{enhanced_tables['correlation_table']}

### Data Quality Analysis
{enhanced_tables['data_quality_table']}

## Field-by-Field Analysis

{tables['field_summary_table']}

### Field-Specific Insights

"""

    # Add field-specific analysis
    for field_name, analysis in field_analysis.items():
        report += f"""
#### {field_name}
- **Wells Analyzed**: {analysis['wells_count']}
- **Average Drilling Difference**: {analysis['average_drilling_diff']:.1f} days
- **Average Completion Difference**: {analysis['average_completion_diff']:.1f} days
- **Average Total Difference**: {analysis['average_total_diff']:.1f} days
- **Drilling Range**: {analysis['min_drilling_diff']:.0f} to {analysis['max_drilling_diff']:.0f} days
- **Completion Range**: {analysis['min_completion_diff']:.0f} to {analysis['max_completion_diff']:.0f} days
"""

    report += f"""
## Extreme Cases Analysis

{tables['extreme_cases_table']}

### Case Studies

#### Highest Total Difference: API12 {calc_diffs['extreme_cases']['highest_drilling_diff']['api12']}
- **Well**: {calc_diffs['extreme_cases']['highest_drilling_diff']['well_name']} in {calc_diffs['extreme_cases']['highest_drilling_diff']['field']} field
- **Drilling Difference**: {calc_diffs['extreme_cases']['highest_drilling_diff']['diff']:.0f} days
- **Potential Cause**: Likely due to drilling interruptions captured by lease method but aggregated by API12 method

#### Lowest Total Difference: API12 {calc_diffs['extreme_cases']['lowest_drilling_diff']['api12']}
- **Well**: {calc_diffs['extreme_cases']['lowest_drilling_diff']['well_name']} in {calc_diffs['extreme_cases']['lowest_drilling_diff']['field']} field
- **Drilling Difference**: {calc_diffs['extreme_cases']['lowest_drilling_diff']['diff']:.0f} days
- **Potential Cause**: Simple drilling timeline with minimal interruptions

## Root Cause Analysis

### Primary Factors Contributing to Differences

{chr(10).join(f'{i+1}. {factor}' for i, factor in enumerate(root_causes['primary_factors']))}

### Methodology-Specific Impacts

{chr(10).join(f'• {impact}' for impact in root_causes['methodology_impacts'])}

### Data Quality Considerations

{chr(10).join(f'• {factor}' for factor in root_causes['data_quality_factors'])}

### Fields Most Affected

The following fields show the highest average total differences:
{chr(10).join(f'• {field}' for field in root_causes['high_difference_analysis']['fields_most_affected'])}

## Well Details

{tables['well_details_table']}

## Recommendations

### Immediate Actions
{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(recommendations['immediate_actions']))}

### Methodology Improvements
{chr(10).join(f'{i+1}. {improvement}' for i, improvement in enumerate(recommendations['methodology_improvements']))}

### Validation Steps
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(recommendations['validation_steps']))}

### Future Research Directions
{chr(10).join(f'{i+1}. {research}' for i, research in enumerate(recommendations['future_research']))}

## Conclusion

This analysis reveals significant methodological differences between the lease-based and API12-based approaches to calculating drilling and completion days. The key findings indicate that:

1. **Timeline Reconstruction Methods** are the primary source of differences, with the lease method using raw WAR timeline analysis while the API12 method uses milestone-based phase calculations.

2. **Gap Handling Philosophy** differs significantly, with fixed thresholds in the lease method versus framework-determined logic in the API12 method.

3. **Data Source Granularity** impacts accuracy, with the lease method processing individual WAR records while the API12 method uses aggregated milestone data.

4. **Extreme Differences** (>100 days) occur in {exec_summary['high_difference_wells_count']} wells, primarily due to different treatment of drilling interruptions and timeline reconstruction methods.

### Recommended Next Steps

1. **Immediate**: Focus validation efforts on the {exec_summary['high_difference_wells_count']} wells showing extreme differences
2. **Short-term**: Implement hybrid approach combining WAR granularity with milestone framework benefits  
3. **Long-term**: Develop adaptive gap thresholds and uncertainty quantification for both methods

This analysis provides the foundation for improving drilling and completion day calculations and ensuring consistency across different analytical approaches in the energy industry.

---

*Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} as part of the API12 drilling completion days methodology comparison study.*
"""

    return report


def save_report_to_file(report_content: str, output_path: str) -> bool:
    """
    Save report to markdown file.
    
    Args:
        report_content (str): Report content
        output_path (str): Output file path
        
    Returns:
        bool: Success status
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return True
    except Exception as e:
        print(f"Error saving report: {e}")
        return False


def create_enhanced_tables(comparison_data: pd.DataFrame) -> Dict[str, str]:
    """
    Create enhanced tabular comparisons for the report.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        
    Returns:
        Dict[str, str]: Dictionary of enhanced markdown tables
    """
    # Create distribution analysis table
    distribution_table_rows = []
    distribution_table_rows.append("| Difference Range (days) | Drilling Count | Drilling % | Completion Count | Completion % | Total Count | Total % |")
    distribution_table_rows.append("|-------------------------|----------------|------------|------------------|--------------|-------------|---------|")
    
    total_wells = len(comparison_data)
    
    # Define ranges
    ranges = [
        ("< -50", lambda x: x < -50),
        ("-50 to 0", lambda x: (-50 <= x) & (x < 0)),
        ("0 to 50", lambda x: (0 <= x) & (x <= 50)),
        ("51 to 100", lambda x: (50 < x) & (x <= 100)),
        ("101 to 200", lambda x: (100 < x) & (x <= 200)),
        ("> 200", lambda x: x > 200)
    ]
    
    for range_label, condition in ranges:
        drill_count = len(comparison_data[condition(comparison_data['drilling_diff'])])
        comp_count = len(comparison_data[condition(comparison_data['completion_diff'])])
        total_count = len(comparison_data[condition(comparison_data['total_diff'])])
        
        distribution_table_rows.append(
            f"| {range_label} | {drill_count} | {drill_count/total_wells*100:.1f}% | "
            f"{comp_count} | {comp_count/total_wells*100:.1f}% | "
            f"{total_count} | {total_count/total_wells*100:.1f}% |"
        )
    
    distribution_table = "\n".join(distribution_table_rows)
    
    # Create data quality analysis table
    quality_table = """
| Data Quality Indicator | Lease Method | API12 Method | Impact on Differences |
|------------------------|--------------|--------------|----------------------|
| **Zero Values** | {lease_zero_drill} drilling, {lease_zero_comp} completion | {api12_zero_drill} drilling, {api12_zero_comp} completion | Zero values may indicate missing data or method limitations |
| **Negative Differences** | N/A | N/A | {neg_drill} drilling, {neg_comp} completion wells show API12 > Lease |
| **Extreme Values (>200d)** | {lease_extreme} wells | {api12_extreme} wells | {extreme_diff} wells with extreme differences |
| **Data Completeness** | Depends on WAR records | Depends on WellRigDays | Incomplete data amplifies differences |
""".format(
        lease_zero_drill=len(comparison_data[comparison_data['lease_drilling_days'] == 0]),
        lease_zero_comp=len(comparison_data[comparison_data['lease_completion_days'] == 0]),
        api12_zero_drill=len(comparison_data[comparison_data['api12_drilling_days'] == 0]),
        api12_zero_comp=len(comparison_data[comparison_data['api12_completion_days'] == 0]),
        neg_drill=len(comparison_data[comparison_data['drilling_diff'] < 0]),
        neg_comp=len(comparison_data[comparison_data['completion_diff'] < 0]),
        lease_extreme=len(comparison_data[comparison_data['lease_drilling_days'] > 200]),
        api12_extreme=len(comparison_data[comparison_data['api12_drilling_days'] > 200]),
        extreme_diff=len(comparison_data[comparison_data['total_diff'].abs() > 200])
    )
    
    # Create correlation analysis table
    correlation_table_rows = []
    correlation_table_rows.append("| Metric Pair | Correlation | Interpretation |")
    correlation_table_rows.append("|-------------|-------------|----------------|")
    
    # Calculate correlations
    correlations = [
        ("Lease Drilling vs API12 Drilling", 
         comparison_data['lease_drilling_days'].corr(comparison_data['api12_drilling_days']),
         "Method agreement on drilling duration"),
        ("Lease Completion vs API12 Completion",
         comparison_data['lease_completion_days'].corr(comparison_data['api12_completion_days']),
         "Method agreement on completion duration"),
        ("Drilling Diff vs Completion Diff",
         comparison_data['drilling_diff'].corr(comparison_data['completion_diff']),
         "Independence of calculation differences"),
        ("Lease Total vs API12 Total",
         (comparison_data['lease_drilling_days'] + comparison_data['lease_completion_days']).corr(
         comparison_data['api12_drilling_days'] + comparison_data['api12_completion_days']),
         "Overall method agreement")
    ]
    
    for metric_pair, corr_value, interpretation in correlations:
        correlation_table_rows.append(
            f"| {metric_pair} | {corr_value:.3f} | {interpretation} |"
        )
    
    correlation_table = "\n".join(correlation_table_rows)
    
    # Create percentile analysis table
    percentile_table_rows = []
    percentile_table_rows.append("| Percentile | Drilling Diff (days) | Completion Diff (days) | Total Diff (days) |")
    percentile_table_rows.append("|------------|---------------------|------------------------|-------------------|")
    
    percentiles = [5, 10, 25, 50, 75, 90, 95]
    for p in percentiles:
        drill_p = comparison_data['drilling_diff'].quantile(p/100)
        comp_p = comparison_data['completion_diff'].quantile(p/100)
        total_p = comparison_data['total_diff'].quantile(p/100)
        percentile_table_rows.append(
            f"| P{p} | {drill_p:.1f} | {comp_p:.1f} | {total_p:.1f} |"
        )
    
    percentile_table = "\n".join(percentile_table_rows)
    
    return {
        'distribution_table': distribution_table,
        'data_quality_table': quality_table,
        'correlation_table': correlation_table,
        'percentile_table': percentile_table
    }


def create_methodology_documentation_tables() -> Dict[str, str]:
    """
    Create detailed methodology documentation tables.
    
    Returns:
        Dict[str, str]: Dictionary of methodology documentation tables
    """
    # Data flow comparison table
    data_flow_table = """
| Step | Lease Method | API12 Method |
|------|--------------|--------------|
| **1. Data Input** | Load pickle files (mv_war_*.bin) + CSV lease data | Access structured well data through framework |
| **2. Well Selection** | Match wells by API12 from lease CSV | Iterate through WellAPI12 objects |
| **3. Timeline Extraction** | Extract WAR start/end dates for each well | Access WellRigDays milestone data |
| **4. Drilling Calculation** | TD_DATE - ADJUSTED_SPUD_DATE with gap logic | Sum DRL milestone phases |
| **5. Gap Analysis** | Apply 300-day threshold for drilling gaps | Framework handles gap logic internally |
| **6. Completion Calculation** | Analyze post-TD WAR records with 8-day gaps | Extract completion milestone phases |
| **7. Data Output** | Write single Excel file with all results | Generate multiple CSV files + plots |
| **8. Validation** | Check data completeness and date logic | Framework validation + consistency checks |
"""
    
    # Algorithm complexity comparison table
    algorithm_table = """
| Algorithm Aspect | Lease Method | API12 Method |
|------------------|--------------|--------------|
| **Time Complexity** | O(n × m) where n=wells, m=WAR records | O(n × k) where n=wells, k=milestones |
| **Space Complexity** | O(n × m) for WAR data storage | O(n) for well objects + framework |
| **Processing Pattern** | Sequential iteration through WAR records | Framework-based milestone aggregation |
| **Memory Usage** | High (loads all WAR data) | Moderate (framework abstraction) |
| **Parallelization** | Limited (shared pickle data) | Possible (independent well objects) |
| **Scalability** | Linear with data size | Linear with optimized framework |
"""
    
    # Business rules comparison table
    business_rules_table = """
| Business Rule | Lease Method Implementation | API12 Method Implementation |
|---------------|----------------------------|----------------------------|
| **Drilling Start** | ADJUSTED_SPUD_DATE from WAR | First DRL milestone date |
| **Drilling End** | TD_DATE from WAR records | Last DRL milestone date |
| **Drilling Interruptions** | Gaps > 300 days restart timeline | Handled by WellRigDays logic |
| **Completion Start** | First post-TD WAR activity | First completion milestone |
| **Completion End** | Last WAR activity date | Last completion milestone |
| **Completion Gaps** | Gaps > 8 days split segments | Framework milestone logic |
| **Early Activities** | Subtract pre-spud days | Included in milestone calculation |
| **Data Quality** | Skip if missing critical dates | Framework validation rules |
"""
    
    # Error handling comparison table
    error_handling_table = """
| Error Type | Lease Method Handling | API12 Method Handling |
|------------|----------------------|----------------------|
| **Missing Data** | Skip well with warning | Framework default values or skip |
| **Invalid Dates** | Date validation checks | Framework date validation |
| **Data Conflicts** | Use first valid occurrence | Framework resolution logic |
| **Calculation Errors** | Try-except blocks with logging | Framework error propagation |
| **Output Errors** | Excel write error handling | CSV write error handling |
| **Memory Issues** | Load data in chunks | Framework memory management |
"""
    
    return {
        'data_flow_table': data_flow_table,
        'algorithm_table': algorithm_table,
        'business_rules_table': business_rules_table,
        'error_handling_table': error_handling_table
    }


def export_analysis_data(comparison_data: pd.DataFrame, methodology_data: Dict[str, Any], output_path: str) -> bool:
    """
    Export analysis data to JSON format.
    
    Args:
        comparison_data (pd.DataFrame): Well comparison data
        methodology_data (Dict[str, Any]): Methodology information
        output_path (str): Output file path
        
    Returns:
        bool: Success status
    """
    try:
        # Generate analysis components
        exec_summary = generate_executive_summary(comparison_data, methodology_data)
        statistical_analysis = generate_statistical_analysis(comparison_data)
        field_analysis = generate_field_analysis(comparison_data)
        root_causes = identify_root_causes(comparison_data, methodology_data)
        accuracy_metrics = calculate_accuracy_metrics(comparison_data)
        
        # Compile export data
        export_data = {
            'analysis_date': datetime.now().isoformat(),
            'dataset_info': {
                'total_wells': len(comparison_data),
                'total_fields': len(comparison_data['field_name'].unique()),
                'fields': comparison_data['field_name'].unique().tolist()
            },
            'comparison_data': comparison_data.to_dict('records'),
            'methodology_data': methodology_data,
            'executive_summary': exec_summary,
            'statistical_analysis': statistical_analysis,
            'field_analysis': field_analysis,
            'root_cause_analysis': root_causes,
            'accuracy_metrics': accuracy_metrics
        }
        
        # Save to JSON file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return True
    except Exception as e:
        print(f"Error exporting analysis data: {e}")
        return False