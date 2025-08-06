"""
Well selector module for API12 drilling completion analysis.

This module provides functions to select representative wells with high and low
differences in drilling and completion days between lease-based and API12-based methods,
with focus on selecting wells from different lease names/fields.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
from .data_loader import calculate_differences


def find_high_difference_well(comparison_df: pd.DataFrame) -> pd.Series:
    """
    Find the well with the highest total difference in drilling and completion days.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        
    Returns:
        pd.Series: Row representing the well with highest total difference
    """
    if comparison_df.empty:
        raise ValueError("Empty dataset provided")
    
    max_idx = comparison_df['total_diff'].idxmax()
    return comparison_df.loc[max_idx]


def find_low_difference_well(comparison_df: pd.DataFrame) -> pd.Series:
    """
    Find the well with the lowest total difference in drilling and completion days.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        
    Returns:
        pd.Series: Row representing the well with lowest total difference
    """
    if comparison_df.empty:
        raise ValueError("Empty dataset provided")
    
    min_idx = comparison_df['total_diff'].idxmin()
    return comparison_df.loc[min_idx]


def select_representative_wells(comparison_df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Select representative wells with high and low differences.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        
    Returns:
        Tuple[pd.Series, pd.Series]: High difference well, Low difference well
        
    Raises:
        ValueError: If dataset is empty
    """
    if comparison_df.empty:
        raise ValueError("Empty dataset provided")
    
    high_well = find_high_difference_well(comparison_df)
    low_well = find_low_difference_well(comparison_df)
    
    return high_well, low_well


def get_wells_by_field(comparison_df: pd.DataFrame, field_name: str, n_wells: int = 2) -> pd.DataFrame:
    """
    Get wells from a specific field/lease name.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        field_name (str): Name of the field/lease
        n_wells (int): Number of wells to return (default: 2)
        
    Returns:
        pd.DataFrame: Wells from the specified field
    """
    field_wells = comparison_df[comparison_df['field_name'] == field_name].copy()
    
    if field_wells.empty:
        return pd.DataFrame()
    
    # Sort by total difference to get most representative wells
    field_wells = field_wells.sort_values('total_diff', ascending=False)
    
    return field_wells.head(n_wells)


