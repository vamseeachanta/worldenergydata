"""
Strategic Markdown Report Generation System

This module provides hierarchical markdown report generation capabilities
optimized for handling 120+ wells without creating messy output.
"""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # Use non-interactive backend for testing
import base64
import io
import json
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Suppress matplotlib warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
plt.style.use("default")


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    max_detailed_wells: int = 20  # Maximum wells to show in detailed sections
    summary_top_n: int = 10  # Top N items to show in summary tables
    include_charts: bool = True  # Whether to include statistical charts
    chart_format: str = "png"  # Chart format ('png', 'svg', 'inline')
    chart_dpi: int = 150  # Chart DPI for high quality
    enable_appendix: bool = False  # Include full data appendix
    confidence_level: float = 0.95  # Statistical confidence level
    results_directory: str = (
        "tests/modules/bsee/analysis/multiple_wells_comparison_test/results"
    )


@dataclass
class ReportSection:
    """Data structure for report sections."""

    title: str
    content: str
    level: int = 2  # Markdown header level (1-6)
    include_in_toc: bool = True
    priority: int = 1  # Priority for ordering (1=highest)


class ChartGenerator:
    """Generate statistical charts for report inclusion."""

    def __init__(self, config: ReportConfig):
        """
        Initialize chart generator.

        Args:
            config: Report configuration
        """
        self.config = config
        # Set up matplotlib for consistent styling
        plt.rcParams["figure.figsize"] = (10, 6)
        plt.rcParams["font.size"] = 10
        plt.rcParams["axes.grid"] = True
        plt.rcParams["grid.alpha"] = 0.3

    def create_distribution_comparison_chart(
        self, lease_data: pd.Series, api12_data: pd.Series, metric_name: str
    ) -> str:
        """
        Create distribution comparison chart.

        Args:
            lease_data: Lease method data
            api12_data: API12 method data
            metric_name: Name of the metric

        Returns:
            str: Chart as base64 encoded string or file path
        """
        if not self.config.include_charts:
            return ""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Histogram comparison
        clean_lease = lease_data.dropna()
        clean_api12 = api12_data.dropna()

        if not clean_lease.empty and not clean_api12.empty:
            ax1.hist(
                clean_lease,
                bins=20,
                alpha=0.7,
                label="Lease Method",
                color="skyblue",
                density=True,
            )
            ax1.hist(
                clean_api12,
                bins=20,
                alpha=0.7,
                label="API12 Method",
                color="lightcoral",
                density=True,
            )
            ax1.set_xlabel(f"{metric_name} (Days)")
            ax1.set_ylabel("Density")
            ax1.set_title(f"{metric_name} Distribution Comparison")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Box plot comparison
            box_data = [clean_lease, clean_api12]
            box_labels = ["Lease Method", "API12 Method"]

            bp = ax2.boxplot(box_data, tick_labels=box_labels, patch_artist=True)
            bp["boxes"][0].set_facecolor("skyblue")
            bp["boxes"][1].set_facecolor("lightcoral")
            ax2.set_ylabel(f"{metric_name} (Days)")
            ax2.set_title(f"{metric_name} Box Plot Comparison")
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()

            return self._save_chart(
                fig, f'{metric_name.lower().replace(" ", "_")}_distribution'
            )

        return ""

    def create_scatter_correlation_chart(
        self, lease_data: pd.Series, api12_data: pd.Series, metric_name: str
    ) -> str:
        """
        Create scatter plot showing correlation between methods.

        Args:
            lease_data: Lease method data
            api12_data: API12 method data
            metric_name: Name of the metric

        Returns:
            str: Chart as base64 encoded string or file path
        """
        if not self.config.include_charts:
            return ""

        # Align data for scatter plot
        aligned_data = pd.DataFrame({"lease": lease_data, "api12": api12_data}).dropna()

        if len(aligned_data) < 3:
            return ""

        fig, ax = plt.subplots(figsize=(8, 8))

        # Scatter plot
        ax.scatter(
            aligned_data["lease"],
            aligned_data["api12"],
            alpha=0.6,
            color="steelblue",
            s=50,
        )

        # Add trend line
        if len(aligned_data) > 1:
            z = np.polyfit(aligned_data["lease"], aligned_data["api12"], 1)
            p = np.poly1d(z)
            ax.plot(
                aligned_data["lease"],
                p(aligned_data["lease"]),
                "r--",
                alpha=0.8,
                linewidth=2,
                label=f'Trend Line (R² = {np.corrcoef(aligned_data["lease"], aligned_data["api12"])[0,1]**2:.3f})',
            )

        # Add diagonal line (perfect correlation)
        min_val = min(aligned_data["lease"].min(), aligned_data["api12"].min())
        max_val = max(aligned_data["lease"].max(), aligned_data["api12"].max())
        ax.plot(
            [min_val, max_val],
            [min_val, max_val],
            "k--",
            alpha=0.5,
            label="Perfect Correlation",
        )

        ax.set_xlabel(f"{metric_name} - Lease Method (Days)")
        ax.set_ylabel(f"{metric_name} - API12 Method (Days)")
        ax.set_title(f"{metric_name} Method Correlation")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        return self._save_chart(
            fig, f'{metric_name.lower().replace(" ", "_")}_correlation'
        )

    def create_difference_analysis_chart(
        self, differences: pd.Series, percentage_diffs: pd.Series, metric_name: str
    ) -> str:
        """
        Create difference analysis chart.

        Args:
            differences: Absolute differences
            percentage_diffs: Percentage differences
            metric_name: Name of the metric

        Returns:
            str: Chart as base64 encoded string or file path
        """
        if not self.config.include_charts:
            return ""

        clean_diffs = differences.dropna()
        clean_pct_diffs = percentage_diffs.dropna()

        if clean_diffs.empty and clean_pct_diffs.empty:
            return ""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Absolute differences histogram
        if not clean_diffs.empty:
            ax1.hist(
                clean_diffs, bins=20, alpha=0.7, color="lightgreen", edgecolor="black"
            )
            ax1.axvline(
                clean_diffs.mean(),
                color="red",
                linestyle="--",
                label=f"Mean: {clean_diffs.mean():.2f}",
            )
            ax1.axvline(
                0, color="black", linestyle="-", alpha=0.5, label="Zero Difference"
            )
            ax1.set_xlabel(f"{metric_name} Difference (API12 - Lease) Days")
            ax1.set_ylabel("Frequency")
            ax1.set_title(f"{metric_name} Absolute Differences")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # Percentage differences histogram
        if not clean_pct_diffs.empty:
            ax2.hist(
                clean_pct_diffs, bins=20, alpha=0.7, color="orange", edgecolor="black"
            )
            ax2.axvline(
                clean_pct_diffs.mean(),
                color="red",
                linestyle="--",
                label=f"Mean: {clean_pct_diffs.mean():.1f}%",
            )
            ax2.axvline(
                0, color="black", linestyle="-", alpha=0.5, label="Zero Difference"
            )
            ax2.set_xlabel(f"{metric_name} Difference (%)")
            ax2.set_ylabel("Frequency")
            ax2.set_title(f"{metric_name} Percentage Differences")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        return self._save_chart(
            fig, f'{metric_name.lower().replace(" ", "_")}_differences'
        )

    def create_status_distribution_chart(self, status_counts: pd.Series) -> str:
        """
        Create status distribution pie chart.

        Args:
            status_counts: Series with status counts

        Returns:
            str: Chart as base64 encoded string or file path
        """
        if not self.config.include_charts or status_counts.empty:
            return ""

        fig, ax = plt.subplots(figsize=(8, 8))

        colors = {"OK": "lightgreen", "REVIEW": "orange", "ERROR": "lightcoral"}
        chart_colors = [
            colors.get(status, "lightgray") for status in status_counts.index
        ]

        wedges, texts, autotexts = ax.pie(
            status_counts.values,
            labels=status_counts.index,
            autopct="%1.1f%%",
            colors=chart_colors,
            startangle=90,
        )

        ax.set_title("Well Status Distribution")

        # Add count annotations
        for i, (wedge, text, autotext) in enumerate(zip(wedges, texts, autotexts)):
            count = status_counts.iloc[i]
            autotext.set_text(f"{autotext.get_text()}\n({count} wells)")

        plt.tight_layout()

        return self._save_chart(fig, "status_distribution")

    def _save_chart(self, fig: plt.Figure, filename: str) -> str:
        """Save chart and return reference."""
        if self.config.chart_format == "inline":
            # Return base64 encoded inline image
            buffer = io.BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=self.config.chart_dpi,
                bbox_inches="tight",
                facecolor="white",
            )
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            return f"data:image/png;base64,{image_base64}"
        else:
            # Save to file
            chart_path = (
                Path(self.config.results_directory)
                / f"{filename}.{self.config.chart_format}"
            )
            fig.savefig(
                chart_path,
                format=self.config.chart_format,
                dpi=self.config.chart_dpi,
                bbox_inches="tight",
                facecolor="white",
            )
            plt.close(fig)
            return str(chart_path)


