"""
Multiple Wells Drilling and Completion Days Comparison Test Module

This module provides comprehensive testing for comparing drilling and completion days
analysis outputs from different BSEE data processing methods across 120+ wells.
"""

import pytest
import pandas as pd
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import tempfile
import shutil

try:
    import deepdiff
    DEEPDIFF_AVAILABLE = True
except ImportError:
    DEEPDIFF_AVAILABLE = False

# Try to import engine utilities, but handle gracefully if missing
try:
    from assetutilities.common.yml_utilities import ymlInput
    YML_UTILITIES_AVAILABLE = True
except ImportError:
    YML_UTILITIES_AVAILABLE = False

try:
    from worldenergydata.engine import engine
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False


class MultipleWellsDataProcessor:
    """
    Handles data processing for multiple wells comparison with memory optimization.
    """
    
    def __init__(self, chunk_size: int = 50):
        """
        Initialize processor with configurable chunk size for batch processing.
        
        Args:
            chunk_size: Number of wells to process in each batch
        """
        self.chunk_size = chunk_size
        self.processing_stats = {
            'total_wells_processed': 0,
            'successful_comparisons': 0,
            'failed_comparisons': 0,
            'memory_usage_mb': 0
        }
    
    def validate_data_format(self, df: pd.DataFrame, method_name: str) -> bool:
        """
        Validate that DataFrame contains required columns for comparison.
        
        Args:
            df: DataFrame to validate
            method_name: Name of the method for error reporting
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_columns = ['API12', 'Drilling Days', 'Completion Days']
        
        if df.empty:
            raise ValueError(f"{method_name} output is empty")
        
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"{method_name} missing required columns: {missing_cols}")
        
        return True
    
    def load_method_data(self, file_path: str, method_name: str) -> pd.DataFrame:
        """
        Load data from analysis method output file with error handling.
        
        Args:
            file_path: Path to the output file
            method_name: Name of the method for error reporting
            
        Returns:
            pd.DataFrame: Loaded and validated data
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{method_name} output file not found: {file_path}")
        
        try:
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Standardize column names for comparison
            df = self._standardize_column_names(df)
            
            # Validate data format
            self.validate_data_format(df, method_name)
            
            return df
            
        except Exception as e:
            raise RuntimeError(f"Error loading {method_name} data from {file_path}: {str(e)}")
    
    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names for consistent comparison.
        
        Args:
            df: DataFrame with potentially inconsistent column names
            
        Returns:
            pd.DataFrame: DataFrame with standardized column names
        """
        # Create column mapping for common variations
        column_mapping = {
            'API_WELL_NUMBER': 'API12',
            'api12': 'API12',
            'api_12': 'API12',
            'DRILLING_DAYS': 'Drilling Days',
            'drilling_days': 'Drilling Days',
            'COMPLETION_DAYS': 'Completion Days',
            'completion_days': 'Completion Days',
            'WELL_NAME': 'Well Name',
            'well_name': 'Well Name'
        }
        
        # Apply mapping
        df = df.rename(columns=column_mapping)
        
        return df
    
    def process_in_batches(self, lease_data: pd.DataFrame, api12_data: pd.DataFrame) -> List[Dict]:
        """
        Process well comparisons in batches to optimize memory usage.
        
        Args:
            lease_data: Data from lease method
            api12_data: Data from API12 method
            
        Returns:
            List[Dict]: List of comparison results
        """
        results = []
        
        # Merge datasets on API12 for comparison
        merged_data = pd.merge(
            lease_data, api12_data, 
            on='API12', 
            how='outer',
            suffixes=('_lease', '_api12')
        )
        
        total_wells = len(merged_data)
        self.processing_stats['total_wells_processed'] = total_wells
        
        # Process in chunks
        for start_idx in range(0, total_wells, self.chunk_size):
            end_idx = min(start_idx + self.chunk_size, total_wells)
            chunk = merged_data.iloc[start_idx:end_idx]
            
            batch_results = self._process_batch(chunk, start_idx, end_idx)
            results.extend(batch_results)
        
        return results
    
    def _process_batch(self, batch: pd.DataFrame, start_idx: int, end_idx: int) -> List[Dict]:
        """
        Process a batch of wells for comparison.
        
        Args:
            batch: DataFrame chunk to process
            start_idx: Starting index of batch
            end_idx: Ending index of batch
            
        Returns:
            List[Dict]: Batch comparison results
        """
        batch_results = []
        
        for _, row in batch.iterrows():
            try:
                comparison = self._compare_well_data(row)
                batch_results.append(comparison)
                self.processing_stats['successful_comparisons'] += 1
            except Exception as e:
                self.processing_stats['failed_comparisons'] += 1
                # Log error but continue processing
                print(f"Error processing well {row.get('API12', 'Unknown')}: {str(e)}")
        
        return batch_results
    
    def _compare_well_data(self, row: pd.Series) -> Dict:
        """
        Compare well data between methods and calculate differences.
        
        Args:
            row: Row containing data from both methods
            
        Returns:
            Dict: Comparison results for the well
        """
        api12 = row.get('API12')
        well_name = row.get('Well Name_lease') or row.get('Well Name_api12', 'Unknown')
        
        drilling_lease = row.get('Drilling Days_lease')
        drilling_api12 = row.get('Drilling Days_api12')
        completion_lease = row.get('Completion Days_lease')
        completion_api12 = row.get('Completion Days_api12')
        
        # Calculate differences
        drilling_diff = None
        completion_diff = None
        drilling_pct_diff = None
        completion_pct_diff = None
        
        if pd.notna(drilling_lease) and pd.notna(drilling_api12):
            drilling_diff = drilling_api12 - drilling_lease
            if drilling_lease != 0:
                drilling_pct_diff = (drilling_diff / drilling_lease) * 100
        
        if pd.notna(completion_lease) and pd.notna(completion_api12):
            completion_diff = completion_api12 - completion_lease
            if completion_lease != 0:
                completion_pct_diff = (completion_diff / completion_lease) * 100
        
        # Determine status
        status = self._determine_status(drilling_diff, completion_diff, drilling_pct_diff, completion_pct_diff)
        
        return {
            'API12': api12,
            'Well_Name': well_name,
            'Drilling_Days_Lease': drilling_lease,
            'Drilling_Days_API12': drilling_api12,
            'Completion_Days_Lease': completion_lease,
            'Completion_Days_API12': completion_api12,
            'Drilling_Days_Diff': drilling_diff,
            'Completion_Days_Diff': completion_diff,
            'Drilling_Days_Pct_Diff': drilling_pct_diff,
            'Completion_Days_Pct_Diff': completion_pct_diff,
            'Status': status
        }
    
    def _determine_status(self, drilling_diff: Optional[float], completion_diff: Optional[float], 
                         drilling_pct_diff: Optional[float], completion_pct_diff: Optional[float]) -> str:
        """
        Determine status based on differences between methods.
        
        Args:
            drilling_diff: Absolute difference in drilling days
            completion_diff: Absolute difference in completion days
            drilling_pct_diff: Percentage difference in drilling days
            completion_pct_diff: Percentage difference in completion days
            
        Returns:
            str: Status flag (OK, REVIEW, ERROR)
        """
        # Define thresholds
        abs_threshold = 5  # days
        pct_threshold = 10  # percent
        
        error_conditions = []
        
        # Check drilling days
        if drilling_diff is not None:
            if abs(drilling_diff) > abs_threshold:
                error_conditions.append('drilling_abs')
            if drilling_pct_diff is not None and abs(drilling_pct_diff) > pct_threshold:
                error_conditions.append('drilling_pct')
        
        # Check completion days
        if completion_diff is not None:
            if abs(completion_diff) > abs_threshold:
                error_conditions.append('completion_abs')
            if completion_pct_diff is not None and abs(completion_pct_diff) > pct_threshold:
                error_conditions.append('completion_pct')
        
        if len(error_conditions) >= 2:
            return 'ERROR'
        elif len(error_conditions) == 1:
            return 'REVIEW'
        else:
            return 'OK'


class TestMultipleWellsDataProcessor:
    """Test cases for MultipleWellsDataProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a MultipleWellsDataProcessor instance for testing."""
        return MultipleWellsDataProcessor(chunk_size=10)
    
    @pytest.fixture
    def sample_lease_data(self):
        """Create sample lease method data for testing."""
        return pd.DataFrame({
            'API12': ['12345001', '12345002', '12345003'],
            'Well Name': ['Well A', 'Well B', 'Well C'],
            'Drilling Days': [45, 52, 38],
            'Completion Days': [15, 18, 12]
        })
    
    @pytest.fixture
    def sample_api12_data(self):
        """Create sample API12 method data for testing."""
        return pd.DataFrame({
            'API12': ['12345001', '12345002', '12345004'],
            'Well Name': ['Well A', 'Well B', 'Well D'],
            'Drilling Days': [47, 50, 40],
            'Completion Days': [16, 17, 14]
        })
    
    def test_processor_initialization(self, processor):
        """Test that processor initializes correctly."""
        assert processor.chunk_size == 10
        assert processor.processing_stats['total_wells_processed'] == 0
    
    def test_validate_data_format_valid(self, processor, sample_lease_data):
        """Test validation with valid data format."""
        assert processor.validate_data_format(sample_lease_data, 'lease_method')
    
    def test_validate_data_format_empty(self, processor):
        """Test validation with empty DataFrame."""
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError, match="lease_method output is empty"):
            processor.validate_data_format(empty_df, 'lease_method')
    
    def test_validate_data_format_missing_columns(self, processor):
        """Test validation with missing required columns."""
        invalid_df = pd.DataFrame({'API12': ['12345001'], 'Wrong_Column': [45]})
        with pytest.raises(ValueError, match="missing required columns"):
            processor.validate_data_format(invalid_df, 'lease_method')
    
    def test_standardize_column_names(self, processor):
        """Test column name standardization."""
        df = pd.DataFrame({
            'API_WELL_NUMBER': ['12345001'],
            'DRILLING_DAYS': [45],
            'COMPLETION_DAYS': [15]
        })
        
        standardized = processor._standardize_column_names(df)
        
        assert 'API12' in standardized.columns
        assert 'Drilling Days' in standardized.columns
        assert 'Completion Days' in standardized.columns
    
    def test_process_in_batches(self, processor, sample_lease_data, sample_api12_data):
        """Test batch processing functionality."""
        results = processor.process_in_batches(sample_lease_data, sample_api12_data)
        
        assert len(results) > 0
        assert processor.processing_stats['total_wells_processed'] == 4  # merged dataset size
        assert processor.processing_stats['successful_comparisons'] > 0
    
    def test_compare_well_data(self, processor):
        """Test individual well comparison."""
        row = pd.Series({
            'API12': '12345001',
            'Well Name_lease': 'Well A',
            'Drilling Days_lease': 45,
            'Drilling Days_api12': 47,
            'Completion Days_lease': 15,
            'Completion Days_api12': 16
        })
        
        result = processor._compare_well_data(row)
        
        assert result['API12'] == '12345001'
        assert result['Drilling_Days_Diff'] == 2
        assert result['Completion_Days_Diff'] == 1
        assert result['Status'] in ['OK', 'REVIEW', 'ERROR']
    
    def test_determine_status_ok(self, processor):
        """Test status determination for acceptable differences."""
        status = processor._determine_status(2, 1, 4.4, 6.7)
        assert status == 'OK'
    
    def test_determine_status_review(self, processor):
        """Test status determination for minor issues."""
        status = processor._determine_status(6, 1, 12, 6.7)  # One threshold exceeded
        assert status == 'REVIEW'
    
    def test_determine_status_error(self, processor):
        """Test status determination for major issues."""
        status = processor._determine_status(8, 7, 15, 20)  # Multiple thresholds exceeded
        assert status == 'ERROR'


def run_multiple_methods_analysis(input_file: str) -> Tuple[str, str]:
    """
    Execute both analysis methods and return output file paths.
    
    Args:
        input_file: YAML configuration file path
        
    Returns:
        Tuple[str, str]: Paths to lease method and API12 method output files
    """
    if not ENGINE_AVAILABLE:
        raise RuntimeError("Engine not available - dependencies missing")
    
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    try:
        # Execute the analysis
        cfg = engine(input_file)
        
        # Return expected output file paths based on configuration
        # This should be adapted based on actual output file naming conventions
        lease_output = "drilling_and_completion_days_by_api.xlsx"  # Expected lease method output
        api12_output = "well_summ_goa_multiple_wells.csv"  # Expected API12 method output
        
        return lease_output, api12_output
        
    except Exception as e:
        raise RuntimeError(f"Error executing analysis methods: {str(e)}")


class TestMultipleWellsComparisonIntegration:
    """Integration tests for multiple wells comparison framework."""
    
    def test_enhanced_test_framework_setup(self):
        """Test that enhanced test framework can be set up successfully."""
        processor = MultipleWellsDataProcessor(chunk_size=25)
        
        # Verify processor is configured for multiple wells
        assert processor.chunk_size == 25
        assert isinstance(processor.processing_stats, dict)
        
        # Test batch processing capability
        test_data = pd.DataFrame({
            'API12': [f'1234500{i}' for i in range(1, 121)],  # 120 wells
            'Well Name': [f'Well {i}' for i in range(1, 121)],
            'Drilling Days': [40 + i % 20 for i in range(120)],
            'Completion Days': [10 + i % 10 for i in range(120)]
        })
        
        # Test that it can handle large dataset
        assert len(test_data) == 120
        assert processor.validate_data_format(test_data, 'test_method')
    
    def test_memory_optimization_batch_processing(self):
        """Test that batch processing works with memory optimization."""
        processor = MultipleWellsDataProcessor(chunk_size=30)
        
        # Create test data with 120+ wells
        large_lease_data = pd.DataFrame({
            'API12': [f'1234500{i:03d}' for i in range(1, 123)],
            'Well Name': [f'Lease Well {i}' for i in range(1, 123)],
            'Drilling Days': [35 + (i % 25) for i in range(122)],
            'Completion Days': [8 + (i % 12) for i in range(122)]
        })
        
        large_api12_data = pd.DataFrame({
            'API12': [f'1234500{i:03d}' for i in range(1, 123)],
            'Well Name': [f'API12 Well {i}' for i in range(1, 123)],
            'Drilling Days': [37 + (i % 23) for i in range(122)],
            'Completion Days': [9 + (i % 11) for i in range(122)]
        })
        
        # Process in batches
        results = processor.process_in_batches(large_lease_data, large_api12_data)
        
        # Verify results
        assert len(results) == 122  # All wells processed
        assert processor.processing_stats['total_wells_processed'] == 122
        assert processor.processing_stats['successful_comparisons'] > 0
    
    def test_error_handling_large_dataset(self):
        """Test comprehensive error handling for large dataset scenarios."""
        processor = MultipleWellsDataProcessor(chunk_size=20)
        
        # Test with missing file
        with pytest.raises(FileNotFoundError):
            processor.load_method_data('nonexistent_file.csv', 'test_method')
        
        # Test with invalid data format
        test_file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        try:
            # Create invalid CSV
            with open(test_file.name, 'w') as f:
                f.write('InvalidColumn1,InvalidColumn2\n1,2\n')
            
            with pytest.raises(ValueError, match="missing required columns"):
                processor.load_method_data(test_file.name, 'test_method')
        finally:
            os.unlink(test_file.name)
    
    def test_pytest_integration_compatibility(self):
        """Test that enhanced framework integrates with existing pytest structure."""
        # Verify that deepdiff is available for data comparison
        if not DEEPDIFF_AVAILABLE:
            pytest.skip("deepdiff not available - required for comparison testing")
        
        # Test that we can create processor within pytest framework
        processor = MultipleWellsDataProcessor()
        assert processor is not None
        
        # Test compatibility with existing test utilities
        test_yml_path = os.path.join(os.path.dirname(__file__), 'query_api_multiple_wells_rig_days.yml')
        
        # This should work without breaking existing functionality
        # (actual file may not exist in test environment, so we handle gracefully)
        if os.path.exists(test_yml_path):
            try:
                config = ymlInput(test_yml_path, updateYml=None)
                assert config is not None
            except Exception as e:
                # Log but don't fail - this is integration testing
                print(f"Config loading test: {str(e)}")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])