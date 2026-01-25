"""
Data Validation and Error Recovery Tests for Enhanced BSEE Data Refresh System

Tests for Task 8.3: Implement data validation and error recovery in ENHANCED system
- Schema validation for downloaded data
- Checksum verification
- Automatic retry mechanisms
- Graceful fallback strategies
- Error reporting and logging
"""

import pytest
import os
import sys
import hashlib
import time
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import zipfile
import io

# Add the analysis directory to Python path for imports
analysis_dir = Path(__file__).parent
if str(analysis_dir) not in sys.path:
    sys.path.insert(0, str(analysis_dir))

from bsee_data_scraper import BSEEDataScraper
from data_freshness_validator import DataFreshnessValidator


class TestDataValidationAndRecovery:
    """Test data validation and error recovery for enhanced BSEE system."""

    def setup_method(self):
        """Setup for each test method."""
        self.scraper = BSEEDataScraper(max_retries=3, timeout=10)
        self.validator = DataFreshnessValidator()
        
    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self, 'scraper'):
            self.scraper.close()

    def test_schema_validation_implementation(self):
        """Test 8.3.1: Schema validation for downloaded data."""
        # Test valid schema validation
        valid_data = pd.DataFrame({
            'api_number': ['123456789012', '123456789013'],
            'well_name': ['Well A', 'Well B'],
            'latitude': [29.5, 29.6],
            'longitude': [-94.2, -94.3],
            'spud_date': ['2023-01-15', '2023-02-20']
        })
        
        validation_result = self.validator.validate_well_data_schema(valid_data)
        
        assert validation_result['is_valid'] == True
        assert len(validation_result['errors']) == 0
        assert 'required_columns_present' in validation_result
        assert validation_result['required_columns_present'] == True
        
        # Test invalid schema validation
        invalid_data = pd.DataFrame({
            'wrong_column': ['value1', 'value2'],
            'another_wrong': ['value3', 'value4']
        })
        
        validation_result = self.validator.validate_well_data_schema(invalid_data)
        
        assert validation_result['is_valid'] == False
        assert len(validation_result['errors']) > 0
        assert any('api_number' in error for error in validation_result['errors'])

    def test_production_data_schema_validation(self):
        """Test 8.3.2: Production data schema validation."""
        # Test valid production data schema
        valid_prod_data = pd.DataFrame({
            'api_well_number': ['123456789012', '123456789013'],
            'production_date': ['2023-01-01', '2023-01-02'],
            'oil_production': [100.5, 150.3],
            'gas_production': [1000.0, 1500.0],
            'water_production': [50.0, 75.0]
        })
        
        validation_result = self.validator.validate_production_data_schema(valid_prod_data)
        
        assert validation_result['is_valid'] == True
        assert validation_result['record_count'] == 2
        assert 'data_types_valid' in validation_result
        
        # Test with invalid data types
        invalid_prod_data = pd.DataFrame({
            'api_well_number': ['123456789012', 'invalid_api'],
            'production_date': ['2023-01-01', 'invalid_date'],
            'oil_production': [100.5, 'not_a_number'],
            'gas_production': [1000.0, None],
            'water_production': [50.0, -10.0]  # Negative production invalid
        })
        
        validation_result = self.validator.validate_production_data_schema(invalid_prod_data)
        
        assert validation_result['is_valid'] == False
        assert len(validation_result['errors']) > 0
        assert 'data_type_errors' in validation_result

    def test_checksum_verification_implementation(self):
        """Test 8.3.3: Checksum verification for data integrity."""
        # Test successful checksum verification
        test_data = b"test data content for checksum verification"
        expected_checksum = hashlib.sha256(test_data).hexdigest()
        
        verification_result = self.validator.verify_data_checksum(test_data, expected_checksum)
        
        assert verification_result['is_valid'] == True
        assert verification_result['calculated_checksum'] == expected_checksum
        assert verification_result['provided_checksum'] == expected_checksum
        
        # Test failed checksum verification
        wrong_checksum = hashlib.sha256(b"different data").hexdigest()
        
        verification_result = self.validator.verify_data_checksum(test_data, wrong_checksum)
        
        assert verification_result['is_valid'] == False
        assert verification_result['calculated_checksum'] != verification_result['provided_checksum']
        assert 'integrity_error' in verification_result

    def test_automatic_retry_mechanisms(self):
        """Test 8.3.4: Automatic retry mechanisms with validation."""
        retry_count = 0
        
        def mock_download_with_retries(*args, **kwargs):
            nonlocal retry_count
            retry_count += 1
            
            if retry_count < 3:
                # First two attempts fail validation
                return {
                    'status': 'error',
                    'error': 'Data validation failed',
                    'validation_errors': ['Schema mismatch', 'Checksum invalid']
                }
            else:
                # Third attempt succeeds
                return {
                    'status': 'success',
                    'data_source': 'well_data',
                    'file_count': 1,
                    'total_records': 100,
                    'validation_status': 'passed'
                }
        
        with patch.object(self.scraper, 'download_and_process', side_effect=mock_download_with_retries):
            result = self.scraper.download_with_validation_retry('well_data', max_attempts=3)
            
            assert result['status'] == 'success'
            assert retry_count == 3
            assert result['validation_status'] == 'passed'

    def test_graceful_fallback_strategies(self):
        """Test 8.3.5: Graceful fallback strategies for data processing."""
        # Test primary method failure with successful fallback
        with patch.object(self.scraper, '_process_zip_in_memory') as mock_primary:
            with patch.object(self.scraper, '_fallback_csv_processing') as mock_fallback:
                # Primary method fails
                mock_primary.side_effect = Exception("Primary processing failed")
                
                # Fallback method succeeds
                mock_fallback.return_value = {
                    'source': 'production_data',
                    'files': {'fallback.csv': {'size': 1000, 'records': 50}},
                    'dataframes': {'production': pd.DataFrame({'col1': [1, 2, 3]})},
                    'metadata': {'processing_method': 'fallback_csv'}
                }
                
                result = self.scraper.process_with_fallback(b"test_zip_content", 'production_data')
                
                assert result['status'] == 'success'
                assert result['processing_method'] == 'fallback_csv'
                assert mock_primary.called
                assert mock_fallback.called

    def test_data_quality_assessment(self):
        """Test 8.3.6: Data quality assessment and scoring."""
        # Test high-quality data
        high_quality_data = pd.DataFrame({
            'api_number': ['123456789012', '123456789013', '123456789014'],
            'well_name': ['Well A', 'Well B', 'Well C'],
            'latitude': [29.5, 29.6, 29.7],
            'longitude': [-94.2, -94.3, -94.4],
            'spud_date': ['2023-01-15', '2023-02-20', '2023-03-10']
        })
        
        quality_score = self.validator.assess_data_quality(high_quality_data)
        
        assert quality_score['overall_score'] >= 0.8  # High quality
        assert quality_score['completeness_score'] >= 0.9
        assert quality_score['consistency_score'] >= 0.8
        assert len(quality_score['quality_issues']) == 0
        
        # Test low-quality data
        low_quality_data = pd.DataFrame({
            'api_number': ['123456789012', None, '123456789014'],
            'well_name': ['Well A', '', 'Well C'],
            'latitude': [29.5, 999.0, 29.7],  # Invalid latitude
            'longitude': [-94.2, None, -94.4],
            'spud_date': ['2023-01-15', 'invalid_date', None]
        })
        
        quality_score = self.validator.assess_data_quality(low_quality_data)
        
        assert quality_score['overall_score'] < 0.6  # Low quality
        assert len(quality_score['quality_issues']) > 0
        assert 'missing_values' in quality_score['quality_issues']
        assert 'invalid_coordinates' in quality_score['quality_issues']

    def test_incremental_validation_recovery(self):
        """Test 8.3.7: Incremental validation and recovery."""
        # Test processing data in chunks with validation
        large_dataset = pd.DataFrame({
            'api_number': [f'12345678901{i}' for i in range(1000)],
            'well_name': [f'Well {i}' for i in range(1000)],
            'latitude': [29.5 + (i * 0.001) for i in range(1000)],
            'longitude': [-94.2 - (i * 0.001) for i in range(1000)]
        })
        
        # Introduce some invalid data in the middle
        large_dataset.loc[500:510, 'latitude'] = None
        large_dataset.loc[750:760, 'api_number'] = 'invalid'
        
        validation_result = self.validator.validate_data_incrementally(large_dataset, chunk_size=100)
        
        assert validation_result['total_chunks'] == 10
        assert validation_result['valid_chunks'] == 8  # 2 chunks have issues
        assert validation_result['invalid_chunks'] == 2
        assert len(validation_result['chunk_errors']) == 2
        assert validation_result['recoverable_data_percentage'] > 0.8

    def test_error_reporting_and_logging(self):
        """Test 8.3.8: Comprehensive error reporting and logging."""
        # Test detailed error reporting
        with patch.object(self.scraper, '_validate_and_process') as mock_validate:
            mock_validate.return_value = {
                'status': 'error',
                'validation_errors': [
                    'Missing required column: api_number',
                    'Invalid data type in latitude column',
                    'Checksum verification failed'
                ],
                'processing_errors': [
                    'ZIP file corruption detected',
                    'Memory allocation failed'
                ],
                'recovery_attempts': [
                    {'method': 'retry_download', 'success': False},
                    {'method': 'fallback_parsing', 'success': False}
                ]
            }
            
            result = self.scraper.download_and_process('war_data')
            
            # Verify comprehensive error reporting
            assert result['status'] == 'error'
            assert 'validation_errors' in result
            assert 'processing_errors' in result
            assert 'recovery_attempts' in result
            assert len(result['validation_errors']) == 3
            assert len(result['processing_errors']) == 2
            assert len(result['recovery_attempts']) == 2

    def test_data_consistency_validation(self):
        """Test 8.3.9: Cross-field data consistency validation."""
        # Test data with consistency issues
        inconsistent_data = pd.DataFrame({
            'api_number': ['123456789012', '123456789013'],
            'well_name': ['Well A', 'Well B'],
            'spud_date': ['2023-06-15', '2023-02-20'],
            'completion_date': ['2023-01-10', '2023-03-15']  # Completion before spud
        })
        
        consistency_result = self.validator.validate_data_consistency(inconsistent_data)
        
        assert consistency_result['is_consistent'] == False
        assert 'date_consistency_errors' in consistency_result
        assert len(consistency_result['date_consistency_errors']) > 0
        
        # Test consistent data
        consistent_data = pd.DataFrame({
            'api_number': ['123456789012', '123456789013'],
            'well_name': ['Well A', 'Well B'],
            'spud_date': ['2023-01-15', '2023-02-20'],
            'completion_date': ['2023-03-10', '2023-04-15']
        })
        
        consistency_result = self.validator.validate_data_consistency(consistent_data)
        
        assert consistency_result['is_consistent'] == True
        assert len(consistency_result.get('date_consistency_errors', [])) == 0

    def test_progressive_data_recovery(self):
        """Test 8.3.10: Progressive data recovery from partial failures."""
        # Simulate progressive recovery scenario
        recovery_stages = [
            {'stage': 'download_retry', 'success': False, 'error': 'Network timeout'},
            {'stage': 'checksum_validation', 'success': False, 'error': 'Checksum mismatch'},
            {'stage': 'fallback_download', 'success': True, 'recovered_size': 0.8},
            {'stage': 'partial_processing', 'success': True, 'processed_records': 800},
            {'stage': 'data_validation', 'success': True, 'valid_records': 750}
        ]
        
        with patch.object(self.scraper, '_progressive_recovery') as mock_recovery:
            mock_recovery.return_value = {
                'status': 'partial_success',
                'recovery_stages': recovery_stages,
                'final_data_quality': 0.75,
                'recoverable_percentage': 0.8,
                'total_records_recovered': 750
            }
            
            result = self.scraper.recover_data_progressively('production_data')
            
            assert result['status'] == 'partial_success'
            assert result['final_data_quality'] == 0.75
            assert result['total_records_recovered'] == 750
            assert len(result['recovery_stages']) == 5

    def test_validation_performance_optimization(self):
        """Test 8.3.11: Validation performance optimization."""
        # Test validation with large dataset
        large_data = pd.DataFrame({
            'api_number': [f'12345678901{i%10}' for i in range(10000)],
            'production_date': ['2023-01-01'] * 10000,
            'oil_production': [100.0 + i for i in range(10000)]
        })
        
        start_time = time.time()
        validation_result = self.validator.validate_production_data_schema(large_data, optimize_for_size=True)
        validation_time = time.time() - start_time
        
        assert validation_result['is_valid'] == True
        assert validation_time < 5.0  # Should complete within 5 seconds
        assert validation_result['optimization_used'] == True
        assert 'performance_metrics' in validation_result

    def test_custom_validation_rules(self):
        """Test 8.3.12: Custom validation rules implementation."""
        # Test custom business rules
        custom_rules = {
            'latitude_range': {'min': 25.0, 'max': 32.0},  # Gulf of Mexico range
            'longitude_range': {'min': -100.0, 'max': -80.0},
            'api_number_format': r'^\d{12}$',  # 12-digit format
            'production_min_threshold': 0.0  # No negative production
        }
        
        test_data = pd.DataFrame({
            'api_number': ['123456789012', '12345678901a', '123456789013'],  # One invalid
            'latitude': [29.5, 35.0, 28.0],  # One out of range
            'longitude': [-94.2, -94.3, -75.0],  # One out of range
            'oil_production': [100.0, -50.0, 200.0]  # One negative
        })
        
        validation_result = self.validator.apply_custom_validation_rules(test_data, custom_rules)
        
        assert validation_result['is_valid'] == False
        assert len(validation_result['rule_violations']) > 0
        assert 'latitude_range' in validation_result['rule_violations']
        assert 'longitude_range' in validation_result['rule_violations']
        assert 'api_number_format' in validation_result['rule_violations']

    def test_validation_state_recovery(self):
        """Test 8.3.13: Validation state recovery after interruptions."""
        # Test resuming validation after interruption
        partial_state = {
            'last_processed_chunk': 5,
            'total_chunks': 10,
            'validated_records': 500,
            'validation_errors': ['Missing data in chunk 3']
        }
        
        with patch.object(self.validator, '_load_validation_state') as mock_load:
            with patch.object(self.validator, '_save_validation_state') as mock_save:
                mock_load.return_value = partial_state
                
                result = self.validator.resume_validation('production_data', state_file='validation.state')
                
                assert mock_load.called
                assert result['resumed_from_chunk'] == 5
                assert result['previously_validated'] == 500
                assert mock_save.called

    def test_multi_format_validation_support(self):
        """Test 8.3.14: Multi-format validation support."""
        # Test CSV validation
        csv_data = """api_number,well_name,latitude,longitude
123456789012,Well A,29.5,-94.2
123456789013,Well B,29.6,-94.3"""
        
        csv_result = self.validator.validate_csv_format(csv_data)
        assert csv_result['is_valid'] == True
        assert csv_result['format'] == 'csv'
        
        # Test JSON validation (if supported)
        json_data = '[{"api_number": "123456789012", "well_name": "Well A"}]'
        
        json_result = self.validator.validate_json_format(json_data)
        if hasattr(self.validator, 'validate_json_format'):
            assert json_result['is_valid'] == True
            assert json_result['format'] == 'json'

    def test_error_recovery_workflow_integration(self):
        """Test 8.3.15: Complete error recovery workflow integration."""
        # Test end-to-end error recovery workflow
        with patch.object(self.scraper.session, 'get') as mock_get:
            # Simulate complex failure scenario
            failure_sequence = [
                # First attempt: Network failure
                Exception("Network connection failed"),
                # Second attempt: Corrupted data
                self._create_mock_corrupted_response(),
                # Third attempt: Success with validation warnings
                self._create_mock_success_with_warnings()
            ]
            
            mock_get.side_effect = failure_sequence
            
            result = self.scraper.download_and_process_with_recovery('well_data')
            
            assert result['status'] in ['success', 'partial_success']
            assert result['recovery_attempts'] == 2
            assert 'final_data_quality' in result
            assert result['final_data_quality'] > 0.5
            assert 'validation_warnings' in result

    # Helper methods

    def _create_mock_corrupted_response(self):
        """Create a mock response with corrupted data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content.return_value = [b'corrupted_zip_content']
        return mock_response

    def _create_mock_success_with_warnings(self):
        """Create a mock successful response with validation warnings."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'content-length': '2000'}
        
        # Create a valid ZIP with some data quality issues
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            csv_content = """api_number,well_name,latitude,longitude
123456789012,Well A,29.5,-94.2
123456789013,,29.6,-94.3
invalid_api,Well C,29.7,-94.4"""
            zf.writestr('well_data.csv', csv_content)
        
        mock_response.iter_content.return_value = [zip_buffer.getvalue()]
        return mock_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])