class StrategicReportGenerator:
    """
    Strategic markdown report generator optimized for large datasets.
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize report generator.

        Args:
            config: Report configuration
        """
        self.config = config or ReportConfig()
        self.chart_generator = ChartGenerator(self.config)

        # Create results directory
        Path(self.config.results_directory).mkdir(parents=True, exist_ok=True)

        # Report sections storage
        self.sections: List[ReportSection] = []
        self.metadata = {
            "generation_time": None,
            "total_wells": 0,
            "report_version": "1.0.0",
        }

    def generate_comprehensive_report(
        self,
        comparison_results: List[Any],
        statistical_summary: Any,
        processing_stats: Dict[str, Any],
    ) -> str:
        """
        Generate comprehensive markdown report for multiple wells comparison.

        Args:
            comparison_results: List of comparison results
            statistical_summary: Statistical summary object
            processing_stats: Processing statistics

        Returns:
            str: Path to generated markdown report
        """
        self.metadata["generation_time"] = datetime.now()
        self.metadata["total_wells"] = len(comparison_results)

        # Convert results to DataFrame for easier manipulation
        results_df = self._results_to_dataframe(comparison_results)

        # Generate all sections
        self._generate_executive_summary(
            results_df, statistical_summary, processing_stats
        )
        self._generate_key_findings(results_df, statistical_summary)
        self._generate_statistical_analysis(results_df, statistical_summary)
        self._generate_summary_tables(results_df)
        self._generate_conditional_detailed_analysis(results_df)

        if self.config.enable_appendix:
            self._generate_appendix(results_df, statistical_summary)

        # Compile final report
        report_content = self._compile_report()

        # Save report
        timestamp = self.metadata["generation_time"].strftime("%Y%m%d_%H%M%S")
        report_path = (
            Path(self.config.results_directory)
            / f"strategic_comparison_report_{timestamp}.md"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return str(report_path)

    def _results_to_dataframe(self, comparison_results: List[Any]) -> pd.DataFrame:
        """Convert comparison results to DataFrame."""
        data = []
        for result in comparison_results:
            data.append(
                {
                    "API12": result.api12,
                    "Well_Name": result.well_name,
                    "Lease_Drilling_Days": result.lease_drilling_days,
                    "API12_Drilling_Days": result.api12_drilling_days,
                    "Lease_Completion_Days": result.lease_completion_days,
                    "API12_Completion_Days": result.api12_completion_days,
                    "Drilling_Diff": result.drilling_diff,
                    "Completion_Diff": result.completion_diff,
                    "Drilling_Pct_Diff": result.drilling_pct_diff,
                    "Completion_Pct_Diff": result.completion_pct_diff,
                    "Status": result.overall_status,
                    "Outlier_Flags": (
                        ",".join(result.outlier_flags) if result.outlier_flags else ""
                    ),
                }
            )

        return pd.DataFrame(data)

    def _generate_executive_summary(
        self,
        results_df: pd.DataFrame,
        statistical_summary: Any,
        processing_stats: Dict[str, Any],
    ):
        """Generate executive summary section."""
        total_wells = len(results_df)
        successful_matches = statistical_summary.successful_matches
        match_rate = (successful_matches / total_wells) * 100 if total_wells > 0 else 0

        status_counts = results_df["Status"].value_counts()
        ok_wells = status_counts.get("OK", 0)
        review_wells = status_counts.get("REVIEW", 0)
        error_wells = status_counts.get("ERROR", 0)

        processing_time = processing_stats.get("processing_time_seconds", 0)

        content = f"""
## Executive Summary

### Overview
This report presents a comprehensive comparison analysis of drilling and completion days between lease-based and API12-based calculation methods across **{total_wells} wells**. The analysis was conducted using advanced statistical methods and automated outlier detection to ensure data quality and reliability.

### Key Performance Indicators

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Total Wells Analyzed** | {total_wells:,} | Complete dataset coverage |
| **Successful Matches** | {successful_matches:,} ({match_rate:.1f}%) | High data alignment |
| **Wells with OK Status** | {ok_wells:,} ({(ok_wells/total_wells)*100:.1f}%) | {"Excellent" if (ok_wells/total_wells) > 0.8 else "Good" if (ok_wells/total_wells) > 0.6 else "Needs Review"} agreement |
| **Wells Requiring Review** | {review_wells:,} ({(review_wells/total_wells)*100:.1f}%) | Minor discrepancies detected |
| **Wells with Errors** | {error_wells:,} ({(error_wells/total_wells)*100:.1f}%) | Significant discrepancies |
| **Processing Time** | {processing_time:.2f} seconds | Efficient analysis |

### Executive Recommendations

"""

        # Add recommendations based on analysis
        if (ok_wells / total_wells) > 0.8:
            content += "✅ **High Confidence**: Both methods show excellent agreement. Proceed with confidence in either method.\n\n"
        elif (error_wells / total_wells) > 0.2:
            content += "⚠️ **Investigation Required**: Significant discrepancies detected. Review methodology and data sources.\n\n"
        else:
            content += "📊 **Standard Review**: Normal variation detected. Focus on wells requiring review for optimization.\n\n"

        self.sections.append(
            ReportSection(
                title="Executive Summary", content=content, level=2, priority=1
            )
        )

    def _generate_key_findings(
        self, results_df: pd.DataFrame, statistical_summary: Any
    ):
        """Generate key findings section."""
        # Calculate key metrics
        drilling_diffs = results_df["Drilling_Diff"].dropna()
        completion_diffs = results_df["Completion_Diff"].dropna()

        mean_drilling_diff = drilling_diffs.mean() if not drilling_diffs.empty else 0
        mean_completion_diff = (
            completion_diffs.mean() if not completion_diffs.empty else 0
        )

        outlier_count = len(statistical_summary.outlier_wells)
        correlation_drilling = statistical_summary.correlation_analysis.get(
            "drilling_days", 0
        )
        correlation_completion = statistical_summary.correlation_analysis.get(
            "completion_days", 0
        )

        content = f"""
## Key Findings

### Method Agreement Analysis

**Drilling Days Comparison:**
- Average difference: **{mean_drilling_diff:+.2f} days** (API12 vs Lease method)
- Correlation coefficient: **{correlation_drilling:.3f}** ({"Strong" if abs(correlation_drilling) > 0.8 else "Moderate" if abs(correlation_drilling) > 0.5 else "Weak"} correlation)
- Wells within 5-day agreement: **{(abs(drilling_diffs) <= 5).sum():,} wells** ({((abs(drilling_diffs) <= 5).sum() / len(drilling_diffs) * 100):.1f}%)

**Completion Days Comparison:**
- Average difference: **{mean_completion_diff:+.2f} days** (API12 vs Lease method)
- Correlation coefficient: **{correlation_completion:.3f}** ({"Strong" if abs(correlation_completion) > 0.8 else "Moderate" if abs(correlation_completion) > 0.5 else "Weak"} correlation)
- Wells within 2-day agreement: **{(abs(completion_diffs) <= 2).sum():,} wells** ({((abs(completion_diffs) <= 2).sum() / len(completion_diffs) * 100):.1f}%)

### Outlier Detection Results

- **Total outliers identified:** {outlier_count:,} wells ({(outlier_count / len(results_df) * 100):.1f}% of dataset)
- **Systematic bias detection:** {"Detected" if abs(mean_drilling_diff) > 3 or abs(mean_completion_diff) > 2 else "Not detected"}
- **Data quality assessment:** {"High" if outlier_count / len(results_df) < 0.1 else "Medium" if outlier_count / len(results_df) < 0.2 else "Requires Review"}

### Statistical Significance

"""

        # Add statistical test results if available
        if (
            hasattr(statistical_summary, "drilling_days_stats")
            and "statistical_tests" in statistical_summary.drilling_days_stats
        ):
            drilling_tests = statistical_summary.drilling_days_stats[
                "statistical_tests"
            ]
            if "ttest" in drilling_tests:
                ttest_result = drilling_tests["ttest"]
                content += f"- **T-test (Drilling Days):** {'Significant' if ttest_result.get('significant', False) else 'Not significant'} difference (p-value: {ttest_result.get('pvalue', 'N/A'):.4f})\n"

        if (
            hasattr(statistical_summary, "completion_days_stats")
            and "statistical_tests" in statistical_summary.completion_days_stats
        ):
            completion_tests = statistical_summary.completion_days_stats[
                "statistical_tests"
            ]
            if "ttest" in completion_tests:
                ttest_result = completion_tests["ttest"]
                content += f"- **T-test (Completion Days):** {'Significant' if ttest_result.get('significant', False) else 'Not significant'} difference (p-value: {ttest_result.get('pvalue', 'N/A'):.4f})\n"

        content += "\n"

        self.sections.append(
            ReportSection(title="Key Findings", content=content, level=2, priority=2)
        )

    def _generate_statistical_analysis(
        self, results_df: pd.DataFrame, statistical_summary: Any
    ):
        """Generate statistical analysis section with charts."""
        content = """
## Statistical Analysis

This section provides detailed statistical analysis of the comparison results, including distribution comparisons and correlation analysis.

### Distribution Analysis

"""

        # Generate distribution charts
        lease_drilling = results_df["Lease_Drilling_Days"].dropna()
        api12_drilling = results_df["API12_Drilling_Days"].dropna()
        lease_completion = results_df["Lease_Completion_Days"].dropna()
        api12_completion = results_df["API12_Completion_Days"].dropna()

        # Drilling days distribution chart
        drilling_chart = self.chart_generator.create_distribution_comparison_chart(
            lease_drilling, api12_drilling, "Drilling Days"
        )
        if drilling_chart:
            if drilling_chart.startswith("data:image"):
                content += (
                    f"![Drilling Days Distribution Comparison]({drilling_chart})\n\n"
                )
            else:
                content += (
                    f"![Drilling Days Distribution Comparison]({drilling_chart})\n\n"
                )

        # Completion days distribution chart
        completion_chart = self.chart_generator.create_distribution_comparison_chart(
            lease_completion, api12_completion, "Completion Days"
        )
        if completion_chart:
            if completion_chart.startswith("data:image"):
                content += f"![Completion Days Distribution Comparison]({completion_chart})\n\n"
            else:
                content += f"![Completion Days Distribution Comparison]({completion_chart})\n\n"

        content += """
### Correlation Analysis

"""

        # Correlation scatter plots
        drilling_scatter = self.chart_generator.create_scatter_correlation_chart(
            lease_drilling, api12_drilling, "Drilling Days"
        )
        if drilling_scatter:
            if drilling_scatter.startswith("data:image"):
                content += f"![Drilling Days Correlation]({drilling_scatter})\n\n"
            else:
                content += f"![Drilling Days Correlation]({drilling_scatter})\n\n"

        completion_scatter = self.chart_generator.create_scatter_correlation_chart(
            lease_completion, api12_completion, "Completion Days"
        )
        if completion_scatter:
            if completion_scatter.startswith("data:image"):
                content += f"![Completion Days Correlation]({completion_scatter})\n\n"
            else:
                content += f"![Completion Days Correlation]({completion_scatter})\n\n"

        content += """
### Difference Analysis

"""

        # Difference analysis charts
        drilling_diffs = results_df["Drilling_Diff"].dropna()
        drilling_pct_diffs = results_df["Drilling_Pct_Diff"].dropna()
        completion_diffs = results_df["Completion_Diff"].dropna()
        completion_pct_diffs = results_df["Completion_Pct_Diff"].dropna()

        drilling_diff_chart = self.chart_generator.create_difference_analysis_chart(
            drilling_diffs, drilling_pct_diffs, "Drilling Days"
        )
        if drilling_diff_chart:
            if drilling_diff_chart.startswith("data:image"):
                content += f"![Drilling Days Differences]({drilling_diff_chart})\n\n"
            else:
                content += f"![Drilling Days Differences]({drilling_diff_chart})\n\n"

        completion_diff_chart = self.chart_generator.create_difference_analysis_chart(
            completion_diffs, completion_pct_diffs, "Completion Days"
        )
        if completion_diff_chart:
            if completion_diff_chart.startswith("data:image"):
                content += (
                    f"![Completion Days Differences]({completion_diff_chart})\n\n"
                )
            else:
                content += (
                    f"![Completion Days Differences]({completion_diff_chart})\n\n"
                )

        # Status distribution
        status_counts = results_df["Status"].value_counts()
        status_chart = self.chart_generator.create_status_distribution_chart(
            status_counts
        )
        if status_chart:
            if status_chart.startswith("data:image"):
                content += f"![Status Distribution]({status_chart})\n\n"
            else:
                content += f"![Status Distribution]({status_chart})\n\n"

        self.sections.append(
            ReportSection(
                title="Statistical Analysis", content=content, level=2, priority=3
            )
        )

    def _generate_summary_tables(self, results_df: pd.DataFrame):
        """Generate summary comparison tables."""
        content = f"""
## Summary Tables

### Top {self.config.summary_top_n} Drilling Days Discrepancies

"""

        # Top drilling days discrepancies
        top_drilling = results_df.nlargest(self.config.summary_top_n, "Drilling_Diff")[
            [
                "API12",
                "Well_Name",
                "Lease_Drilling_Days",
                "API12_Drilling_Days",
                "Drilling_Diff",
                "Status",
            ]
        ].round(2)

        if not top_drilling.empty:
            content += self._dataframe_to_markdown(top_drilling)
            content += "\n\n"

        content += f"""
### Top {self.config.summary_top_n} Completion Days Discrepancies

"""

        # Top completion days discrepancies
        top_completion = results_df.nlargest(
            self.config.summary_top_n, "Completion_Diff"
        )[
            [
                "API12",
                "Well_Name",
                "Lease_Completion_Days",
                "API12_Completion_Days",
                "Completion_Diff",
                "Status",
            ]
        ].round(
            2
        )

        if not top_completion.empty:
            content += self._dataframe_to_markdown(top_completion)
            content += "\n\n"

        # Method comparison statistics
        content += """
### Method Comparison Statistics

| Metric | Lease Method | API12 Method | Difference |
|--------|--------------|--------------|------------|
"""

        lease_drilling_mean = results_df["Lease_Drilling_Days"].mean()
        api12_drilling_mean = results_df["API12_Drilling_Days"].mean()
        lease_completion_mean = results_df["Lease_Completion_Days"].mean()
        api12_completion_mean = results_df["API12_Completion_Days"].mean()

        content += f"| **Avg Drilling Days** | {lease_drilling_mean:.1f} | {api12_drilling_mean:.1f} | {api12_drilling_mean - lease_drilling_mean:+.1f} |\n"
        content += f"| **Avg Completion Days** | {lease_completion_mean:.1f} | {api12_completion_mean:.1f} | {api12_completion_mean - lease_completion_mean:+.1f} |\n"

        lease_drilling_std = results_df["Lease_Drilling_Days"].std()
        api12_drilling_std = results_df["API12_Drilling_Days"].std()
        lease_completion_std = results_df["Lease_Completion_Days"].std()
        api12_completion_std = results_df["API12_Completion_Days"].std()

        content += f"| **Drilling Days Std Dev** | {lease_drilling_std:.1f} | {api12_drilling_std:.1f} | {api12_drilling_std - lease_drilling_std:+.1f} |\n"
        content += f"| **Completion Days Std Dev** | {lease_completion_std:.1f} | {api12_completion_std:.1f} | {api12_completion_std - lease_completion_std:+.1f} |\n"

        content += "\n"

        self.sections.append(
            ReportSection(title="Summary Tables", content=content, level=2, priority=4)
        )

    def _generate_conditional_detailed_analysis(self, results_df: pd.DataFrame):
        """Generate conditional detailed analysis (only for wells requiring attention)."""
        # Filter wells that need attention
        attention_wells = results_df[results_df["Status"].isin(["REVIEW", "ERROR"])]

        if attention_wells.empty:
            content = """
## Detailed Analysis

**Excellent News!** All wells show acceptable agreement between methods. No detailed analysis of problem wells is needed.

### Quality Assurance Summary
- All wells meet quality thresholds
- No systematic issues detected
- Both methods are performing consistently

"""
        else:
            content = f"""
## Detailed Analysis

This section focuses on the **{len(attention_wells)} wells** that require attention, avoiding information overload from the full dataset.

### Wells Requiring Review ({len(attention_wells[attention_wells['Status'] == 'REVIEW'])} wells)

Wells with minor discrepancies that should be reviewed:

"""

            review_wells = attention_wells[attention_wells["Status"] == "REVIEW"].head(
                self.config.max_detailed_wells
            )
            if not review_wells.empty:
                review_table = review_wells[
                    [
                        "API12",
                        "Well_Name",
                        "Drilling_Diff",
                        "Completion_Diff",
                        "Outlier_Flags",
                    ]
                ].round(2)
                content += self._dataframe_to_markdown(review_table)
                content += "\n\n"

            error_wells = attention_wells[attention_wells["Status"] == "ERROR"]
            if not error_wells.empty:
                content += f"""
### Wells with Errors ({len(error_wells)} wells)

Wells with significant discrepancies requiring immediate investigation:

"""

                error_table = error_wells.head(self.config.max_detailed_wells)[
                    [
                        "API12",
                        "Well_Name",
                        "Drilling_Diff",
                        "Completion_Diff",
                        "Outlier_Flags",
                    ]
                ].round(2)
                content += self._dataframe_to_markdown(error_table)
                content += "\n\n"

            if len(attention_wells) > self.config.max_detailed_wells:
                content += f"""
### Additional Wells

*Note: Showing top {self.config.max_detailed_wells} wells requiring attention.
Total wells needing review: {len(attention_wells)}.
Complete data available in exported CSV files.*

"""

        self.sections.append(
            ReportSection(
                title="Detailed Analysis", content=content, level=2, priority=5
            )
        )

    def _generate_appendix(self, results_df: pd.DataFrame, statistical_summary: Any):
        """Generate optional appendix with complete data."""
        if not self.config.enable_appendix:
            return

        content = """
## Appendix: Complete Data Reference

### Full Dataset Summary

"""

        content += f"- **Total Wells:** {len(results_df):,}\n"
        content += f"- **Data Completeness:** {(1 - results_df.isnull().sum().sum() / (len(results_df) * len(results_df.columns))) * 100:.1f}%\n"

        # Handle generation_time safely
        if self.metadata.get("generation_time"):
            content += f"- **Analysis Date:** {self.metadata['generation_time'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        else:
            from datetime import datetime

            content += f"- **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        content += """
### Statistical Test Details

"""

        # Add detailed statistical test results if available
        if hasattr(statistical_summary, "drilling_days_stats"):
            content += "**Drilling Days Statistical Tests:**\n"
            drilling_stats = statistical_summary.drilling_days_stats
            if "statistical_tests" in drilling_stats:
                tests = drilling_stats["statistical_tests"]
                for test_name, test_results in tests.items():
                    if isinstance(test_results, dict) and "pvalue" in test_results:
                        content += f"- {test_name.title()}: p-value = {test_results['pvalue']:.6f}, "
                        content += (
                            f"significant = {test_results.get('significant', False)}\n"
                        )
            content += "\n"

        content += """
### Data Export Information

Complete datasets have been exported to CSV files for detailed analysis:
- `strategic_comparison_detailed_YYYYMMDD_HHMMSS.csv` - Complete well-by-well comparison
- `statistical_summary_YYYYMMDD_HHMMSS.json` - Detailed statistical results

### Methodology Notes

This analysis used advanced statistical methods including:
- Z-score and IQR-based outlier detection
- Two-sample t-tests and Mann-Whitney U tests
- Correlation analysis and effect size calculations
- DBSCAN clustering for anomaly detection

"""

        self.sections.append(
            ReportSection(title="Appendix", content=content, level=2, priority=10)
        )

    def _compile_report(self) -> str:
        """Compile all sections into final report."""
        # Sort sections by priority
        self.sections.sort(key=lambda x: x.priority)

        # Generate table of contents
        toc_sections = [s for s in self.sections if s.include_in_toc]
        toc = self._generate_table_of_contents(toc_sections)

        # Header
        header = f"""# Multiple Wells Drilling and Completion Days Comparison Report

> **Generated:** {self.metadata['generation_time'].strftime('%Y-%m-%d %H:%M:%S')}
> **Total Wells Analyzed:** {self.metadata['total_wells']:,}
> **Report Version:** {self.metadata['report_version']}

---

{toc}

---

"""

        # Compile sections
        report_content = header
        for section in self.sections:
            report_content += section.content
            report_content += "\n---\n\n"

        # Footer
        footer = f"""
## Report Generation Details

- **Analysis Engine:** Strategic Markdown Report Generator v{self.metadata['report_version']}
- **Generation Time:** {self.metadata['generation_time'].strftime('%Y-%m-%d %H:%M:%S')}
- **Configuration:** Max detailed wells = {self.config.max_detailed_wells}, Charts enabled = {self.config.include_charts}
- **Quality Assurance:** Automated statistical validation and outlier detection applied

---

*This report was generated automatically by the WorldEnergyData analysis framework.*
"""

        report_content += footer

        return report_content

    def _generate_table_of_contents(self, sections: List[ReportSection]) -> str:
        """Generate table of contents."""
        toc = "## Table of Contents\n\n"

        for section in sections:
            indent = "  " * (section.level - 2)
            anchor = section.title.lower().replace(" ", "-").replace(":", "")
            toc += f"{indent}- [{section.title}](#{anchor})\n"

        return toc

    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to markdown table format."""
        if df.empty:
            return ""

        # Get column names
        columns = list(df.columns)

        # Create header row
        header = "| " + " | ".join(columns) + " |"

        # Create separator row
        separator = "|" + "|".join([" --- " for _ in columns]) + "|"

        # Create data rows
        rows = []
        for _, row in df.iterrows():
            row_values = []
            for col in columns:
                value = row[col]
                if pd.isna(value):
                    row_values.append("")
                elif isinstance(value, float):
                    row_values.append(f"{value:.2f}")
                else:
                    row_values.append(str(value))
            rows.append("| " + " | ".join(row_values) + " |")

        # Combine all parts
        markdown_table = "\n".join([header, separator] + rows)
        return markdown_table


if __name__ == "__main__":
    # Example usage
    config = ReportConfig(
        max_detailed_wells=15,
        summary_top_n=10,
        include_charts=True,
        enable_appendix=False,
    )

    generator = StrategicReportGenerator(config)

    print("Strategic Report Generator initialized successfully!")
    print(
        f"Configuration: max_detailed_wells={config.max_detailed_wells}, include_charts={config.include_charts}"
    )
