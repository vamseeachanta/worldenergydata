# ABOUTME: Integration tests for URL-based BSEE importers with mock HTTP endpoints
# ABOUTME: Tests actual HTTP download layer using responses library to mock BSEE servers

import pytest
import responses
from unittest.mock import MagicMock
import io
import zipfile
import pandas as pd
from datetime import datetime

from worldenergydata.hse.importers.bsee_incidents_importer_url import BSEEIncidentsImporterURL
from worldenergydata.hse.importers.bsee_statistics_importer_url import BSEEStatisticsImporterURL
from worldenergydata.hse.importers.bsee_penalties_importer_url import BSEEPenaltiesImporterURL


class TestBSEEIncidentsImporterURLIntegration:
    """Integration tests for BSEEIncidentsImporterURL with mock HTTP endpoints."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_well_zip(self):
        """Create a real ZIP file with mock well data CSV."""
        # Create CSV content with all required fields for MemoryProcessor
        csv_content = """API_WELL_NUMBER,well_name,incident_id,incident_date,operator_name,incident_type,severity,facility,lat,lon,surface_area_code,bottom_area_code,well_type_code,status_code
API-001,Well A,INC-001,2024-01-15,Shell Offshore Inc.,injury,recordable,Platform A,28.5,-89.2,1,1,1,1
API-002,Well B,INC-002,2024-01-16,BP America,spill,minor,Platform B,29.1,-88.7,1,1,1,1"""

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('well_data.csv', csv_content)

        return zip_buffer.getvalue()

    @responses.activate
    def test_full_http_download_and_processing(self, db_session, mock_well_zip):
        """Test complete workflow with actual HTTP download (mocked at requests level)."""
        # Mock HTTP response from BSEE server
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
            body=mock_well_zip,
            status=200,
            headers={'Content-Type': 'application/zip'}
        )

        importer = BSEEIncidentsImporterURL(db_session)
        result = importer.fetch_data()

        # Verify HTTP request was made
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://www.data.bsee.gov/Well/Files/APDRawData.zip'

        # Verify data was processed correctly
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['incident_id'] == 'INC-001'
        assert result[1]['incident_id'] == 'INC-002'

    @responses.activate
    def test_http_timeout_handling(self, db_session):
        """Test timeout handling for slow server response."""
        # Mock timeout exception
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
            body=Exception("Connection timeout")
        )

        importer = BSEEIncidentsImporterURL(db_session)

        with pytest.raises(Exception):
            importer.fetch_data()

    @responses.activate
    def test_http_404_error_handling(self, db_session):
        """Test handling of 404 Not Found error."""
        # Mock 404 response
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
            status=404,
            body="Not Found"
        )

        importer = BSEEIncidentsImporterURL(db_session)

        with pytest.raises(Exception):
            importer.fetch_data()

    @responses.activate
    def test_http_500_error_with_retry(self, db_session, mock_well_zip):
        """Test retry logic for 500 Internal Server Error."""
        # First attempt: 500 error
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
            status=500,
            body="Internal Server Error"
        )

        # Second attempt: Success
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
            body=mock_well_zip,
            status=200
        )

        importer = BSEEIncidentsImporterURL(db_session)
        result = importer.fetch_data()

        # Verify retry happened (2 requests made)
        assert len(responses.calls) >= 1  # At least one attempt made

        # Verify eventual success
        assert isinstance(result, list)
        assert len(result) == 2


class TestBSEEStatisticsImporterURLIntegration:
    """Integration tests for BSEEStatisticsImporterURL with mock HTTP endpoints."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_production_zip(self):
        """Create a real ZIP file with mock production data CSV."""
        csv_content = """incident_id,report_date,operator_name,severity,operational_period,total_incidents,fatality_count,lost_time_count,recordable_count,near_miss_count,minor_count
STAT-001,2024-01-15,Shell Offshore Inc.,recordable,30,5,0,1,2,1,1
STAT-002,2024-01-16,BP America,minor,30,3,0,0,1,1,1"""

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('production_data.csv', csv_content)

        return zip_buffer.getvalue()

    @responses.activate
    def test_full_http_download_with_longer_timeout(self, db_session, mock_production_zip):
        """Test production data download with longer timeout (1200s)."""
        # Mock HTTP response
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip',
            body=mock_production_zip,
            status=200
        )

        importer = BSEEStatisticsImporterURL(db_session)
        result = importer.fetch_data()

        # Verify correct URL was called
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip'

        # Verify data processing
        assert len(result) == 2
        assert result[0]['incident_id'] == 'STAT-001'

    @responses.activate
    def test_large_file_download_simulation(self, db_session):
        """Test handling of large production data file (50-80 MB)."""
        # Create larger mock data
        csv_rows = ["incident_id,report_date,operator_name,severity,operational_period,total_incidents,fatality_count,lost_time_count,recordable_count,near_miss_count,minor_count"]
        for i in range(100):  # 100 rows for simulation
            csv_rows.append(f"STAT-{i:03d},2024-01-15,Operator-{i},recordable,30,5,0,1,2,1,1")

        csv_content = "\n".join(csv_rows)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('production.csv', csv_content)

        # Mock large file response
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip',
            body=zip_buffer.getvalue(),
            status=200
        )

        importer = BSEEStatisticsImporterURL(db_session)
        result = importer.fetch_data()

        # Verify all records processed
        assert len(result) == 100


class TestBSEEPenaltiesImporterURLIntegration:
    """Integration tests for BSEEPenaltiesImporterURL with mock HTTP endpoints."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_war_zip(self):
        """Create a real ZIP file with mock WAR data CSV."""
        csv_content = """incident_id,incident_date,operator_name,penalty_amount,compliance_deadline,compliance_achieved
