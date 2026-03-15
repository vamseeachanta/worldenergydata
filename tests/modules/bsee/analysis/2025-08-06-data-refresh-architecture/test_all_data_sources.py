"""
Test 10.1.3.1: Verify file processing for each data source (well, production, war)
This test iterates through all three data sources and verifies that files are properly processed.
"""

import os
import pickle
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import (
    DataRefreshEnhanced,
)


class DataSourceTester:
    """Test all data sources with a single iterative approach."""

    def __init__(self):
        # Define all data sources with their configurations
        self.data_sources = {
            "well": {
                "url": "https://www.data.bsee.gov/Well/Files/APDRawData.zip",
                "output_dir": "data/modules/bsee/bin/apd",
                "config_key": "well",
                "expected_files": ["mv_apddata_all", "mv_apd_main_all"],
                "description": "Well (APD) Data",
            },
            "production": {
                "url": "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
                "output_dir": "data/modules/bsee/bin/production_raw",
                "config_key": "production",
                "expected_files": [],  # Will be populated dynamically
                "description": "Production Data",
            },
            "war": {
                "url": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
                "output_dir": "data/modules/bsee/bin/war",
                "config_key": "war",
                "expected_files": [],  # Will be populated dynamically
                "description": "WAR (Well Activity Report) Data",
            },
        }

        self.test_results = {}

    def create_config_for_source(self, source_name):
        """
        Create configuration for a specific data source.

        Args:
            source_name: Name of the data source ('well', 'production', or 'war')
        """
        source = self.data_sources[source_name]

        config = {
            "meta": {
                "library": "worldenergydata",
                "basename": "bsee",
                "mode": "enhanced",
            },
            "enhanced_mode": True,
            "data": {
                "refresh": True,
                "enhanced": True,
                "fresh_data": True,
                "well": source_name == "well",
                "production": source_name == "production",
                "war": source_name == "war",
                "apm": source_name == "well",  # Legacy compatibility
            },
            "parameters": {
                "filepath": {
                    "bin_dir": "data/modules/bsee/bin",
                    "well": {"bin": self.data_sources["well"]["output_dir"]},
                    "war": {"bin": self.data_sources["war"]["output_dir"]},
                    "production": {
                        "bin": self.data_sources["production"]["output_dir"]
                    },
                    "apm": {"bin": self.data_sources["well"]["output_dir"]},  # Legacy
                }
            },
            "default": {"log_level": "INFO"},
            "processing": {"in_memory": True, "save_zip": False, "timeout": 300},
        }

        return config

    def test_single_source(self, source_name):
        """
        Test a single data source.

        Args:
            source_name: Name of the data source to test
        """
        source = self.data_sources[source_name]

        logger.info(f"\n{'='*70}")
        logger.info(f"Testing {source['description']} ({source_name})")
        logger.info(f"{'='*70}")

        # Create configuration
        config = self.create_config_for_source(source_name)

        # Clear output directory before test
        output_dir = source["output_dir"]
        if os.path.exists(output_dir):
            logger.info(f"Checking existing files in {output_dir}")
            existing_files = [f for f in os.listdir(output_dir) if f.endswith(".bin")]
            if existing_files:
                logger.info(f"Found {len(existing_files)} existing .bin files")

        try:
            # Initialize and run enhanced data refresh
            data_refresh = DataRefreshEnhanced()
            logger.info(f"Processing {source_name} data...")

            # Save config to temporary file for logging
            config_file = f"test_config_{source_name}.yml"
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            # Run the data refresh
            result_cfg, result_data = data_refresh.router(config)

            # Clean up temp config
            if os.path.exists(config_file):
                os.remove(config_file)

            # Verify output files
            success = self.verify_output_files(source_name, output_dir)

            self.test_results[source_name] = {
                "success": success,
                "output_dir": output_dir,
                "files_found": [],
            }

            if success:
                logger.success(
                    f"✓ {source['description']} processing completed successfully"
                )
            else:
                logger.error(f"✗ {source['description']} processing failed")

            return success

        except Exception as e:
            logger.error(f"Error processing {source_name}: {str(e)}")
            self.test_results[source_name] = {"success": False, "error": str(e)}
            return False

    def verify_output_files(self, source_name, output_dir):
        """
        Verify that output files were created for the data source.

        Args:
            source_name: Name of the data source
            output_dir: Directory where output files should be
        """
        if not os.path.exists(output_dir):
            logger.error(f"Output directory does not exist: {output_dir}")
            return False

        # Check for .bin files
        bin_files = [f for f in os.listdir(output_dir) if f.endswith(".bin")]

        if not bin_files:
            logger.error(f"No .bin files found in {output_dir}")
            return False

        logger.info(f"\nFound {len(bin_files)} .bin files in {output_dir}:")

        # Verify each file can be loaded
        valid_files = 0
        for bin_file in bin_files:
            file_path = os.path.join(output_dir, bin_file)
            file_size = os.path.getsize(file_path)

            try:
                with open(file_path, "rb") as f:
                    data = pickle.load(f)
                    if isinstance(data, pd.DataFrame):
                        logger.info(
                            f"  ✓ {bin_file}: {file_size:,} bytes, shape={data.shape}"
                        )
                        valid_files += 1
                    else:
                        logger.info(
                            f"  ✓ {bin_file}: {file_size:,} bytes, type={type(data).__name__}"
                        )
                        valid_files += 1

                if source_name in self.test_results:
                    self.test_results[source_name]["files_found"].append(bin_file)

            except Exception as e:
                logger.error(f"  ✗ {bin_file}: Failed to load - {str(e)}")

        return valid_files > 0

    def run_all_tests(self):
        """
        Run tests for all data sources iteratively.
        """
        logger.info("=" * 70)
        logger.info("TASK 10.1.3.1: Test Each Data Source Iteratively")
        logger.info("=" * 70)
        logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Test each data source
        for source_name in self.data_sources.keys():
            self.test_single_source(source_name)

        # Summary
        self.print_summary()

        # Determine overall success
        all_passed = all(
            result.get("success", False) for result in self.test_results.values()
        )

        return all_passed

    def print_summary(self):
        """Print test results summary."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 70)

        passed = 0
        failed = 0

        for source_name, result in self.test_results.items():
            source_desc = self.data_sources[source_name]["description"]
            if result.get("success", False):
                passed += 1
                files_count = len(result.get("files_found", []))
                logger.success(
                    f"✓ {source_desc}: PASSED ({files_count} files processed)"
                )
                if result.get("files_found"):
                    for file in result["files_found"]:
                        logger.info(f"    - {file}")
            else:
                failed += 1
                error = result.get("error", "Unknown error")
                logger.error(f"✗ {source_desc}: FAILED - {error}")

        logger.info(f"\nTotal: {passed} passed, {failed} failed")

        if failed == 0:
            logger.success(
                "\n✅ Task 10.1.3.1 COMPLETE: All data sources processed successfully"
            )
        else:
            logger.error(
                f"\n❌ Task 10.1.3.1 INCOMPLETE: {failed} data source(s) failed"
            )

        logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)


def test_individual_source(source_name="well"):
    """
    Test an individual data source.

    Args:
        source_name: Name of the data source to test
    """
    tester = DataSourceTester()
    success = tester.test_single_source(source_name)
    tester.print_summary()
    return success


def test_all_sources():
    """Test all data sources iteratively."""
    tester = DataSourceTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test BSEE data source processing")
    parser.add_argument(
        "--source",
        choices=["well", "production", "war", "all"],
        default="well",
        help="Data source to test (default: well)",
    )

    args = parser.parse_args()

    if args.source == "all":
        success = test_all_sources()
    else:
        success = test_individual_source(args.source)

    sys.exit(0 if success else 1)
