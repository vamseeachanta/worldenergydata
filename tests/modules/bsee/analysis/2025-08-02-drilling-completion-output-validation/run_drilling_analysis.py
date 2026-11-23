"""Direct execution of drilling completion days analysis for validation"""

import os
import sys

import pandas as pd
from loguru import logger

# Add the src directory to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../src"))
)

from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.july.drilling_and_completion_days import (
    DrillingCompletionDays,
)


def run_drilling_analysis():
    """Run the drilling completion days analysis with test configuration"""

    # Create instance
    dcd = DrillingCompletionDays()

    # Set up configuration based on the existing config file
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)

    cfg = {
        "Analysis": {
            "result_folder": results_dir,
            "file_name_for_overwrite": "drilling_completion_validation",
        },
        "filepath": {
            "war_files": {
                "main": "data/modules/bsee/bin/war/mv_war_main.bin",
                "prop": "data/modules/bsee/bin/war/mv_war_main_prop.bin",
                "boreholes": "data/modules/bsee/bin/war/mv_war_boreholes_view.bin",
            },
            "leases": "tests/modules/bsee/analysis/leases.csv",
        },
    }

    try:
        # Run the analysis
        logger.info("Starting drilling completion days analysis for validation")
        dcd.router(cfg)

        # Check for output file
        expected_filename = "drilling_and_completion_days_by_api_validation.xlsx"
        output_path = os.path.join(results_dir, expected_filename)

        # Check if file was created with timestamp
        import glob

        validation_files = glob.glob(
            os.path.join(
                results_dir, "drilling_and_completion_days_by_api_validation*.xlsx"
            )
        )

        if validation_files:
            output_path = validation_files[0]  # Get the first matching file
            logger.info(f"Output file created: {output_path}")

            # Get file info
            file_size = os.path.getsize(output_path)
            logger.info(f"File size: {file_size:,} bytes")

            # Load and check content
            df = pd.read_excel(output_path)
            logger.info(f"Output contains {len(df)} rows and {len(df.columns)} columns")
            logger.info(f"Columns: {', '.join(df.columns)}")

            return output_path, df
        else:
            logger.error("No output file was created")
            return None, None

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        logger.exception(e)
        return None, None


if __name__ == "__main__":
    output_path, df = run_drilling_analysis()
    if output_path:
        print(f"\nAnalysis completed successfully!")
        print(f"Output file: {output_path}")
        print(f"Data shape: {df.shape}")
    else:
        print("\nAnalysis failed. Check the logs for details.")
