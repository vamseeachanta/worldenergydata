"""
CSV Export Module for Drilling Days Comparison

This module provides functionality to export comparison results and individual
method outputs to CSV format for future analysis and Excel compatibility.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging
import csv

logger = logging.getLogger(__name__)


class CSVExporter:
    """
    Exports drilling days comparison data to CSV format.
    
    Provides functionality for:
    - Standardized comparison CSV with 10 required columns
    - Individual method output exports  
    - Timestamped file naming for version control
    - Metadata headers for processing information
    - Excel and pandas compatibility
    """
    
    def __init__(self):
        """Initialize the CSV exporter."""
        self.standardized_columns = [
            'API12_number', 'Well_name', 'lease_method_drilling_days', 'api12_method_drilling_days',
            'lease_method_completion_days', 'api12_method_completion_days',
            'Drilling_days_difference', 'Completion_days_difference',
            'Drilling_days_percent_diff', 'Completion_days_percent_diff',
            'Status_flag', 'Notes'
        ]
        
        logger.info("CSVExporter initialized")
    
    def prepare_standardized_format(self, comparison_data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data in the standardized CSV format with required columns.
        
        Args:
            comparison_data: DataFrame with comparison results from ComparisonAnalyzer
            
        Returns:
            DataFrame formatted with standardized column names
        """
        logger.info(f"Preparing standardized format for {len(comparison_data)} wells")
        
        # Create standardized DataFrame
        standardized_df = pd.DataFrame()
        
        # Map existing columns to standardized format
        column_mapping = {
            'api_number': 'API12_number',
            'well_name_lease': 'Well_name',
            'drilling_days_lease': 'lease_method_drilling_days',
            'drilling_days_api12': 'api12_method_drilling_days',
            'completion_days_lease': 'lease_method_completion_days',
            'completion_days_api12': 'api12_method_completion_days',
            'drilling_days_difference': 'Drilling_days_difference',
            'completion_days_difference': 'Completion_days_difference',
            'drilling_days_percent_diff': 'Drilling_days_percent_diff',
            'completion_days_percent_diff': 'Completion_days_percent_diff',
            'status_flag': 'Status_flag'
        }
        
        # Map existing columns
        for old_col, new_col in column_mapping.items():
            if old_col in comparison_data.columns:
                standardized_df[new_col] = comparison_data[old_col]
            else:
                standardized_df[new_col] = 'N/A'
        
        # Handle Well_name - prefer lease method name, fallback to API12 method
        if 'well_name_lease' in comparison_data.columns:
            standardized_df['Well_name'] = comparison_data['well_name_lease']
        elif 'well_name_api12' in comparison_data.columns:
            standardized_df['Well_name'] = comparison_data['well_name_api12']
        elif 'well_name' in comparison_data.columns:
            standardized_df['Well_name'] = comparison_data['well_name']
        else:
            standardized_df['Well_name'] = 'N/A'
        
        # Add Notes column with automatic content
        standardized_df['Notes'] = standardized_df.apply(self._generate_notes, axis=1)
        
        # Format numeric columns for Excel compatibility
        standardized_df = self._format_for_excel_compatibility(standardized_df)
        
        logger.info(f"Standardized format prepared with {len(standardized_df)} rows")
        return standardized_df
    
    def export_comparison_results(self, 
                                comparison_data: pd.DataFrame, 
                                output_path: Union[str, Path],
                                include_metadata: bool = True,
                                create_dirs: bool = True) -> None:
        """
        Export comparison results to CSV file with standardized format.
        
        Args:
            comparison_data: DataFrame with comparison results
            output_path: Path to save the CSV file
            include_metadata: Whether to include metadata headers
            create_dirs: Whether to create output directories if they don't exist
        """
        output_path = Path(output_path)
        
        if create_dirs:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Exporting comparison results to: {output_path}")
        
        # Prepare standardized format
        standardized_df = self.prepare_standardized_format(comparison_data)
        
        # Create CSV content
        if include_metadata:
            self._write_csv_with_metadata(standardized_df, output_path, "Drilling Days Comparison Results")
        else:
            standardized_df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Comparison results exported successfully: {output_path}")
    
    def export_lease_method_data(self, 
                               lease_data: pd.DataFrame, 
                               output_path: Union[str, Path],
                               include_metadata: bool = True) -> None:
        """
        Export lease method data to CSV file.
        
        Args:
            lease_data: DataFrame with lease method results
            output_path: Path to save the CSV file
            include_metadata: Whether to include metadata headers
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Exporting lease method data to: {output_path}")
        
        if include_metadata:
            self._write_csv_with_metadata(lease_data, output_path, "Lease Method Drilling and Completion Days")
        else:
            lease_data.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Lease method data exported: {output_path}")
    
    def export_api12_method_data(self, 
                               api12_data: pd.DataFrame, 
                               output_path: Union[str, Path],
                               include_metadata: bool = True) -> None:
        """
        Export API12 method data to CSV file.
        
        Args:
            api12_data: DataFrame with API12 method results
            output_path: Path to save the CSV file
            include_metadata: Whether to include metadata headers
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Exporting API12 method data to: {output_path}")
        
        if include_metadata:
            self._write_csv_with_metadata(api12_data, output_path, "API12 Method Drilling and Completion Days")
        else:
            api12_data.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"API12 method data exported: {output_path}")
    
    def export_all_files(self, 
                        comparison_data: pd.DataFrame,
                        lease_data: Optional[pd.DataFrame] = None,
                        api12_data: Optional[pd.DataFrame] = None,
                        output_dir: Union[str, Path] = "results",
                        use_timestamps: bool = True) -> Dict[str, Path]:
        """
        Export all CSV files (comparison, lease method, API12 method) to directory.
        
        Args:
            comparison_data: DataFrame with comparison results
            lease_data: Optional DataFrame with lease method data
            api12_data: Optional DataFrame with API12 method data
            output_dir: Directory to save files
            use_timestamps: Whether to use timestamped filenames
            
        Returns:
            Dictionary mapping file types to their paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Exporting all CSV files to: {output_dir}")
        
        exported_files = {}
        
        # Export comparison results
        if use_timestamps:
            comparison_filename = self.generate_timestamped_filename("drilling_days_comparison", "csv")
        else:
            comparison_filename = "drilling_days_comparison.csv"
        
        comparison_path = output_dir / comparison_filename
        self.export_comparison_results(comparison_data, comparison_path)
        exported_files['comparison'] = comparison_path
        
        # Export lease method data if provided
        if lease_data is not None:
            if use_timestamps:
                lease_filename = self.generate_timestamped_filename("drilling_days_lease_method", "csv")
            else:
                lease_filename = "drilling_days_lease_method.csv"
            
            lease_path = output_dir / lease_filename
            self.export_lease_method_data(lease_data, lease_path)
            exported_files['lease_method'] = lease_path
        
        # Export API12 method data if provided
        if api12_data is not None:
            if use_timestamps:
                api12_filename = self.generate_timestamped_filename("drilling_days_api12_method", "csv")
            else:
                api12_filename = "drilling_days_api12_method.csv"
            
            api12_path = output_dir / api12_filename
            self.export_api12_method_data(api12_data, api12_path)
            exported_files['api12_method'] = api12_path
        
        logger.info(f"All CSV files exported successfully. Files: {list(exported_files.keys())}")
        return exported_files
    
    def generate_timestamped_filename(self, base_name: str, extension: str) -> str:
        """
        Generate timestamped filename for version control.
        
        Args:
            base_name: Base filename without extension
            extension: File extension (without dot)
            
        Returns:
            Timestamped filename in format: base_name_YYYYMMDD.extension
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{base_name}_{timestamp}.{extension}"
    
    def _write_csv_with_metadata(self, 
                                df: pd.DataFrame, 
                                output_path: Path, 
                                description: str) -> None:
        """
        Write CSV file with metadata headers.
        
        Args:
            df: DataFrame to write
            output_path: Output file path
            description: Description for metadata header
        """
        # First write just the CSV data for pandas compatibility in tests
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        # For metadata, create a separate info file or include it as comments that pandas ignores
        # Read the existing CSV content
        with open(output_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        # Write back with metadata as comments at the top
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write metadata headers as comments
            f.write(f"# {description}\n")
            f.write(f"# Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Generated by: WorldEnergyData Drilling Days Comparison Tool\n")
            f.write(f"# Total Records: {len(df)}\n")
            f.write(f"# Columns: {', '.join(df.columns)}\n")
            f.write("#\n")
            
            # Write the CSV content
            f.write(csv_content)
    
    def _format_for_excel_compatibility(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format DataFrame for Excel compatibility.
        
        Args:
            df: DataFrame to format
            
        Returns:
            Formatted DataFrame
        """
        df_formatted = df.copy()
        
        # Handle infinity values for Excel compatibility
        numeric_columns = ['Drilling_days_percent_diff', 'Completion_days_percent_diff']
        
        for col in numeric_columns:
            if col in df_formatted.columns:
                # Replace infinity with a large number or text
                df_formatted[col] = df_formatted[col].replace([np.inf, -np.inf], 'N/A')
                
                # Format numeric values to reasonable precision
                try:
                    df_formatted[col] = pd.to_numeric(df_formatted[col])
                    if df_formatted[col].dtype in ['float64', 'float32']:
                        df_formatted[col] = df_formatted[col].round(2)
                except (ValueError, TypeError):
                    # Keep original values if they can't be converted to numeric
                    pass
        
        # Ensure API numbers are formatted consistently
        if 'API12_number' in df_formatted.columns:
            df_formatted['API12_number'] = df_formatted['API12_number'].astype(str)
        
        # Format missing values consistently
        df_formatted = df_formatted.fillna('N/A')
        
        return df_formatted
    
    def _generate_notes(self, row: pd.Series) -> str:
        """
        Generate notes based on row data.
        
        Args:
            row: DataFrame row
            
        Returns:
            Generated notes string
        """
        notes = []
        
        # Check for significant differences
        drilling_diff_val = row.get('Drilling_days_difference', np.nan)
        if pd.notna(drilling_diff_val) and str(drilling_diff_val) != 'N/A':
            try:
                drilling_diff = abs(float(drilling_diff_val))
                if drilling_diff > 10:
                    notes.append(f"Large drilling days difference ({drilling_diff:.0f}d)")
                elif drilling_diff > 5:
                    notes.append(f"Moderate drilling days difference ({drilling_diff:.0f}d)")
            except (ValueError, TypeError):
                pass
        
        completion_diff_val = row.get('Completion_days_difference', np.nan)
        if pd.notna(completion_diff_val) and str(completion_diff_val) != 'N/A':
            try:
                completion_diff = abs(float(completion_diff_val))
                if completion_diff > 6:
                    notes.append(f"Large completion days difference ({completion_diff:.0f}d)")
                elif completion_diff > 3:
                    notes.append(f"Moderate completion days difference ({completion_diff:.0f}d)")
            except (ValueError, TypeError):
                pass
        
        # Check status flag
        status = row.get('Status_flag', '')
        if status == 'ERROR':
            notes.append("Requires immediate attention")
        elif status == 'REVIEW':
            notes.append("Requires review")
        
        # Handle percentage differences
        drilling_pct = row.get('Drilling_days_percent_diff', np.nan)
        completion_pct = row.get('Completion_days_percent_diff', np.nan)
        
        if pd.notna(drilling_pct) and str(drilling_pct) != 'N/A':
            try:
                pct_val = float(drilling_pct)
                if abs(pct_val) > 20:
                    notes.append(f"High drilling days variance ({pct_val:.1f}%)")
            except (ValueError, TypeError):
                pass
        
        if pd.notna(completion_pct) and str(completion_pct) != 'N/A':
            try:
                pct_val = float(completion_pct)
                if abs(pct_val) > 20:
                    notes.append(f"High completion days variance ({pct_val:.1f}%)")
            except (ValueError, TypeError):
                pass
        
        return '; '.join(notes) if notes else 'No significant issues'
    
    def validate_csv_output(self, csv_path: Union[str, Path]) -> Dict[str, any]:
        """
        Validate exported CSV file for data integrity.
        
        Args:
            csv_path: Path to CSV file to validate
            
        Returns:
            Dictionary with validation results
        """
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            return {'valid': False, 'error': 'File does not exist'}
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            validation_result = {
                'valid': True,
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': list(df.columns),
                'has_required_columns': True,
                'missing_columns': [],
                'data_types': {},
                'missing_values': {}
            }
            
            # Check for required columns in comparison files
            if 'API12_number' in df.columns:  # This is a comparison file
                required_cols = ['API12_number', 'Status_flag']
                missing_cols = [col for col in required_cols if col not in df.columns]
                validation_result['missing_columns'] = missing_cols
                validation_result['has_required_columns'] = len(missing_cols) == 0
            
            # Check data types
            for col in df.columns:
                validation_result['data_types'][col] = str(df[col].dtype)
                missing_count = df[col].isna().sum()
                validation_result['missing_values'][col] = missing_count
            
            logger.info(f"CSV validation completed for {csv_path}")
            return validation_result
            
        except Exception as e:
            logger.error(f"CSV validation failed for {csv_path}: {e}")
            return {'valid': False, 'error': str(e)}