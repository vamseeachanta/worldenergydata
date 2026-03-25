"""Platform structure data from BSEE ZIP download."""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger


class PlatformDataFromZip:
    """Load and process platform structure data from ZIP files."""

    COLUMNS = [
        "AREA_CODE",
        "BLOCK_NUMBER",
        "COMPLEX_ID_NUM",
        "STRUCTURE_NUMBER",
        "STRUCTURE_NAME",
        "STRUC_TYPE_CODE",
        "MAJ_STRUC_FLAG",
        "FIELD_NAME_CODE",
        "WATER_DEPTH",
        "INSTALL_DATE",
        "REMOVAL_DATE",
        "DECK_COUNT",
        "SLOT_COUNT",
        "SLANT_SLOT_COUNT",
        "SLOT_DRILL_COUNT",
        "SATELLITE_COMPLETION_COUNT",
        "UNDERWATER_COMPLETION_COUNT",
        "HELIPORT_FLAG",
        "ATTENDED_8_HR_FL",
        "MANNED_24_HR_FL",
        "LATITUDE",
        "LONGITUDE",
        "LEASE_NUMBER",
        "DISTRICT_CODE",
        "AUTHORITY_TYPE",
        "AUTHORITY_NUMBER",
        "AUTHORITY_STATUS",
        "STE_CLRNCE_DATE",
        "INCS",
    ]

    def router(self, cfg: Dict[str, Any]) -> tuple:
        """Main entry point for platform data processing."""
        return cfg, None

    def save_platform_data_to_binary(self, cfg: Dict[str, Any]) -> None:
        """Save platform data to binary format from ZIP."""
        logger.info("Saving platform data to binary format")
        try:
            from worldenergydata.bsee.data.processors import MemoryProcessor
            from worldenergydata.bsee.data.scrapers import BSEEWebScraper

            scraper = BSEEWebScraper()
            processor = MemoryProcessor(use_optimized=False)

            zip_data = scraper.download_platform_data()
            if zip_data:
                processed = processor.process_platform_data(zip_data, cfg)
                if processed:
                    bin_path = (
                        cfg.get("parameters", {})
                        .get("filepath", {})
                        .get("platform", {})
                        .get("bin", "data/modules/bsee/bin/platform")
                    )
                    processor.save_to_binary(processed, bin_path, "platform_data")
                    logger.info(f"Platform data saved to {bin_path}")
            scraper.close()
        except Exception as e:
            logger.error(f"Error saving platform data: {str(e)}")
