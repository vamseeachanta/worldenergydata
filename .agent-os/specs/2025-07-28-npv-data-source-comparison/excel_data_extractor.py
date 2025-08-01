"""
Excel Data Extraction Utilities for NPV Data Source Comparison.
Extracts production and price data from Excel benchmark files for comparison with manual analysis.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Union
import warnings
warnings.filterwarnings('ignore', category=UserWarning)


class ExcelDataExtractor:
    """Extract and validate data from Excel benchmark files."""
    
    def __init__(self, excel_path: str):
        """
        Initialize the Excel data extractor.
        
        Args:
            excel_path: Path to the Excel file containing benchmark data
        """
        self.excel_path = excel_path
        self.sheet_name = "NPV w Mo'ly data chart"  # Default sheet name
        self._validate_file_exists()
    
    def _validate_file_exists(self):
        """Validate that the Excel file exists."""
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Excel file not found: {self.excel_path}")
    
    def extract_production_data(self, row_index: int = 22, start_col: int = 2, 
                              end_col: Optional[int] = None,
                              handle_missing: str = 'skip') -> List[float]:
        """
        Extract production data from specified row (default Row 22: JSM Total AVGMoly).
        
        Args:
            row_index: Excel row index (0-based, so Row 22 in Excel = index 21)
            start_col: Starting column index (default 2 to skip labels)
            end_col: Ending column index (None for all columns)
            handle_missing: How to handle missing values ('skip', 'interpolate', 'zero')
            
        Returns:
            List of production values
        """
        try:
            # Read the Excel file
            df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name, 
                             header=None, engine='openpyxl')
            
            # Excel rows are 1-based, pandas is 0-based
            row_idx = row_index - 1
            
            # Extract the row data
            if end_col is None:
                row_data = df.iloc[row_idx, start_col:]
            else:
                row_data = df.iloc[row_idx, start_col:end_col]
            
            # Convert to numeric values
            production_values = []
            for val in row_data:
                try:
                    # Handle various formats (strings with commas, currency symbols, etc.)
                    if pd.isna(val):
                        if handle_missing == 'zero':
                            production_values.append(0.0)
                        elif handle_missing == 'skip':
                            continue
                        else:  # interpolate will be handled later
                            production_values.append(None)
                    else:
                        # Remove currency symbols and commas
                        if isinstance(val, str):
                            val = val.replace('$', '').replace(',', '').strip()
                        numeric_val = float(val)
                        if numeric_val >= 0:  # Only positive production values
                            production_values.append(numeric_val)
                except (ValueError, TypeError):
                    if handle_missing == 'zero':
                        production_values.append(0.0)
                    elif handle_missing != 'skip':
                        production_values.append(None)
            
            # Handle interpolation if requested
            if handle_missing == 'interpolate' and None in production_values:
                production_values = self._interpolate_missing(production_values)
            
            # Remove any remaining None values
            production_values = [v for v in production_values if v is not None]
            
            return production_values
            
        except Exception as e:
            print(f"Error extracting production data: {e}")
            return []
    
    def extract_oil_prices(self, row_index: int = 4, start_col: int = 2,
                          end_col: Optional[int] = None) -> List[float]:
        """
        Extract oil price data from specified row (default Row 4: BRENT prices).
        
        Args:
            row_index: Excel row index (1-based, so Row 4 in Excel = index 3)
            start_col: Starting column index
            end_col: Ending column index
            
        Returns:
            List of oil prices
        """
        try:
            # Read the Excel file
            df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name,
                             header=None, engine='openpyxl')
            
            # Excel rows are 1-based, pandas is 0-based
            row_idx = row_index - 1
            
            # Extract the row data
            if end_col is None:
                row_data = df.iloc[row_idx, start_col:]
            else:
                row_data = df.iloc[row_idx, start_col:end_col]
            
            # Convert to numeric values
            price_values = []
            for val in row_data:
                try:
                    if pd.isna(val):
                        continue
                    # Remove currency symbols and commas
                    if isinstance(val, str):
                        val = val.replace('$', '').replace(',', '').strip()
                    numeric_val = float(val)
                    # Oil prices should be in reasonable range
                    if 10 <= numeric_val <= 200:
                        price_values.append(numeric_val)
                except (ValueError, TypeError):
                    continue
            
            return price_values
            
        except Exception as e:
            print(f"Error extracting oil price data: {e}")
            return []
    
    def align_data(self, production_data: List[float], 
                   oil_prices: List[float]) -> Dict[str, List[float]]:
        """
        Align production and price data to ensure same length.
        
        Args:
            production_data: List of production values
            oil_prices: List of oil prices
            
        Returns:
            Dictionary with aligned 'production' and 'prices' lists
        """
        min_length = min(len(production_data), len(oil_prices))
        
        return {
            'production': production_data[:min_length],
            'prices': oil_prices[:min_length],
            'periods': min_length
        }
    
    def extract_metadata(self) -> Dict[str, any]:
        """
        Extract metadata about the Excel file and data.
        
        Returns:
            Dictionary containing metadata
        """
        try:
            # Read Excel file info
            xl = pd.ExcelFile(self.excel_path)
            sheet_names = xl.sheet_names
            
            # Find the NPV sheet
            npv_sheet = None
            for sheet in sheet_names:
                if 'NPV' in sheet or 'Mo\'ly' in sheet:
                    npv_sheet = sheet
                    break
            
            # Get data dimensions
            if npv_sheet:
                df = pd.read_excel(self.excel_path, sheet_name=npv_sheet, 
                                 header=None, engine='openpyxl')
                data_shape = df.shape
            else:
                data_shape = (0, 0)
            
            return {
                'sheet_name': npv_sheet or self.sheet_name,
                'all_sheets': sheet_names,
                'data_range': f"{data_shape[0]} rows x {data_shape[1]} columns",
                'extraction_date': datetime.now().isoformat(),
                'file_path': self.excel_path
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'extraction_date': datetime.now().isoformat()
            }
    
    def validate_data_integrity(self, production_data: List[float],
                               oil_prices: List[float]) -> Dict[str, any]:
        """
        Validate integrity of extracted data.
        
        Args:
            production_data: List of production values
            oil_prices: List of oil prices
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check production data
        production_valid = True
        if not production_data:
            issues.append("No production data extracted")
            production_valid = False
        elif len(production_data) < 12:
            issues.append(f"Limited production data: only {len(production_data)} months")
        
        # Check for outliers in production
        if production_data:
            prod_mean = np.mean(production_data)
            prod_std = np.std(production_data)
            outliers = [i for i, v in enumerate(production_data) 
                       if abs(v - prod_mean) > 3 * prod_std]
            if outliers:
                issues.append(f"Production outliers at indices: {outliers}")
        
        # Check price data
        prices_valid = True
        if not oil_prices:
            issues.append("No price data extracted")
            prices_valid = False
        elif len(oil_prices) < 12:
            issues.append(f"Limited price data: only {len(oil_prices)} months")
        
        # Check price reasonableness
        if oil_prices:
            unreasonable_prices = [i for i, p in enumerate(oil_prices)
                                 if p < 20 or p > 150]
            if unreasonable_prices:
                issues.append(f"Unusual prices at indices: {unreasonable_prices}")
        
        # Check data alignment
        if production_data and oil_prices:
            len_diff = abs(len(production_data) - len(oil_prices))
            if len_diff > 0:
                issues.append(f"Data length mismatch: {len_diff} periods difference")
        
        return {
            'production_valid': production_valid,
            'prices_valid': prices_valid,
            'data_aligned': len(production_data) == len(oil_prices) if production_data and oil_prices else False,
            'issues': issues,
            'production_count': len(production_data) if production_data else 0,
            'price_count': len(oil_prices) if oil_prices else 0
        }
    
    def export_data(self, production_data: List[float], oil_prices: List[float],
                   output_path: str, include_metadata: bool = True):
        """
        Export extracted data to CSV file.
        
        Args:
            production_data: List of production values
            oil_prices: List of oil prices
            output_path: Path for output CSV file
            include_metadata: Whether to include metadata in the file
        """
        # Align data first
        aligned = self.align_data(production_data, oil_prices)
        
        # Create DataFrame
        df = pd.DataFrame({
            'Period': range(1, aligned['periods'] + 1),
            'Production_BBL': aligned['production'],
            'Oil_Price_USD': aligned['prices'],
            'Revenue_USD': [p * price for p, price in 
                          zip(aligned['production'], aligned['prices'])]
        })
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        
        # Add metadata as separate file if requested
        if include_metadata:
            metadata = self.extract_metadata()
            metadata_path = output_path.replace('.csv', '_metadata.txt')
            with open(metadata_path, 'w') as f:
                f.write("Excel Data Extraction Report\n")
                f.write("="*50 + "\n")
                f.write(f"Source: {metadata.get('file_path', 'Unknown')}\n")
                f.write(f"Sheet: {metadata.get('sheet_name', 'Unknown')}\n")
                f.write(f"Extracted: {metadata.get('extraction_date', 'Unknown')}\n")
                f.write(f"Data Range: {metadata.get('data_range', 'Unknown')}\n")
                f.write(f"Periods: {aligned['periods']}\n")
    
    def _interpolate_missing(self, values: List[Optional[float]]) -> List[float]:
        """
        Interpolate missing values in a list.
        
        Args:
            values: List with possible None values
            
        Returns:
            List with interpolated values
        """
        # Convert to pandas Series for easy interpolation
        s = pd.Series(values)
        s = s.interpolate(method='linear', limit_direction='both')
        return s.tolist()
    
    def compare_with_manual_data(self, manual_production: List[float],
                                manual_prices: List[float]) -> Dict[str, any]:
        """
        Compare Excel data with manually extracted data.
        
        Args:
            manual_production: Production data from manual analysis
            manual_prices: Price data from manual analysis
            
        Returns:
            Comparison report dictionary
        """
        # Extract Excel data
        excel_production = self.extract_production_data()
        excel_prices = self.extract_oil_prices()
        
        # Align all data to same length
        min_len = min(len(excel_production), len(excel_prices),
                     len(manual_production), len(manual_prices))
        
        excel_prod_aligned = excel_production[:min_len]
        excel_price_aligned = excel_prices[:min_len]
        manual_prod_aligned = manual_production[:min_len]
        manual_price_aligned = manual_prices[:min_len]
        
        # Calculate differences
        prod_diffs = [abs(e - m) / e * 100 if e != 0 else 0
                     for e, m in zip(excel_prod_aligned, manual_prod_aligned)]
        price_diffs = [abs(e - m) / e * 100 if e != 0 else 0
                      for e, m in zip(excel_price_aligned, manual_price_aligned)]
        
        return {
            'periods_compared': min_len,
            'production': {
                'avg_difference_pct': np.mean(prod_diffs),
                'max_difference_pct': max(prod_diffs),
                'total_excel': sum(excel_prod_aligned),
                'total_manual': sum(manual_prod_aligned),
                'correlation': np.corrcoef(excel_prod_aligned, manual_prod_aligned)[0, 1]
            },
            'prices': {
                'avg_difference_pct': np.mean(price_diffs),
                'max_difference_pct': max(price_diffs),
                'avg_excel': np.mean(excel_price_aligned),
                'avg_manual': np.mean(manual_price_aligned),
                'correlation': np.corrcoef(excel_price_aligned, manual_price_aligned)[0, 1]
            }
        }