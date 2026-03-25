"""Compare drilling completion days outputs between original and test results"""

import os
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from loguru import logger

warnings.filterwarnings("ignore")


class OutputComparison:
    """Class to handle comparison between original and test outputs"""

    def __init__(self, original_path, test_path):
        """Initialize with file paths"""
        self.original_path = original_path
        self.test_path = test_path
        self.original_df = None
        self.test_df = None
        self.comparison_results = {}

    def load_files(self):
        """Load both Excel files"""
        try:
            logger.info(f"Loading original file: {self.original_path}")
            self.original_df = pd.read_excel(self.original_path)
            logger.info(
                f"Original file loaded: {len(self.original_df)} rows, {len(self.original_df.columns)} columns"
            )

            logger.info(f"Loading test file: {self.test_path}")
            self.test_df = pd.read_excel(self.test_path)
            logger.info(
                f"Test file loaded: {len(self.test_df)} rows, {len(self.test_df.columns)} columns"
            )

            return True
        except Exception as e:
            logger.error(f"Error loading files: {str(e)}")
            return False

    def compare_structure(self):
        """Compare the structure of both dataframes"""
        results = {
            "row_count": {
                "original": len(self.original_df),
                "test": len(self.test_df),
                "match": len(self.original_df) == len(self.test_df),
            },
            "column_count": {
                "original": len(self.original_df.columns),
                "test": len(self.test_df.columns),
                "match": len(self.original_df.columns) == len(self.test_df.columns),
            },
            "columns": {
                "original": list(self.original_df.columns),
                "test": list(self.test_df.columns),
                "match": list(self.original_df.columns) == list(self.test_df.columns),
                "missing_in_test": list(
                    set(self.original_df.columns) - set(self.test_df.columns)
                ),
                "extra_in_test": list(
                    set(self.test_df.columns) - set(self.original_df.columns)
                ),
            },
        }

        self.comparison_results["structure"] = results
        return results

    def prepare_for_comparison(self):
        """Prepare dataframes for comparison by aligning them"""
        # Ensure both dataframes have the same columns
        common_columns = list(set(self.original_df.columns) & set(self.test_df.columns))

        if len(common_columns) < len(self.original_df.columns):
            logger.warning("Not all columns are present in both files")

        # Sort by API_WELL_NUMBER if it exists for consistent ordering
        if "API_WELL_NUMBER" in common_columns:
            self.original_df = self.original_df.sort_values(
                "API_WELL_NUMBER"
            ).reset_index(drop=True)
            self.test_df = self.test_df.sort_values("API_WELL_NUMBER").reset_index(
                drop=True
            )

        # Select only common columns for comparison
        self.original_df_aligned = self.original_df[common_columns]
        self.test_df_aligned = self.test_df[common_columns]

        return common_columns

    def compare_data(self):
        """Perform detailed cell-by-cell comparison"""
        common_columns = self.prepare_for_comparison()

        # Initialize results
        results = {
            "total_cells": 0,
            "matching_cells": 0,
            "different_cells": 0,
            "match_percentage": 0.0,
            "column_metrics": {},
            "differences": [],
        }

        # Ensure same number of rows for comparison
        min_rows = min(len(self.original_df_aligned), len(self.test_df_aligned))

        if min_rows == 0:
            logger.error("No rows to compare")
            self.comparison_results["data"] = results
            return results

        # Compare data column by column
        for col in common_columns:
            col_matches = 0
            col_differences = 0
            col_diff_details = []

            for idx in range(min_rows):
                original_val = self.original_df_aligned[col].iloc[idx]
                test_val = self.test_df_aligned[col].iloc[idx]

                # Handle different comparison types
                match = self._compare_values(original_val, test_val, col)

                if match:
                    col_matches += 1
                else:
                    col_differences += 1
                    # Record difference details
                    if (
                        len(col_diff_details) < 10
                    ):  # Limit to first 10 differences per column
                        api_num = (
                            self.original_df_aligned.get(
                                "API_WELL_NUMBER", pd.Series()
                            ).iloc[idx]
                            if "API_WELL_NUMBER" in self.original_df_aligned
                            else idx
                        )
                        col_diff_details.append(
                            {
                                "row": idx,
                                "api": api_num,
                                "original": original_val,
                                "test": test_val,
                            }
                        )

            # Store column metrics
            col_total = min_rows
            col_match_pct = (col_matches / col_total * 100) if col_total > 0 else 0

            results["column_metrics"][col] = {
                "total_cells": col_total,
                "matches": col_matches,
                "differences": col_differences,
                "match_percentage": round(col_match_pct, 2),
                "sample_differences": col_diff_details,
            }

            results["total_cells"] += col_total
            results["matching_cells"] += col_matches
            results["different_cells"] += col_differences

        # Calculate overall match percentage
        if results["total_cells"] > 0:
            results["match_percentage"] = round(
                (results["matching_cells"] / results["total_cells"]) * 100, 2
            )

        self.comparison_results["data"] = results
        return results

    def _compare_values(self, val1, val2, column_name):
        """Compare two values with appropriate logic based on data type"""
        # Handle NaN/None values
        if pd.isna(val1) and pd.isna(val2):
            return True
        if pd.isna(val1) or pd.isna(val2):
            return False

        # Handle date columns
        if "DATE" in column_name:
            try:
                # Convert to datetime if string
                if isinstance(val1, str):
                    val1 = pd.to_datetime(val1)
                if isinstance(val2, str):
                    val2 = pd.to_datetime(val2)
                return val1 == val2
            except:
                return str(val1) == str(val2)

        # Handle numeric columns with tolerance
        if column_name in [
            "DRILLING_DAYS",
            "COMPLETION_DAYS",
            "MAX_BH_TOTAL_MD",
            "MAX_WELL_BORE_TVD",
            "MAX_DRILL_FLUID_WGT",
            "WATER_DEPTH",
        ]:
            try:
                num1 = float(val1)
                num2 = float(val2)
                # Use small tolerance for floating point comparison
                return abs(num1 - num2) < 0.001
            except:
                return str(val1) == str(val2)

        # Default string comparison
        return str(val1).strip() == str(val2).strip()

    def generate_summary_report(self):
        """Generate a comprehensive comparison summary"""
        report = []
        report.append("# Drilling Completion Days Output Comparison Report")
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n## File Information")
        report.append(f"- **Original File:** {os.path.basename(self.original_path)}")
        report.append(f"- **Test File:** {os.path.basename(self.test_path)}")

        # Structure comparison
        if "structure" in self.comparison_results:
            struct = self.comparison_results["structure"]
            report.append("\n## Structure Comparison")
            report.append(
                f"- **Row Count:** Original: {struct['row_count']['original']}, "
                f"Test: {struct['row_count']['test']} "
                f"({'✅ MATCH' if struct['row_count']['match'] else '❌ DIFFERENT'})"
            )
            report.append(
                f"- **Column Count:** Original: {struct['column_count']['original']}, "
                f"Test: {struct['column_count']['test']} "
                f"({'✅ MATCH' if struct['column_count']['match'] else '❌ DIFFERENT'})"
            )

            if struct["columns"]["missing_in_test"]:
                report.append(
                    f"- **Missing Columns in Test:** {', '.join(struct['columns']['missing_in_test'])}"
                )
            if struct["columns"]["extra_in_test"]:
                report.append(
                    f"- **Extra Columns in Test:** {', '.join(struct['columns']['extra_in_test'])}"
                )

        # Data comparison
        if "data" in self.comparison_results:
            data = self.comparison_results["data"]
            report.append("\n## Data Comparison Summary")
            report.append(f"- **Total Cells Compared:** {data['total_cells']:,}")
            report.append(f"- **Matching Cells:** {data['matching_cells']:,}")
            report.append(f"- **Different Cells:** {data['different_cells']:,}")
            report.append(
                f"- **Overall Match Percentage:** {data['match_percentage']}%"
            )

            # Column-by-column results
            report.append("\n## Column-by-Column Analysis")
            report.append(
                "\n| Column | Total Cells | Matches | Differences | Match % |"
            )
            report.append("|--------|-------------|---------|-------------|---------|")

            for col, metrics in sorted(data["column_metrics"].items()):
                report.append(
                    f"| {col} | {metrics['total_cells']} | "
                    f"{metrics['matches']} | {metrics['differences']} | "
                    f"{metrics['match_percentage']}% |"
                )

            # Sample differences
            report.append("\n## Sample Differences (First 10 per column)")
            for col, metrics in data["column_metrics"].items():
                if metrics["sample_differences"]:
                    report.append(f"\n### {col}")
                    report.append("| Row | API Number | Original Value | Test Value |")
                    report.append("|-----|------------|----------------|------------|")
                    for diff in metrics["sample_differences"]:
                        api = diff["api"] if not pd.isna(diff["api"]) else "N/A"
                        report.append(
                            f"| {diff['row']} | {api} | {diff['original']} | {diff['test']} |"
                        )

        # Overall conclusion
        report.append("\n## Conclusion")
        if "data" in self.comparison_results:
            match_pct = self.comparison_results["data"]["match_percentage"]
            if match_pct == 100:
                report.append(
                    "✅ **PERFECT MATCH** - The test output matches the original output exactly!"
                )
            elif match_pct >= 95:
                report.append(
                    f"✅ **EXCELLENT MATCH** - {match_pct}% of cells match. Minor differences detected."
                )
            elif match_pct >= 90:
                report.append(
                    f"⚠️ **GOOD MATCH** - {match_pct}% of cells match. Some differences require review."
                )
            else:
                report.append(
                    f"❌ **SIGNIFICANT DIFFERENCES** - Only {match_pct}% of cells match. Investigation needed."
                )

        return "\n".join(report)


