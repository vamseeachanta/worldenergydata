# ABOUTME: URL-based BSEE incident importer using public APDRawData.zip
# ABOUTME: Downloads from BSEE public API and processes well/incident data in memory

from pathlib import Path
from typing import Any, Dict, List

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.modules.hse.importers.bsee_incidents_importer import (
    BSEEIncidentsImporter,
)


class BSEEIncidentsImporterURL(BSEEIncidentsImporter):
    """
    URL-based variant of BSEEIncidentsImporter.

    Downloads HSE incident data from public BSEE APDRawData.zip instead of using
    local CSV files. All normalization, validation, and persistence logic is
    inherited from parent class.

    Public Data Source:
        https://www.data.bsee.gov/Well/Files/APDRawData.zip
        - Well data including incidents, permits, and drilling information
        - Updated daily by BSEE
        - Typical file size: 10-20 MB compressed

    Usage:
        importer = BSEEIncidentsImporterURL(db_session)
        stats = importer.import_data()
        print(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    BSEE_WELL_DATA_URL = "https://www.data.bsee.gov/Well/Files/APDRawData.zip"

    def __init__(self, db_session, use_optimized: bool = True):
        """
        Initialize URL-based BSEE incidents importer.

        Args:
            db_session: SQLAlchemy database session
            use_optimized: Whether to use optimized processing for large files (default True)
        """
        super().__init__(db_session, csv_file_path=None)
        self.use_optimized = use_optimized
        self.scraper = BSEEWebScraper()
        self.processor = MemoryProcessor(use_optimized=use_optimized)

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw incident data from BSEE public API.

        Downloads APDRawData.zip from BSEE, extracts contents in memory,
        processes well data, and returns records as list of dictionaries.

        Returns:
            List of dictionaries containing raw incident data from BSEE API

        Raises:
            ValueError: If download fails after all retries
            RuntimeError: If ZIP extraction or processing fails
        """
        # Download ZIP file to memory
        zip_data = self.scraper.download_zip_to_memory(
            self.BSEE_WELL_DATA_URL, data_type="well"
        )

        if zip_data is None:
            raise ValueError(f"Failed to download data from {self.BSEE_WELL_DATA_URL}")

        # Process ZIP contents in memory
        # Returns: Dict[filename, Dict['data': DataFrame, 'metadata': {...}]]
        processed_data = self.processor.process_well_data(
            zip_data, cfg={}  # Use default processing configuration
        )

        # Convert DataFrames to list of dictionaries for BaseImporter compatibility
        records = []
        for filename, file_data in processed_data.items():
            # Extract DataFrame from processing result
            if isinstance(file_data, dict) and "data" in file_data:
                df = file_data["data"]
            else:
                df = file_data

            # Convert to list of dicts
            file_records = df.to_dict("records")
            records.extend(file_records)

        return records

    # normalize_data() inherited unchanged from BSEEIncidentsImporter
    # Performs field mapping:
    #   - incident_id → bsee_incident_id
    #   - incident_date (string) → incident_date (datetime)
    #   - operator_name → operator
    #   - facility → facility_name
    #   - lat/lon (string) → latitude/longitude (float)
