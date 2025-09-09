"""
Data processor adapters for well data verification.

Imports and extends existing BSEE data processors and validators.
"""

from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger  # Reusing existing loguru setup

# Import existing BSEE processors and validators
from worldenergydata.modules.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.modules.bsee.analysis.financial.validators import (
    validate_required_columns,
    validate_date_columns,
    validate_numeric_columns,
    validate_lease_numbers
)


class BSEEDataAdapter:
    """
    Adapter class that imports and extends BSEE data processors.
    Provides a unified interface for verification workflows.
    """
    
    def __init__(self):
        """Initialize adapter with BSEE processor."""
        self.processor = MemoryProcessor()
        logger.debug("Initialized BSEEDataAdapter with MemoryProcessor")
    
    def load_production_data(self, 
                            data_source: Union[str, pd.DataFrame],
                            **kwargs) -> pd.DataFrame:
        """
        Load production data using BSEE processor.
        
        Args:
            data_source: Path to data file or DataFrame
            **kwargs: Additional loading parameters
            
        Returns:
            Loaded DataFrame
        """
        if isinstance(data_source, pd.DataFrame):
            logger.info(f"Loading production data from DataFrame with {len(data_source)} rows")
            return data_source
        
        # Use BSEE processor for file loading
        # Note: Actual implementation would use the processor's load method
        logger.info(f"Loading production data from {data_source}")
        
        # For now, return empty DataFrame as placeholder
        # In real implementation, would use: self.processor.load_data(data_source)
        return pd.DataFrame()
    
    def process_well_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process well data using BSEE patterns.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Processed DataFrame
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for processing")
            return df
        
        # Apply standard processing steps
        processed = df.copy()
        
        # Normalize column names (following BSEE patterns)
        processed.columns = processed.columns.str.upper().str.replace(' ', '_')
        
        # Ensure standard columns exist
        standard_columns = ['WELL_ID', 'LEASE_NUM', 'PRODUCTION_DATE', 'OIL_VOLUME', 'GAS_VOLUME']
        for col in standard_columns:
            if col not in processed.columns and col != 'WATER_VOLUME':
                logger.warning(f"Missing standard column: {col}")
        
        logger.debug(f"Processed {len(processed)} rows of well data")
        return processed
    
    def validate_lease_numbers(self, df: pd.DataFrame, lease_col: str = "LEASE_NUM") -> pd.DataFrame:
        """
        Validate and normalize lease numbers using BSEE validators.
        
        Args:
            df: DataFrame with lease numbers
            lease_col: Name of lease number column
            
        Returns:
            DataFrame with validated lease numbers
        """
        if lease_col not in df.columns:
            logger.warning(f"Lease column {lease_col} not found")
            return df
        
        # Use imported BSEE validator
        validated = validate_lease_numbers(df, lease_col)
        logger.info(f"Validated lease numbers for {len(validated)} rows")
        return validated
    
    def validate_production_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate production data columns using BSEE validators.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Validated DataFrame
        """
        # Define column types
        date_columns = ['PRODUCTION_DATE', 'COMPLETION_DATE', 'SPUD_DATE']
        numeric_columns = ['OIL_VOLUME', 'GAS_VOLUME', 'WATER_VOLUME', 'DAYS_ON_PRODUCTION']
        
        # Apply date validation
        date_cols_present = [col for col in date_columns if col in df.columns]
        if date_cols_present:
            df = validate_date_columns(df, date_cols_present)
        
        # Apply numeric validation
        numeric_cols_present = [col for col in numeric_columns if col in df.columns]
        if numeric_cols_present:
            df = validate_numeric_columns(df, numeric_cols_present, fill_invalid=0)
        
        logger.info("Validated production columns")
        return df
    
    def check_required_columns(self, df: pd.DataFrame, required_cols: List[str]) -> bool:
        """
        Check for required columns using BSEE validator.
        
        Args:
            df: DataFrame to check
            required_cols: List of required columns
            
        Returns:
            True if all required columns present
        """
        try:
            validate_required_columns(df, required_cols)
            return True
        except ValueError as e:
            logger.error(f"Required columns validation failed: {e}")
            return False
    
    def calculate_statistics(self, df: pd.DataFrame, column: str) -> Dict[str, float]:
        """
        Calculate basic statistics for a column.
        
        Args:
            df: DataFrame
            column: Column name
            
        Returns:
            Dictionary of statistics
        """
        if column not in df.columns:
            logger.warning(f"Column {column} not found for statistics")
            return {}
        
        series = pd.to_numeric(df[column], errors='coerce')
        
        return {
            'count': series.count(),
            'mean': series.mean(),
            'std': series.std(),
            'min': series.min(),
            'max': series.max(),
            'median': series.median(),
            'q25': series.quantile(0.25),
            'q75': series.quantile(0.75)
        }
    
    def detect_outliers(self, df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.Series:
        """
        Detect outliers using statistical method.
        
        Args:
            df: DataFrame
            column: Column to check
            threshold: Standard deviation threshold
            
        Returns:
            Boolean Series marking outliers
        """
        if column not in df.columns:
            logger.warning(f"Column {column} not found for outlier detection")
            return pd.Series([False] * len(df))
        
        series = pd.to_numeric(df[column], errors='coerce')
        
        # Calculate z-scores
        mean = series.mean()
        std = series.std()
        
        if std == 0:
            return pd.Series([False] * len(df))
        
        z_scores = np.abs((series - mean) / std)
        outliers = z_scores > threshold
        
        outlier_count = outliers.sum()
        if outlier_count > 0:
            logger.info(f"Detected {outlier_count} outliers in {column}")
        
        return outliers
    
    def check_data_completeness(self, df: pd.DataFrame, required_fields: List[str]) -> Dict[str, Any]:
        """
        Check data completeness for required fields.
        
        Args:
            df: DataFrame to check
            required_fields: List of required fields
            
        Returns:
            Completeness report
        """
        report = {
            'total_rows': len(df),
            'field_completeness': {},
            'overall_completeness': 0.0
        }
        
        for field in required_fields:
            if field in df.columns:
                non_null = df[field].notna().sum()
                completeness = (non_null / len(df)) * 100 if len(df) > 0 else 0
                report['field_completeness'][field] = {
                    'non_null_count': non_null,
                    'null_count': len(df) - non_null,
                    'completeness_pct': completeness
                }
            else:
                report['field_completeness'][field] = {
                    'non_null_count': 0,
                    'null_count': len(df),
                    'completeness_pct': 0.0
                }
        
        # Calculate overall completeness
        if report['field_completeness']:
            completeness_values = [f['completeness_pct'] for f in report['field_completeness'].values()]
            report['overall_completeness'] = sum(completeness_values) / len(completeness_values)
        
        logger.info(f"Overall data completeness: {report['overall_completeness']:.2f}%")
        return report