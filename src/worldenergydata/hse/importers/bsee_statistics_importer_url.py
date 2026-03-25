# ABOUTME: URL-based BSEE statistics importer using public incident statistics data
# ABOUTME: Downloads from BSEE public API and processes aggregated safety statistics in memory

from typing import Any, Dict, List

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.hse.importers.bsee_statistics_importer import (
    BSEEStatisticsImporter,
)


class BSEEStatisticsImporterURL(BSEEStatisticsImporter):
    """
    URL-based variant of BSEEStatisticsImporter.

    Downloads HSE safety statistics from the BSEE public data portal instead
    of using local CSV files. All normalization, validation, and persistence
    logic is inherited from parent class.

    Public Data Source:
        https://www.data.bsee.gov/Other/DataTables/IncidentInvestigations.aspx
        - Aggregated safety statistics and incident counts
        - Updated regularly by BSEE

    TODO: The exact raw data download URL for incident statistics should be
        confirmed from the BSEE data portal. The current URL follows the
        standard BSEE naming convention. Production data (ProductionRawData.zip)
        is NOT the correct source for safety statistics.

    Usage:
        importer = BSEEStatisticsImporterURL(db_session)
        stats = importer.import_data()
        print(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    # Incident statistics raw data (not ProductionRawData.zip which is production data)
    BSEE_INCIDENT_STATS_URL = (
        "https://www.data.bsee.gov/Other/Files/IncidentStatisticsRawData.zip"
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
        Fetch raw safety statistics data from BSEE public API.

        Downloads incident statistics raw data from BSEE, extracts contents
        in memory, and returns records as list of dictionaries.

        Returns:
            List of dictionaries containing raw safety statistics from BSEE API

        Raises:
            ValueError: If download fails after all retries
            RuntimeError: If ZIP extraction or processing fails
        """
        # Download ZIP file to memory
        zip_data = self.scraper.download_zip_to_memory(
            self.BSEE_INCIDENT_STATS_URL, data_type="default"
        )

        if zip_data is None:
            raise ValueError(
                f"Failed to download data from {self.BSEE_INCIDENT_STATS_URL}"
            )

        # Process ZIP contents in memory using generic processor
        # Statistics data is not well/production/WAR specific
        processed_data = self.processor.process_zip_in_memory(zip_data)

        # Convert DataFrames to list of dictionaries for BaseImporter compatibility
        records = []
        for _filename, df in processed_data.items():
            file_records = df.to_dict("records")
            records.extend(file_records)

        return records

    # normalize_data(), validate_data(), is_duplicate(), and import_record()
    # inherited from BSEEStatisticsImporter.
    # Persists to SafetyStatistic model (not HSEIncident).
    # Field mappings:
    #   - report_date (string) → report_date (datetime)
    #   - operator_name → operator
    #   - facility → facility_name
    #   - operational_period, total_incidents, counts (string) → integers
