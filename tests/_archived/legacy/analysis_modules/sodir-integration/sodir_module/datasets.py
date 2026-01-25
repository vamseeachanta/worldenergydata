"""
SODIR Analysis-Ready Dataset Generation

Creates analysis-ready datasets for cross-regional comparison
between SODIR and BSEE data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatasetGenerator:
    """Generates analysis-ready datasets from SODIR data."""
    
    def __init__(self, storage=None):
        """
        Initialize DatasetGenerator.
        
        Args:
            storage: Optional DataStorage instance
        """
        self.storage = storage
        self._dataset_configs = self._define_dataset_configs()
        
    def _define_dataset_configs(self) -> Dict[str, Dict]:
        """Define configurations for different dataset types."""
        return {
            'wellbore_analysis': {
                'required_fields': ['wellbore_id', 'field_id', 'status', 
                                  'depth_meters', 'coordinates', 'spud_date'],
                'aggregations': ['field', 'status', 'year'],
                'metrics': ['count', 'avg_depth', 'success_rate']
            },
            'field_production': {
                'required_fields': ['field_id', 'field_name', 'discovery_year',
                                  'production_start', 'recoverable_oil', 'recoverable_gas'],
                'aggregations': ['field', 'year', 'operator'],
                'metrics': ['production_volumes', 'recovery_factors', 'field_maturity']
            },
            'exploration_activity': {
                'required_fields': ['wellbore_id', 'purpose', 'result', 
                                  'completion_date', 'total_depth'],
                'aggregations': ['year', 'operator', 'area'],
                'metrics': ['success_rate', 'drilling_efficiency', 'discovery_size']
            },
            'cross_regional': {
                'required_fields': ['region', 'field_id', 'production_data',
                                  'economic_indicators'],
                'aggregations': ['region', 'field_type', 'water_depth'],
                'metrics': ['comparative_production', 'cost_efficiency', 'resource_density']
            }
        }
        
    def create_wellbore_dataset(self, wellbore_data: pd.DataFrame,
                               field_data: pd.DataFrame = None) -> pd.DataFrame:
        """
        Create analysis-ready wellbore dataset.
        
        Args:
            wellbore_data: Raw wellbore data
            field_data: Optional field data for enrichment
            
        Returns:
            Analysis-ready wellbore DataFrame
        """
        try:
            # Create copy to avoid modifying original
            df = wellbore_data.copy()
            
            # Add derived fields
            if 'spud_date' in df.columns:
                df['spud_date'] = pd.to_datetime(df['spud_date'], errors='coerce')
                df['year'] = df['spud_date'].dt.year
                df['quarter'] = df['spud_date'].dt.quarter
                
            # Calculate drilling duration if dates available
            if 'completion_date' in df.columns and 'spud_date' in df.columns:
                df['completion_date'] = pd.to_datetime(df['completion_date'], errors='coerce')
                df['drilling_days'] = (df['completion_date'] - df['spud_date']).dt.days
                
            # Add success indicator
            if 'status' in df.columns:
                df['is_successful'] = df['status'].isin(['PRODUCING', 'SHUT_IN', 'COMPLETED'])
                
            # Add water depth category
            if 'water_depth' in df.columns:
                df['water_depth_category'] = pd.cut(
                    df['water_depth'],
                    bins=[0, 200, 500, 1000, float('inf')],
                    labels=['Shallow', 'Mid-depth', 'Deep', 'Ultra-deep']
                )
                
            # Merge with field data if provided
            if field_data is not None and 'field_id' in df.columns:
                field_cols = ['field_id', 'field_name', 'operator', 'discovery_year']
                field_subset = field_data[field_cols].drop_duplicates()
                df = df.merge(field_subset, on='field_id', how='left')
                
            # Add data quality indicators
            df['data_completeness'] = df.notna().sum(axis=1) / len(df.columns)
            
            logger.info(f"Created wellbore dataset with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Failed to create wellbore dataset: {e}")
            raise
    
    def generate_wellbore_dataset(self, wellbore_data: Union[pd.DataFrame, List[Dict[str, Any]]],
                                 field_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Generate analysis-ready wellbore dataset (alias for create_wellbore_dataset).
        
        Args:
            wellbore_data: Raw wellbore data (DataFrame or list of dicts)
            field_data: Optional field data for enrichment
            
        Returns:
            Analysis-ready wellbore DataFrame
        """
        # Convert list to DataFrame if necessary
        if isinstance(wellbore_data, list):
            wellbore_data = pd.DataFrame(wellbore_data)
            
        return self.create_wellbore_dataset(wellbore_data, field_data)
    
    def generate_production_dataset(self, production_data: Union[pd.DataFrame, List[Dict[str, Any]]],
                                   field_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Generate analysis-ready production dataset (alias for create_production_dataset).
        
        Args:
            production_data: Raw production data (DataFrame or list of dicts)
            field_data: Optional field data for enrichment
            
        Returns:
            Analysis-ready production DataFrame
        """
        # Convert list to DataFrame if necessary
        if isinstance(production_data, list):
            production_data = pd.DataFrame(production_data)
            
        # If field_data not provided, create minimal field data
        if field_data is None:
            field_data = pd.DataFrame({'field_id': [], 'field_name': []})
            
        return self.create_production_dataset(production_data, field_data)
            
    def create_production_dataset(self, production_data: pd.DataFrame,
                                 field_data: pd.DataFrame) -> pd.DataFrame:
        """
        Create analysis-ready production dataset.
        
        Args:
            production_data: Raw production data
            field_data: Field information
            
        Returns:
            Analysis-ready production DataFrame
        """
        try:
            # Merge production with field data
            df = production_data.merge(field_data, on='field_id', how='left')
            
            # Convert date columns
            date_cols = ['production_date', 'production_start', 'discovery_date']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    
            # Add time-based features
            if 'production_date' in df.columns:
                df['year'] = df['production_date'].dt.year
                df['month'] = df['production_date'].dt.month
                df['quarter'] = df['production_date'].dt.quarter
                
            # Calculate field maturity
            if 'production_start' in df.columns and 'production_date' in df.columns:
                df['production_years'] = (df['production_date'] - df['production_start']).dt.days / 365.25
                df['maturity_phase'] = pd.cut(
                    df['production_years'],
                    bins=[0, 2, 5, 10, 20, float('inf')],
                    labels=['Early', 'Growth', 'Plateau', 'Mature', 'Late-life']
                )
                
            # Add production metrics
            if 'oil_production' in df.columns and 'gas_production' in df.columns:
                # Convert to barrel of oil equivalent (BOE)
                df['boe_production'] = df['oil_production'] + (df['gas_production'] / 6000)
                
                # Calculate cumulative production
                df['cumulative_oil'] = df.groupby('field_id')['oil_production'].cumsum()
                df['cumulative_gas'] = df.groupby('field_id')['gas_production'].cumsum()
                
            # Add recovery factor if reserves data available
            if 'recoverable_oil' in df.columns and 'cumulative_oil' in df.columns:
                df['recovery_factor'] = df['cumulative_oil'] / df['recoverable_oil']
                
            logger.info(f"Created production dataset with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Failed to create production dataset: {e}")
            raise
            
    def create_cross_regional_dataset(self, sodir_data: pd.DataFrame,
                                     bsee_data: pd.DataFrame = None) -> pd.DataFrame:
        """
        Create dataset for cross-regional comparison.
        
        Args:
            sodir_data: SODIR data (Norwegian)
            bsee_data: Optional BSEE data (US Gulf of Mexico)
            
        Returns:
            Combined dataset for cross-regional analysis
        """
        try:
            # Add region identifier to SODIR data
            sodir_data = sodir_data.copy()
            sodir_data['region'] = 'Norway_NCS'
            sodir_data['country'] = 'Norway'
            sodir_data['regulatory_body'] = 'SODIR'
            
            if bsee_data is not None:
                # Add region identifier to BSEE data
                bsee_data = bsee_data.copy()
                bsee_data['region'] = 'US_GOM'
                bsee_data['country'] = 'United States'
                bsee_data['regulatory_body'] = 'BSEE'
                
                # Standardize column names for comparison
                column_mapping = {
                    'wellbore_id': 'well_id',
                    'field_id': 'field_id',
                    'operator': 'operator_name',
                    'water_depth': 'water_depth_m',
                    'total_depth': 'total_depth_m',
                    'production_start': 'first_production_date',
                    'status': 'well_status'
                }
                
                # Rename columns for consistency
                for old_col, new_col in column_mapping.items():
                    if old_col in sodir_data.columns:
                        sodir_data.rename(columns={old_col: new_col}, inplace=True)
                    if old_col in bsee_data.columns:
                        bsee_data.rename(columns={old_col: new_col}, inplace=True)
                        
                # Combine datasets
                common_cols = list(set(sodir_data.columns) & set(bsee_data.columns))
                df = pd.concat([
                    sodir_data[common_cols],
                    bsee_data[common_cols]
                ], ignore_index=True)
                
            else:
                df = sodir_data
                
            # Add comparative metrics
            if 'water_depth_m' in df.columns:
                df['water_depth_class'] = pd.cut(
                    df['water_depth_m'],
                    bins=[0, 200, 500, 1500, float('inf')],
                    labels=['Shallow', 'Mid-water', 'Deepwater', 'Ultra-deep']
                )
                
            # Add field size classification
            if 'recoverable_oil' in df.columns:
                df['field_size_class'] = pd.cut(
                    df['recoverable_oil'],
                    bins=[0, 50, 200, 500, float('inf')],
                    labels=['Small', 'Medium', 'Large', 'Giant']
                )
                
            logger.info(f"Created cross-regional dataset with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Failed to create cross-regional dataset: {e}")
            raise
            
    def prepare_time_series(self, df: pd.DataFrame, 
                           date_col: str,
                           value_cols: List[str],
                           freq: str = 'M') -> pd.DataFrame:
        """
        Prepare time series dataset for analysis.
        
        Args:
            df: Input DataFrame
            date_col: Name of date column
            value_cols: Columns to include in time series
            freq: Frequency for resampling ('D', 'M', 'Q', 'Y')
            
        Returns:
            Time series DataFrame
        """
        try:
            # Set date as index
            ts_df = df.copy()
            ts_df[date_col] = pd.to_datetime(ts_df[date_col])
            ts_df.set_index(date_col, inplace=True)
            
            # Select value columns
            ts_df = ts_df[value_cols]
            
            # Resample to specified frequency
            ts_df = ts_df.resample(freq).agg({
                col: 'sum' if 'production' in col.lower() else 'mean'
                for col in value_cols
            })
            
            # Fill missing values
            ts_df.fillna(method='ffill', inplace=True)
            
            # Add time-based features
            ts_df['year'] = ts_df.index.year
            ts_df['month'] = ts_df.index.month
            ts_df['quarter'] = ts_df.index.quarter
            
            # Add moving averages
            for col in value_cols:
                ts_df[f'{col}_ma3'] = ts_df[col].rolling(window=3).mean()
                ts_df[f'{col}_ma12'] = ts_df[col].rolling(window=12).mean()
                
            logger.info(f"Created time series with {len(ts_df)} periods")
            return ts_df
            
        except Exception as e:
            logger.error(f"Failed to prepare time series: {e}")
            raise
            
    def create_summary_statistics(self, df: pd.DataFrame,
                                group_cols: List[str],
                                metric_cols: List[str]) -> pd.DataFrame:
        """
        Create summary statistics for dataset.
        
        Args:
            df: Input DataFrame
            group_cols: Columns to group by
            metric_cols: Columns to calculate metrics for
            
        Returns:
            Summary statistics DataFrame
        """
        try:
            # Define aggregation functions
            agg_funcs = {}
            for col in metric_cols:
                if col in df.columns:
                    if df[col].dtype in ['int64', 'float64']:
                        agg_funcs[col] = ['count', 'mean', 'std', 'min', 'max', 'sum']
                    else:
                        agg_funcs[col] = ['count', 'nunique']
                        
            # Calculate grouped statistics
            summary = df.groupby(group_cols).agg(agg_funcs)
            
            # Flatten column names
            summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
            summary.reset_index(inplace=True)
            
            logger.info(f"Created summary statistics with {len(summary)} groups")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create summary statistics: {e}")
            raise
            
    def validate_dataset(self, df: pd.DataFrame,
                       dataset_type: str) -> Dict[str, Any]:
        """
        Validate dataset quality and completeness.
        
        Args:
            df: DataFrame to validate
            dataset_type: Type of dataset from configs
            
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'record_count': len(df),
            'issues': [],
            'warnings': [],
            'completeness': {}
        }
        
        # Check required fields
        if dataset_type in self._dataset_configs:
            config = self._dataset_configs[dataset_type]
            required_fields = config.get('required_fields', [])
            
            for field in required_fields:
                if field not in df.columns:
                    results['issues'].append(f"Missing required field: {field}")
                    results['valid'] = False
                else:
                    # Check completeness
                    completeness = df[field].notna().sum() / len(df)
                    results['completeness'][field] = completeness
                    
                    if completeness < 0.5:
                        results['warnings'].append(
                            f"Low completeness for {field}: {completeness:.1%}"
                        )
                        
        # Check for duplicates
        if df.duplicated().any():
            dup_count = df.duplicated().sum()
            results['warnings'].append(f"Found {dup_count} duplicate records")
            
        # Check data types
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        for col in numeric_cols:
            if df[col].isna().all():
                results['warnings'].append(f"Column {col} contains only null values")
                
        return results