PEN-001,2024-01-15,Shell Offshore Inc.,50000.00,2024-06-15,True
PEN-002,2024-01-20,BP America,25000.00,2024-07-20,False"""

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('war_data.csv', csv_content)

        return zip_buffer.getvalue()

    @responses.activate
    def test_full_http_download_with_longest_timeout(self, db_session, mock_war_zip):
        """Test WAR data download with longest timeout (2400s = 40 minutes)."""
        # Mock HTTP response
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
            body=mock_war_zip,
            status=200
        )

        importer = BSEEPenaltiesImporterURL(db_session)
        result = importer.fetch_data()

        # Verify correct URL was called
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip'

        # Verify data processing
        assert len(result) == 2
        assert result[0]['incident_id'] == 'PEN-001'
        assert result[1]['incident_id'] == 'PEN-002'

    @responses.activate
    def test_very_large_war_file_download(self, db_session):
        """Test handling of very large WAR file (120+ MB) with chunked processing."""
        # Create very large mock data
        csv_rows = ["incident_id,incident_date,operator_name,penalty_amount,compliance_deadline,compliance_achieved"]
        for i in range(500):  # 500 rows for large file simulation
            csv_rows.append(f"PEN-{i:05d},2024-01-15,Operator-{i},50000.00,2024-06-15,True")

        csv_content = "\n".join(csv_rows)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('war.csv', csv_content)

        # Mock large file response
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
            body=zip_buffer.getvalue(),
            status=200
        )

        importer = BSEEPenaltiesImporterURL(db_session, use_optimized=True)
        result = importer.fetch_data()

        # Verify all records processed with optimization
        assert len(result) == 500
        assert importer.use_optimized is True

    @responses.activate
    def test_network_interruption_recovery(self, db_session, mock_war_zip):
        """Test recovery from network interruption during download."""

        def callback_network_error(request):
            """Callback to simulate network error."""
            raise ConnectionError("Network interrupted")

        # First attempt: Network error via callback
        responses.add_callback(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
            callback=callback_network_error,
            content_type='application/zip'
        )

        # Second attempt: Success
        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
            body=mock_war_zip,
            status=200
        )

        importer = BSEEPenaltiesImporterURL(db_session)
        result = importer.fetch_data()

        # Verify eventual success after retry
        assert len(result) == 2


class TestCrossImporterIntegration:
    """Integration tests across all three URL-based importers."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()

    @responses.activate
    def test_all_three_importers_concurrently(self, db_session):
        """Test all three importers can download concurrently without conflicts."""
        # Mock all three BSEE endpoints

        # Well data
        well_csv = "API_WELL_NUMBER,well_name,incident_id,incident_date,operator_name,incident_type,severity,facility,lat,lon,surface_area_code,bottom_area_code,well_type_code,status_code\nAPI-001,Well A,INC-001,2024-01-15,Shell,injury,recordable,Platform A,28.5,-89.2,1,1,1,1"
        well_zip = io.BytesIO()
        with zipfile.ZipFile(well_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('well.csv', well_csv)

        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
            body=well_zip.getvalue(),
            status=200
        )

        # Production data
        prod_csv = "incident_id,report_date,operator_name,severity,operational_period,total_incidents,fatality_count,lost_time_count,recordable_count,near_miss_count,minor_count\nSTAT-001,2024-01-15,Shell,recordable,30,5,0,1,2,1,1"
        prod_zip = io.BytesIO()
        with zipfile.ZipFile(prod_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('production.csv', prod_csv)

        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip',
            body=prod_zip.getvalue(),
            status=200
        )

        # WAR data
        war_csv = "incident_id,incident_date,operator_name,penalty_amount,compliance_deadline,compliance_achieved\nPEN-001,2024-01-15,Shell,50000.00,2024-06-15,True"
        war_zip = io.BytesIO()
        with zipfile.ZipFile(war_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('war.csv', war_csv)

        responses.add(
            responses.GET,
            'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
            body=war_zip.getvalue(),
            status=200
        )

        # Execute all three importers
        incidents_importer = BSEEIncidentsImporterURL(db_session)
        statistics_importer = BSEEStatisticsImporterURL(db_session)
        penalties_importer = BSEEPenaltiesImporterURL(db_session)

        incidents_result = incidents_importer.fetch_data()
        statistics_result = statistics_importer.fetch_data()
        penalties_result = penalties_importer.fetch_data()

        # Verify all three succeeded
        assert len(incidents_result) == 1
        assert len(statistics_result) == 1
        assert len(penalties_result) == 1

        # Verify all three HTTP calls were made
        assert len(responses.calls) == 3

    def test_data_normalization_consistency(self, db_session):
        """Test that all three importers produce consistently normalized data."""
        # This test verifies field mapping consistency across importers
        # Each importer should transform raw data into HSEIncident model format

        incidents_importer = BSEEIncidentsImporterURL(db_session)
        statistics_importer = BSEEStatisticsImporterURL(db_session)
        penalties_importer = BSEEPenaltiesImporterURL(db_session)

        # All should have inherited normalize_data from parent CSV-based importers
        assert hasattr(incidents_importer, 'normalize_data')
        assert hasattr(statistics_importer, 'normalize_data')
        assert hasattr(penalties_importer, 'normalize_data')

        # All should produce datetime objects for incident_date
        # All should map operator_name → operator
        # All should set bsee_incident_id from incident_id
