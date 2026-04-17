# ABOUTME: URL-based BSEE statistics importer using public ProductionRawData.zip
# ABOUTME: Downloads from BSEE public API and processes aggregated production statistics in memory

from pathlib import Path
from typing import Any, Dict, List

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.common.logging import get_logger
from worldenergydata.modules.hse.importers.bsee_statistics_importer import (
    BSEEStatisticsImporter,
)

logger = get_logger(__name__)


class BSEEStatisticsImporterURL(BSEEStatisticsImporter):
    """
    URL-based variant of BSEEStatisticsImporter.

    Downloads HSE safety statistics from public BSEE ProductionRawData.zip instead
    of using local CSV files. All normalization, validation, and persistence logic
    is inherited from parent class.

    Public Data Source:
        https://www.data.bsee.gov/Production/Files/ProductionRawData.zip
        - Aggregated production statistics including incident counts
        - Updated bi-monthly by BSEE
        - Typical file size: 50-80 MB compressed

    Usage:
        importer = BSEEStatisticsImporterURL(db_session)
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    BSEE_PRODUCTION_DATA_URL = (
        "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip"
    )

    def __init__(self, db_session, use_optimized: bool = True):
        """
        Initialize URL-based BSEE statistics importer.

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
        Fetch raw statistics data from BSEE public API.

        Downloads ProductionRawData.zip from BSEE, extracts contents in memory,
        processes production statistics, and returns records as list of dictionaries.

        Returns:
            List of dictionaries containing raw production statistics from BSEE API

        Raises:
            ValueError: If download fails after all retries
            RuntimeError: If ZIP extraction or processing fails
        """
        # Download ZIP file to memory (larger file, longer timeout)
        zip_data = self.scraper.download_zip_to_memory(
            self.BSEE_PRODUCTION_DATA_URL, data_type="production"
        )

        if zip_data is None:
            raise ValueError(
                f"Failed to download data from {self.BSEE_PRODUCTION_DATA_URL}"
            )

        # Process ZIP contents in memory
        # Production data requires optimized processing due to size (50-80 MB)
        processed_data = self.processor.process_production_data(
            zip_data, cfg={"calculate_boe": True}  # Calculate barrels of oil equivalent
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

    # normalize_data() inherited unchanged from BSEEStatisticsImporter
    # Performs field mapping:
    #   - incident_id → bsee_incident_id
    #   - report_date (string) → incident_date (datetime)
    #   - operator_name → operator
    #   - incident_type → automatically set to 'equipment_failure'
    #   - severity → severity (unchanged)
    #   - operational_period, total_incidents, counts (string) → integers
