# ABOUTME: Unit tests for URL-based BSEE penalties importer
# ABOUTME: Tests download from public eWellWARRawData.zip with optimized processing

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd

from worldenergydata.modules.hse.importers.bsee_penalties_importer_url import BSEEPenaltiesImporterURL
from worldenergydata.modules.hse.database.models import HSEIncident


class TestBSEEPenaltiesImporterURL:
    """Test URL-based BSEE penalties importer."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_zip_data(self):
        """Mock ZIP file bytes."""
        return b'PK\x03\x04' + b'\x00' * 100

    @pytest.fixture
    def mock_processed_data(self):
        """Mock processed WAR data from MemoryProcessor."""
        return {
            'war_data.csv': {
                'data': pd.DataFrame([
                    {
                        'incident_id': 'PEN-001',
                        'incident_date': '2024-01-15',
                        'operator_name': 'Shell Offshore Inc.',
                        'penalty_amount': '50000.00',
                        'compliance_deadline': '2024-06-15',
                        'compliance_achieved': 'True'
                    },
                    {
                        'incident_id': 'PEN-002',
                        'incident_date': '2024-01-20',
                        'operator_name': 'BP America',
                        'penalty_amount': '25000.00',
                        'compliance_deadline': '2024-07-20',
                        'compliance_achieved': 'False'
                    }
                ]),
                'metadata': {'rows': 2, 'columns': 6}
            }
        }

    def test_importer_initialization(self, db_session):
        """Test BSEEPenaltiesImporterURL can be instantiated."""
        importer = BSEEPenaltiesImporterURL(db_session)

        assert importer is not None
        assert importer.db_session == db_session
        assert importer.BSEE_WAR_DATA_URL == 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip'
        assert importer.use_optimized is True
        assert hasattr(importer, 'scraper')
        assert hasattr(importer, 'processor')

    def test_importer_requires_optimization_for_large_file(self, db_session):
        """Test importer uses optimized processing by default for 120+ MB WAR file."""
        importer = BSEEPenaltiesImporterURL(db_session)

        # WAR data is largest BSEE dataset - optimization STRONGLY RECOMMENDED
        assert importer.use_optimized is True
        assert importer.processor.use_optimized is True

    def test_fetch_data_downloads_from_war_url(self, db_session, mock_zip_data, mock_processed_data):
        """Test fetch_data downloads from BSEE WAR URL with longest timeout."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data) as mock_download, \
             patch.object(importer.processor, 'process_war_data', return_value=mock_processed_data) as mock_process:

            result = importer.fetch_data()

            # Verify scraper was called with correct URL and data type (uses 2400s timeout)
            mock_download.assert_called_once_with(
                'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
                data_type='war'
            )

            # Verify processor was called with year/month extraction enabled
            mock_process.assert_called_once_with(
                mock_zip_data,
                config={'extract_year_month': True}
            )

            # Verify result
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]['incident_id'] == 'PEN-001'
            assert result[1]['incident_id'] == 'PEN-002'

    def test_fetch_data_handles_download_failure(self, db_session):
        """Test fetch_data raises error when WAR download fails."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=None):
            with pytest.raises(ValueError, match="Failed to download data"):
                importer.fetch_data()

    def test_fetch_data_uses_longest_timeout(self, db_session, mock_zip_data, mock_processed_data):
        """Test fetch_data uses WAR data type for longest timeout (2400s = 40 minutes)."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data) as mock_download, \
             patch.object(importer.processor, 'process_war_data', return_value=mock_processed_data):

            importer.fetch_data()

            # Verify data_type='war' was passed (which triggers 2400s timeout in scraper)
            call_args = mock_download.call_args
            assert call_args[1]['data_type'] == 'war'

    def test_normalize_data_converts_penalty_amount_to_float(self, db_session, mock_zip_data, mock_processed_data):
        """Test normalize_data converts string penalty_amount to float."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data), \
             patch.object(importer.processor, 'process_war_data', return_value=mock_processed_data):

            raw_data_list = importer.fetch_data()
            raw_data = raw_data_list[0]

            # Normalize
            normalized = importer.normalize_data(raw_data)

            # Verify penalty_amount conversion
            assert 'penalty_amount' in normalized
            assert isinstance(normalized['penalty_amount'], float)
            assert normalized['penalty_amount'] == 50000.00

    def test_normalize_data_converts_compliance_deadline_to_datetime(self, db_session, mock_zip_data, mock_processed_data):
        """Test normalize_data converts compliance_deadline string to datetime."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data), \
             patch.object(importer.processor, 'process_war_data', return_value=mock_processed_data):

            raw_data_list = importer.fetch_data()
            raw_data = raw_data_list[0]

            normalized = importer.normalize_data(raw_data)

            # Verify compliance_deadline conversion
            assert 'compliance_deadline' in normalized
            assert isinstance(normalized['compliance_deadline'], datetime)
            assert normalized['compliance_deadline'] == datetime(2024, 6, 15)

    def test_normalize_data_converts_compliance_achieved_to_boolean(self, db_session, mock_zip_data, mock_processed_data):
        """Test normalize_data converts compliance_achieved string to boolean."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data), \
             patch.object(importer.processor, 'process_war_data', return_value=mock_processed_data):

            raw_data_list = importer.fetch_data()

            # Test True conversion
            normalized_true = importer.normalize_data(raw_data_list[0])
            assert isinstance(normalized_true.get('compliance_achieved'), bool)
            assert normalized_true.get('compliance_achieved') is True

            # Test False conversion
            normalized_false = importer.normalize_data(raw_data_list[1])
            assert isinstance(normalized_false.get('compliance_achieved'), bool)
            assert normalized_false.get('compliance_achieved') is False

    def test_normalize_data_sets_incident_type_violation(self, db_session, mock_zip_data, mock_processed_data):
        """Test normalize_data hardcodes incident_type to 'violation' for penalties."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data), \
             patch.object(importer.processor, 'process_war_data', return_value=mock_processed_data):

            raw_data_list = importer.fetch_data()
            raw_data = raw_data_list[0]

            normalized = importer.normalize_data(raw_data)

            # Verify incident_type is hardcoded to 'violation'
            assert normalized['incident_type'] == 'violation'

    def test_full_import_workflow(self, db_session, mock_zip_data, mock_processed_data):
        """Test complete import workflow from WAR URL download to database persistence."""
        importer = BSEEPenaltiesImporterURL(db_session)

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data), \
             patch.object(importer.processor, 'process_war_data', return_value=mock_processed_data):

            stats = importer.import_data()

            assert 'imported_count' in stats
            assert 'skipped_count' in stats

    def test_importer_handles_multiple_war_files(self, db_session, mock_zip_data):
        """Test importer aggregates data from multiple WAR CSV files."""
        importer = BSEEPenaltiesImporterURL(db_session)

        mock_data = {
            'war_2024_q1.csv': pd.DataFrame([{'incident_id': 'PEN-001', 'incident_date': '2024-01-15', 'operator_name': 'Shell', 'penalty_amount': '50000.00', 'compliance_deadline': '2024-06-15', 'compliance_achieved': 'True'}]),
            'war_2024_q2.csv': pd.DataFrame([{'incident_id': 'PEN-002', 'incident_date': '2024-04-15', 'operator_name': 'BP', 'penalty_amount': '75000.00', 'compliance_deadline': '2024-09-15', 'compliance_achieved': 'False'}])
        }

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=mock_zip_data), \
             patch.object(importer.processor, 'process_war_data', return_value=mock_data):

            result = importer.fetch_data()

            assert len(result) == 2
            assert result[0]['incident_id'] == 'PEN-001'
            assert result[1]['incident_id'] == 'PEN-002'

    def test_importer_can_disable_optimization_with_warning(self, db_session):
        """Test importer can be initialized without optimization (not recommended for WAR)."""
        # Note: For 120+ MB WAR files, use_optimized=False may cause MemoryError
        importer = BSEEPenaltiesImporterURL(db_session, use_optimized=False)

        assert importer.processor.use_optimized is False


