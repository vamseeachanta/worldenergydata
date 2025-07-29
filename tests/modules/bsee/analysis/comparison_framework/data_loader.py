"""
DataLoader module for drilling days comparison framework.

This module provides functionality to load and preprocess data from both
drilling days calculation methods (lease method Excel files and API12 method CSV files).
"""

import pandas as pd
import os
import glob
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


class DataLoaderError(Exception):
    """Custom exception for DataLoader errors."""
    pass


class DataLoader:
    """
    DataLoader class for loading and preprocessing drilling days data.
    
    Handles loading data from both methods:
    - Lease method: Excel files with columns API_WELL_NUMBER, DRILLING_DAYS, COMPLETION_DAYS
    - API12 method: CSV files with columns API12, Drilling Days, Completion Days
    
    Standardizes column names and data types for comparison analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DataLoader with configuration.
        
        Args:
            config: Configuration dictionary with method-specific settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._get_default_config()
        
        if config:
            self._validate_config(config)
            self.config.update(config)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for DataLoader."""
        return {
            'lease_method': {
                'file_extension': '.xlsx',
                'required_columns': ['API_WELL_NUMBER', 'DRILLING_DAYS', 'COMPLETION_DAYS'],
                'optional_columns': ['WELL_NAME', 'WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE']
            },
            'api12_method': {
                'file_pattern': 'block_api12_*.csv',
                'required_columns': ['API12', 'Drilling Days', 'Completion Days'],
                'optional_columns': ['API10', 'WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE', 'WELL_NAME']
            },
            'standardized_columns': {
                'api_number': 'string',
                'drilling_days': 'float64',
                'completion_days': 'float64',
                'spud_date': 'datetime64[ns]',
                'total_depth_date': 'datetime64[ns]',
                'well_name': 'string'
            },
            'missing_data': {
                'api_number_action': 'drop',  # Drop rows with missing API numbers
                'drilling_days_fill': 0.0,    # Fill missing drilling days with 0
                'completion_days_fill': 0.0   # Fill missing completion days with 0
            },
            'date_formats': ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']
        }
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration parameters.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            DataLoaderError: If configuration is invalid
        """
        required_sections = ['lease_method', 'api12_method']
        
        for section in required_sections:
            if section not in config:
                raise DataLoaderError(f"Invalid configuration: missing {section} section")
    
    def load_lease_method_data(self, file_path: str) -> pd.DataFrame:
        """
        Load data from lease method Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            DataFrame with loaded data
            
        Raises:
            DataLoaderError: If file cannot be loaded or processed
        """
        try:
            if not os.path.exists(file_path):
                raise DataLoaderError(f"File not found: {file_path}")
            
            self.logger.info(f"Loading lease method data from: {file_path}")
            
            # Load Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_cols = self.config['lease_method']['required_columns']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                raise DataLoaderError(
                    f"Missing required columns in lease method file: {missing_cols}"
                )
            
            self.logger.info(f"Successfully loaded {len(df)} rows from lease method file")
            return df
            
        except pd.errors.EmptyDataError:
            raise DataLoaderError(f"Empty or invalid Excel file: {file_path}")
        except Exception as e:
            if isinstance(e, DataLoaderError):
                raise
            self.logger.error(f"Error loading lease method file {file_path}: {str(e)}")
            raise DataLoaderError(f"Invalid file format or error reading file: {file_path}")
    
    def load_api12_method_data(self, directory: str, file_pattern: str) -> pd.DataFrame:
        """
        Load data from API12 method CSV files.
        
        Args:
            directory: Directory containing CSV files
            file_pattern: File pattern to match (e.g., 'block_api12_*.csv')
            
        Returns:
            DataFrame with combined data from all matching files
            
        Raises:
            DataLoaderError: If no files found or processing fails
        """
        try:
            search_pattern = os.path.join(directory, file_pattern)
            csv_files = glob.glob(search_pattern)
            
            if not csv_files:
                raise DataLoaderError(
                    f"No files found matching pattern: {search_pattern}"
                )
            
            self.logger.info(f"Found {len(csv_files)} API12 method files to process")
            
            dfs = []
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    
                    # Validate required columns
                    required_cols = self.config['api12_method']['required_columns']
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    
                    if missing_cols:
                        self.logger.warning(
                            f"Skipping file {csv_file}: missing columns {missing_cols}"
                        )
                        continue
                    
                    dfs.append(df)
                    self.logger.debug(f"Loaded {len(df)} rows from {csv_file}")
                    
                except Exception as e:
                    self.logger.warning(f"Error processing file {csv_file}: {str(e)}")
                    continue
            
            if not dfs:
                raise DataLoaderError("No valid CSV files could be processed")
            
            # Combine all dataframes
            combined_df = pd.concat(dfs, ignore_index=True)
            self.logger.info(f"Successfully combined {len(combined_df)} rows from API12 method files")
            
            return combined_df
            
        except Exception as e:
            if isinstance(e, DataLoaderError):
                raise
            self.logger.error(f"Error processing CSV files: {str(e)}")
            raise DataLoaderError(f"Error processing CSV files: {str(e)}")
    
    def standardize_column_names(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        """
        Standardize column names for consistent processing.
        
        Args:
            df: DataFrame to standardize
            method: Method type ('lease' or 'api12')
            
        Returns:
            DataFrame with standardized column names
        """
        df_copy = df.copy()
        
        if method == 'lease':
            column_mapping = {
                'API_WELL_NUMBER': 'api_number',
                'DRILLING_DAYS': 'drilling_days',
                'COMPLETION_DAYS': 'completion_days',
                'WELL_SPUD_DATE': 'spud_date',
                'TOTAL_DEPTH_DATE': 'total_depth_date',
                'WELL_NAME': 'well_name'
            }
        elif method == 'api12':
            column_mapping = {
                'API12': 'api_number',
                'Drilling Days': 'drilling_days',
                'Completion Days': 'completion_days',
                'WELL_SPUD_DATE': 'spud_date',
                'TOTAL_DEPTH_DATE': 'total_depth_date',
                'WELL_NAME': 'well_name'
            }
        else:
            raise DataLoaderError(f"Unknown method type: {method}")
        
        # Rename columns that exist in the dataframe
        existing_mappings = {
            old_name: new_name for old_name, new_name in column_mapping.items()
            if old_name in df_copy.columns
        }
        
        df_copy = df_copy.rename(columns=existing_mappings)
        
        self.logger.debug(f"Standardized {len(existing_mappings)} column names for {method} method")
        return df_copy
    
    def validate_and_convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and convert data types to standardized formats.
        
        Args:
            df: DataFrame to validate and convert
            
        Returns:
            DataFrame with converted data types
            
        Raises:
            DataLoaderError: If data type conversion fails
        """
        df_copy = df.copy()
        
        try:
            # Convert numeric columns
            if 'drilling_days' in df_copy.columns:
                df_copy['drilling_days'] = pd.to_numeric(
                    df_copy['drilling_days'], errors='coerce'
                )
            
            if 'completion_days' in df_copy.columns:
                df_copy['completion_days'] = pd.to_numeric(
                    df_copy['completion_days'], errors='coerce'
                )
            
            # Convert date columns
            date_columns = ['spud_date', 'total_depth_date']
            for col in date_columns:
                if col in df_copy.columns:
                    df_copy[col] = self._convert_date_column(df_copy[col])
            
            # Ensure API numbers are strings
            if 'api_number' in df_copy.columns:
                df_copy['api_number'] = df_copy['api_number'].astype(str)
            
            self.logger.debug("Successfully converted data types")
            return df_copy
            
        except Exception as e:
            self.logger.error(f"Data type conversion failed: {str(e)}")
            raise DataLoaderError(f"Data type conversion failed: {str(e)}")
    
    def _convert_date_column(self, series: pd.Series) -> pd.Series:
        """
        Convert date column using multiple format attempts.
        
        Args:
            series: Series with date values to convert
            
        Returns:
            Series with converted datetime values
        """
        if series.empty:
            return series
        
        # Try pandas automatic parsing first
        try:
            return pd.to_datetime(series, errors='coerce')
        except:
            pass
        
        # Try specific formats
        for date_format in self.config['date_formats']:
            try:
                return pd.to_datetime(series, format=date_format, errors='coerce')
            except:
                continue
        
        # If all else fails, return as is with warning
        self.logger.warning("Could not convert date column, returning as is")
        return series
    
    def handle_missing_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing data according to configuration.
        
        Args:
            df: DataFrame to process
            
        Returns:
            DataFrame with missing data handled
        """
        df_copy = df.copy()
        
        # Handle missing API numbers (required field)
        if 'api_number' in df_copy.columns:
            if self.config['missing_data']['api_number_action'] == 'drop':
                initial_count = len(df_copy)
                df_copy = df_copy.dropna(subset=['api_number'])
                dropped_count = initial_count - len(df_copy)
                if dropped_count > 0:
                    self.logger.info(f"Dropped {dropped_count} rows with missing API numbers")
        
        # Fill missing drilling days
        if 'drilling_days' in df_copy.columns:
            fill_value = self.config['missing_data']['drilling_days_fill']
            missing_count = df_copy['drilling_days'].isna().sum()
            if missing_count > 0:
                df_copy['drilling_days'] = df_copy['drilling_days'].fillna(fill_value)
                self.logger.info(f"Filled {missing_count} missing drilling days with {fill_value}")
        
        # Fill missing completion days
        if 'completion_days' in df_copy.columns:
            fill_value = self.config['missing_data']['completion_days_fill']
            missing_count = df_copy['completion_days'].isna().sum()
            if missing_count > 0:
                df_copy['completion_days'] = df_copy['completion_days'].fillna(fill_value)
                self.logger.info(f"Filled {missing_count} missing completion days with {fill_value}")
        
        return df_copy
    
    def preprocess_data(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        """
        Complete preprocessing pipeline for data standardization.
        
        Args:
            df: DataFrame to preprocess
            method: Method type ('lease' or 'api12')
            
        Returns:
            DataFrame with standardized structure and data types
        """
        # Step 1: Standardize column names
        df_processed = self.standardize_column_names(df, method)
        
        # Step 2: Validate and convert data types
        df_processed = self.validate_and_convert_data_types(df_processed)
        
        # Step 3: Handle missing data
        df_processed = self.handle_missing_data(df_processed)
        
        self.logger.info(f"Completed preprocessing for {method} method: {len(df_processed)} rows")
        return df_processed
    
    def load_and_preprocess_lease_method(self, file_path: str) -> pd.DataFrame:
        """
        Complete workflow to load and preprocess lease method data.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            DataFrame with standardized, preprocessed data
        """
        # Load raw data
        raw_data = self.load_lease_method_data(file_path)
        
        # Preprocess data
        processed_data = self.preprocess_data(raw_data, 'lease')
        
        return processed_data
    
    def load_and_preprocess_api12_method(self, directory: str, 
                                       file_pattern: str) -> pd.DataFrame:
        """
        Complete workflow to load and preprocess API12 method data.
        
        Args:
            directory: Directory containing CSV files
            file_pattern: File pattern to match
            
        Returns:
            DataFrame with standardized, preprocessed data
        """
        # Load raw data
        raw_data = self.load_api12_method_data(directory, file_pattern)
        
        # Preprocess data
        processed_data = self.preprocess_data(raw_data, 'api12')
        
        return processed_data
    
    def get_data_summary(self, df: pd.DataFrame, method: str) -> Dict[str, Any]:
        """
        Generate summary statistics for loaded data.
        
        Args:
            df: DataFrame to summarize
            method: Method type for labeling
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'method': method,
            'total_rows': len(df),
            'unique_apis': df['api_number'].nunique() if 'api_number' in df.columns else 0,
            'date_range': {},
            'drilling_days_stats': {},
            'completion_days_stats': {},
            'missing_data': {}
        }
        
        # Date range analysis
        if 'spud_date' in df.columns and df['spud_date'].notna().any():
            summary['date_range']['spud_date_min'] = df['spud_date'].min()
            summary['date_range']['spud_date_max'] = df['spud_date'].max()
        
        # Drilling days statistics
        if 'drilling_days' in df.columns:
            drilling_days = df['drilling_days'].dropna()
            if not drilling_days.empty:
                summary['drilling_days_stats'] = {
                    'mean': drilling_days.mean(),
                    'median': drilling_days.median(),
                    'min': drilling_days.min(),
                    'max': drilling_days.max(),
                    'std': drilling_days.std()
                }
        
        # Completion days statistics
        if 'completion_days' in df.columns:
            completion_days = df['completion_days'].dropna()
            if not completion_days.empty:
                summary['completion_days_stats'] = {
                    'mean': completion_days.mean(),
                    'median': completion_days.median(),
                    'min': completion_days.min(),
                    'max': completion_days.max(),
                    'std': completion_days.std()
                }
        
        # Missing data analysis
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                summary['missing_data'][col] = {
                    'count': missing_count,
                    'percentage': (missing_count / len(df)) * 100
                }
        
        return summary