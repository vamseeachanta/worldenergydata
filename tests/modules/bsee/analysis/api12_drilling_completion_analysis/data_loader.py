"""
Data loader module for API12 drilling completion analysis.

This module provides functions to load, validate, and standardize data 
from both lease-based and API12-based methods for drilling and completion 
days comparison analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List
import json
import re


def load_lease_data(file_path: str) -> pd.DataFrame:
    """
    Load lease method data from Excel file.
    
    Args:
        file_path (str): Path to the Excel file containing lease method data
        
    Returns:
        pd.DataFrame: Loaded lease data with standardized structure
        
    Raises:
        FileNotFoundError: If the file does not exist
        pd.errors.EmptyDataError: If the file is empty
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        df = pd.read_excel(file_path)
        
        # Convert data types
        df = convert_data_types_lease(df)
        
        return df
    except Exception as e:
        raise Exception(f"Error loading Excel file {file_path}: {str(e)}")


def load_api12_data(file_path: str) -> pd.DataFrame:
    """
    Load API12 method data from CSV file.
    
    Args:
        file_path (str): Path to the CSV file containing API12 method data
        
    Returns:
        pd.DataFrame: Loaded API12 data with standardized structure
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        df = pd.read_csv(file_path)
        
        # Convert data types
        df = convert_data_types_api12(df)
        
        # Parse rigdays_by_milestone JSON column if present
        if 'rigdays_by_milestone' in df.columns:
            df = parse_rigdays_milestone(df)
        
        return df
    except Exception as e:
        raise Exception(f"Error loading CSV file {file_path}: {str(e)}")


def validate_lease_columns(df: pd.DataFrame) -> bool:
    """
    Validate that lease data has required columns.
    
    Args:
        df (pd.DataFrame): Lease data DataFrame
        
    Returns:
        bool: True if all required columns are present
    """
    required_columns = [
        'API_WELL_NUMBER',
        'DRILLING_DAYS',
        'COMPLETION_DAYS',
        'WELL_SPUD_DATE',
        'TOTAL_DEPTH_DATE'
    ]
    
    return all(col in df.columns for col in required_columns)


def validate_api12_columns(df: pd.DataFrame) -> bool:
    """
    Validate that API12 data has required columns.
    
    Args:
        df (pd.DataFrame): API12 data DataFrame
        
    Returns:
        bool: True if all required columns are present
    """
    required_columns = [
        'API12',
        'Drilling Days',
        'Completion Days',
        'WELL_SPUD_DATE',
        'TOTAL_DEPTH_DATE'
    ]
    
    return all(col in df.columns for col in required_columns)


def standardize_data(lease_df: pd.DataFrame, api12_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Standardize column names and data structure for both datasets.
    
    Args:
        lease_df (pd.DataFrame): Lease method data
        api12_df (pd.DataFrame): API12 method data
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Standardized lease and API12 data
    """
    # Create standardized lease data
    lease_std = lease_df.copy()
    lease_std = lease_std.rename(columns={
        'API_WELL_NUMBER': 'api12',
        'DRILLING_DAYS': 'drilling_days',
        'COMPLETION_DAYS': 'completion_days',
        'WELL_SPUD_DATE': 'spud_date',
        'TOTAL_DEPTH_DATE': 'td_date',
        'WELL_NAME': 'well_name',
        'LEASE_NAME': 'field_name',
        'MAX_BH_TOTAL_MD': 'total_depth'
    })
    
    # Create standardized API12 data
    api12_std = api12_df.copy()
    api12_std = api12_std.rename(columns={
        'API12': 'api12',
        'Drilling Days': 'drilling_days',
        'Completion Days': 'completion_days',
        'WELL_SPUD_DATE': 'spud_date',
        'TOTAL_DEPTH_DATE': 'td_date',
        'WELL_NAME': 'well_name',
        'Total Measured Depth': 'total_depth'
    })
    
    # Ensure consistent data types - use int64 for API12, float64 for days
    if 'api12' in lease_std.columns:
        lease_std['api12'] = pd.to_numeric(lease_std['api12'], errors='coerce', downcast=None).astype('int64')
    if 'api12' in api12_std.columns:
        api12_std['api12'] = pd.to_numeric(api12_std['api12'], errors='coerce', downcast=None).astype('int64')
    
    for col in ['drilling_days', 'completion_days']:
        if col in lease_std.columns:
            lease_std[col] = pd.to_numeric(lease_std[col], errors='coerce')
        if col in api12_std.columns:
            api12_std[col] = pd.to_numeric(api12_std[col], errors='coerce')
    
    return lease_std, api12_std


