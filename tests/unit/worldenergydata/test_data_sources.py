"""
Unit tests for simple data source utilities.
"""

import pytest
from pathlib import Path
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, mock_open


class TestDataSourceUtilities:
    """Test suite for data source utility functions."""
    
    def test_path_validation(self):
        """Test path validation utilities."""
        # Valid paths
        assert Path('data/test.csv').suffix == '.csv'
        assert Path('data/test.xlsx').suffix == '.xlsx'
        assert Path('data/test.parquet').suffix == '.parquet'
        
        # Invalid paths should be detectable
        assert Path('data/test').suffix == ''
        assert Path('data/test.txt').suffix == '.txt'
    
    def test_date_format_conversion(self):
        """Test date format conversion utilities."""
        # YYYYMM to datetime
        date_str = '202301'
        dt = datetime.strptime(date_str, '%Y%m')
        assert dt.year == 2023
        assert dt.month == 1
        
        # YYYYMMDD to datetime
        date_str = '20230115'
        dt = datetime.strptime(date_str, '%Y%m%d')
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 15
        
        # Datetime to YYYYMM
        dt = datetime(2023, 1, 15)
        date_str = dt.strftime('%Y%m')
        assert date_str == '202301'
    
    def test_data_type_inference(self):
        """Test automatic data type inference."""
        # Numeric types
        assert isinstance(int('123'), int)
        assert isinstance(float('123.45'), float)
        
        # Boolean types
        assert bool('True') == True
        assert bool('') == False
        
        # String types
        assert isinstance('test_string', str)
    
    def test_file_size_calculation(self):
        """Test file size calculation utilities."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('test content ' * 100)
            temp_path = Path(f.name)
        
        # Check file exists and has size
        assert temp_path.exists()
        assert temp_path.stat().st_size > 0
        
        # Calculate size in different units
        size_bytes = temp_path.stat().st_size
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        
        assert size_bytes > 0
        assert size_kb < size_bytes
        assert size_mb < size_kb
        
        # Clean up
        temp_path.unlink()
    
    def test_data_chunking(self):
        """Test data chunking utilities."""
        # Create sample data
        data = list(range(100))
        chunk_size = 10
        
        # Chunk the data
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        
        assert len(chunks) == 10
        assert len(chunks[0]) == 10
        assert chunks[0] == list(range(10))
        assert chunks[-1] == list(range(90, 100))
    
    def test_column_name_standardization(self):
        """Test column name standardization."""
        # Test various column name formats
        columns = [
            'Test Column',
            'test-column',
            'TEST_COLUMN',
            'test.column',
            '  test column  '
        ]
        
        # Standardize to uppercase with underscores
        standardized = [col.strip().upper().replace(' ', '_').replace('-', '_').replace('.', '_') 
                        for col in columns]
        
        expected = [
            'TEST_COLUMN',
            'TEST_COLUMN',
            'TEST_COLUMN',
            'TEST_COLUMN',
            'TEST_COLUMN'
        ]
        
        assert standardized == expected
    
    def test_missing_value_detection(self):
        """Test missing value detection."""
        # Various representations of missing values
        missing_values = [None, np.nan, '', 'N/A', 'NA', 'null', 'NULL']
        
        def is_missing(value):
            if value is None or value == '':
                return True
            if isinstance(value, float) and np.isnan(value):
                return True
            if isinstance(value, str) and value.upper() in ['N/A', 'NA', 'NULL']:
                return True
            return False
        
        for value in missing_values:
            assert is_missing(value) == True
        
        # Non-missing values
        non_missing = [0, 0.0, 'valid', False, []]
        for value in non_missing:
            assert is_missing(value) == False
    
    def test_data_validation_ranges(self):
        """Test data validation for numeric ranges."""
        def validate_range(value, min_val, max_val):
            return min_val <= value <= max_val
        
        # Test oil production range (0 to 1,000,000 BBL)
        assert validate_range(5000, 0, 1000000) == True
        assert validate_range(-100, 0, 1000000) == False
        assert validate_range(2000000, 0, 1000000) == False
        
        # Test water depth range (0 to 12,000 feet)
        assert validate_range(5000, 0, 12000) == True
        assert validate_range(-100, 0, 12000) == False
        assert validate_range(15000, 0, 12000) == False
    
    def test_unit_conversion(self):
        """Test unit conversion utilities."""
        # BBL to cubic meters
        bbl_to_m3 = 0.158987
        barrels = 1000
        cubic_meters = barrels * bbl_to_m3
        assert abs(cubic_meters - 158.987) < 0.001
        
        # MCF to cubic meters  
        mcf_to_m3 = 28.3168
        mcf = 100
        cubic_meters = mcf * mcf_to_m3
        assert abs(cubic_meters - 2831.68) < 0.01
        
        # Feet to meters
        ft_to_m = 0.3048
        feet = 1000
        meters = feet * ft_to_m
        assert abs(meters - 304.8) < 0.01
    
    def test_api_number_validation(self):
        """Test API well number validation."""
        def validate_api_number(api):
            # Should be 12 digits (can have dashes)
            api_clean = api.replace('-', '').replace(' ', '')
            return len(api_clean) == 12 and api_clean.isdigit()
        
        # Valid API numbers
        valid_apis = [
            '177104123450',
            '177-104-12345-01',
            '177 104 12345 01'
        ]
        
        for api in valid_apis:
            assert validate_api_number(api) == True
        
        # Invalid API numbers
        invalid_apis = [
            '12345',  # Too short
            '1771041234501234',  # Too long
            'ABC104123450',  # Contains letters
            ''  # Empty
        ]
        
        for api in invalid_apis:
            assert validate_api_number(api) == False
    
    def test_coordinate_validation(self):
        """Test coordinate validation for Gulf of Mexico."""
        def validate_gom_coordinates(lat, lon):
            # Gulf of Mexico approximate bounds
            return (18.0 <= lat <= 30.5) and (-97.5 <= lon <= -81.0)
        
        # Valid GOM coordinates
        assert validate_gom_coordinates(28.0, -90.0) == True
        assert validate_gom_coordinates(25.5, -94.0) == True
        
        # Invalid coordinates (outside GOM)
        assert validate_gom_coordinates(40.0, -90.0) == False  # Too far north
        assert validate_gom_coordinates(28.0, -75.0) == False  # Too far east
        assert validate_gom_coordinates(15.0, -90.0) == False  # Too far south
        assert validate_gom_coordinates(28.0, -100.0) == False  # Too far west
    
    def test_production_decline_calculation(self):
        """Test production decline rate calculation."""
        def calculate_decline_rate(initial, final, time_periods):
            if initial <= 0 or final <= 0 or time_periods <= 0:
                return None
            return 1 - (final / initial) ** (1 / time_periods)
        
        # Test normal decline
        initial_prod = 1000
        final_prod = 800
        periods = 12
        
        decline_rate = calculate_decline_rate(initial_prod, final_prod, periods)
        assert decline_rate is not None
        assert 0.01 < decline_rate < 0.03  # Reasonable monthly decline
        
        # Test edge cases
        assert calculate_decline_rate(0, 100, 12) is None
        assert calculate_decline_rate(100, 0, 12) is None
        assert calculate_decline_rate(100, 100, 12) == 0  # No decline
    
    def test_checksum_calculation(self):
        """Test checksum calculation for data integrity."""
        import hashlib
        
        def calculate_checksum(data):
            if isinstance(data, str):
                data = data.encode('utf-8')
            return hashlib.md5(data).hexdigest()
        
        # Test string checksum
        data1 = "test data"
        checksum1 = calculate_checksum(data1)
        assert len(checksum1) == 32  # MD5 produces 32 character hex
        
        # Same data should produce same checksum
        checksum2 = calculate_checksum("test data")
        assert checksum1 == checksum2
        
        # Different data should produce different checksum
        checksum3 = calculate_checksum("different data")
        assert checksum1 != checksum3
    
    def test_field_name_normalization(self):
        """Test field name normalization."""
        def normalize_field_name(name):
            # Remove special characters, convert to uppercase
            import re
            normalized = re.sub(r'[^A-Za-z0-9\s]', '', name)
            normalized = normalized.upper().strip()
            normalized = re.sub(r'\s+', '_', normalized)
            return normalized
        
        # Test various field name formats
        assert normalize_field_name("St. Malo") == "ST_MALO"
        assert normalize_field_name("Jack/St. Malo") == "JACKST_MALO"
        assert normalize_field_name("anchor field") == "ANCHOR_FIELD"
        assert normalize_field_name("Julia (2014)") == "JULIA_2014"