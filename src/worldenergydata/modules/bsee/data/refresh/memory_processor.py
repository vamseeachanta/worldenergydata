"""
Memory Processor Module

This module handles in-memory processing of BSEE zip files,
extracting and processing data without writing to disk.
"""

import io
import zipfile
import pickle
import pandas as pd
from typing import Any, Dict, Optional, ByteString, List
from loguru import logger
from pathlib import Path
import csv


class MemoryProcessor:
    """
    Process BSEE data entirely in memory.
    
    This class handles extraction and processing of zip file contents
    in memory, avoiding disk storage of large files.
    """
    
    def __init__(self):
        """Initialize the memory processor."""
        self.processed_data = {}
        self.zip_file_list = []  # Store original filenames from zip
    
    def process_zip_in_memory(self, zip_data: ByteString) -> Dict[str, pd.DataFrame]:
        """
        Process a zip file entirely in memory.
        
        Args:
            zip_data: Bytes of the zip file
            
        Returns:
            Dictionary mapping filenames to DataFrames
        """
        data_dict = {}
        
        try:
            # Create a BytesIO object from the zip data
            zip_buffer = io.BytesIO(zip_data)
            
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                # List all files in the zip
                file_list = zip_file.namelist()
                self.zip_file_list = file_list  # Store for later reference
                logger.info(f"Found {len(file_list)} files in zip archive")
                
                for filename in file_list:
                    # Skip directories and non-CSV files
                    if filename.endswith('/') or not filename.lower().endswith('.txt'):
                        continue
                    
                    logger.info(f"Processing file: {filename}")
                    
                    try:
                        # Try different encodings for CSV data
                        encodings = ['utf-8', 'ISO-8859-1', 'latin-1']
                        df = None
                        
                        for encoding in encodings:
                            try:
                                # Re-open file for each encoding attempt
                                with zip_file.open(filename) as file:
                                    df = pd.read_csv(file, low_memory=False, encoding=encoding)
                                    logger.info(f"Successfully read {filename} with {encoding} encoding")
                                    break
                            except UnicodeDecodeError:
                                continue
                            except Exception as e:
                                if 'utf-8' in str(e).lower() or 'decode' in str(e).lower():
                                    continue
                                else:
                                    raise
                        
                        if df is not None:
                            data_dict[filename] = df
                            logger.info(f"Loaded {filename}: {df.shape[0]} rows, {df.shape[1]} columns")
                        else:
                            logger.error(f"Could not decode {filename} with any encoding")
                            
                    except Exception as e:
                        logger.error(f"Error processing {filename}: {str(e)}")
                        continue
            
            return data_dict
            
        except zipfile.BadZipFile:
            logger.error("Invalid zip file format")
            return {}
        except Exception as e:
            logger.error(f"Error processing zip file: {str(e)}")
            return {}
    
    def process_well_data(self, zip_data: ByteString, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process well (APD) data from zip.
        
        Args:
            zip_data: Bytes of the zip file
            cfg: Configuration dictionary
            
        Returns:
            Processed well data dictionary
        """
        logger.info("Processing well data in memory")
        
        # Extract data from zip
        data_dict = self.process_zip_in_memory(zip_data)
        
        if not data_dict:
            logger.error("No data extracted from well zip file")
            return {}
        
        # Process according to configuration
        processed = {}
        
        # Get configured columns if specified
        apm_columns = cfg.get('parameters', {}).get('filepath', {}).get('apm', {}).get('columns', [[]])[0]
        
        for filename, df in data_dict.items():
            # Apply column filtering if specified
            if apm_columns:
                available_cols = [col for col in apm_columns if col in df.columns]
                if available_cols:
                    df = df[available_cols]
                    logger.info(f"Filtered to {len(available_cols)} columns")
            
            # Store processed data
            processed[filename] = {
                'data': df,
                'shape': df.shape,
                'columns': df.columns.tolist(),
                'dtypes': df.dtypes.to_dict()
            }
        
        return processed
    
    def process_war_data(self, zip_data: ByteString, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process WAR (Well Activity Report) data from zip.
        
        Args:
            zip_data: Bytes of the zip file
            cfg: Configuration dictionary
            
        Returns:
            Processed WAR data dictionary
        """
        logger.info("Processing WAR data in memory")
        
        # Extract data from zip
        data_dict = self.process_zip_in_memory(zip_data)
        
        if not data_dict:
            logger.error("No data extracted from WAR zip file")
            return {}
        
        processed = {}
        
        for filename, df in data_dict.items():
            # WAR-specific processing can be added here
            processed[filename] = {
                'data': df,
                'shape': df.shape,
                'columns': df.columns.tolist(),
                'dtypes': df.dtypes.to_dict()
            }
        
        return processed
    
    def process_production_data(self, zip_data: ByteString, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process production data from zip.
        
        Args:
            zip_data: Bytes of the zip file
            cfg: Configuration dictionary
            
        Returns:
            Processed production data dictionary
        """
        logger.info("Processing production data in memory")
        
        # Extract data from zip
        data_dict = self.process_zip_in_memory(zip_data)
        
        if not data_dict:
            logger.error("No data extracted from production zip file")
            return {}
        
        processed = {}
        
        for filename, df in data_dict.items():
            # Production-specific processing
            # Check for production-related columns
            prod_columns = ['PRODUCTION_DATE', 'OIL_VOL', 'GAS_VOL', 'WATER_VOL']
            available_prod_cols = [col for col in prod_columns if col in df.columns]
            
            if available_prod_cols:
                logger.info(f"Found production columns: {available_prod_cols}")
            
            processed[filename] = {
                'data': df,
                'shape': df.shape,
                'columns': df.columns.tolist(),
                'dtypes': df.dtypes.to_dict()
            }
        
        return processed
    
    def save_dataframe_to_binary(self, df: pd.DataFrame, output_dir: str, filename: str) -> str:
        """
        Save a single DataFrame to binary format (.bin file) using pickle.
        
        Args:
            df: DataFrame to save
            output_dir: Output directory path
            filename: Original filename from zip (used to derive output name)
            
        Returns:
            Path to saved file
        """
        try:
            # Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Extract base name from original filename (e.g., mv_apd_data_all.txt -> mv_apd_data_all.bin)
            base_name = Path(filename).stem
            output_file = output_path / f"{base_name}.bin"
            
            # Save using pickle with .bin extension
            with open(output_file, 'wb') as f:
                pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.info(f"Saved DataFrame to binary: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error saving DataFrame to binary: {str(e)}")
            raise
    
    def save_to_binary(self, data: Dict[str, Any], output_dir: str, prefix: str) -> None:
        """
        Save processed data to binary format (.bin files) using pickle.
        Preserves original filenames from zip archive.
        
        Args:
            data: Processed data dictionary (keys are original filenames from zip)
            output_dir: Output directory path
            prefix: Filename prefix (unused, keeping for compatibility)
        """
        try:
            # Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save each file's data as a separate .bin file
            for original_filename, file_data in data.items():
                # Extract base name from original filename (e.g., mv_apd_data_all.txt -> mv_apd_data_all)
                base_name = Path(original_filename).stem  # This removes the extension
                
                # Create output filename with .bin extension
                output_file = output_path / f"{base_name}.bin"
                
                # Extract just the DataFrame for compatibility
                if isinstance(file_data, dict) and 'data' in file_data:
                    df_to_save = file_data['data']
                else:
                    df_to_save = file_data
                
                # Save using pickle with .bin extension
                with open(output_file, 'wb') as f:
                    pickle.dump(df_to_save, f, protocol=pickle.HIGHEST_PROTOCOL)
                
                logger.info(f"Saved binary file: {output_file} (from {original_filename})")
            
        except Exception as e:
            logger.error(f"Error saving binary data: {str(e)}")
            raise
    
    def estimate_memory_usage(self, zip_data: ByteString) -> Dict[str, float]:
        """
        Estimate memory usage for processing a zip file.
        
        Args:
            zip_data: Bytes of the zip file
            
        Returns:
            Dictionary with memory usage estimates
        """
        zip_size_mb = len(zip_data) / (1024 * 1024)
        
        # Rule of thumb: CSV data expands ~2-3x when loaded into DataFrame
        estimated_df_size_mb = zip_size_mb * 2.5
        
        # Additional overhead for processing
        overhead_mb = 50  # Base overhead
        
        total_estimate_mb = zip_size_mb + estimated_df_size_mb + overhead_mb
        
        return {
            'zip_size_mb': zip_size_mb,
            'estimated_df_size_mb': estimated_df_size_mb,
            'overhead_mb': overhead_mb,
            'total_estimate_mb': total_estimate_mb
        }
    
    def validate_data_integrity(self, data: Dict[str, Any]) -> bool:
        """
        Validate the integrity of processed data.
        
        Args:
            data: Processed data dictionary
            
        Returns:
            True if data is valid, False otherwise
        """
        if not data:
            logger.error("No data to validate")
            return False
        
        valid = True
        
        for filename, file_data in data.items():
            if isinstance(file_data, dict) and 'data' in file_data:
                df = file_data['data']
                
                # Check for empty DataFrame
                if df.empty:
                    logger.warning(f"{filename}: DataFrame is empty")
                    valid = False
                
                # Check for all null columns
                null_cols = df.columns[df.isnull().all()].tolist()
                if null_cols:
                    logger.warning(f"{filename}: Columns with all null values: {null_cols}")
                
                # Basic data validation
                logger.info(f"{filename}: {len(df)} rows, {len(df.columns)} columns")
        
        return valid