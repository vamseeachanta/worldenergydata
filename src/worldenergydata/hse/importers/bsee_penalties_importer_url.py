# ABOUTME: URL-based BSEE penalties importer using public INCs/civil penalties data
# ABOUTME: Downloads from BSEE public API and processes INC (Incidents of Non-Compliance) records

from typing import Any, Dict, List

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.hse.importers.bsee_penalties_importer import (

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)
    BSEEPenaltiesImporter,
)


class BSEEPenaltiesImporterURL(BSEEPenaltiesImporter):
    """
    URL-based variant of BSEEPenaltiesImporter.

    Downloads HSE violation and civil penalty data (INCs - Incidents of
    Non-Compliance) from the BSEE public data portal instead of using
    local CSV files. All normalization, validation, and persistence logic
    is inherited from parent class.

    Public Data Source:
        https://www.data.bsee.gov/Company/INCs/Default.aspx
        - Incidents of Non-Compliance (INC) and civil penalty records
        - Updated regularly by BSEE
        - Typical file size: 5-10 MB compressed

    Usage:
        importer = BSEEPenaltiesImporterURL(db_session)
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    # INCs (Incidents of Non-Compliance) raw data
    # (not eWellWARRawData.zip which is well activity reports)
    BSEE_INC_DATA_URL = "https://www.data.bsee.gov/Company/Files/INCSRawData.zip"

    def __init__(self, db_session, use_optimized: bool = True):
        """
        Initialize URL-based BSEE penalties importer.

        Args:
            db_session: SQLAlchemy database session
            use_optimized: Whether to use optimized processing (default True)
        """
        super().__init__(db_session, csv_file_path=None)
        self.use_optimized = use_optimized
        self.scraper = BSEEWebScraper()
        self.processor = MemoryProcessor(use_optimized=use_optimized)

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw penalty/violation data from BSEE public API.

        Downloads INCSRawData.zip from BSEE, extracts contents in memory,
        processes INC records, and returns records as list of dictionaries.

        Returns:
            List of dictionaries containing raw INC/penalty data from BSEE API

        Raises:
            ValueError: If download fails after all retries
            RuntimeError: If ZIP extraction or processing fails
        """
        # Download ZIP file to memory
        zip_data = self.scraper.download_zip_to_memory(
            self.BSEE_INC_DATA_URL, data_type="default"
        )

        if zip_data is None:
            raise ValueError(f"Failed to download data from {self.BSEE_INC_DATA_URL}")

        # Process ZIP contents in memory using generic processor
        # INC data is not well/production/WAR specific
        processed_data = self.processor.process_zip_in_memory(zip_data)

        # Convert DataFrames to list of dictionaries for BaseImporter compatibility
        records = []
        for _filename, df in processed_data.items():
            file_records = df.to_dict("records")
            records.extend(file_records)

        return records

    # normalize_data() and import_record() inherited from BSEEPenaltiesImporter
    # normalize_data() performs field mapping:
    #   - incident_id → bsee_incident_id
    #   - incident_date (string) → incident_date (datetime)
    #   - operator_name → operator
    #   - incident_type → automatically set to 'violation'
    #   - penalty_amount (string) → penalty_amount (float)
    #   - compliance_deadline (string) → compliance_deadline (datetime)
    #   - compliance_achieved (string) → compliance_achieved (boolean)
    # import_record() creates both HSEIncident and ViolationIncident records
