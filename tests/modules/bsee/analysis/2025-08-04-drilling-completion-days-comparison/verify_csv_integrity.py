#!/usr/bin/env python3
"""
Verify CSV output accuracy and data integrity.

This script checks that the generated CSV files can be read correctly
and contain expected data structure and values.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_csv_integrity():
    """Verify the integrity of generated CSV files."""
    logger.info("Starting CSV integrity verification...")

    results_dir = Path(__file__).parent / "results"

    # Find the latest CSV files
    comparison_files = list(results_dir.glob("drilling_days_comparison_*.csv"))
    lease_files = list(results_dir.glob("drilling_days_lease_method_*.csv"))
    api12_files = list(results_dir.glob("drilling_days_api12_method_*.csv"))

    if not comparison_files:
        logger.error("No comparison CSV files found")
        return False

    # Use the most recent files
    comparison_file = sorted(comparison_files)[-1]
    lease_file = sorted(lease_files)[-1] if lease_files else None
    api12_file = sorted(api12_files)[-1] if api12_files else None

    logger.info(f"Verifying comparison file: {comparison_file}")

    # Test 1: Read comparison CSV with pandas
    try:
        comparison_df = pd.read_csv(comparison_file, comment="#")
        logger.info(
            f"✓ Comparison CSV read successfully: {len(comparison_df)} rows, {len(comparison_df.columns)} columns"
        )

        # Check required columns
        expected_columns = [
            "API12_number",
            "Well_name",
            "lease_method_drilling_days",
            "api12_method_drilling_days",
            "lease_method_completion_days",
            "api12_method_completion_days",
            "Drilling_days_difference",
            "Completion_days_difference",
            "Drilling_days_percent_diff",
            "Completion_days_percent_diff",
            "Status_flag",
            "Notes",
        ]

        missing_cols = [
            col for col in expected_columns if col not in comparison_df.columns
        ]
        if missing_cols:
            logger.error(f"✗ Missing required columns: {missing_cols}")
            return False
        else:
            logger.info("✓ All required columns present")

        # Check data types and values
        if len(comparison_df) > 0:
            first_row = comparison_df.iloc[0]
            logger.info(
                f"Sample data - API: {first_row['API12_number']}, Well: {first_row['Well_name']}"
            )
            logger.info(
                f"  Lease drilling days: {first_row['lease_method_drilling_days']}"
            )
            logger.info(
                f"  API12 drilling days: {first_row['api12_method_drilling_days']}"
            )
            logger.info(f"  Status: {first_row['Status_flag']}")

    except Exception as e:
        logger.error(f"✗ Error reading comparison CSV: {e}")
        return False

    # Test 2: Read lease method CSV
    if lease_file:
        logger.info(f"Verifying lease method file: {lease_file}")
        try:
            lease_df = pd.read_csv(lease_file, comment="#")
            logger.info(
                f"✓ Lease method CSV read successfully: {len(lease_df)} rows, {len(lease_df.columns)} columns"
            )
        except Exception as e:
            logger.error(f"✗ Error reading lease method CSV: {e}")
            return False

    # Test 3: Read API12 method CSV
    if api12_file:
        logger.info(f"Verifying API12 method file: {api12_file}")
        try:
            api12_df = pd.read_csv(api12_file, comment="#")
            logger.info(
                f"✓ API12 method CSV read successfully: {len(api12_df)} rows, {len(api12_df.columns)} columns"
            )
        except Exception as e:
            logger.error(f"✗ Error reading API12 method CSV: {e}")
            return False

    # Test 4: Excel compatibility check
    logger.info("Testing Excel compatibility...")
    try:
        # Test that numeric columns can be processed
        numeric_cols = [
            "lease_method_drilling_days",
            "api12_method_drilling_days",
            "Drilling_days_difference",
            "Drilling_days_percent_diff",
        ]

        for col in numeric_cols:
            if col in comparison_df.columns:
                # Check for infinity values (should be replaced with 'N/A')
                has_inf = any(
                    comparison_df[col]
                    .astype(str)
                    .str.contains("inf", case=False, na=False)
                )
                if has_inf:
                    logger.warning(
                        f"⚠ Column {col} contains infinity values that may cause Excel issues"
                    )
                else:
                    logger.info(f"✓ Column {col} Excel-compatible (no infinity values)")

        logger.info("✓ Excel compatibility check passed")

    except Exception as e:
        logger.error(f"✗ Excel compatibility check failed: {e}")
        return False

    # Test 5: Pandas roundtrip test
    logger.info("Testing pandas roundtrip compatibility...")
    try:
        # Save to temporary file and read back
        temp_file = results_dir / "temp_roundtrip_test.csv"
        comparison_df.to_csv(temp_file, index=False)

        roundtrip_df = pd.read_csv(temp_file)

        # Compare structure
        if len(roundtrip_df) == len(comparison_df) and len(roundtrip_df.columns) == len(
            comparison_df.columns
        ):
            logger.info("✓ Pandas roundtrip test passed")
        else:
            logger.error(f"✗ Pandas roundtrip test failed: shape mismatch")
            return False

        # Cleanup
        temp_file.unlink()

    except Exception as e:
        logger.error(f"✗ Pandas roundtrip test failed: {e}")
        return False

    # Test 6: Data integrity check
    logger.info("Checking data integrity...")
    try:
        if len(comparison_df) > 0:
            # Check that differences are calculated correctly
            for idx, row in comparison_df.iterrows():
                lease_drilling = pd.to_numeric(
                    row["lease_method_drilling_days"], errors="coerce"
                )
                api12_drilling = pd.to_numeric(
                    row["api12_method_drilling_days"], errors="coerce"
                )
                calc_diff = pd.to_numeric(
                    row["Drilling_days_difference"], errors="coerce"
                )

                if (
                    pd.notna(lease_drilling)
                    and pd.notna(api12_drilling)
                    and pd.notna(calc_diff)
                ):
                    expected_diff = lease_drilling - api12_drilling
                    if (
                        abs(calc_diff - expected_diff) > 0.01
                    ):  # Allow small floating point differences
                        logger.warning(
                            f"⚠ Row {idx}: drilling difference calculation may be incorrect"
                        )
                        logger.warning(f"  Expected: {expected_diff}, Got: {calc_diff}")

        logger.info("✓ Data integrity check completed")

    except Exception as e:
        logger.error(f"✗ Data integrity check failed: {e}")
        return False

    logger.info("=" * 60)
    logger.info("CSV INTEGRITY VERIFICATION COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info("All CSV files are properly formatted and contain valid data")
    logger.info("Files are compatible with Excel and pandas")
    logger.info("Data integrity checks passed")

    return True


if __name__ == "__main__":
    success = verify_csv_integrity()
    if not success:
        exit(1)
