"""Deepwater structure data from BSEE ZIP download."""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger


class DeepwaterStructureDataFromZip:
    """Load and process deepwater structure data from ZIP files."""

    COLUMNS = [
        "AREA_CODE",
        "BLOCK_NUMBER",
        "COMPLEX_ID_NUM",
        "STRUCTURE_NUMBER",
        "STRUCTURE_NAME",
        "STRUC_TYPE_CODE",
        "WATER_DEPTH",
        "INSTALL_DATE",
        "REMOVAL_DATE",
        "LATITUDE",
        "LONGITUDE",
        "LEASE_NUMBER",
        "DISTRICT_CODE",
        "FIELD_NAME_CODE",
        "AUTHORITY_TYPE",
        "AUTHORITY_NUMBER",
        "HULL_TYPE",
        "PROJECT_NAME",
    ]

    def router(self, cfg: Dict[str, Any]) -> tuple:
        """Main entry point for deepwater structure data processing."""
        return cfg, None

    def save_deepwater_structure_data_to_binary(self, cfg: Dict[str, Any]) -> None:
        """Save deepwater structure data to binary format from ZIP."""
        logger.info("Saving deepwater structure data to binary format")
        try:
            from worldenergydata.bsee.data.processors import MemoryProcessor
            from worldenergydata.bsee.data.scrapers import BSEEWebScraper

            scraper = BSEEWebScraper()
            processor = MemoryProcessor(use_optimized=False)

            zip_data = scraper.download_deepwater_structure_data()
            if zip_data:
                processed = processor.process_deepwater_structure_data(zip_data, cfg)
                if processed:
                    bin_path = (
                        cfg.get("parameters", {})
                        .get("filepath", {})
                        .get("deepwater_structure", {})
                        .get("bin", "data/modules/bsee/bin/deepwater_structure")
                    )
                    processor.save_to_binary(
                        processed, bin_path, "deepwater_structure_data"
                    )
                    logger.info(f"Deepwater structure data saved to {bin_path}")
            scraper.close()
        except Exception as e:
            logger.error(f"Error saving deepwater structure data: {str(e)}")
