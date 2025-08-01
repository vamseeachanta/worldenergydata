"""
Tests for Excel data extraction utilities for NPV data source comparison.
This module tests extraction of production and price data from Excel benchmarks.
"""

import pytest
import pandas as pd
import numpy as np
import os
import sys
from typing import List, Dict, Tuple, Optional

# Add src to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

try:
    from worldenergydata.modules.bsee.analysis.excel_data_extractor import ExcelDataExtractor
    EXCEL_EXTRACTOR_AVAILABLE = True
except ImportError:
    EXCEL_EXTRACTOR_AVAILABLE = False
    ExcelDataExtractor = None


class TestExcelDataExtraction:
    """Test suite for Excel data extraction utilities."""
    
    @pytest.fixture
    def excel_file_path(self):
        """Path to the Excel benchmark file."""
        return r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
    
    @pytest.fixture
    def extractor(self, excel_file_path):
        """Create ExcelDataExtractor instance."""
        if not EXCEL_EXTRACTOR_AVAILABLE:
            pytest.skip("ExcelDataExtractor not available")
        return ExcelDataExtractor(excel_file_path)
    
    def test_excel_file_exists(self, excel_file_path):
        """Test that the Excel benchmark file exists."""
        assert os.path.exists(excel_file_path), f"Excel file not found: {excel_file_path}"
    
    def test_extractor_initialization(self, extractor, excel_file_path):
        """Test ExcelDataExtractor initialization."""
        assert extractor is not None
        assert extractor.excel_path == excel_file_path
        assert hasattr(extractor, 'extract_production_data')
        assert hasattr(extractor, 'extract_oil_prices')
    
    def test_extract_production_data_row_22(self, extractor):
        """Test extraction of production data from Row 22 (JSM Total AVGMoly)."""
        production_data = extractor.extract_production_data(row_index=22)
        
        assert production_data is not None, "Production data extraction returned None"
        assert len(production_data) > 0, "No production data extracted"
        assert isinstance(production_data, list), "Production data should be a list"
        
        # Validate production values
        for value in production_data:
            assert isinstance(value, (int, float)), f"Production value {value} is not numeric"
            assert value >= 0, f"Production value {value} should not be negative"
        
        # Check reasonable production ranges (barrels per day)
        assert all(0 <= v <= 1000000 for v in production_data), "Production values outside reasonable range"
        
        print(f"Extracted {len(production_data)} production data points")
        print(f"Production range: {min(production_data):.0f} - {max(production_data):.0f} BBL/day")
    
    def test_extract_oil_prices_row_2(self, extractor):
        """Test extraction of oil prices from Row 4 (BRENT prices)."""
        oil_prices = extractor.extract_oil_prices(row_index=4)
        
        assert oil_prices is not None, "Oil price extraction returned None"
        assert len(oil_prices) > 0, "No oil price data extracted"
        assert isinstance(oil_prices, list), "Oil prices should be a list"
        
        # Validate price values
        for price in oil_prices:
            assert isinstance(price, (int, float)), f"Oil price {price} is not numeric"
            assert price > 0, f"Oil price {price} should be positive"
        
        # Check reasonable price ranges (USD per barrel)
        assert all(10 <= p <= 200 for p in oil_prices), "Oil prices outside reasonable range ($10-$200/bbl)"
        
        print(f"Extracted {len(oil_prices)} oil price data points")
        print(f"Price range: ${min(oil_prices):.2f} - ${max(oil_prices):.2f}/bbl")
    
    def test_extract_with_date_range(self, extractor):
        """Test extraction with specific date range."""
        # Extract data for specific columns (assuming columns represent months)
        production_data = extractor.extract_production_data(
            row_index=22,
            start_col=2,  # Skip first two columns (labels)
            end_col=50    # First 48 months
        )
        
        assert production_data is not None
        assert len(production_data) <= 48, "Should not exceed requested column range"
        assert len(production_data) > 0, "Should have some data in range"
    
    def test_data_alignment(self, extractor):
        """Test that production and price data can be aligned."""
        production_data = extractor.extract_production_data(row_index=22)
        oil_prices = extractor.extract_oil_prices(row_index=2)
        
        # Get aligned data
        aligned_data = extractor.align_data(production_data, oil_prices)
        
        assert aligned_data is not None
        assert 'production' in aligned_data
        assert 'prices' in aligned_data
        assert len(aligned_data['production']) == len(aligned_data['prices'])
        
        print(f"Aligned {len(aligned_data['production'])} data points")
    
    def test_extract_with_metadata(self, extractor):
        """Test extraction with metadata (dates, labels)."""
        metadata = extractor.extract_metadata()
        
        assert metadata is not None
        assert 'sheet_name' in metadata
        assert 'data_range' in metadata
        assert 'extraction_date' in metadata
        
        # Should identify the NPV sheet
        assert 'NPV' in metadata['sheet_name'] or 'Mo\'ly' in metadata['sheet_name']
    
    def test_handle_missing_data(self, extractor):
        """Test handling of missing or invalid data."""
        # Test with a row that might have gaps
        production_data = extractor.extract_production_data(
            row_index=22,
            handle_missing='interpolate'
        )
        
        # Should have no None values after interpolation
        assert all(v is not None for v in production_data), "Interpolation should fill missing values"
        assert all(isinstance(v, (int, float)) for v in production_data), "All values should be numeric"
    
    def test_extract_multiple_rows(self, extractor):
        """Test extraction of multiple data rows for comparison."""
        # Extract multiple production scenarios if available
        rows_to_extract = [20, 21, 22, 23]  # Assuming nearby rows might have related data
        
        multi_row_data = {}
        for row in rows_to_extract:
            try:
                data = extractor.extract_production_data(row_index=row)
                if data and len(data) > 0:
                    multi_row_data[f'row_{row}'] = data
            except Exception:
                continue
        
        assert len(multi_row_data) > 0, "Should extract at least some data"
        print(f"Extracted data from {len(multi_row_data)} rows")
    
    def test_validate_data_integrity(self, extractor):
        """Test data integrity validation."""
        production_data = extractor.extract_production_data(row_index=22)
        oil_prices = extractor.extract_oil_prices(row_index=2)
        
        # Validate data integrity
        integrity_report = extractor.validate_data_integrity(production_data, oil_prices)
        
        assert integrity_report is not None
        assert 'production_valid' in integrity_report
        assert 'prices_valid' in integrity_report
        assert 'issues' in integrity_report
        
        if not integrity_report['production_valid'] or not integrity_report['prices_valid']:
            print(f"Data integrity issues: {integrity_report['issues']}")
    
    def test_export_extracted_data(self, extractor, tmp_path):
        """Test exporting extracted data to CSV for analysis."""
        production_data = extractor.extract_production_data(row_index=22)
        oil_prices = extractor.extract_oil_prices(row_index=4)
        
        # Export to CSV
        export_path = tmp_path / "extracted_excel_data.csv"
        extractor.export_data(
            production_data=production_data,
            oil_prices=oil_prices,
            output_path=str(export_path)
        )
        
        assert export_path.exists(), "Export file should be created"
        
        # Verify exported data
        df = pd.read_csv(export_path)
        assert 'Production_BBL' in df.columns
        assert 'Oil_Price_USD' in df.columns
        assert 'Revenue_USD' in df.columns
        assert len(df) > 0, "Exported data should not be empty"
    
    @pytest.mark.parametrize("row_index,expected_min,expected_max", [
        (4, 20, 150),    # Oil prices typically between $20-$150
        (22, 1000, 100000),  # Production typically between 1k-100k BBL/day
    ])
    def test_data_ranges(self, extractor, row_index, expected_min, expected_max):
        """Test that extracted data falls within expected ranges."""
        if row_index == 4:
            data = extractor.extract_oil_prices(row_index=row_index)
        else:
            data = extractor.extract_production_data(row_index=row_index)
        
        assert data is not None
        assert len(data) > 0
        
        # Check ranges
        min_val = min(data)
        max_val = max(data)
        
        assert min_val >= expected_min * 0.5, f"Minimum value {min_val} below expected range"
        assert max_val <= expected_max * 2, f"Maximum value {max_val} above expected range"
    
    def test_performance_extraction(self, extractor):
        """Test extraction performance for large datasets."""
        import time
        
        start_time = time.time()
        production_data = extractor.extract_production_data(row_index=22)
        production_time = time.time() - start_time
        
        start_time = time.time()
        oil_prices = extractor.extract_oil_prices(row_index=2)
        price_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert production_time < 2.0, f"Production extraction took {production_time:.2f}s (>2s)"
        assert price_time < 2.0, f"Price extraction took {price_time:.2f}s (>2s)"
        
        print(f"Performance: Production {production_time:.3f}s, Prices {price_time:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])