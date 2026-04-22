# ABOUTME: Unit tests for URL-based BSEE statistics importer
# ABOUTME: Tests download from public ProductionRawData.zip and BOE calculations

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from worldenergydata.hse.database.models import HSEIncident
from worldenergydata.hse.importers.bsee_statistics_importer_url import (
    BSEEStatisticsImporterURL,
)


class TestBSEEStatisticsImporterURL:
    """Test URL-based BSEE statistics importer."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_zip_data(self):
        """Mock ZIP file bytes."""
        return b"PK\x03\x04" + b"\x00" * 100

    @pytest.fixture
    def mock_processed_data(self):
        """Mock processed production data from MemoryProcessor."""
        return {
            "production_data.csv": {
                "data": pd.DataFrame(
                    [
                        {
                            "incident_id": "STAT-001",
                            "report_date": "2024-01-15",
                            "operator_name": "Shell Offshore Inc.",
                            "severity": "recordable",
                            "operational_period": "30",
                            "total_incidents": "5",
                            "fatality_count": "0",
                            "lost_time_count": "1",
                            "recordable_count": "2",
                            "near_miss_count": "1",
                            "minor_count": "1",
                        },
                        {
                            "incident_id": "STAT-002",
                            "report_date": "2024-01-16",
                            "operator_name": "BP America",
                            "severity": "minor",
                            "operational_period": "30",
                            "total_incidents": "3",
                            "fatality_count": "0",
                            "lost_time_count": "0",
                            "recordable_count": "1",
                            "near_miss_count": "1",
                            "minor_count": "1",
                        },
                    ]
                ),
                "metadata": {"rows": 2, "columns": 11},
            }
        }

    def test_importer_initialization(self, db_session):
        """Test BSEEStatisticsImporterURL can be instantiated."""
        importer = BSEEStatisticsImporterURL(db_session)

        assert importer is not None
        assert importer.db_session == db_session
        assert (
            importer.BSEE_PRODUCTION_DATA_URL
            == "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip"
        )
        assert importer.use_optimized is True
        assert hasattr(importer, "scraper")
        assert hasattr(importer, "processor")

    def test_fetch_data_downloads_from_url(
        self, db_session, mock_zip_data, mock_processed_data
    ):
        """Test fetch_data downloads from BSEE production URL with BOE calculation."""
        importer = BSEEStatisticsImporterURL(db_session)

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
            ) as mock_download,
            patch.object(
                importer.processor,
                "process_production_data",
                return_value=mock_processed_data,
            ) as mock_process,
        ):

            result = importer.fetch_data()

            # Verify scraper was called with correct URL and data type
            mock_download.assert_called_once_with(
                "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
                data_type="production",
            )

            # Verify processor was called with BOE calculation enabled
            mock_process.assert_called_once_with(
                mock_zip_data, cfg={"calculate_boe": True}
            )

            # Verify result
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["incident_id"] == "STAT-001"
            assert result[1]["incident_id"] == "STAT-002"

    def test_fetch_data_handles_download_failure(self, db_session):
        """Test fetch_data raises error when download fails."""
        importer = BSEEStatisticsImporterURL(db_session)

        with patch.object(
            importer.scraper, "download_zip_to_memory", return_value=None
        ):
            with pytest.raises(ValueError, match="Failed to download data"):
                importer.fetch_data()

    def test_fetch_data_uses_longer_timeout(
        self, db_session, mock_zip_data, mock_processed_data
    ):
        """Test fetch_data uses production data type for longer timeout (1200s)."""
        importer = BSEEStatisticsImporterURL(db_session)

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
            ) as mock_download,
            patch.object(
                importer.processor,
                "process_production_data",
                return_value=mock_processed_data,
            ),
        ):

            importer.fetch_data()

            # Verify data_type='production' was passed (which triggers 1200s timeout in scraper)
            call_args = mock_download.call_args
            assert call_args[1]["data_type"] == "production"

    def test_normalize_data_converts_string_integers(
        self, db_session, mock_zip_data, mock_processed_data
    ):
        """Test normalize_data converts string count fields to integers."""
        importer = BSEEStatisticsImporterURL(db_session)

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
            ),
            patch.object(
                importer.processor,
                "process_production_data",
                return_value=mock_processed_data,
            ),
        ):

            raw_data_list = importer.fetch_data()
            raw_data = raw_data_list[0]

            # Normalize
            normalized = importer.normalize_data(raw_data)

            # Verify integer conversions
            assert isinstance(normalized.get("operational_period"), int)
            assert normalized.get("operational_period") == 30
            assert isinstance(normalized.get("total_incidents"), int)
            assert normalized.get("total_incidents") == 5
            assert isinstance(normalized.get("fatality_count"), int)
            assert normalized.get("fatality_count") == 0
            assert isinstance(normalized.get("lost_time_count"), int)
            assert normalized.get("lost_time_count") == 1

    def test_normalize_data_sets_incident_type_equipment_failure(
        self, db_session, mock_zip_data, mock_processed_data
    ):
        """Test normalize_data hardcodes incident_type to 'equipment_failure'."""
        importer = BSEEStatisticsImporterURL(db_session)

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
            ),
            patch.object(
                importer.processor,
                "process_production_data",
                return_value=mock_processed_data,
            ),
        ):

            raw_data_list = importer.fetch_data()
            raw_data = raw_data_list[0]

            normalized = importer.normalize_data(raw_data)

            # Verify incident_type is hardcoded
            assert normalized["incident_type"] == "equipment_failure"

    def test_normalize_data_maps_report_date_to_incident_date(
        self, db_session, mock_zip_data, mock_processed_data
    ):
        """Test normalize_data maps report_date to incident_date."""
        importer = BSEEStatisticsImporterURL(db_session)

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
            ),
            patch.object(
                importer.processor,
                "process_production_data",
                return_value=mock_processed_data,
            ),
        ):

            raw_data_list = importer.fetch_data()
            raw_data = raw_data_list[0]

            normalized = importer.normalize_data(raw_data)

            # Verify date mapping
            assert isinstance(normalized["incident_date"], datetime)
            assert normalized["incident_date"] == datetime(2024, 1, 15)

    def test_full_import_workflow(self, db_session, mock_zip_data, mock_processed_data):
        """Test complete import workflow from URL download to database persistence."""
        importer = BSEEStatisticsImporterURL(db_session)

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
            ),
            patch.object(
                importer.processor,
                "process_production_data",
                return_value=mock_processed_data,
            ),
        ):

            stats = importer.import_data()

            assert "imported_count" in stats
            assert "skipped_count" in stats

    def test_importer_handles_multiple_csv_files(self, db_session, mock_zip_data):
        """Test importer aggregates data from multiple CSVs in production ZIP."""
        importer = BSEEStatisticsImporterURL(db_session)

        mock_data = {
            "production_2024_01.csv": pd.DataFrame(
                [
                    {
                        "incident_id": "STAT-001",
                        "report_date": "2024-01-15",
                        "operator_name": "Shell",
                        "severity": "recordable",
                        "operational_period": "30",
                        "total_incidents": "5",
                        "fatality_count": "0",
                        "lost_time_count": "1",
                        "recordable_count": "2",
                        "near_miss_count": "1",
                        "minor_count": "1",
                    }
                ]
            ),
            "production_2024_02.csv": pd.DataFrame(
                [
                    {
                        "incident_id": "STAT-002",
                        "report_date": "2024-02-15",
                        "operator_name": "BP",
                        "severity": "minor",
                        "operational_period": "28",
                        "total_incidents": "3",
                        "fatality_count": "0",
                        "lost_time_count": "0",
                        "recordable_count": "1",
                        "near_miss_count": "1",
                        "minor_count": "1",
                    }
                ]
            ),
        }

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=mock_zip_data
            ),
            patch.object(
                importer.processor, "process_production_data", return_value=mock_data
            ),
        ):

            result = importer.fetch_data()

            assert len(result) == 2
            assert result[0]["incident_id"] == "STAT-001"
            assert result[1]["incident_id"] == "STAT-002"

    def test_importer_uses_optimized_processing(self, db_session):
        """Test importer uses optimized processor by default for large production files."""
        importer = BSEEStatisticsImporterURL(db_session)

        assert importer.processor.use_optimized is True

    def test_importer_can_disable_optimization(self, db_session):
        """Test importer can be initialized without optimization."""
        importer = BSEEStatisticsImporterURL(db_session, use_optimized=False)

        assert importer.processor.use_optimized is False


class TestBSEEStatisticsImporterURLPerformance:
    """Performance-related tests for statistics importer."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()

    def test_large_file_handling(self, db_session):
        """Test importer can handle large production data files (50-80 MB)."""
        importer = BSEEStatisticsImporterURL(db_session)

        # Create large mock dataset (simulate 50k records)
        large_data = {
            "production.csv": pd.DataFrame(
                [
                    {
                        "incident_id": f"STAT-{i:05d}",
                        "report_date": "2024-01-15",
                        "operator_name": "Shell",
                        "severity": "recordable",
                        "operational_period": "30",
                        "total_incidents": "5",
                        "fatality_count": "0",
                        "lost_time_count": "1",
                        "recordable_count": "2",
                        "near_miss_count": "1",
                        "minor_count": "1",
                    }
                    for i in range(1000)  # 1000 records for test performance
                ]
            )
        }

        with (
            patch.object(
                importer.scraper, "download_zip_to_memory", return_value=b"mock"
            ),
            patch.object(
                importer.processor, "process_production_data", return_value=large_data
            ),
        ):

            result = importer.fetch_data()

            assert len(result) == 1000
            assert result[0]["incident_id"] == "STAT-00000"
            assert result[999]["incident_id"] == "STAT-00999"
