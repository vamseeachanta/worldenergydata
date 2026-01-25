"""Test suite for data comparison functionality"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../src')))


class TestDataComparison:
    """Test suite for validating data comparison logic"""
    
    def test_load_excel_files(self):
        """Test that Excel files can be loaded successfully"""
        # Test with sample data
        test_data = pd.DataFrame({
            'API_WELL_NUMBER': ['12345', '67890'],
            'DRILLING_DAYS': [10, 20],
            'COMPLETION_DAYS': [5, 8]
        })
        
        # Mock file reading
        with patch('pandas.read_excel', return_value=test_data):
            df = pd.read_excel('test.xlsx')
            assert len(df) == 2
            assert 'API_WELL_NUMBER' in df.columns
    
    def test_row_count_comparison(self):
        """Test row count comparison between dataframes"""
        df1 = pd.DataFrame({'A': [1, 2, 3]})
        df2 = pd.DataFrame({'A': [1, 2, 3]})
        df3 = pd.DataFrame({'A': [1, 2]})
        
        assert len(df1) == len(df2)
        assert len(df1) != len(df3)
    
    def test_column_comparison(self):
        """Test column name comparison"""
        df1 = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        df2 = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        df3 = pd.DataFrame({'A': [1], 'B': [2], 'D': [3]})
        
        assert list(df1.columns) == list(df2.columns)
        assert list(df1.columns) != list(df3.columns)
    
    def test_cell_by_cell_comparison(self):
        """Test cell-by-cell value comparison"""
        df1 = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df2 = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df3 = pd.DataFrame({
            'A': [1, 2, 4],  # Different value
            'B': ['x', 'y', 'z']
        })
        
        # Test exact match
        comparison = df1.equals(df2)
        assert comparison == True
        
        # Test with difference
        comparison = df1.equals(df3)
        assert comparison == False
        
        # Find specific differences
        diff_mask = df1 != df3
        assert diff_mask['A'].iloc[2] == True
        assert diff_mask['B'].iloc[2] == False
    
    def test_numeric_tolerance_comparison(self):
        """Test comparison with numeric tolerance for floating point values"""
        df1 = pd.DataFrame({'value': [1.0001, 2.0002, 3.0003]})
        df2 = pd.DataFrame({'value': [1.0002, 2.0001, 3.0004]})
        
        # Test with tolerance
        tolerance = 0.001
        diff = np.abs(df1['value'] - df2['value'])
        within_tolerance = diff <= tolerance
        
        assert all(within_tolerance)
    
    def test_date_comparison(self):
        """Test date column comparison"""
        df1 = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-02-01'])
        })
        df2 = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-02-01'])
        })
        df3 = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-02-02'])  # Different date
        })
        
        assert df1['date'].equals(df2['date'])
        assert not df1['date'].equals(df3['date'])
    
    def test_missing_value_handling(self):
        """Test comparison with missing values"""
        df1 = pd.DataFrame({'A': [1, 2, np.nan], 'B': ['x', None, 'z']})
        df2 = pd.DataFrame({'A': [1, 2, np.nan], 'B': ['x', None, 'z']})
        df3 = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        
        # pandas equals considers NaN values as equal
        assert df1.equals(df2)
        assert not df1.equals(df3)
    
    def test_data_type_mismatch(self):
        """Test handling of data type mismatches"""
        df1 = pd.DataFrame({'A': [1, 2, 3]})  # int
        df2 = pd.DataFrame({'A': ['1', '2', '3']})  # string
        
        # Direct comparison should fail
        assert not df1.equals(df2)
        
        # After type conversion
        df2['A'] = pd.to_numeric(df2['A'])
        assert df1.equals(df2)
    
    def test_comparison_metrics_calculation(self):
        """Test calculation of comparison metrics"""
        df1 = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': ['a', 'b', 'c', 'd', 'e']
        })
        df2 = pd.DataFrame({
            'A': [1, 2, 3, 4, 6],  # One difference
            'B': ['a', 'b', 'x', 'd', 'e']  # One difference
        })
        
        # Calculate metrics
        total_cells = df1.size
        matching_cells = (df1 == df2).sum().sum()
        match_percentage = (matching_cells / total_cells) * 100
        
        assert total_cells == 10
        assert matching_cells == 8
        assert match_percentage == 80.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])