"""
Corrupted Data Handling Tests for Enhanced BSEE Data Refresh System

Tests for Task 8.2: Write tests for corrupted data handling in ENHANCED system
- Malformed ZIP files
- Incomplete downloads
- Invalid CSV/data formats
- Empty or truncated files
- Data validation failures
"""

import pytest
import os
import sys
import io
import zipfile
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import gzip
import struct

# Add the analysis directory to Python path for imports
analysis_dir = Path(__file__).parent
if str(analysis_dir) not in sys.path:
    sys.path.insert(0, str(analysis_dir))

from bsee_data_scraper import BSEEDataScraper
from data_freshness_validator import DataFreshnessValidator


class TestCorruptedDataHandling:
    """Test corrupted data handling in enhanced BSEE data refresh system."""

    def setup_method(self):
        """Setup for each test method."""
        self.scraper = BSEEDataScraper(max_retries=1, timeout=5)
        self.validator = DataFreshnessValidator()
        
    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self, 'scraper'):
            self.scraper.close()

    def test_malformed_zip_file_handling(self):
        """Test 8.2.1: Malformed ZIP file handling."""
        # Test completely invalid ZIP file
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': '1000'}
            # Return invalid ZIP content
            mock_response.iter_content.return_value = [b'This is not a ZIP file content'] * 10
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('well_data')
            
            assert result['status'] == 'error'
            assert 'zip' in result['error'].lower() or 'corrupt' in result['error'].lower()
            assert result['data_source'] == 'well_data'
            
        # Test truncated ZIP file (valid header but incomplete)
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': '5000'}
            
            # Create a truncated ZIP file (valid header but incomplete)
            truncated_zip = b'PK\x03\x04\x14\x00\x00\x00\x08\x00'  # ZIP header but truncated
            mock_response.iter_content.return_value = [truncated_zip]
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('production_data')
            
            assert result['status'] == 'error'
            assert 'zip' in result['error'].lower() or 'truncated' in result['error'].lower()

    def test_corrupted_zip_entries(self):
        """Test 8.2.2: Corrupted ZIP entries handling."""
        # Create a ZIP with corrupted entries
        corrupted_zip_content = self._create_corrupted_zip()
        
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': str(len(corrupted_zip_content))}
            mock_response.iter_content.return_value = [corrupted_zip_content]
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('war_data')
            
            assert result['status'] == 'error'
            assert 'zip' in result['error'].lower() or 'corrupt' in result['error'].lower()
            assert result['data_source'] == 'war_data'

    def test_incomplete_download_detection(self):
        """Test 8.2.3: Incomplete download detection."""
        # Test content-length mismatch
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': '10000'}  # Claims 10KB
            # But only returns 1KB
            mock_response.iter_content.return_value = [b'x' * 1024]
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('well_data')
            
            assert result['status'] == 'error'
            assert 'incomplete' in result['error'].lower() or 'size' in result['error'].lower()
            assert result['expected_size'] == 10000
            assert result['actual_size'] == 1024

    def test_invalid_csv_data_formats(self):
        """Test 8.2.4: Invalid CSV data format handling."""
        # Create ZIP with invalid CSV data
        invalid_csv_zip = self._create_zip_with_invalid_csv()
        
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': str(len(invalid_csv_zip))}
            mock_response.iter_content.return_value = [invalid_csv_zip]
            mock_get.return_value = mock_response
            
            with patch.object(self.scraper, '_process_zip_in_memory') as mock_process:
                # Simulate CSV parsing error
                mock_process.side_effect = pd.errors.ParserError("CSV parsing failed")
                
                result = self.scraper.download_and_process('production_data')
                
                assert result['status'] == 'error'
                assert 'csv' in result['error'].lower() or 'parsing' in result['error'].lower()

    def test_empty_file_handling(self):
        """Test 8.2.5: Empty file handling."""
        # Test completely empty response
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': '0'}
            mock_response.iter_content.return_value = []  # Empty content
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('war_data')
            
            assert result['status'] == 'error'
            assert 'empty' in result['error'].lower() or 'no content' in result['error'].lower()
            
        # Test ZIP with empty files inside
        empty_zip = self._create_zip_with_empty_files()
        
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': str(len(empty_zip))}
            mock_response.iter_content.return_value = [empty_zip]
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('well_data')
            
            # Should handle gracefully but report the issue
            assert result['status'] == 'error' or (
                result['status'] == 'success' and 
                result['file_count'] == 0
            )

    def test_data_encoding_issues(self):
        """Test 8.2.6: Data encoding issues handling."""
        # Test invalid UTF-8 encoding in CSV data
        invalid_encoding_zip = self._create_zip_with_encoding_issues()
        
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': str(len(invalid_encoding_zip))}
            mock_response.iter_content.return_value = [invalid_encoding_zip]
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('production_data')
            
            # Should handle encoding issues gracefully
            if result['status'] == 'error':
                assert 'encoding' in result['error'].lower() or 'decode' in result['error'].lower()
            else:
                # If handled gracefully, should still process some data
                assert result['status'] == 'success'
                assert 'encoding_warnings' in result

    def test_schema_validation_failures(self):
        """Test 8.2.7: Schema validation failure handling."""
        # Create ZIP with data that doesn't match expected schema
        wrong_schema_zip = self._create_zip_with_wrong_schema()
        
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': str(len(wrong_schema_zip))}
            mock_response.iter_content.return_value = [wrong_schema_zip]
            mock_get.return_value = mock_response
            
            # Mock schema validation to fail
            with patch.object(self.validator, 'validate_data_schema') as mock_validate:
                mock_validate.return_value = {
                    'is_valid': False,
                    'errors': ['Missing required columns: api_number, well_name']
                }
                
                result = self.scraper.download_and_process('war_data')
                
                assert result['status'] == 'error'
                assert 'schema' in result['error'].lower() or 'validation' in result['error'].lower()
                assert 'schema_errors' in result
                assert len(result['schema_errors']) > 0

    def test_data_type_conversion_errors(self):
        """Test 8.2.8: Data type conversion error handling."""
        # Test data that can't be converted to expected types
        type_error_zip = self._create_zip_with_type_errors()
        
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': str(len(type_error_zip))}
            mock_response.iter_content.return_value = [type_error_zip]
            mock_get.return_value = mock_response
            
            with patch.object(self.scraper, '_process_zip_in_memory') as mock_process:
                # Simulate type conversion error
                mock_process.side_effect = ValueError("Could not convert string to float")
                
                result = self.scraper.download_and_process('well_data')
                
                assert result['status'] == 'error'
                assert 'type' in result['error'].lower() or 'conversion' in result['error'].lower()

    def test_memory_corruption_detection(self):
        """Test 8.2.9: Memory corruption detection during processing."""
        # Test scenario where data gets corrupted in memory
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': '1000'}
            
            # Simulate memory corruption by returning different content each time
            call_count = 0
            def corrupted_content(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return [b'valid_zip_start']
                else:
                    return [b'corrupted_data']
            
            mock_response.iter_content.side_effect = corrupted_content
            mock_get.return_value = mock_response
            
            # Mock checksum validation to detect corruption
            with patch.object(self.scraper, '_verify_data_integrity') as mock_verify:
                mock_verify.return_value = False
                
                result = self.scraper.download_and_process('production_data')
                
                assert result['status'] == 'error'
                assert 'integrity' in result['error'].lower() or 'corruption' in result['error'].lower()

    def test_partial_file_recovery(self):
        """Test 8.2.10: Partial file recovery from corrupted archives."""
        # Test ability to recover some files from partially corrupted ZIP
        partial_corrupt_zip = self._create_partially_corrupted_zip()
        
        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': str(len(partial_corrupt_zip))}
            mock_response.iter_content.return_value = [partial_corrupt_zip]
            mock_get.return_value = mock_response
            
            result = self.scraper.download_and_process('war_data')
            
            # Should report partial success with warnings
            assert result['status'] in ['success', 'warning', 'partial_success']
            if 'corrupted_files' in result:
                assert len(result['corrupted_files']) > 0
            if 'recovered_files' in result:
                assert len(result['recovered_files']) > 0

    def test_data_consistency_validation(self):
        """Test 8.2.11: Data consistency validation."""
        # Test detection of inconsistent data (e.g., duplicate keys, missing relationships)
        with patch.object(self.validator, 'validate_data_consistency') as mock_consistency:
            mock_consistency.return_value = {
                'is_consistent': False,
                'issues': [
                    'Duplicate API numbers found: [123456, 789012]',
                    'Missing well completion dates for 15% of records'
                ]
            }
            
            # Create valid ZIP but with inconsistent data
            consistent_zip = self._create_zip_with_valid_structure()
            
            with patch.object(self.scraper.session, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status = Mock()
                mock_response.headers = {'content-length': str(len(consistent_zip))}
                mock_response.iter_content.return_value = [consistent_zip]
                mock_get.return_value = mock_response
                
                result = self.scraper.download_and_process('well_data')
                
                # Should complete but report consistency issues
                assert result['status'] in ['warning', 'partial_success']
                assert 'consistency_issues' in result
                assert len(result['consistency_issues']) > 0

    def test_error_recovery_mechanisms(self):
        """Test 8.2.12: Error recovery mechanisms for corrupted data."""
        # Test automatic fallback to alternative processing methods
        with patch.object(self.scraper.session, 'get') as mock_get:
            # First attempt with corrupted data
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {'content-length': '1000'}
            mock_response.iter_content.return_value = [b'corrupted_zip_data']
            mock_get.return_value = mock_response
            
            # Mock the primary processing to fail, then fallback to succeed
            with patch.object(self.scraper, '_process_zip_in_memory') as mock_process:
                with patch.object(self.scraper, '_fallback_processing') as mock_fallback:
                    mock_process.side_effect = zipfile.BadZipFile("Bad ZIP file")
                    mock_fallback.return_value = {
                        'source': 'production_data',
                        'files': {'recovered.csv': {'size': 1000}},
                        'dataframes': {'recovered': pd.DataFrame({'col1': [1, 2, 3]})},
                        'metadata': {'recovery_method': 'fallback_parser'}
                    }
                    
                    result = self.scraper.download_and_process('production_data')
                    
                    # Should succeed using fallback method
                    assert result['status'] == 'success'
                    assert 'recovery_method' in result
                    assert result['recovery_method'] == 'fallback_parser'
                    assert mock_fallback.called

    # Helper methods to create test data

    def _create_corrupted_zip(self):
        """Create a ZIP file with corrupted entries."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # Add a normal file
            zf.writestr('normal.txt', 'This is normal content')
            
        # Corrupt the ZIP by modifying some bytes
        zip_content = zip_buffer.getvalue()
        corrupted = bytearray(zip_content)
        # Corrupt the central directory
        if len(corrupted) > 100:
            corrupted[50:60] = b'\x00' * 10
        return bytes(corrupted)

    def _create_zip_with_invalid_csv(self):
        """Create a ZIP with invalid CSV data."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # CSV with malformed structure
            invalid_csv = "col1,col2,col3\nvalue1,value2\n\"unclosed quote,value4,value5\nvalue6,value7,value8"
            zf.writestr('invalid.csv', invalid_csv)
        return zip_buffer.getvalue()

    def _create_zip_with_empty_files(self):
        """Create a ZIP with empty files."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('empty1.csv', '')
            zf.writestr('empty2.txt', '')
        return zip_buffer.getvalue()

    def _create_zip_with_encoding_issues(self):
        """Create a ZIP with encoding issues."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # CSV with invalid UTF-8 bytes
            invalid_utf8 = b"col1,col2\nvalue1,\xff\xfevalue2\n"
            zf.writestr('encoding_issue.csv', invalid_utf8)
        return zip_buffer.getvalue()

    def _create_zip_with_wrong_schema(self):
        """Create a ZIP with wrong schema."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # CSV with unexpected columns
            wrong_schema_csv = "unexpected_col1,unexpected_col2\nvalue1,value2\n"
            zf.writestr('wrong_schema.csv', wrong_schema_csv)
        return zip_buffer.getvalue()

    def _create_zip_with_type_errors(self):
        """Create a ZIP with data type errors."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # CSV with type conversion issues
            type_error_csv = "api_number,latitude,longitude\nabc123,not_a_number,also_not_a_number\n"
            zf.writestr('type_error.csv', type_error_csv)
        return zip_buffer.getvalue()

    def _create_partially_corrupted_zip(self):
        """Create a ZIP with some good and some corrupted files."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # Good file
            zf.writestr('good_file.csv', 'col1,col2\nvalue1,value2\n')
            # This will be corrupted after creation
            zf.writestr('will_be_corrupted.csv', 'col1,col2\ndata1,data2\n')
            
        # Partially corrupt the ZIP (corrupt one file's data but keep structure)
        zip_content = bytearray(zip_buffer.getvalue())
        # Find and corrupt part of the file data (not the directory structure)
        if len(zip_content) > 200:
            zip_content[-100:-50] = b'\x00' * 50
        return bytes(zip_content)

    def _create_zip_with_valid_structure(self):
        """Create a ZIP with valid structure for consistency testing."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            csv_content = """api_number,well_name,latitude,longitude
123456,Well A,29.5,-94.2
789012,Well B,29.6,-94.3
123456,Well A Duplicate,29.5,-94.2"""
            zf.writestr('well_data.csv', csv_content)
        return zip_buffer.getvalue()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])