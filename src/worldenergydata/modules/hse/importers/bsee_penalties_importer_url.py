# ABOUTME: URL-based BSEE penalties importer using public eWellWARRawData.zip
# ABOUTME: Downloads from BSEE public API and processes well activity reports for violation data

from typing import Any, Dict, List

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.common.logging import get_logger
from worldenergydata.modules.hse.importers.bsee_penalties_importer import (
    BSEEPenaltiesImporter,
)

logger = get_logger(__name__)


class BSEEPenaltiesImporterURL(BSEEPenaltiesImporter):
    """
    URL-based variant of BSEEPenaltiesImporter.

    Downloads HSE violation and penalty data from public BSEE eWellWARRawData.zip
    instead of using local CSV files. All normalization, validation, and persistence
    logic is inherited from parent class.

    Public Data Source:
        https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip
        - Well Activity Reports (WAR) including compliance and violation data
        - Updated daily by BSEE
        - Typical file size: 120+ MB compressed (largest BSEE dataset)

    Note:
        This importer processes WAR data to extract violation and penalty information.
        The large file size requires optimized processing with chunking and parallel
        execution to avoid memory issues.

    Usage:
        importer = BSEEPenaltiesImporterURL(db_session)
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    BSEE_WAR_DATA_URL = "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip"

    def __init__(self, db_session, use_optimized: bool = True):
        """
        Initialize URL-based BSEE penalties importer.

        Args:
            db_session: SQLAlchemy database session
            use_optimized: Whether to use optimized processing (STRONGLY RECOMMENDED
                          for WAR data due to large file size)
        """
        super().__init__(db_session, csv_file_path=None)
        self.use_optimized = use_optimized
        self.scraper = BSEEWebScraper()
        self.processor = MemoryProcessor(use_optimized=use_optimized)

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw penalty/violation data from BSEE public API.

        Downloads eWellWARRawData.zip from BSEE, extracts contents in memory,
        processes well activity reports, and returns records as list of dictionaries.

        WARNING: This is the largest BSEE dataset (120+ MB compressed). Optimized
        processing is STRONGLY RECOMMENDED to avoid memory issues.

        Returns:
            List of dictionaries containing raw violation/penalty data from BSEE API

        Raises:
            ValueError: If download fails after all retries
            RuntimeError: If ZIP extraction or processing fails
            MemoryError: If processing without optimization on machines with < 4GB RAM
        """
        # Download ZIP file to memory (largest file, longest timeout: 2400s = 40min)
        zip_data = self.scraper.download_zip_to_memory(
            self.BSEE_WAR_DATA_URL, data_type="war"
        )

        if zip_data is None:
            raise ValueError(f"Failed to download data from {self.BSEE_WAR_DATA_URL}")

        # Process ZIP contents in memory
        # WAR data REQUIRES optimized processing due to size (120+ MB)
        # Uses chunking (25k rows) and parallel processing (2 workers) to avoid memory issues
        processed_data = self.processor.process_war_data(
            zip_data,
            cfg={"extract_year_month": True},  # Extract year/month from activity dates
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

    # normalize_data() inherited unchanged from BSEEPenaltiesImporter
    # Performs field mapping:
    #   - incident_id → bsee_incident_id
    #   - incident_date (string) → incident_date (datetime)
    #   - operator_name → operator
    #   - incident_type → automatically set to 'violation'
    #   - penalty_amount (string) → penalty_amount (float)
    #   - compliance_deadline (string) → compliance_deadline (datetime)
    #   - compliance_achieved (string) → compliance_achieved (boolean)