def convert_data_types_lease(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert lease data to appropriate data types.
    
    Args:
        df (pd.DataFrame): Raw lease data
        
    Returns:
        pd.DataFrame: Data with converted types
    """
    df_converted = df.copy()
    
    # Convert API well number to int64 for large numbers
    if 'API_WELL_NUMBER' in df_converted.columns:
        df_converted['API_WELL_NUMBER'] = pd.to_numeric(df_converted['API_WELL_NUMBER'], errors='coerce', downcast=None).astype('int64')
    
    # Convert drilling and completion days to numeric
    for col in ['DRILLING_DAYS', 'COMPLETION_DAYS']:
        if col in df_converted.columns:
            df_converted[col] = pd.to_numeric(df_converted[col], errors='coerce')
    
    # Convert depth measurements to numeric
    for col in ['MAX_BH_TOTAL_MD', 'MAX_WELL_BORE_TVD', 'WATER_DEPTH']:
        if col in df_converted.columns:
            df_converted[col] = pd.to_numeric(df_converted[col], errors='coerce')
    
    return df_converted


def convert_data_types_api12(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert API12 data to appropriate data types.
    
    Args:
        df (pd.DataFrame): Raw API12 data
        
    Returns:
        pd.DataFrame: Data with converted types
    """
    df_converted = df.copy()
    
    # Convert API12 to int64 for large numbers
    if 'API12' in df_converted.columns:
        df_converted['API12'] = pd.to_numeric(df_converted['API12'], errors='coerce', downcast=None).astype('int64')
    
    # Convert drilling and completion days to numeric
    for col in ['Drilling Days', 'Completion Days']:
        if col in df_converted.columns:
            df_converted[col] = pd.to_numeric(df_converted[col], errors='coerce')
    
    # Convert depth measurements to numeric
    for col in ['Total Measured Depth', 'Water Depth (feet)']:
        if col in df_converted.columns:
            df_converted[col] = pd.to_numeric(df_converted[col], errors='coerce')
    
    return df_converted


def convert_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generic function to convert data types for test purposes.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with converted types
    """
    df_converted = df.copy()
    
    # Convert common numeric columns
    numeric_columns = ['API12', 'Drilling Days', 'Completion Days', 'API_WELL_NUMBER', 
                      'DRILLING_DAYS', 'COMPLETION_DAYS']
    
    for col in numeric_columns:
        if col in df_converted.columns:
            df_converted[col] = pd.to_numeric(df_converted[col], errors='coerce')
    
    return df_converted


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values in the dataset.
    
    Args:
        df (pd.DataFrame): Input DataFrame with potential missing values
        
    Returns:
        pd.DataFrame: DataFrame with missing values handled
    """
    df_cleaned = df.copy()
    
    # Remove rows where API12 is missing (critical identifier)
    if 'API12' in df_cleaned.columns:
        df_cleaned = df_cleaned.dropna(subset=['API12'])
    
    # For drilling and completion days, we might keep NaN values for analysis
    # They indicate data availability differences between methods
    
    return df_cleaned


def parse_rigdays_milestone(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the rigdays_by_milestone JSON column to extract drilling and completion days.
    
    Args:
        df (pd.DataFrame): DataFrame with rigdays_by_milestone column
        
    Returns:
        pd.DataFrame: DataFrame with parsed milestone data
    """
    if 'rigdays_by_milestone' not in df.columns:
        return df
    
    df_parsed = df.copy()
    
    # Initialize new columns
    df_parsed['milestone_drilling_days'] = np.nan
    df_parsed['milestone_completion_days'] = np.nan
    df_parsed['milestone_rig_days'] = np.nan
    
    for idx, milestone_str in df_parsed['rigdays_by_milestone'].items():
        if pd.isna(milestone_str) or milestone_str == '':
            continue
            
        try:
            # Parse JSON string
            milestone_data = json.loads(milestone_str)
            
            # Extract values
            df_parsed.loc[idx, 'milestone_drilling_days'] = milestone_data.get('drilling_days', np.nan)
            df_parsed.loc[idx, 'milestone_completion_days'] = milestone_data.get('completion_days', np.nan)
            df_parsed.loc[idx, 'milestone_rig_days'] = milestone_data.get('rig_days', np.nan)
            
        except (json.JSONDecodeError, TypeError) as e:
            # Keep as NaN if parsing fails
            continue
    
    return df_parsed


def load_and_prepare_data(lease_file: str, api12_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load and prepare both datasets for analysis.
    
    Args:
        lease_file (str): Path to lease method Excel file
        api12_file (str): Path to API12 method CSV file
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Prepared lease and API12 data
        
    Raises:
        ValueError: If required columns are missing from either dataset
    """
    # Load raw data
    lease_df = load_lease_data(lease_file)
    api12_df = load_api12_data(api12_file)
    
    # Validate required columns
    if not validate_lease_columns(lease_df):
        raise ValueError("Lease data is missing required columns")
    
    if not validate_api12_columns(api12_df):
        raise ValueError("API12 data is missing required columns")
    
    # Standardize data structure
    lease_std, api12_std = standardize_data(lease_df, api12_df)
    
    # Handle missing values
    lease_clean = handle_missing_values(lease_std)
    api12_clean = handle_missing_values(api12_std)
    
    return lease_clean, api12_clean


def get_matching_wells(lease_df: pd.DataFrame, api12_df: pd.DataFrame) -> List[int]:
    """
    Get list of API12 numbers that exist in both datasets.
    
    Args:
        lease_df (pd.DataFrame): Standardized lease data
        api12_df (pd.DataFrame): Standardized API12 data
        
    Returns:
        List[int]: List of API12 numbers present in both datasets
    """
    lease_apis = set(lease_df['api12'].dropna().astype('int64'))
    api12_apis = set(api12_df['api12'].dropna().astype('int64'))
    
    matching_apis = list(lease_apis.intersection(api12_apis))
    return sorted(matching_apis)


def calculate_differences(lease_df: pd.DataFrame, api12_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate differences in drilling and completion days between methods.
    
    Args:
        lease_df (pd.DataFrame): Standardized lease data
        api12_df (pd.DataFrame): Standardized API12 data
        
    Returns:
        pd.DataFrame: DataFrame with differences calculated
    """
    # Get matching wells
    matching_wells = get_matching_wells(lease_df, api12_df)
    
    # Create comparison dataframe
    comparison_data = []
    
    for api12 in matching_wells:
        lease_row = lease_df[lease_df['api12'] == api12].iloc[0]
        api12_row = api12_df[api12_df['api12'] == api12].iloc[0]
        
        drilling_diff = lease_row['drilling_days'] - api12_row['drilling_days']
        completion_diff = lease_row['completion_days'] - api12_row['completion_days']
        total_diff = abs(drilling_diff) + abs(completion_diff)
        
        comparison_data.append({
            'api12': api12,
            'lease_drilling_days': lease_row['drilling_days'],
            'api12_drilling_days': api12_row['drilling_days'],
            'drilling_diff': drilling_diff,
            'lease_completion_days': lease_row['completion_days'],
            'api12_completion_days': api12_row['completion_days'],
            'completion_diff': completion_diff,
            'total_diff': total_diff,
            'well_name': lease_row.get('well_name', ''),
            'field_name': lease_row.get('field_name', '')
        })
    
    return pd.DataFrame(comparison_data)