class TestBSEEPenaltiesImporterURLPerformance:
    """Performance tests for penalties importer with large WAR dataset."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()

    def test_very_large_file_handling(self, db_session):
        """Test importer can handle very large WAR files (120+ MB) with optimization."""
        importer = BSEEPenaltiesImporterURL(db_session)

        # Create large mock dataset (simulate massive WAR file)
        large_data = {
            'war.csv': pd.DataFrame([
                {
                    'incident_id': f'PEN-{i:06d}',
                    'incident_date': '2024-01-15',
                    'operator_name': 'Shell',
                    'penalty_amount': '50000.00',
                    'compliance_deadline': '2024-06-15',
                    'compliance_achieved': 'True'
                }
                for i in range(5000)  # 5000 records for test performance
            ])
        }

        with patch.object(importer.scraper, 'download_zip_to_memory', return_value=b'mock'), \
             patch.object(importer.processor, 'process_war_data', return_value=large_data):

            result = importer.fetch_data()

            assert len(result) == 5000
            assert result[0]['incident_id'] == 'PEN-000000'
            assert result[4999]['incident_id'] == 'PEN-004999'

    def test_optimized_processing_enabled(self, db_session):
        """Test importer uses optimized processor for chunking and parallel processing."""
        importer = BSEEPenaltiesImporterURL(db_session)

        # Verify OptimizedProcessor is available and enabled
        assert importer.processor.use_optimized is True

        # For WAR data, OptimizedProcessor should use:
        # - Smallest chunk size (25k rows)
        # - Fewest parallel workers (2)
        # - Data type optimization (category, float32, int16)
        # These are internal to MemoryProcessor/OptimizedProcessor
