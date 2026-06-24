"""Pipeline location data from BSEE ZIP download."""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from worldenergydata.common.data_resolver import get_module_data_safe

_BSEE_BIN = str(get_module_data_safe("bsee") / "bin")


class PipelineLocationDataFromZip:
    """Load and process pipeline location data from ZIP files."""

    COLUMNS = [
        "PERMIT_NUMBER",
        "SEGMENT_NUMBER",
        "POINT_NUMBER",
        "LATITUDE",
        "LONGITUDE",
        "AREA_CODE",
        "BLOCK_NUMBER",
        "WATER_DEPTH",
        "POINT_TYPE",
        "DESCRIPTION",
    ]

    def router(self, cfg: Dict[str, Any]) -> tuple:
        """Main entry point for pipeline location data processing."""
        return cfg, None

    def save_pipeline_location_data_to_binary(self, cfg: Dict[str, Any]) -> None:
        """Save pipeline location data to binary format from ZIP."""
        logger.info("Saving pipeline location data to binary format")
        try:
            from worldenergydata.bsee.data.processors import MemoryProcessor
            from worldenergydata.bsee.data.scrapers import BSEEWebScraper

            scraper = BSEEWebScraper()
            processor = MemoryProcessor(use_optimized=False)

            zip_data = scraper.download_pipeline_location_data()
            if zip_data:
                processed = processor.process_pipeline_location_data(zip_data, cfg)
                if processed:
                    bin_path = (
                        cfg.get("parameters", {})
                        .get("filepath", {})
                        .get("pipeline_location", {})
                        .get("bin", f"{_BSEE_BIN}/pipeline_location")
                    )
                    processor.save_to_binary(
                        processed, bin_path, "pipeline_location_data"
                    )
                    logger.info(f"Pipeline location data saved to {bin_path}")
            scraper.close()
        except Exception as e:
            logger.error(f"Error saving pipeline location data: {str(e)}")
