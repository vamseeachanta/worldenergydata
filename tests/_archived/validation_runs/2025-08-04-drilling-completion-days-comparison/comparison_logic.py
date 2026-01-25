"""
Comparison Logic Module for Drilling Days Analysis

This module provides classes for comparing drilling and completion days data
from different BSEE analysis methods (lease-based vs API12-based).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ComparisonDataLoader:
    """
    Handles loading and standardizing data from different method outputs.
    
    Supports:
    - Excel files from lease method (drilling_and_completion_days_by_api_*.xlsx)
    - CSV files from API12 method (well_summ_*.csv)
    """
    
    def __init__(self):
        self.lease_method_columns = {
            'API_WELL_NUMBER': 'api_number',
            'WELL_NAME': 'well_name',
            'DRILLING_DAYS': 'drilling_days_lease',
            'COMPLETION_DAYS': 'completion_days_lease',
            'LEASE_NAME': 'lease_name',
            'WATER_DEPTH': 'water_depth'
        }
        
        self.api12_method_columns = {
            'API12': 'api_number',
            'WELL_NAME': 'well_name',
            'Drilling Days': 'drilling_days_api12',
            'Completion Days': 'completion_days_api12',
            'Water Depth (feet)': 'water_depth'
        }
    
    def load_lease_method_data(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Load data from lease method Excel output.
        
        Args:
            file_path: Path to Excel file with lease method results
            
        Returns:
            DataFrame with standardized column names
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Lease method file not found: {file_path}")
        
        logger.info(f"Loading lease method data from: {file_path}")
        
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Error reading Excel file {file_path}: {e}")
        
        # Validate required columns
        missing_cols = set(self.lease_method_columns.keys()) - set(df.columns)
        required_cols = {'API_WELL_NUMBER', 'DRILLING_DAYS', 'COMPLETION_DAYS'}
        missing_required = required_cols - set(df.columns)
        
        if missing_required:
            raise ValueError(f"Missing required columns in lease method data: {missing_required}")
        
        # Standardize column names
        df_renamed = df.rename(columns=self.lease_method_columns)
        
        # Ensure API numbers are numeric
        df_renamed['api_number'] = pd.to_numeric(df_renamed['api_number'], errors='coerce')
        
        # Clean and validate data
        df_cleaned = self._clean_lease_data(df_renamed)
        
        logger.info(f"Loaded {len(df_cleaned)} wells from lease method")
        return df_cleaned
    
    def load_api12_method_data(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Load data from API12 method CSV output.
        
        Args:
            file_path: Path to CSV file with API12 method results
            
        Returns:
            DataFrame with standardized column names
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"API12 method file not found: {file_path}")
        
        logger.info(f"Loading API12 method data from: {file_path}")
        
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Error reading CSV file {file_path}: {e}")
        
        # Validate required columns
        missing_cols = set(self.api12_method_columns.keys()) - set(df.columns)
        required_cols = {'API12', 'Drilling Days', 'Completion Days'}
        missing_required = required_cols - set(df.columns)
        
        if missing_required:
            raise ValueError(f"Missing required columns in API12 method data: {missing_required}")
        
        # Standardize column names
        df_renamed = df.rename(columns=self.api12_method_columns)
        
        # Ensure API numbers are numeric
        df_renamed['api_number'] = pd.to_numeric(df_renamed['api_number'], errors='coerce')
        
        # Clean and validate data
        df_cleaned = self._clean_api12_data(df_renamed)
        
        logger.info(f"Loaded {len(df_cleaned)} wells from API12 method")
        return df_cleaned
    
    def _clean_lease_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate lease method data."""
        # Remove rows with invalid API numbers
        df = df.dropna(subset=['api_number'])
        
        # Ensure drilling and completion days are numeric
        df['drilling_days_lease'] = pd.to_numeric(df['drilling_days_lease'], errors='coerce')
        df['completion_days_lease'] = pd.to_numeric(df['completion_days_lease'], errors='coerce')
        
        # Remove rows with invalid drilling/completion days
        df = df.dropna(subset=['drilling_days_lease', 'completion_days_lease'])
        
        # Remove negative days (data quality issue)
        df = df[(df['drilling_days_lease'] >= 0) & (df['completion_days_lease'] >= 0)]
        
        return df
    
    def _clean_api12_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate API12 method data."""
        # Remove rows with invalid API numbers
        df = df.dropna(subset=['api_number'])
        
        # Ensure drilling and completion days are numeric
        df['drilling_days_api12'] = pd.to_numeric(df['drilling_days_api12'], errors='coerce')
        df['completion_days_api12'] = pd.to_numeric(df['completion_days_api12'], errors='coerce')
        
        # Remove rows with invalid drilling/completion days
        df = df.dropna(subset=['drilling_days_api12', 'completion_days_api12'])
        
        # Remove negative days (data quality issue)
        df = df[(df['drilling_days_api12'] >= 0) & (df['completion_days_api12'] >= 0)]
        
        return df


class ComparisonAnalyzer:
    """
    Performs analysis and comparison of drilling/completion days between methods.
    
    Capabilities:
    - Match wells by API12 number
    - Calculate absolute and percentage differences
    - Flag discrepancies based on thresholds
    - Generate comparison statistics
    """
    
    def __init__(self, 
                 drilling_days_threshold: float = 5.0,
                 completion_days_threshold: float = 3.0,
                 percentage_threshold: float = 10.0):
        """
        Initialize analyzer with discrepancy thresholds.
        
        Args:
            drilling_days_threshold: Absolute difference threshold for drilling days
            completion_days_threshold: Absolute difference threshold for completion days
            percentage_threshold: Percentage difference threshold for flagging
        """
        self.drilling_days_threshold = drilling_days_threshold
        self.completion_days_threshold = completion_days_threshold
        self.percentage_threshold = percentage_threshold
        
        logger.info(f"Initialized ComparisonAnalyzer with thresholds: "
                   f"drilling={drilling_days_threshold}d, completion={completion_days_threshold}d, "
                   f"percentage={percentage_threshold}%")
    
    def match_wells_by_api(self, lease_data: pd.DataFrame, api12_data: pd.DataFrame) -> pd.DataFrame:
        """
        Match wells between datasets using API12 numbers.
        
        Args:
            lease_data: DataFrame from lease method
            api12_data: DataFrame from API12 method
            
        Returns:
            DataFrame with matched wells containing data from both methods
        """
        logger.info(f"Matching wells: {len(lease_data)} lease wells vs {len(api12_data)} API12 wells")
        
        # Perform inner join on API numbers
        matched = pd.merge(
            lease_data,
            api12_data,
            on='api_number',
            how='inner',
            suffixes=('_lease', '_api12')
        )
        
        logger.info(f"Found {len(matched)} matching wells")
        
        if len(matched) == 0:
            logger.warning("No wells matched between datasets. Check API number formats.")
        
        return matched
    
    def calculate_drilling_days_differences(self, matched_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate drilling days differences and percentage differences.
        
        Args:
            matched_data: DataFrame with matched wells from both methods
            
        Returns:
            DataFrame with drilling days comparison columns added
        """
        df = matched_data.copy()
        
        # Calculate absolute difference (lease - api12)
        df['drilling_days_difference'] = (
            df['drilling_days_lease'] - df['drilling_days_api12']
        )
        
        # Calculate percentage difference
        df['drilling_days_percent_diff'] = df.apply(
            lambda row: self._calculate_percentage_difference(
                row['drilling_days_lease'], 
                row['drilling_days_api12']
            ), axis=1
        )
        
        logger.info("Calculated drilling days differences")
        return df
    
    def calculate_completion_days_differences(self, matched_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate completion days differences and percentage differences.
        
        Args:
            matched_data: DataFrame with matched wells from both methods
            
        Returns:
            DataFrame with completion days comparison columns added
        """
        df = matched_data.copy()
        
        # Calculate absolute difference (lease - api12)
        df['completion_days_difference'] = (
            df['completion_days_lease'] - df['completion_days_api12']
        )
        
        # Calculate percentage difference
        df['completion_days_percent_diff'] = df.apply(
            lambda row: self._calculate_percentage_difference(
                row['completion_days_lease'], 
                row['completion_days_api12']
            ), axis=1
        )
        
        logger.info("Calculated completion days differences")
        return df
    
    def apply_discrepancy_flags(self, comparison_data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply status flags based on discrepancy thresholds.
        
        Args:
            comparison_data: DataFrame with calculated differences
            
        Returns:
            DataFrame with status_flag column added
        """
        df = comparison_data.copy()
        
        def determine_flag(row):
            """Determine status flag for a row based on thresholds."""
            drilling_abs_diff = abs(row['drilling_days_difference'])
            completion_abs_diff = abs(row['completion_days_difference'])
            drilling_percent_diff = abs(row['drilling_days_percent_diff'])
            completion_percent_diff = abs(row['completion_days_percent_diff'])
            
            # ERROR: Large absolute or percentage differences
            if (drilling_abs_diff > self.drilling_days_threshold * 2 or 
                completion_abs_diff > self.completion_days_threshold * 2 or
                drilling_percent_diff > self.percentage_threshold * 2 or
                completion_percent_diff > self.percentage_threshold * 2):
                return 'ERROR'
            
            # REVIEW: Moderate differences
            elif (drilling_abs_diff > self.drilling_days_threshold or 
                  completion_abs_diff > self.completion_days_threshold or
                  drilling_percent_diff > self.percentage_threshold or
                  completion_percent_diff > self.percentage_threshold):
                return 'REVIEW'
            
            # OK: Within acceptable thresholds
            else:
                return 'OK'
        
        df['status_flag'] = df.apply(determine_flag, axis=1)
        
        # Log flag distribution
        flag_counts = df['status_flag'].value_counts()
        logger.info(f"Status flag distribution: {flag_counts.to_dict()}")
        
        return df
    
    def perform_complete_comparison(self, matched_data: pd.DataFrame) -> pd.DataFrame:
        """
        Perform complete comparison analysis including all calculations and flags.
        
        Args:
            matched_data: DataFrame with matched wells from both methods
            
        Returns:
            DataFrame with complete comparison analysis
        """
        logger.info("Performing complete comparison analysis")
        
        # Calculate all differences
        df = self.calculate_drilling_days_differences(matched_data)
        df = self.calculate_completion_days_differences(df)
        df = self.apply_discrepancy_flags(df)
        
        # Add summary statistics
        df = self._add_summary_statistics(df)
        
        logger.info("Complete comparison analysis finished")
        return df
    
    def _calculate_percentage_difference(self, value1: float, value2: float) -> float:
        """
        Calculate percentage difference between two values.
        
        Formula: ((value1 - value2) / value2) * 100
        
        Args:
            value1: First value (lease method)
            value2: Second value (API12 method, baseline)
            
        Returns:
            Percentage difference
        """
        if pd.isna(value1) or pd.isna(value2):
            return np.nan
        
        if value2 == 0:
            return np.inf if value1 != 0 else 0.0
        
        return ((value1 - value2) / value2) * 100
    
    def _add_summary_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add summary statistics to comparison data."""
        # Calculate statistics for the dataset
        drilling_stats = {
            'mean_drilling_diff': df['drilling_days_difference'].mean(),
            'std_drilling_diff': df['drilling_days_difference'].std(),
            'median_drilling_diff': df['drilling_days_difference'].median()
        }
        
        completion_stats = {
            'mean_completion_diff': df['completion_days_difference'].mean(),
            'std_completion_diff': df['completion_days_difference'].std(),
            'median_completion_diff': df['completion_days_difference'].median()
        }
        
        # Store stats as attributes for later use
        self.drilling_stats = drilling_stats
        self.completion_stats = completion_stats
        
        logger.info(f"Summary statistics calculated: "
                   f"drilling_diff_mean={drilling_stats['mean_drilling_diff']:.2f}, "
                   f"completion_diff_mean={completion_stats['mean_completion_diff']:.2f}")
        
        return df
    
    def get_comparison_summary(self) -> Dict:
        """
        Get summary statistics of the comparison analysis.
        
        Returns:
            Dictionary with summary statistics
        """
        if not hasattr(self, 'drilling_stats'):
            raise ValueError("No comparison analysis has been performed yet")
        
        return {
            'drilling_statistics': self.drilling_stats,
            'completion_statistics': self.completion_stats,
            'thresholds': {
                'drilling_days_threshold': self.drilling_days_threshold,
                'completion_days_threshold': self.completion_days_threshold,
                'percentage_threshold': self.percentage_threshold
            }
        }