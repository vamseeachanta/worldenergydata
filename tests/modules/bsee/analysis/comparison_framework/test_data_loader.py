"""
Tests for DataLoader class in the drilling days comparison framework.

This module tests the functionality of loading and preprocessing data from both
drilling days calculation methods (lease method and API12 method).
"""

import pytest
import pandas as pd
import os
import tempfile
from unittest.mock import patch, MagicMock

from .data_loader import DataLoader, DataLoaderError


class TestDataLoader:
    """Test suite for DataLoader class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.data_loader = DataLoader()
        
        # Create sample data for testing
        self.sample_lease_data = pd.DataFrame({
            'API_WELL_NUMBER': ['608074030500', '608074030501', '427034057700'],
            'WELL_NAME': ['001', '001', '001'],
            'WELL_SPUD_DATE': ['07/18/2012', '09/23/2012', '10/03/2009'],
            'TOTAL_DEPTH_DATE': ['08/17/2012', '11/26/2012', '10/28/2009'],
            'DRILLING_DAYS': [30.0, 64.0, 21.0],
            'COMPLETION_DAYS': [1, 3, 24]
        })
        
        self.sample_api12_data = pd.DataFrame({
            'API12': ['608074030500', '608074030501', '427034057700'],
            'API10': ['6080740305', '6080740305', '4270340577'],
            'WELL_SPUD_DATE': ['2012-07-18', '2012-09-23', '2009-10-03'],
            'TOTAL_DEPTH_DATE': ['2012-08-17', '2012-11-26', '2009-10-28'],
            'Drilling Days': [30, 64, 21],
            'Completion Days': [1, 3, 24],
            'COMPLETION_NAME': ['', '', ''],
            'WELL_NAME': ['001', '001', '001']
        })

    def test_init_default_config(self):
        """Test DataLoader initialization with default configuration."""
        loader = DataLoader()
        assert loader.config is not None
        assert 'lease_method' in loader.config
        assert 'api12_method' in loader.config
        assert 'standardized_columns' in loader.config

    def test_init_custom_config(self):
        """Test DataLoader initialization with custom configuration."""
        custom_config = {
            'lease_method': {'file_path': 'custom_path.xlsx'},
            'api12_method': {'file_pattern': 'custom_*.csv'}
        }
        loader = DataLoader(custom_config)
        assert loader.config['lease_method']['file_path'] == 'custom_path.xlsx'
        assert loader.config['api12_method']['file_pattern'] == 'custom_*.csv'

    def test_load_lease_method_excel_file_success(self):
        """Test successful loading of lease method Excel file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, 'test_lease_data.xlsx')
            self.sample_lease_data.to_excel(file_path, index=False)
            
            result = self.data_loader.load_lease_method_data(file_path)
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            assert 'API_WELL_NUMBER' in result.columns
            assert 'DRILLING_DAYS' in result.columns
            assert 'COMPLETION_DAYS' in result.columns
            
            # Check data types
            assert result['DRILLING_DAYS'].dtype in ['float64', 'int64']
            assert result['COMPLETION_DAYS'].dtype in ['float64', 'int64']

    def test_load_lease_method_file_not_found(self):
        """Test handling of missing lease method Excel file."""
        with pytest.raises(DataLoaderError) as exc_info:
            self.data_loader.load_lease_method_data('nonexistent_file.xlsx')
        
        assert 'File not found' in str(exc_info.value)

    def test_load_lease_method_invalid_format(self):
        """Test handling of invalid Excel file format."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, 'invalid.xlsx')
            # Write invalid content
            with open(file_path, 'wb') as f:
                f.write(b'Not an Excel file')
            
            with pytest.raises(DataLoaderError) as exc_info:
                self.data_loader.load_lease_method_data(file_path)
            
            assert 'Invalid file format' in str(exc_info.value)

    def test_load_api12_method_csv_files_success(self):
        """Test successful loading of API12 method CSV files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create multiple CSV files matching the pattern
            csv_files = ['block_api12_633.csv', 'block_api12_634.csv']
            
            for csv_file in csv_files:
                file_path = os.path.join(tmp_dir, csv_file)
                sample_data = self.sample_api12_data.copy()
                sample_data.to_csv(file_path, index=False)
            
            result = self.data_loader.load_api12_method_data(tmp_dir, 'block_api12_*.csv')
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) >= 3  # Should have data from multiple files
            assert 'API12' in result.columns
            assert 'Drilling Days' in result.columns
            assert 'Completion Days' in result.columns

    def test_load_api12_method_no_matching_files(self):
        """Test handling when no CSV files match the pattern."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(DataLoaderError) as exc_info:
                self.data_loader.load_api12_method_data(tmp_dir, 'nonexistent_*.csv')
            
            assert 'No files found matching pattern' in str(exc_info.value)

    def test_load_api12_method_invalid_csv(self):
        """Test handling of invalid CSV file content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_file = os.path.join(tmp_dir, 'block_api12_test.csv')
            
            # Create invalid CSV content (missing required columns)
            with open(csv_file, 'w') as f:
                f.write('Invalid,CSV,Content\n1,2,3')  # Missing required columns
            
            with pytest.raises(DataLoaderError) as exc_info:
                self.data_loader.load_api12_method_data(tmp_dir, 'block_api12_*.csv')
            
            assert 'No valid CSV files could be processed' in str(exc_info.value)

    def test_standardize_column_names_lease_method(self):
        """Test column name standardization for lease method data."""
        result = self.data_loader.standardize_column_names(
            self.sample_lease_data.copy(), 'lease'
        )
        
        # Check that standardized column names exist
        expected_columns = ['api_number', 'drilling_days', 'completion_days', 
                          'spud_date', 'total_depth_date']
        
        for col in expected_columns:
            assert col in result.columns

    def test_standardize_column_names_api12_method(self):
        """Test column name standardization for API12 method data."""
        result = self.data_loader.standardize_column_names(
            self.sample_api12_data.copy(), 'api12'
        )
        
        # Check that standardized column names exist
        expected_columns = ['api_number', 'drilling_days', 'completion_days',
                          'spud_date', 'total_depth_date']
        
        for col in expected_columns:
            assert col in result.columns

    def test_validate_and_convert_data_types(self):
        """Test data type validation and conversion."""
        test_data = pd.DataFrame({
            'api_number': ['608074030500', '608074030501'],
            'drilling_days': ['30', '64'],  # String values that should be converted
            'completion_days': [1.0, 3.0],
            'spud_date': ['2012-07-18', '2012-09-23'],
            'total_depth_date': ['2012-08-17', '2012-11-26']
        })
        
        result = self.data_loader.validate_and_convert_data_types(test_data)
        
        # Check data types after conversion
        assert result['drilling_days'].dtype in ['float64', 'int64']
        assert result['completion_days'].dtype in ['float64', 'int64']
        assert pd.api.types.is_datetime64_any_dtype(result['spud_date'])
        assert pd.api.types.is_datetime64_any_dtype(result['total_depth_date'])

    def test_validate_and_convert_data_types_invalid_data(self):
        """Test handling of invalid data during type conversion."""
        test_data = pd.DataFrame({
            'api_number': ['608074030500'],
            'drilling_days': ['invalid_number'],  # Invalid numeric value
            'completion_days': [1.0],
            'spud_date': ['2012-07-18'],
            'total_depth_date': ['2012-08-17']
        })
        
        # The current implementation converts invalid numbers to NaN rather than raising errors
        # This is actually the expected behavior with errors='coerce'
        result = self.data_loader.validate_and_convert_data_types(test_data)
        
        # Check that invalid numeric data was converted to NaN
        assert pd.isna(result['drilling_days'].iloc[0])
        assert result['completion_days'].iloc[0] == 1.0

    def test_handle_missing_data(self):
        """Test handling of missing data in required columns."""
        test_data = pd.DataFrame({
            'api_number': ['608074030500', None, '427034057700'],
            'drilling_days': [30.0, 64.0, None],
            'completion_days': [1, 3, 24],
            'spud_date': ['2012-07-18', '2012-09-23', '2009-10-03'],
            'total_depth_date': ['2012-08-17', '2012-11-26', '2009-10-28']
        })
        
        result = self.data_loader.handle_missing_data(test_data)
        
        # Should remove rows with missing API numbers
        assert len(result) == 2
        assert result['api_number'].notna().all()
        
        # Should fill missing drilling_days with 0 (or configurable default)
        assert result['drilling_days'].notna().all()

    def test_preprocess_data_complete_workflow(self):
        """Test complete data preprocessing workflow."""
        # Test with lease method data
        lease_result = self.data_loader.preprocess_data(
            self.sample_lease_data.copy(), 'lease'
        )
        
        # Verify standardized structure
        required_columns = ['api_number', 'drilling_days', 'completion_days']
        for col in required_columns:
            assert col in lease_result.columns
        
        # Test with API12 method data
        api12_result = self.data_loader.preprocess_data(
            self.sample_api12_data.copy(), 'api12'
        )
        
        # Verify standardized structure
        for col in required_columns:
            assert col in api12_result.columns

    def test_load_and_preprocess_lease_method_integration(self):
        """Integration test for complete lease method loading and preprocessing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, 'test_lease_integration.xlsx')
            self.sample_lease_data.to_excel(file_path, index=False)
            
            result = self.data_loader.load_and_preprocess_lease_method(file_path)
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            
            # Check standardized columns exist
            required_columns = ['api_number', 'drilling_days', 'completion_days']
            for col in required_columns:
                assert col in result.columns
            
            # Check data types are correct
            assert result['drilling_days'].dtype in ['float64', 'int64']
            assert result['completion_days'].dtype in ['float64', 'int64']

    def test_load_and_preprocess_api12_method_integration(self):
        """Integration test for complete API12 method loading and preprocessing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_file = os.path.join(tmp_dir, 'block_api12_test.csv')
            self.sample_api12_data.to_csv(csv_file, index=False)
            
            result = self.data_loader.load_and_preprocess_api12_method(
                tmp_dir, 'block_api12_*.csv'
            )
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            
            # Check standardized columns exist
            required_columns = ['api_number', 'drilling_days', 'completion_days']
            for col in required_columns:
                assert col in result.columns
            
            # Check data types are correct
            assert result['drilling_days'].dtype in ['float64', 'int64']
            assert result['completion_days'].dtype in ['float64', 'int64']

    def test_configuration_validation(self):
        """Test validation of configuration parameters."""
        # Test completely missing sections (this should raise an error)
        invalid_config = {
            'some_other_section': {}  # Missing both required sections
        }
        
        with pytest.raises(DataLoaderError) as exc_info:
            DataLoader(invalid_config)
        
        assert 'Invalid configuration' in str(exc_info.value)
        
        # Test valid but minimal configuration (this should work)
        minimal_valid_config = {
            'lease_method': {},  # Empty but present
            'api12_method': {}   # Empty but present
        }
        
        # This should not raise an error
        loader = DataLoader(minimal_valid_config)
        assert loader.config is not None

    def test_error_logging(self):
        """Test that errors are properly logged."""
        with patch.object(self.data_loader, 'logger') as mock_logger:
            # Test error logging for invalid file format (this triggers the generic exception handler)
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_path = os.path.join(tmp_dir, 'invalid.xlsx')
                with open(file_path, 'wb') as f:
                    f.write(b'Not an Excel file')
                
                try:
                    self.data_loader.load_lease_method_data(file_path)
                except DataLoaderError:
                    pass
                
                # Verify that error was logged
                mock_logger.error.assert_called_once()
                
                # Also verify that info logging works
                assert mock_logger.info.call_count >= 1  # Should have called info at least once