def main():
    """Main execution function"""
    # Define file paths
    original_file = "docs/modules/bsee/data/SME_Roy_attachments/2025-08-01/drilling_and_completion_days_by_api.xlsx"
    test_file = "tests/modules/bsee/analysis/2025-08-02-drilling-completion-output-validation/results/drilling_and_completion_days_by_api_validation.xlsx"

    # Get absolute paths
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../..")
    )
    original_path = os.path.join(project_root, original_file)
    test_path = os.path.join(project_root, test_file)

    logger.info("Starting output comparison")

    # Create comparison instance
    comparison = OutputComparison(original_path, test_path)

    # Load files
    if not comparison.load_files():
        logger.error("Failed to load files for comparison")
        return

    # Compare structure
    logger.info("Comparing file structure...")
    structure_results = comparison.compare_structure()

    # Compare data
    logger.info("Comparing data content...")
    data_results = comparison.compare_data()

    # Generate report
    logger.info("Generating comparison report...")
    report = comparison.generate_summary_report()

    # Save report
    report_path = os.path.join(
        os.path.dirname(test_path),
        f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"Comparison report saved to: {report_path}")

    # Print summary to console
    print("\n" + "=" * 50)
    print("COMPARISON SUMMARY")
    print("=" * 50)
    print(
        f"Row Count Match: {'YES' if structure_results['row_count']['match'] else 'NO'}"
    )
    print(
        f"Column Count Match: {'YES' if structure_results['column_count']['match'] else 'NO'}"
    )
    print(f"Overall Data Match: {data_results['match_percentage']}%")
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
