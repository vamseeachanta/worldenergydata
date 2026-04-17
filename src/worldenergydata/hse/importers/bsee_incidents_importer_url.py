# ABOUTME: URL-based BSEE incident importer using public incident investigation data
# ABOUTME: Downloads from BSEE public API and processes incident investigation records in memory

from typing import Any, Dict, List

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.common.logging import get_logger
from worldenergydata.hse.importers.bsee_incidents_importer import (
    BSEEIncidentsImporter,
)

logger = get_logger(__name__)


class BSEEIncidentsImporterURL(BSEEIncidentsImporter):
    """
    URL-based variant of BSEEIncidentsImporter.

    Downloads HSE incident investigation data from the BSEE public data portal.
    All normalization, validation, and persistence logic is inherited from
    parent class.

    Public Data Source:
        https://www.data.bsee.gov/Other/DataTables/IncidentInvestigations.aspx
        - Incident investigation records reported under 30 CFR 250.188
        - Updated regularly by BSEE
        - Typical file size: 5-15 MB compressed

    TODO: The exact raw data download URL for incident investigations should be
        confirmed from https://www.data.bsee.gov/Other/DataTables/IncidentInvestigations.aspx
        as BSEE may change their file hosting paths. The current URL follows the
        standard BSEE naming convention for raw data downloads.

    Usage:
        importer = BSEEIncidentsImporterURL(db_session)
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    # Incident investigation raw data (not APDRawData.zip which is well permit data)
    BSEE_INCIDENT_DATA_URL = (
        "https://www.data.bsee.gov/Other/Files/IncidentInvestigationsRawData.zip"
    )

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
        Fetch raw incident investigation data from BSEE public API.

        Downloads incident investigation raw data from BSEE, extracts contents
        in memory, and returns records as list of dictionaries.

        Returns:
            List of dictionaries containing raw incident investigation data

        Raises:
            ValueError: If download fails after all retries
            RuntimeError: If ZIP extraction or processing fails
        """
        # Download ZIP file to memory
        zip_data = self.scraper.download_zip_to_memory(
            self.BSEE_INCIDENT_DATA_URL, data_type="default"
        )

        if zip_data is None:
            raise ValueError(
                f"Failed to download data from {self.BSEE_INCIDENT_DATA_URL}"
            )

        # Process ZIP contents in memory using generic processor
        # Incident investigation data is not well/production/WAR specific
        processed_data = self.processor.process_zip_in_memory(zip_data)

        # Convert DataFrames to list of dictionaries for BaseImporter compatibility
        records = []
        for _filename, df in processed_data.items():
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