def analyze_wells_by_field(comparison_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Analyze wells grouped by field name, selecting two representative wells from each.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        
    Returns:
        Dict[str, Dict[str, Any]]: Analysis results by field name
    """
    results = {}
    
    # Get unique field names
    field_names = comparison_df['field_name'].unique()
    
    for field_name in field_names:
        field_wells = get_wells_by_field(comparison_df, field_name, n_wells=2)
        
        if field_wells.empty:
            continue
            
        # Calculate field statistics
        field_stats = {
            'total_wells': len(comparison_df[comparison_df['field_name'] == field_name]),
            'wells_analyzed': len(field_wells),
            'selected_wells': [],
            'field_statistics': {
                'mean_drilling_diff': field_wells['drilling_diff'].mean(),
                'mean_completion_diff': field_wells['completion_diff'].mean(),
                'mean_total_diff': field_wells['total_diff'].mean(),
                'max_total_diff': field_wells['total_diff'].max(),
                'min_total_diff': field_wells['total_diff'].min()
            }
        }
        
        # Add well details
        for _, well in field_wells.iterrows():
            well_info = {
                'api12': well['api12'],
                'well_name': well['well_name'],
                'lease_drilling_days': well['lease_drilling_days'],
                'api12_drilling_days': well['api12_drilling_days'],
                'drilling_diff': well['drilling_diff'],
                'lease_completion_days': well['lease_completion_days'],
                'api12_completion_days': well['api12_completion_days'],
                'completion_diff': well['completion_diff'],
                'total_diff': well['total_diff']
            }
            field_stats['selected_wells'].append(well_info)
        
        results[field_name] = field_stats
    
    return results


def get_well_details(comparison_df: pd.DataFrame, api12_num: int) -> Dict[str, Any]:
    """
    Get detailed information for a specific well.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        api12_num (int): API12 number of the well
        
    Returns:
        Dict[str, Any]: Detailed well information
        
    Raises:
        ValueError: If well not found
    """
    well_row = comparison_df[comparison_df['api12'] == api12_num]
    
    if well_row.empty:
        raise ValueError(f"Well with API12 {api12_num} not found in comparison data")
    
    well = well_row.iloc[0]
    
    return {
        'api12': well['api12'],
        'well_name': well['well_name'],
        'field_name': well['field_name'],
        'lease_drilling_days': well['lease_drilling_days'],
        'api12_drilling_days': well['api12_drilling_days'],
        'drilling_diff': well['drilling_diff'],
        'lease_completion_days': well['lease_completion_days'],
        'api12_completion_days': well['api12_completion_days'],
        'completion_diff': well['completion_diff'],
        'total_diff': well['total_diff']
    }


def calculate_difference_statistics(comparison_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Calculate statistical summary of differences.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        
    Returns:
        Dict[str, Dict[str, float]]: Statistics for each difference type
    """
    stats = {}
    
    for diff_type in ['drilling_diff', 'completion_diff', 'total_diff']:
        if diff_type in comparison_df.columns:
            data = comparison_df[diff_type]
            stats[diff_type] = {
                'mean': float(data.mean()),
                'std': float(data.std()),
                'min': float(data.min()),
                'max': float(data.max()),
                'median': float(data.median()),
                'q25': float(data.quantile(0.25)),
                'q75': float(data.quantile(0.75))
            }
    
    return stats


def filter_wells_by_criteria(comparison_df: pd.DataFrame, criteria: Dict[str, Tuple[str, float]]) -> pd.DataFrame:
    """
    Filter wells based on specified criteria.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        criteria (Dict[str, Tuple[str, float]]): Filtering criteria
            Format: {'column_name': ('operator', value)}
            Operators: '>', '<', '>=', '<=', '==', '!='
    
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    filtered_df = comparison_df.copy()
    
    for column, (operator, value) in criteria.items():
        if column not in filtered_df.columns:
            continue
            
        if operator == '>':
            filtered_df = filtered_df[filtered_df[column] > value]
        elif operator == '<':
            filtered_df = filtered_df[filtered_df[column] < value]
        elif operator == '>=':
            filtered_df = filtered_df[filtered_df[column] >= value]
        elif operator == '<=':
            filtered_df = filtered_df[filtered_df[column] <= value]
        elif operator == '==':
            filtered_df = filtered_df[filtered_df[column] == value]
        elif operator == '!=':
            filtered_df = filtered_df[filtered_df[column] != value]
    
    return filtered_df


def rank_wells_by_difference(comparison_df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    """
    Rank wells by total difference.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        ascending (bool): Sort order (default: False for descending)
        
    Returns:
        pd.DataFrame: DataFrame sorted by total difference
    """
    return comparison_df.sort_values('total_diff', ascending=ascending).reset_index(drop=True)


def validate_well_selection(comparison_df: pd.DataFrame, selected_wells: List[int]) -> bool:
    """
    Validate that selected wells exist in the comparison data.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison data
        selected_wells (List[int]): List of API12 numbers to validate
        
    Returns:
        bool: True if all wells exist, False otherwise
    """
    available_wells = set(comparison_df['api12'].astype('int64'))
    selected_wells_set = set(selected_wells)
    
    return selected_wells_set.issubset(available_wells)


def generate_well_comparison_summary(lease_df: pd.DataFrame, api12_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate comprehensive summary of well comparisons between lease and API12 methods.
    
    Args:
        lease_df (pd.DataFrame): Standardized lease data
        api12_df (pd.DataFrame): Standardized API12 data
        
    Returns:
        Dict[str, Any]: Comprehensive comparison summary
    """
    # Calculate differences
    comparison_df = calculate_differences(lease_df, api12_df)
    
    # Overall statistics
    overall_stats = calculate_difference_statistics(comparison_df)
    
    # Analysis by field
    field_analysis = analyze_wells_by_field(comparison_df)
    
    # Representative wells
    high_well, low_well = select_representative_wells(comparison_df)
    
    # Field summary
    field_summary = {}
    for field_name in comparison_df['field_name'].unique():
        field_data = comparison_df[comparison_df['field_name'] == field_name]
        field_summary[field_name] = {
            'well_count': len(field_data),
            'avg_drilling_diff': float(field_data['drilling_diff'].mean()),
            'avg_completion_diff': float(field_data['completion_diff'].mean()),
            'avg_total_diff': float(field_data['total_diff'].mean())
        }
    
    return {
        'summary': {
            'total_wells': len(comparison_df),
            'total_fields': len(comparison_df['field_name'].unique()),
            'fields': list(comparison_df['field_name'].unique())
        },
        'overall_statistics': overall_stats,
        'field_analysis': field_analysis,
        'field_summary': field_summary,
        'representative_wells': {
            'high_difference': {
                'api12': high_well['api12'],
                'field_name': high_well['field_name'],
                'well_name': high_well['well_name'],
                'total_diff': high_well['total_diff'],
                'drilling_diff': high_well['drilling_diff'],
                'completion_diff': high_well['completion_diff']
            },
            'low_difference': {
                'api12': low_well['api12'],
                'field_name': low_well['field_name'],
                'well_name': low_well['well_name'],
                'total_diff': low_well['total_diff'],
                'drilling_diff': low_well['drilling_diff'],
                'completion_diff': low_well['completion_diff']
            }
        }
    }


def export_field_analysis_to_csv(field_analysis: Dict[str, Any], output_path: str) -> None:
    """
    Export field analysis results to CSV file.
    
    Args:
        field_analysis (Dict[str, Any]): Field analysis results
        output_path (str): Path to save CSV file
    """
    rows = []
    
    for field_name, field_data in field_analysis.items():
        for well_info in field_data['selected_wells']:
            row = {
                'field_name': field_name,
                'api12': well_info['api12'],
                'well_name': well_info['well_name'],
                'lease_drilling_days': well_info['lease_drilling_days'],
                'api12_drilling_days': well_info['api12_drilling_days'],
                'drilling_diff': well_info['drilling_diff'],
                'lease_completion_days': well_info['lease_completion_days'],
                'api12_completion_days': well_info['api12_completion_days'],
                'completion_diff': well_info['completion_diff'],
                'total_diff': well_info['total_diff']
            }
            rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)