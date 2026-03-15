"""
Markdown Report Generator for Drilling Days Comparison

This module provides functionality to generate markdown-formatted comparison reports
for drilling and completion days analysis between different BSEE methods.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarkdownReportGenerator:
    """
    Generates markdown-formatted comparison reports for drilling days analysis.

    Creates tables with the 5-column format specified in the requirements:
    - API Number
    - Drilling Days (Lease Method)
    - Drilling Days (API12 Method)
    - Completion Days (Lease Method)
    - Completion Days (API12 Method)

    Includes status flags and difference analysis.
    """

    def __init__(self):
        """Initialize the markdown report generator."""
        self.column_config = {
            "api_number": {"header": "API12 Number", "width": 15, "align": "center"},
            "drilling_lease": {
                "header": "Drilling Days (Lease)",
                "width": 20,
                "align": "center",
            },
            "drilling_api12": {
                "header": "Drilling Days (API12)",
                "width": 20,
                "align": "center",
            },
            "completion_lease": {
                "header": "Completion Days (Lease)",
                "width": 22,
                "align": "center",
            },
            "completion_api12": {
                "header": "Completion Days (API12)",
                "width": 22,
                "align": "center",
            },
        }

        logger.info("MarkdownReportGenerator initialized")

    def generate_comparison_table(self, comparison_data: pd.DataFrame) -> str:
        """
        Generate a markdown table from comparison data.

        Args:
            comparison_data: DataFrame with comparison results from ComparisonAnalyzer

        Returns:
            Formatted markdown table as string
        """
        if comparison_data.empty:
            return self._generate_empty_table_message()

        logger.info(f"Generating markdown table for {len(comparison_data)} wells")

        # Extract and format the data for the 5-column table
        table_data = self._prepare_table_data(comparison_data)

        # Generate the markdown table
        markdown_table = self._create_markdown_table(table_data)

        # Add status summary if status flags are available
        if "status_flag" in comparison_data.columns:
            status_summary = self._create_status_summary(comparison_data)
            markdown_table += "\n\n" + status_summary

        return markdown_table

    def save_comparison_report(
        self,
        comparison_data: pd.DataFrame,
        output_path: Union[str, Path],
        title: Optional[str] = None,
    ) -> None:
        """
        Save comparison report to a markdown file.

        Args:
            comparison_data: DataFrame with comparison results
            output_path: Path to save the markdown file
            title: Optional custom title for the report
        """
        output_path = Path(output_path)

        logger.info(f"Saving comparison report to: {output_path}")

        # Generate the complete report
        report_content = self._generate_complete_report(comparison_data, title)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info(f"Report saved successfully to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving report to {output_path}: {e}")
            raise

    def _prepare_table_data(self, comparison_data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for the 5-column markdown table format.

        Args:
            comparison_data: Raw comparison data from ComparisonAnalyzer

        Returns:
            DataFrame formatted for table generation
        """
        # Create the table with required columns
        table_data = pd.DataFrame()

        # API Number (required)
        table_data["api_number"] = comparison_data["api_number"]

        # Drilling Days columns
        table_data["drilling_lease"] = comparison_data.get("drilling_days_lease", "N/A")
        table_data["drilling_api12"] = comparison_data.get("drilling_days_api12", "N/A")

        # Completion Days columns
        table_data["completion_lease"] = comparison_data.get(
            "completion_days_lease", "N/A"
        )
        table_data["completion_api12"] = comparison_data.get(
            "completion_days_api12", "N/A"
        )

        # Format numeric values
        for col in [
            "drilling_lease",
            "drilling_api12",
            "completion_lease",
            "completion_api12",
        ]:
            table_data[col] = table_data[col].apply(self._format_numeric_value)

        # Format API numbers
        table_data["api_number"] = table_data["api_number"].apply(
            self._format_api_number
        )

        return table_data

    def _create_markdown_table(self, table_data: pd.DataFrame) -> str:
        """
        Create the actual markdown table with proper formatting.

        Args:
            table_data: Prepared data for table generation

        Returns:
            Formatted markdown table string
        """
        # Create header row
        headers = [
            self.column_config["api_number"]["header"],
            self.column_config["drilling_lease"]["header"],
            self.column_config["drilling_api12"]["header"],
            self.column_config["completion_lease"]["header"],
            self.column_config["completion_api12"]["header"],
        ]

        header_row = "| " + " | ".join(headers) + " |"

        # Create separator row
        separators = []
        for col_key in [
            "api_number",
            "drilling_lease",
            "drilling_api12",
            "completion_lease",
            "completion_api12",
        ]:
            config = self.column_config[col_key]
            if config["align"] == "center":
                separators.append(":" + "-" * (config["width"] - 2) + ":")
            elif config["align"] == "right":
                separators.append("-" * (config["width"] - 1) + ":")
            else:
                separators.append("-" * config["width"])

        separator_row = "| " + " | ".join(separators) + " |"

        # Create data rows
        data_rows = []
        for _, row in table_data.iterrows():
            formatted_row = []
            for col in [
                "api_number",
                "drilling_lease",
                "drilling_api12",
                "completion_lease",
                "completion_api12",
            ]:
                value = str(row[col])
                formatted_row.append(value)

            data_rows.append("| " + " | ".join(formatted_row) + " |")

        # Combine all parts
        table_lines = [header_row, separator_row] + data_rows

        return "\n".join(table_lines)

    def _create_status_summary(self, comparison_data: pd.DataFrame) -> str:
        """
        Create a status summary section for the report.

        Args:
            comparison_data: DataFrame with status_flag column

        Returns:
            Formatted status summary string
        """
        status_counts = comparison_data["status_flag"].value_counts()

        summary_lines = ["## Status Summary", ""]

        total_wells = len(comparison_data)

        for status in ["OK", "REVIEW", "ERROR"]:
            count = status_counts.get(status, 0)
            percentage = (count / total_wells) * 100 if total_wells > 0 else 0

            if status == "OK":
                emoji = "✅"
                description = "Within acceptable thresholds"
            elif status == "REVIEW":
                emoji = "⚠️"
                description = "Moderate discrepancies requiring review"
            else:  # ERROR
                emoji = "❌"
                description = "Significant discrepancies requiring investigation"

            summary_lines.append(
                f"- **{emoji} {status}**: {count} wells ({percentage:.1f}%) - {description}"
            )

        summary_lines.extend(["", f"**Total Wells Compared**: {total_wells}"])

        return "\n".join(summary_lines)

    def _generate_complete_report(
        self, comparison_data: pd.DataFrame, title: Optional[str] = None
    ) -> str:
        """
        Generate a complete markdown report with title, metadata, and table.

        Args:
            comparison_data: DataFrame with comparison results
            title: Optional custom title

        Returns:
            Complete formatted report string
        """
        # Default title if none provided
        if title is None:
            title = "Drilling and Completion Days Comparison Report"

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Report sections
        report_sections = [
            f"# {title}",
            "",
            f"**Generated**: {timestamp}",
            f"**Wells Analyzed**: {len(comparison_data)}",
            "",
            "## Comparison Table",
            "",
            "The following table compares drilling and completion days between the lease-based method and API12-based method:",
            "",
            self.generate_comparison_table(comparison_data),
        ]

        # Add analysis summary if we have difference data
        if "drilling_days_difference" in comparison_data.columns:
            analysis_summary = self._create_analysis_summary(comparison_data)
            report_sections.extend(["", analysis_summary])

        # Add methodology note
        methodology_note = self._create_methodology_note()
        report_sections.extend(["", methodology_note])

        return "\n".join(report_sections)

    def _create_analysis_summary(self, comparison_data: pd.DataFrame) -> str:
        """
        Create an analysis summary section.

        Args:
            comparison_data: DataFrame with difference calculations

        Returns:
            Formatted analysis summary string
        """
        summary_lines = ["## Analysis Summary", ""]

        # Drilling days analysis
        if "drilling_days_difference" in comparison_data.columns:
            drilling_diff = comparison_data["drilling_days_difference"].dropna()
            if len(drilling_diff) > 0:
                mean_diff = drilling_diff.mean()
                std_diff = drilling_diff.std()
                max_diff = drilling_diff.abs().max()

                summary_lines.extend(
                    [
                        "### Drilling Days Differences",
                        f"- **Mean Difference**: {mean_diff:.1f} days (Lease - API12)",
                        f"- **Standard Deviation**: {std_diff:.1f} days",
                        f"- **Maximum Absolute Difference**: {max_diff:.1f} days",
                        "",
                    ]
                )

        # Completion days analysis
        if "completion_days_difference" in comparison_data.columns:
            completion_diff = comparison_data["completion_days_difference"].dropna()
            if len(completion_diff) > 0:
                mean_diff = completion_diff.mean()
                std_diff = completion_diff.std()
                max_diff = completion_diff.abs().max()

                summary_lines.extend(
                    [
                        "### Completion Days Differences",
                        f"- **Mean Difference**: {mean_diff:.1f} days (Lease - API12)",
                        f"- **Standard Deviation**: {std_diff:.1f} days",
                        f"- **Maximum Absolute Difference**: {max_diff:.1f} days",
                        "",
                    ]
                )

        return "\n".join(summary_lines)

    def _create_methodology_note(self) -> str:
        """
        Create a methodology note section.

        Returns:
            Formatted methodology note string
        """
        return """## Methodology

**Data Sources:**
- **Lease Method**: Based on lease number approach using drilling_and_completion_days analysis
- **API12 Method**: Based on API12 number approach using well_api12 analysis

**Status Flag Criteria:**
- **✅ OK**: Differences within acceptable thresholds (≤5 days drilling, ≤3 days completion, ≤10% percentage)
- **⚠️ REVIEW**: Moderate differences requiring investigation (≤10 days drilling, ≤6 days completion, ≤20% percentage)
- **❌ ERROR**: Significant differences requiring immediate attention (>10 days drilling, >6 days completion, >20% percentage)

**Note**: Differences are calculated as (Lease Method - API12 Method). Positive values indicate lease method reports higher days."""

    def _format_numeric_value(self, value) -> str:
        """
        Format numeric values for display in the table.

        Args:
            value: Numeric value to format

        Returns:
            Formatted string representation
        """
        if pd.isna(value):
            return "N/A"

        try:
            numeric_value = float(value)
            if numeric_value == int(numeric_value):
                return str(int(numeric_value))
            else:
                return f"{numeric_value:.1f}"
        except (ValueError, TypeError):
            return str(value)

    def _format_api_number(self, api_number) -> str:
        """
        Format API numbers for consistent display.

        Args:
            api_number: API number to format

        Returns:
            Formatted API number string
        """
        if pd.isna(api_number):
            return "N/A"

        try:
            # Convert to string and ensure it's properly formatted
            api_str = str(int(float(api_number)))
            return api_str
        except (ValueError, TypeError):
            return str(api_number)

    def _generate_empty_table_message(self) -> str:
        """
        Generate message for when no comparison data is available.

        Returns:
            Empty table message
        """
        return """## Drilling and Completion Days Comparison

No matching wells found between the two methods for comparison.

**Possible reasons:**
- No common API numbers between datasets
- Data quality issues preventing matching
- Empty input datasets

Please verify that both methods have generated valid output data with matching API numbers."""
