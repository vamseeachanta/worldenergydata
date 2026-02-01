"""Pipeline permit data from BSEE ZIP download."""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger


class PipelinePermitDataFromZip:
    """Load and process pipeline permit data from ZIP files."""

    COLUMNS = [
        "PERMIT_NUMBER",
        "LEASE_NUMBER",
        "AREA_CODE",
        "BLOCK_NUMBER",
        "STATUS_CODE",
        "STATUS_DATE",
        "PIPELINE_TYPE",
        "PIPELINE_SEGMENT",
        "PRODUCT_CODE",
        "OPERATOR_NUM",
        "SORT_NAME",
        "PERMIT_DATE",
        "APPROVAL_DATE",
        "DIAMETER",
        "LENGTH",
        "WATER_DEPTH",
        "FROM_FACILITY",
        "TO_FACILITY",
        "DISTRICT_CODE",
    ]

    def router(self, cfg: Dict[str, Any]) -> tuple:
        """Main entry point for pipeline permit data processing."""
        return cfg, None

    def save_pipeline_permit_data_to_binary(self, cfg: Dict[str, Any]) -> None:
        """Save pipeline permit data to binary format from ZIP."""
        logger.info("Saving pipeline permit data to binary format")
        try:
            from worldenergydata.modules.bsee.data.processors import MemoryProcessor
            from worldenergydata.modules.bsee.data.scrapers import BSEEWebScraper

            scraper = BSEEWebScraper()
            processor = MemoryProcessor(use_optimized=False)

            zip_data = scraper.download_pipeline_permit_data()
            if zip_data:
                processed = processor.process_pipeline_permit_data(zip_data, cfg)
                if processed:
                    bin_path = (
                        cfg.get("parameters", {})
                        .get("filepath", {})
                        .get("pipeline_permit", {})
                        .get("bin", "data/modules/bsee/bin/pipeline_permit")
                    )
                    processor.save_to_binary(
                        processed, bin_path, "pipeline_permit_data"
                    )
                    logger.info(f"Pipeline permit data saved to {bin_path}")
            scraper.close()
        except Exception as e:
            logger.error(f"Error saving pipeline permit data: {str(e)}")
