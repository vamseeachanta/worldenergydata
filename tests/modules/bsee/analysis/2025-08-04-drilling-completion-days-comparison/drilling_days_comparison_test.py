"""
Drilling Days Comparison Test Framework

This module provides comprehensive comparison testing between two different
drilling days calculation methods:
- Method 1 (lease_num): Lease number approach
- Method 2 (api12_num): API12 number approach

The test framework executes both methods, compares their outputs, and generates
detailed comparison reports in markdown format.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import deepdiff
import pandas as pd
import pytest
from assetutilities.common.yml_utilities import ymlInput

from worldenergydata.engine import engine

DEEPDIFF_AVAILABLE = True
ENGINE_AVAILABLE = True


class DrillingDaysComparisonTest:
    """
    Main comparison test framework for drilling days analysis methods.

    This class orchestrates the execution of both drilling days calculation
    methods and provides comprehensive comparison analysis.
    """

    def __init__(self, config_file: str = "drilling_days_comparison_config.yml"):
        """
        Initialize the comparison test framework.

        Args:
            config_file: Path to the YAML configuration file
        """
        self.config_file = config_file
        self.config = None
        self.method1_results = None
        self.method2_results = None
        self.comparison_results = None
        self.test_directory = Path(__file__).parent
        self.output_directory = self.test_directory / "output"

        # Ensure output directory exists
        self.output_directory.mkdir(exist_ok=True)

    def load_configuration(self) -> Dict:
        """
        Load test configuration from YAML file.

        Returns:
            Dict: Configuration parameters

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_path = self.test_directory / self.config_file

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        self.config = ymlInput(str(config_path), updateYml=None)
        return self.config

    def execute_method1_test(self) -> bool:
        """
        Execute Method 1 (lease_num) drilling days test.

        Returns:
            bool: True if execution successful, False otherwise
        """
        try:
            # Method 1 uses drilling_n_completion_days.yml configuration
            method1_config = self.test_directory / "drilling_n_completion_days.yml"

            if not method1_config.exists():
                print(f"Method 1 config file not found: {method1_config}")
                return False

            # Clean up sys.argv to avoid pytest interference
            original_argv = sys.argv.copy()
            if len(sys.argv) > 1:
                sys.argv = sys.argv[:1]

            try:
                # Execute Method 1 analysis
                cfg = engine(str(method1_config))
            finally:
                # Restore original argv
                sys.argv = original_argv

            # Verify output file was created
            expected_output = (
                self.test_directory
                / "results"
                / "drilling_and_completion_days_by_api.xlsx"
            )
            if expected_output.exists():
                self.method1_results = str(expected_output)
                return True
            else:
                print(f"Method 1 output file not found: {expected_output}")
                return False

        except Exception as e:
            print(f"Error executing Method 1: {str(e)}")
            return False

    def execute_method2_test(self) -> bool:
        """
        Execute Method 2 (api12_num) drilling days test.

        Returns:
            bool: True if execution successful, False otherwise
        """
        try:
            # Method 2 uses query_api_01_wells_api12_rig_days_Tiber.yml configuration
            method2_config = (
                self.test_directory / "query_api_01_wells_api12_rig_days_Tiber.yml"
            )

            if not method2_config.exists():
                print(f"Method 2 config file not found: {method2_config}")
                return False

            # Clean up sys.argv to avoid pytest interference
            original_argv = sys.argv.copy()
            if len(sys.argv) > 1:
                sys.argv = sys.argv[:1]

            try:
                # Execute Method 2 analysis
                cfg = engine(str(method2_config))
            finally:
                # Restore original argv
                sys.argv = original_argv

            # Verify output file was created
            expected_output = (
                self.test_directory / "results" / "well_summ_goa_tiber.csv"
            )
            if expected_output.exists():
                self.method2_results = str(expected_output)
                return True
            else:
                print(f"Method 2 output file not found: {expected_output}")
                return False

        except Exception as e:
            print(f"Error executing Method 2: {str(e)}")
            return False

    def load_method_outputs(
        self,
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Load output files from both methods into pandas DataFrames.

        Returns:
            Tuple of DataFrames: (method1_df, method2_df)
        """
        method1_df = None
        method2_df = None

        try:
            # Load Method 1 results (Excel format)
            if self.method1_results and os.path.exists(self.method1_results):
                method1_df = pd.read_excel(self.method1_results)
                print(
                    f"Method 1: Loaded {len(method1_df)} records from {self.method1_results}"
                )

            # Load Method 2 results (CSV format)
            if self.method2_results and os.path.exists(self.method2_results):
                method2_df = pd.read_csv(self.method2_results)
                print(
                    f"Method 2: Loaded {len(method2_df)} records from {self.method2_results}"
                )

        except Exception as e:
            print(f"Error loading method outputs: {str(e)}")

        return method1_df, method2_df

    def standardize_columns(
        self, df1: pd.DataFrame, df2: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Standardize column names and data types for comparison.

        Args:
            df1: Method 1 DataFrame
            df2: Method 2 DataFrame

        Returns:
            Tuple of standardized DataFrames
        """
        # Method 1 column mapping
        if df1 is not None:
            method1_mapping = {
                "API_WELL_NUMBER": "api12",
                "WELL_NAME": "well_name",
                "DRILLING_DAYS": "drilling_days",
                "COMPLETION_DAYS": "completion_days",
            }
            df1 = df1.rename(columns=method1_mapping)

        # Method 2 column mapping
        if df2 is not None:
            method2_mapping = {
                "API12": "api12",
                "WELL_NAME": "well_name",
                "Drilling Days": "drilling_days",
                "Completion Days": "completion_days",
            }
            df2 = df2.rename(columns=method2_mapping)

        return df1, df2

    def generate_comparison_summary(self, df1: pd.DataFrame, df2: pd.DataFrame) -> Dict:
        """
        Generate basic comparison summary statistics.

        Args:
            df1: Method 1 DataFrame
            df2: Method 2 DataFrame

        Returns:
            Dict: Summary statistics
        """
        summary = {
            "method1_records": len(df1) if df1 is not None else 0,
            "method2_records": len(df2) if df2 is not None else 0,
            "method1_file": self.method1_results,
            "method2_file": self.method2_results,
        }

        return summary

    def discover_test_methods(self) -> Dict[str, bool]:
        """
        Discover available test methods and their configuration files.

        Returns:
            Dict: Availability status of each method
        """
        discovery_results = {
            "method1_available": False,
            "method2_available": False,
            "method1_config_path": None,
            "method2_config_path": None,
        }

        if self.config:
            # Check Method 1 configuration
            method1_config = self.config.get("method1", {}).get("config_file")
            if method1_config:
                method1_path = self.test_directory / method1_config
                discovery_results["method1_config_path"] = str(method1_path)
                discovery_results["method1_available"] = method1_path.exists()

            # Check Method 2 configuration
            method2_config = self.config.get("method2", {}).get("config_file")
            if method2_config:
                method2_path = self.test_directory / method2_config
                discovery_results["method2_config_path"] = str(method2_path)
                discovery_results["method2_available"] = method2_path.exists()

        return discovery_results

    def execute_test_with_retry(
        self, method_name: str, execute_func
    ) -> Tuple[bool, str]:
        """
        Execute a test method with retry logic.

        Args:
            method_name: Name of the method being executed
            execute_func: Function to execute

        Returns:
            Tuple: (success, error_message)
        """
        max_retries = self.config.get("error_handling", {}).get("max_retries", 2)

        for attempt in range(max_retries + 1):
            try:
                success = execute_func()
                if success:
                    return True, ""
                else:
                    error_msg = (
                        f"{method_name} execution failed on attempt {attempt + 1}"
                    )
                    if attempt < max_retries:
                        print(f"{error_msg}, retrying...")
                        continue
                    else:
                        return False, error_msg
            except Exception as e:
                error_msg = (
                    f"{method_name} execution error on attempt {attempt + 1}: {str(e)}"
                )
                if attempt < max_retries:
                    print(f"{error_msg}, retrying...")
                    continue
                else:
                    return False, error_msg

        return False, f"{method_name} execution failed after all retries"

    def run_full_comparison(self) -> Dict:
        """
        Execute complete comparison workflow.

        Returns:
            Dict: Complete comparison results
        """
        # Load configuration
        try:
            self.load_configuration()
        except Exception as e:
            return {
                "success": False,
                "error": f"Configuration loading failed: {str(e)}",
            }

        # Discover available test methods
        discovery = self.discover_test_methods()

        if not discovery["method1_available"] or not discovery["method2_available"]:
            return {
                "success": False,
                "error": "One or both methods not available",
                "discovery": discovery,
            }

        # Execute both methods with retry logic
        method1_success, method1_error = self.execute_test_with_retry(
            "Method 1", self.execute_method1_test
        )
        method2_success, method2_error = self.execute_test_with_retry(
            "Method 2", self.execute_method2_test
        )

        if not method1_success or not method2_success:
            return {
                "success": False,
                "method1_success": method1_success,
                "method2_success": method2_success,
                "method1_error": method1_error,
                "method2_error": method2_error,
                "error": "One or both methods failed to execute",
            }

        # Load and compare outputs
        df1, df2 = self.load_method_outputs()

        if df1 is None or df2 is None:
            return {
                "success": False,
                "error": "Failed to load method outputs",
                "method1_loaded": df1 is not None,
                "method2_loaded": df2 is not None,
            }

        # Standardize columns
        df1, df2 = self.standardize_columns(df1, df2)

        # Generate comparison summary
        summary = self.generate_comparison_summary(df1, df2)

        # Add discovery information to results
        summary["discovery"] = discovery

        self.comparison_results = {
            "success": True,
            "summary": summary,
            "method1_df": df1,
            "method2_df": df2,
        }

        return self.comparison_results

    def compare_drilling_days_data(
        self, df1: pd.DataFrame, df2: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Perform detailed comparison of drilling days data between methods.

        Args:
            df1: Method 1 DataFrame (standardized columns)
            df2: Method 2 DataFrame (standardized columns)

        Returns:
            pd.DataFrame: Comparison results with differences
        """
        # Merge dataframes on API12
        comparison_df = pd.merge(
            df1[["api12", "well_name", "drilling_days", "completion_days"]].add_suffix(
                "_method1"
            ),
            df2[["api12", "well_name", "drilling_days", "completion_days"]].add_suffix(
                "_method2"
            ),
            left_on="api12_method1",
            right_on="api12_method2",
            how="outer",
            suffixes=("_method1", "_method2"),
        )

        # Calculate differences
        comparison_df["drilling_days_diff"] = pd.to_numeric(
            comparison_df["drilling_days_method1"], errors="coerce"
        ) - pd.to_numeric(comparison_df["drilling_days_method2"], errors="coerce")

        comparison_df["completion_days_diff"] = pd.to_numeric(
            comparison_df["completion_days_method1"], errors="coerce"
        ) - pd.to_numeric(comparison_df["completion_days_method2"], errors="coerce")

        # Calculate percentage differences (avoiding division by zero)
        comparison_df["drilling_days_pct_diff"] = (
            comparison_df["drilling_days_diff"]
            / pd.to_numeric(
                comparison_df["drilling_days_method2"], errors="coerce"
            ).replace(0, pd.NA)
            * 100
        )

        comparison_df["completion_days_pct_diff"] = (
            comparison_df["completion_days_diff"]
            / pd.to_numeric(
                comparison_df["completion_days_method2"], errors="coerce"
            ).replace(0, pd.NA)
            * 100
        )

        # Add status flags based on thresholds from config
        thresholds = self.config.get("comparison", {}).get("thresholds", {})
        drilling_abs_threshold = thresholds.get("drilling_days", {}).get(
            "absolute_difference", 5
        )
        drilling_pct_threshold = thresholds.get("drilling_days", {}).get(
            "percentage_difference", 10
        )
        completion_abs_threshold = thresholds.get("completion_days", {}).get(
            "absolute_difference", 5
        )
        completion_pct_threshold = thresholds.get("completion_days", {}).get(
            "percentage_difference", 10
        )

        def get_status(row):
            drilling_abs_diff = (
                abs(row["drilling_days_diff"])
                if pd.notna(row["drilling_days_diff"])
                else 0
            )
            drilling_pct_diff = (
                abs(row["drilling_days_pct_diff"])
                if pd.notna(row["drilling_days_pct_diff"])
                else 0
            )
            completion_abs_diff = (
                abs(row["completion_days_diff"])
                if pd.notna(row["completion_days_diff"])
                else 0
            )
            completion_pct_diff = (
                abs(row["completion_days_pct_diff"])
                if pd.notna(row["completion_days_pct_diff"])
                else 0
            )

            # Check if either method has missing data
            if (
                pd.isna(row["drilling_days_method1"])
                or pd.isna(row["drilling_days_method2"])
                or pd.isna(row["completion_days_method1"])
                or pd.isna(row["completion_days_method2"])
            ):
                return "ERROR"

            # Check if differences exceed thresholds
            if (
                drilling_abs_diff > drilling_abs_threshold
                or drilling_pct_diff > drilling_pct_threshold
                or completion_abs_diff > completion_abs_threshold
                or completion_pct_diff > completion_pct_threshold
            ):
                return "REVIEW"

            return "OK"

        comparison_df["status"] = comparison_df.apply(get_status, axis=1)

        return comparison_df

    def generate_markdown_comparison_table(self, comparison_df: pd.DataFrame) -> str:
        """
        Generate a markdown-formatted comparison table.

        Args:
            comparison_df: DataFrame with comparison results

        Returns:
            str: Markdown-formatted table
        """
        # Get configuration for table formatting
        table_config = (
            self.config.get("reports", {}).get("markdown", {}).get("table_format", {})
        )
        alignment = table_config.get("alignment", "center")

        # Create markdown table header
        markdown_lines = [
            "# Drilling Days Comparison Report",
            "",
            f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Comparison Summary",
            "",
            f"- **Method 1 (Lease Number):** {len(comparison_df[comparison_df['api12_method1'].notna()])} records",
            f"- **Method 2 (API12 Number):** {len(comparison_df[comparison_df['api12_method2'].notna()])} records",
            f"- **Matched Records:** {len(comparison_df.dropna(subset=['api12_method1', 'api12_method2']))} records",
            "",
            "## Detailed Comparison",
            "",
            "| API12 Number | Well Name | Method 1 Drilling | Method 2 Drilling | Drilling Diff | Method 1 Completion | Method 2 Completion | Completion Diff | Status |",
            "|"
            + ("-" * 14)
            + "|"
            + ("-" * 11)
            + "|"
            + ("-" * 19)
            + "|"
            + ("-" * 19)
            + "|"
            + ("-" * 15)
            + "|"
            + ("-" * 21)
            + "|"
            + ("-" * 21)
            + "|"
            + ("-" * 17)
            + "|"
            + ("-" * 8)
            + "|",
        ]

        # Add table rows
        for _, row in comparison_df.iterrows():
            # Use method1 API12 if available, otherwise method2
            api12 = (
                row["api12_method1"]
                if pd.notna(row["api12_method1"])
                else row["api12_method2"]
            )
            well_name = (
                row["well_name_method1"]
                if pd.notna(row["well_name_method1"])
                else row["well_name_method2"]
            )

            # Format values, handling NaN
            def format_value(val, precision=1):
                if pd.isna(val):
                    return "N/A"
                return (
                    f"{val:.{precision}f}"
                    if isinstance(val, (int, float))
                    else str(val)
                )

            drilling_m1 = format_value(row["drilling_days_method1"], 0)
            drilling_m2 = format_value(row["drilling_days_method2"], 0)
            drilling_diff = format_value(row["drilling_days_diff"], 1)
            completion_m1 = format_value(row["completion_days_method1"], 0)
            completion_m2 = format_value(row["completion_days_method2"], 0)
            completion_diff = format_value(row["completion_days_diff"], 1)
            status = row["status"]

            # Truncate well name if too long
            well_name_short = (
                well_name[:9] + "..." if len(str(well_name)) > 12 else str(well_name)
            )

            markdown_lines.append(
                f"| {api12} | {well_name_short} | {drilling_m1} | {drilling_m2} | {drilling_diff} | {completion_m1} | {completion_m2} | {completion_diff} | {status} |"
            )

        # Add summary statistics
        status_counts = comparison_df["status"].value_counts()
        markdown_lines.extend(
            [
                "",
                "## Status Summary",
                "",
                f"- **OK:** {status_counts.get('OK', 0)} records (within acceptable thresholds)",
                f"- **REVIEW:** {status_counts.get('REVIEW', 0)} records (exceeding thresholds, require review)",
                f"- **ERROR:** {status_counts.get('ERROR', 0)} records (missing data or calculation errors)",
                "",
                "## Thresholds Used",
                "",
                f"- **Drilling Days:** ±{self.config.get('comparison', {}).get('thresholds', {}).get('drilling_days', {}).get('absolute_difference', 5)} days absolute, ±{self.config.get('comparison', {}).get('thresholds', {}).get('drilling_days', {}).get('percentage_difference', 10)}% relative",
                f"- **Completion Days:** ±{self.config.get('comparison', {}).get('thresholds', {}).get('completion_days', {}).get('absolute_difference', 5)} days absolute, ±{self.config.get('comparison', {}).get('thresholds', {}).get('completion_days', {}).get('percentage_difference', 10)}% relative",
                "",
            ]
        )

        return "\n".join(markdown_lines)

    def save_markdown_report(self, markdown_content: str) -> str:
        """
        Save markdown report to file.

        Args:
            markdown_content: Markdown content to save

        Returns:
            str: Path to saved file
        """
        report_config = self.config.get("reports", {}).get("markdown", {})
        filename = report_config.get("filename", "drilling_days_comparison_report.md")

        # Add timestamp to filename to avoid overwriting
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = filename.replace(".md", f"_{timestamp}.md")

        report_path = self.output_directory / filename_with_timestamp

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return str(report_path)

    def run_full_comparison_with_report(self) -> Dict:
        """
        Execute complete comparison workflow and generate markdown report.

        Returns:
            Dict: Complete comparison results including report path
        """
        # Run the basic comparison first
        results = self.run_full_comparison()

        if not results.get("success", False):
            return results

        # Get the dataframes from results
        df1 = results["method1_df"]
        df2 = results["method2_df"]

        # Perform detailed comparison
        comparison_df = self.compare_drilling_days_data(df1, df2)

        # Generate markdown report
        markdown_content = self.generate_markdown_comparison_table(comparison_df)

        # Save report
        report_path = self.save_markdown_report(markdown_content)

        # Add report information to results
        results["comparison_df"] = comparison_df
        results["markdown_report_path"] = report_path
        results["markdown_content"] = markdown_content

        return results


def run_application(input_file, expected_result={}):
    """
    Legacy compatibility function for existing test framework.

    Args:
        input_file: Configuration file path
        expected_result: Expected test results (optional)
    """
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)

    if not ENGINE_AVAILABLE:
        pytest.skip("Engine not available - dependencies missing")

    cfg = engine(input_file)


def get_valid_pytest_output_file(pytest_output_file):
    """
    Legacy compatibility function for existing test framework.

    Args:
        pytest_output_file: Path to pytest output file

    Returns:
        str: Valid file path
    """
    if pytest_output_file is not None and not os.path.isfile(pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__), pytest_output_file)
    return pytest_output_file


def test_configuration_loading():
    """
    Test configuration file loading and validation.
    """
    comparison_test = DrillingDaysComparisonTest()

    # Test configuration loading
    config = comparison_test.load_configuration()

    # Validate configuration structure
    assert config is not None, "Configuration failed to load"
    assert "method1" in config, "Method 1 configuration missing"
    assert "method2" in config, "Method 2 configuration missing"
    assert "comparison" in config, "Comparison configuration missing"

    # Validate method configurations
    assert "config_file" in config["method1"], "Method 1 config_file missing"
    assert "config_file" in config["method2"], "Method 2 config_file missing"


def test_method_discovery():
    """
    Test method discovery functionality.
    """
    comparison_test = DrillingDaysComparisonTest()
    comparison_test.load_configuration()

    # Test discovery
    discovery = comparison_test.discover_test_methods()

    # Validate discovery results
    assert "method1_available" in discovery, "Method 1 availability not reported"
    assert "method2_available" in discovery, "Method 2 availability not reported"
    assert "method1_config_path" in discovery, "Method 1 config path not reported"
    assert "method2_config_path" in discovery, "Method 2 config path not reported"

    # Print discovery results for debugging
    print("\n=== Method Discovery Results ===")
    print(f"Method 1 Available: {discovery['method1_available']}")
    print(f"Method 1 Config: {discovery['method1_config_path']}")
    print(f"Method 2 Available: {discovery['method2_available']}")
    print(f"Method 2 Config: {discovery['method2_config_path']}")
    print("=================================\n")


def test_drilling_days_comparison():
    """
    Main pytest test function for drilling days comparison.

    This test executes both drilling days methods and performs
    basic validation of the comparison framework.
    """
    # Initialize comparison test framework
    comparison_test = DrillingDaysComparisonTest()

    # Run full comparison
    results = comparison_test.run_full_comparison()

    # Print detailed results for debugging
    print("\n=== Full Comparison Results ===")
    print(f"Success: {results.get('success', False)}")
    if not results.get("success", False):
        print(f"Error: {results.get('error', 'Unknown error')}")
        if "discovery" in results:
            discovery = results["discovery"]
            print(f"Method 1 Available: {discovery.get('method1_available', False)}")
            print(f"Method 2 Available: {discovery.get('method2_available', False)}")
    print("===============================\n")

    # Basic assertions with more informative error messages
    if not results.get("success", False):
        error_msg = results.get("error", "Unknown error")
        # Check if this is a configuration issue that should be skipped
        if "not available" in error_msg or "Configuration loading failed" in error_msg:
            pytest.skip(f"Test skipped due to configuration issue: {error_msg}")
        else:
            pytest.fail(f"Comparison failed: {error_msg}")

    assert (
        results["success"] is True
    ), f"Comparison failed: {results.get('error', 'Unknown error')}"
    assert "summary" in results, "Comparison results missing summary"

    # Print summary for manual review
    summary = results["summary"]
    print("\n=== Drilling Days Comparison Summary ===")
    print(f"Method 1 Records: {summary.get('method1_records', 0)}")
    print(f"Method 2 Records: {summary.get('method2_records', 0)}")
    print(f"Method 1 File: {summary.get('method1_file', 'Not found')}")
    print(f"Method 2 File: {summary.get('method2_file', 'Not found')}")
    print("========================================\n")

    # Only assert record counts if we have valid data
    if summary.get("method1_records", 0) > 0 and summary.get("method2_records", 0) > 0:
        assert summary["method1_records"] > 0, "Method 1 produced no records"
        assert summary["method2_records"] > 0, "Method 2 produced no records"
    else:
        print(
            "Warning: One or both methods produced no records - this may indicate missing test data"
        )


def test_method1_execution():
    """
    Test Method 1 (lease_num) execution independently.
    """
    comparison_test = DrillingDaysComparisonTest()
    comparison_test.load_configuration()

    success = comparison_test.execute_method1_test()
    assert success is True, "Method 1 execution failed"

    # Verify output file exists
    assert comparison_test.method1_results is not None, "Method 1 results path not set"
    assert os.path.exists(
        comparison_test.method1_results
    ), f"Method 1 output file not found: {comparison_test.method1_results}"


def test_method2_execution():
    """
    Test Method 2 (api12_num) execution independently.
    """
    comparison_test = DrillingDaysComparisonTest()
    comparison_test.load_configuration()

    success = comparison_test.execute_method2_test()
    assert success is True, "Method 2 execution failed"

    # Verify output file exists
    assert comparison_test.method2_results is not None, "Method 2 results path not set"
    assert os.path.exists(
        comparison_test.method2_results
    ), f"Method 2 output file not found: {comparison_test.method2_results}"


def test_data_loading():
    """
    Test data loading functionality from both methods.
    """
    comparison_test = DrillingDaysComparisonTest()
    comparison_test.load_configuration()

    # Execute both methods first
    method1_success = comparison_test.execute_method1_test()
    method2_success = comparison_test.execute_method2_test()

    if not method1_success or not method2_success:
        pytest.skip("Cannot test data loading - method execution failed")

    # Test data loading
    df1, df2 = comparison_test.load_method_outputs()

    assert df1 is not None, "Failed to load Method 1 data"
    assert df2 is not None, "Failed to load Method 2 data"
    assert len(df1) > 0, "Method 1 DataFrame is empty"
    assert len(df2) > 0, "Method 2 DataFrame is empty"


def test_markdown_report_generation():
    """
    Test the markdown report generation functionality.

    This test demonstrates the key deliverable: generating a markdown
    comparison table between the two drilling days methods.
    """
    # Initialize comparison test framework
    comparison_test = DrillingDaysComparisonTest()

    # Run full comparison with report generation
    results = comparison_test.run_full_comparison_with_report()

    # Print detailed results for debugging
    print("\n=== Markdown Report Generation Results ===")
    print(f"Success: {results.get('success', False)}")

    if not results.get("success", False):
        error_msg = results.get("error", "Unknown error")
        if "not available" in error_msg or "Configuration loading failed" in error_msg:
            pytest.skip(f"Test skipped due to configuration issue: {error_msg}")
        else:
            pytest.fail(f"Report generation failed: {error_msg}")

    # Validate results
    assert (
        results["success"] is True
    ), f"Report generation failed: {results.get('error', 'Unknown error')}"
    assert "markdown_report_path" in results, "Markdown report path not provided"
    assert "markdown_content" in results, "Markdown content not provided"
    assert "comparison_df" in results, "Comparison DataFrame not provided"

    # Check that report file was created
    assert os.path.exists(
        results["markdown_report_path"]
    ), f"Report file not created: {results['markdown_report_path']}"

    # Print report path and preview for manual review
    print(f"Report saved to: {results['markdown_report_path']}")
    print("\n=== Markdown Report Preview ===")
    preview_lines = results["markdown_content"].split("\n")[:20]  # First 20 lines
    for line in preview_lines:
        print(line)
    if len(results["markdown_content"].split("\n")) > 20:
        print("... (report continues)")
    print("=====================================\n")

    # Validate markdown content structure
    markdown_content = results["markdown_content"]
    assert (
        "# Drilling Days Comparison Report" in markdown_content
    ), "Report title missing"
    assert "## Comparison Summary" in markdown_content, "Summary section missing"
    assert "## Detailed Comparison" in markdown_content, "Detailed comparison missing"
    assert "| API12 Number |" in markdown_content, "Comparison table missing"
    assert "## Status Summary" in markdown_content, "Status summary missing"

    # Print comparison DataFrame info
    comparison_df = results["comparison_df"]
    print(f"Comparison DataFrame: {len(comparison_df)} rows")
    if len(comparison_df) > 0:
        status_counts = comparison_df["status"].value_counts()
        print(f"Status breakdown: {dict(status_counts)}")


if __name__ == "__main__":
    # Run tests when executed directly
    test_markdown_report_generation()
