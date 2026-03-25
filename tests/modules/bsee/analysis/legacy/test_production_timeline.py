#!/usr/bin/env python3
"""
Test script to verify the production timeline functionality
"""
import os
import sys
from pathlib import Path

from loguru import logger

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from worldenergydata.engine import engine


def test_production_timeline():
    """Test the production timeline analysis with the anchor field data"""

    logger.basicConfig(level=logger.INFO)
    logger = logger.getLogger(__name__)

    # Use the simple config file
    config_file = current_dir / "query_field_anchor_simple.yml"

    if not config_file.exists():
        logger.error(f"Config file not found: {config_file}")
        return False

    try:
        logger.info("Running production timeline analysis...")
        cfg = engine(str(config_file))

        # Check if result files were created
        result_folder = cfg.get("Analysis", {}).get("result_folder", "")
        groups_label = cfg.get("meta", {}).get("label", "test")

        # Check for well timeline file
        timeline_file = Path(result_folder) / f"well_timeline_{groups_label}.csv"
        if timeline_file.exists():
            logger.info(f"Timeline file created: {timeline_file}")

            # Read and check the timeline data
            import pandas as pd

            timeline_df = pd.read_csv(timeline_file)
            logger.info(f"Timeline columns: {list(timeline_df.columns)}")

            # Check if new columns exist
            expected_columns = [
                "PRODUCTION_START_COUNT",
                "PRODUCTION_END_COUNT",
                "PRODUCING_CURRENTLY_COUNT",
            ]
            for col in expected_columns:
                if col in timeline_df.columns:
                    logger.info(f"✓ Column {col} found in timeline")
                else:
                    logger.warning(f"✗ Column {col} missing from timeline")
        else:
            logger.warning(f"Timeline file not found: {timeline_file}")

        # Check for plot file
        plot_file = Path(result_folder) / "Plot" / f"well_timeline_{groups_label}.html"
        if plot_file.exists():
            logger.info(f"✓ Plot file created: {plot_file}")
        else:
            logger.warning(f"✗ Plot file not found: {plot_file}")

        logger.info("Production timeline analysis completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error running production timeline analysis: {e}")
        return False


if __name__ == "__main__":
    success = test_production_timeline()
    sys.exit(0 if success else 1)
