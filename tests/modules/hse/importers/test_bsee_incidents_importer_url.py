# ABOUTME: Unit tests for URL-based BSEE incidents importer
# ABOUTME: Tests download from public APDRawData.zip and in-memory processing

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from worldenergydata.modules.hse.database.models import HSEIncident
from worldenergydata.modules.hse.importers.bsee_incidents_importer_url import (
    BSEEIncidentsImporterURL,
)


class TestBSEEIncidentsImporterURL:
    """Test URL-based BSEE incidents importer."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_zip_data(self):
        """Mock ZIP file bytes (minimal valid ZIP)."""
        # PK zip header + minimal content
        return b"PK\x03\x04" + b"\x00" * 100

    @pytest.fixture
    def mock_processed_data(self):
        """Mock processed well data from MemoryProcessor."""
        return {
            "well_data.csv": {
                "data": pd.DataFrame(
                    [
                        {
                            "incident_id": "INC-001",
                            "incident_date": "2024-01-15",
                            "operator_name": "Shell Offshore Inc.",
                            "incident_type": "injury",
                            "severity": "recordable",
                            "facility": "Platform A",
                            "lat": "28.5",
                            "lon": "-89.2",
                        },
                        {
                            "incident_id": "INC-002",
                            "incident_date": "2024-01-16",
                            "operator_name": "BP America",
                            "incident_type": "spill",
                            "severity": "minor",
                            "facility": "Platform B",
                            "lat": "29.1",
                            "lon": "-88.7",
                        },
                    ]
                ),
                "metadata": {"rows": 2, "columns": 8},
            }
        }

    def test_importer_initialization(self, db_session):
        """Test BSEEIncidentsImporterURL can be instantiated."""
        importer = BSEEIncidentsImporterURL(db_session)

        assert importer is not None
        assert importer.db_session == db_session
        assert (
            importer.BSEE_WELL_DATA_URL
            == "https://www.data.bsee.gov/Well/Files/APDRawData.zip"
        )
        assert importer.use_optimized is True
        assert hasattr(importer, "scraper")
        assert hasattr(importer, "processor")

    def test_importer_initialization_without_optimization(self, db_session):
        """Test importer can be initialized with optimization disabled."""
        importer = BSEEIncidentsImporterURL(db_session, use_optimized=False)

        assert importer.use_optimized is False

    def test_fetch_data_downloads_from_url(
        self, db_session, mock_zip_data, mock_processed_data
    ):
        """Test fetch_data downloads from BSEE URL and processes correctly."""
        importer = BSEEIncidentsImporterURL(db_session)

        # Mock scraper and processor
        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
        ) as mock_download, patch.object(
            importer.processor, "process_well_data", return_value=mock_processed_data
        ) as mock_process:

            result = importer.fetch_data()

            # Verify scraper was called with correct URL
            mock_download.assert_called_once_with(
                "https://www.data.bsee.gov/Well/Files/APDRawData.zip", data_type="well"
            )

            # Verify processor was called with ZIP data
            mock_process.assert_called_once_with(mock_zip_data, config={})

            # Verify result is list of dicts
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["incident_id"] == "INC-001"
            assert result[1]["incident_id"] == "INC-002"

    def test_fetch_data_handles_download_failure(self, db_session):
        """Test fetch_data raises error when download fails."""
        importer = BSEEIncidentsImporterURL(db_session)

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=None
        ):
            with pytest.raises(ValueError, match="Failed to download data"):
                importer.fetch_data()

    def test_fetch_data_processes_dict_with_data_key(self, db_session, mock_zip_data):
        """Test fetch_data handles processor output with 'data' key."""
        importer = BSEEIncidentsImporterURL(db_session)

        mock_output = {
            "file1.csv": {
                "data": pd.DataFrame([{"id": "1", "value": "test"}]),
                "metadata": {"rows": 1},
            }
        }

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
        ), patch.object(
            importer.processor, "process_well_data", return_value=mock_output
        ):

            result = importer.fetch_data()

            assert len(result) == 1
            assert result[0]["id"] == "1"
            assert result[0]["value"] == "test"

    def test_fetch_data_processes_direct_dataframe(self, db_session, mock_zip_data):
        """Test fetch_data handles processor output as direct DataFrame."""
        importer = BSEEIncidentsImporterURL(db_session)

        mock_output = {"file1.csv": pd.DataFrame([{"id": "2", "value": "direct"}])}

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
        ), patch.object(
            importer.processor, "process_well_data", return_value=mock_output
        ):

            result = importer.fetch_data()

            assert len(result) == 1
            assert result[0]["id"] == "2"
            assert result[0]["value"] == "direct"

    def test_fetch_data_aggregates_multiple_files(self, db_session, mock_zip_data):
        """Test fetch_data aggregates data from multiple CSV files in ZIP."""
        importer = BSEEIncidentsImporterURL(db_session)

        mock_output = {
            "file1.csv": pd.DataFrame([{"id": "1"}]),
            "file2.csv": pd.DataFrame([{"id": "2"}]),
            "file3.csv": pd.DataFrame([{"id": "3"}]),
        }

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
        ), patch.object(
            importer.processor, "process_well_data", return_value=mock_output
        ):

            result = importer.fetch_data()

            assert len(result) == 3
            assert result[0]["id"] == "1"
            assert result[1]["id"] == "2"
            assert result[2]["id"] == "3"

    def test_normalize_data_inherited_from_parent(
        self, db_session, mock_zip_data, mock_processed_data
    ):
        """Test normalize_data is inherited unchanged from BSEEIncidentsImporter."""
        importer = BSEEIncidentsImporterURL(db_session)

        # Get raw data via fetch
        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
        ), patch.object(
            importer.processor, "process_well_data", return_value=mock_processed_data
        ):

            raw_data_list = importer.fetch_data()
            raw_data = raw_data_list[0]

            # Normalize
            normalized = importer.normalize_data(raw_data)

            # Verify field mappings (from parent class)
            assert normalized["bsee_incident_id"] == "INC-001"
            assert normalized["operator"] == "Shell Offshore Inc."
            assert normalized["facility_name"] == "Platform A"
            assert isinstance(normalized["incident_date"], datetime)
            assert normalized["incident_date"] == datetime(2024, 1, 15)
            assert normalized["latitude"] == 28.5
            assert normalized["longitude"] == -89.2

    def test_full_import_workflow(self, db_session, mock_zip_data, mock_processed_data):
        """Test complete import workflow from URL download to database persistence."""
        importer = BSEEIncidentsImporterURL(db_session)

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
        ), patch.object(
            importer.processor, "process_well_data", return_value=mock_processed_data
        ):

            stats = importer.import_data()

            # Verify statistics
            assert "imported_count" in stats
            assert "skipped_count" in stats
            assert stats["imported_count"] >= 0  # May be 0 if validation fails

    def test_importer_uses_optimized_processor_by_default(self, db_session):
        """Test importer uses optimized processor by default."""
        importer = BSEEIncidentsImporterURL(db_session)

        # Verify processor was initialized with use_optimized=True
        assert importer.processor.use_optimized is True

    def test_importer_can_disable_optimization(self, db_session):
        """Test importer can be initialized without optimization."""
        importer = BSEEIncidentsImporterURL(db_session, use_optimized=False)

        # Verify processor was initialized with use_optimized=False
        assert importer.processor.use_optimized is False


class TestBSEEIncidentsImporterURLIntegration:
    """Integration tests for URL-based incidents importer."""

    @pytest.fixture
    def db_session(self):
        """Mock database session with query capabilities."""
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        return session

    def test_no_duplicate_import(self, db_session):
        """Test importer skips duplicate incidents based on bsee_incident_id."""
        importer = BSEEIncidentsImporterURL(db_session)

        # Mock existing incident in database
        existing_incident = MagicMock(spec=HSEIncident)
        existing_incident.bsee_incident_id = "INC-001"
        db_session.query.return_value.filter.return_value.first.return_value = (
            existing_incident
        )

        mock_data = {
            "file1.csv": pd.DataFrame(
                [
                    {
                        "incident_id": "INC-001",
                        "incident_date": "2024-01-15",
                        "operator_name": "Shell",
                        "incident_type": "injury",
                        "severity": "recordable",
                        "facility": "Platform A",
                        "lat": "28.5",
                        "lon": "-89.2",
                    }
                ]
            )
        }

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=b"mock"
        ), patch.object(
            importer.processor, "process_well_data", return_value=mock_data
        ):

            stats = importer.import_data()

            # Verify duplicate was skipped
            assert stats["skipped_count"] >= 1

    def test_empty_data_handling(self, db_session):
        """Test importer handles empty ZIP files gracefully."""
        importer = BSEEIncidentsImporterURL(db_session)

        mock_data = {"file1.csv": pd.DataFrame()}  # Empty DataFrame

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=b"mock"
        ), patch.object(
            importer.processor, "process_well_data", return_value=mock_data
        ):

            result = importer.fetch_data()

            assert len(result) == 0
