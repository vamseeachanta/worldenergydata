"""
Test suite for Strategic Markdown Report Generation System

This module tests the hierarchical report generation capabilities
optimized for handling 120+ wells without creating messy output.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    # Also need comparison result classes
    from advanced_comparison_engine import ComparisonResult, StatisticalSummary
    from strategic_report_generator import (
        ChartGenerator,
        ReportConfig,
        ReportSection,
        StrategicReportGenerator,
    )

    GENERATOR_AVAILABLE = True
except ImportError as e:
    GENERATOR_AVAILABLE = False
    print(f"Warning: Could not import strategic report generator: {e}")


@pytest.mark.skipif(
    not GENERATOR_AVAILABLE, reason="Strategic report generator not available"
)
class TestReportConfig:
    """Test report configuration class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ReportConfig()

        assert config.max_detailed_wells == 20
        assert config.summary_top_n == 10
        assert config.include_charts == True
        assert config.chart_format == "png"
        assert config.chart_dpi == 150
        assert config.enable_appendix == False
        assert config.confidence_level == 0.95

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ReportConfig(
            max_detailed_wells=15,
            summary_top_n=5,
            include_charts=False,
            chart_format="svg",
            enable_appendix=True,
        )

        assert config.max_detailed_wells == 15
        assert config.summary_top_n == 5
        assert config.include_charts == False
        assert config.chart_format == "svg"
        assert config.enable_appendix == True


@pytest.mark.skipif(
    not GENERATOR_AVAILABLE, reason="Strategic report generator not available"
)
class TestReportSection:
    """Test report section data structure."""

    def test_report_section_creation(self):
        """Test report section creation."""
        section = ReportSection(
            title="Test Section",
            content="Test content",
            level=3,
            include_in_toc=False,
            priority=5,
        )

        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert section.level == 3
        assert section.include_in_toc == False
        assert section.priority == 5

    def test_report_section_defaults(self):
        """Test report section default values."""
        section = ReportSection(title="Default Section", content="Default content")

        assert section.level == 2
        assert section.include_in_toc == True
        assert section.priority == 1


@pytest.mark.skipif(
    not GENERATOR_AVAILABLE, reason="Strategic report generator not available"
)
class TestChartGenerator:
    """Test chart generation functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return ReportConfig(
            include_charts=True,
            chart_format="png",
            chart_dpi=100,  # Lower DPI for faster tests
            results_directory=temp_dir,
        )

    @pytest.fixture
    def chart_generator(self, config):
        """Create chart generator instance."""
        return ChartGenerator(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample data for charts."""
        np.random.seed(42)
        lease_data = pd.Series(np.random.normal(45, 10, 50))
        api12_data = pd.Series(np.random.normal(47, 8, 50))
        return lease_data, api12_data

    def test_chart_generator_initialization(self, chart_generator):
        """Test chart generator initialization."""
        assert chart_generator.config is not None
        assert chart_generator.config.include_charts == True

    def test_distribution_comparison_chart(self, chart_generator, sample_data):
        """Test distribution comparison chart generation."""
        lease_data, api12_data = sample_data

        chart_path = chart_generator.create_distribution_comparison_chart(
            lease_data, api12_data, "Drilling Days"
        )

        assert chart_path != ""
        if not chart_path.startswith("data:image"):
            assert os.path.exists(chart_path)
            assert "drilling_days_distribution" in chart_path

    def test_scatter_correlation_chart(self, chart_generator, sample_data):
        """Test scatter correlation chart generation."""
        lease_data, api12_data = sample_data

        chart_path = chart_generator.create_scatter_correlation_chart(
            lease_data, api12_data, "Drilling Days"
        )

        assert chart_path != ""
        if not chart_path.startswith("data:image"):
            assert os.path.exists(chart_path)
            assert "drilling_days_correlation" in chart_path

    def test_difference_analysis_chart(self, chart_generator, sample_data):
        """Test difference analysis chart generation."""
        lease_data, api12_data = sample_data
        differences = api12_data - lease_data
        percentage_diffs = (differences / lease_data) * 100

        chart_path = chart_generator.create_difference_analysis_chart(
            differences, percentage_diffs, "Drilling Days"
        )

        assert chart_path != ""
        if not chart_path.startswith("data:image"):
            assert os.path.exists(chart_path)
            assert "drilling_days_differences" in chart_path

    def test_status_distribution_chart(self, chart_generator):
        """Test status distribution chart generation."""
        status_counts = pd.Series({"OK": 80, "REVIEW": 15, "ERROR": 5})

        chart_path = chart_generator.create_status_distribution_chart(status_counts)

        assert chart_path != ""
        if not chart_path.startswith("data:image"):
            assert os.path.exists(chart_path)
            assert "status_distribution" in chart_path

    def test_empty_data_handling(self, chart_generator):
        """Test chart generation with empty data."""
        empty_series = pd.Series([])

        chart_path = chart_generator.create_distribution_comparison_chart(
            empty_series, empty_series, "Test Metric"
        )

        assert chart_path == ""

    def test_charts_disabled(self, temp_dir):
        """Test chart generation when charts are disabled."""
        config = ReportConfig(include_charts=False, results_directory=temp_dir)
        chart_generator = ChartGenerator(config)

        lease_data = pd.Series([1, 2, 3, 4, 5])
        api12_data = pd.Series([2, 3, 4, 5, 6])

        chart_path = chart_generator.create_distribution_comparison_chart(
            lease_data, api12_data, "Test Metric"
        )

        assert chart_path == ""

    @patch("matplotlib.pyplot.close")
    def test_chart_cleanup(self, mock_close, chart_generator, sample_data):
        """Test that charts are properly cleaned up after generation."""
        lease_data, api12_data = sample_data

        chart_generator.create_distribution_comparison_chart(
            lease_data, api12_data, "Test Metric"
        )

        # Verify that plt.close was called to prevent memory leaks
        mock_close.assert_called()


@pytest.mark.skipif(
    not GENERATOR_AVAILABLE, reason="Strategic report generator not available"
)
class TestStrategicReportGenerator:
    """Test strategic report generator functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return ReportConfig(
            max_detailed_wells=10,
            summary_top_n=5,
            include_charts=False,  # Disable for faster tests
            enable_appendix=False,
            results_directory=temp_dir,
        )

    @pytest.fixture
    def generator(self, config):
        """Create report generator instance."""
        return StrategicReportGenerator(config)

    @pytest.fixture
    def sample_comparison_results(self):
        """Create sample comparison results."""
        results = []
        np.random.seed(42)

        for i in range(50):  # 50 wells for testing
            api12 = f"60812400{i:04d}"
            well_name = f"Well {i+1}"

            lease_drilling = np.random.normal(45, 10)
            api12_drilling = np.random.normal(47, 8)
            lease_completion = np.random.normal(15, 4)
            api12_completion = np.random.normal(16, 3)

            drilling_diff = api12_drilling - lease_drilling
            completion_diff = api12_completion - lease_completion
            drilling_pct_diff = (
                (drilling_diff / lease_drilling) * 100 if lease_drilling != 0 else 0
            )
            completion_pct_diff = (
                (completion_diff / lease_completion) * 100
                if lease_completion != 0
                else 0
            )

            # Determine status
            issues = 0
            outlier_flags = []

            if abs(drilling_diff) > 5:
                issues += 1
                outlier_flags.append("drilling_absolute_outlier")
            if abs(drilling_pct_diff) > 10:
                issues += 1
                outlier_flags.append("drilling_percentage_outlier")
            if abs(completion_diff) > 3:
                issues += 1
                outlier_flags.append("completion_absolute_outlier")

            if issues >= 2:
                status = "ERROR"
            elif issues >= 1:
                status = "REVIEW"
            else:
                status = "OK"

            result = ComparisonResult(
                api12=api12,
                well_name=well_name,
                lease_drilling_days=lease_drilling,
                api12_drilling_days=api12_drilling,
                lease_completion_days=lease_completion,
                api12_completion_days=api12_completion,
                drilling_diff=drilling_diff,
                completion_diff=completion_diff,
                drilling_pct_diff=drilling_pct_diff,
                completion_pct_diff=completion_pct_diff,
                overall_status=status,
                outlier_flags=outlier_flags,
                statistical_significance={
                    "drilling_z_score": 0.0,
                    "completion_z_score": 0.0,
                },
            )

            results.append(result)

        return results

    @pytest.fixture
    def sample_statistical_summary(self, sample_comparison_results):
        """Create sample statistical summary."""
        outlier_wells = [r.api12 for r in sample_comparison_results if r.outlier_flags]

        return StatisticalSummary(
            total_wells=len(sample_comparison_results),
            successful_matches=len(sample_comparison_results),
            drilling_days_stats={
                "lease_method": {"mean": 45.0, "std": 10.0},
                "api12_method": {"mean": 47.0, "std": 8.0},
                "statistical_tests": {"ttest": {"pvalue": 0.15, "significant": False}},
            },
            completion_days_stats={
                "lease_method": {"mean": 15.0, "std": 4.0},
                "api12_method": {"mean": 16.0, "std": 3.0},
                "statistical_tests": {"ttest": {"pvalue": 0.08, "significant": False}},
            },
            outlier_wells=outlier_wells,
            cluster_analysis={
                "method": "clustering",
                "outlier_count": len(outlier_wells),
            },
            correlation_analysis={"drilling_days": 0.85, "completion_days": 0.78},
            distribution_comparison={
                "drilling_outliers": {},
                "completion_outliers": {},
            },
        )

    @pytest.fixture
    def sample_processing_stats(self):
        """Create sample processing statistics."""
        return {
            "total_wells_analyzed": 50,
            "successful_comparisons": 50,
            "failed_comparisons": 0,
            "outliers_detected": 15,
            "significant_discrepancies": 5,
            "processing_time_seconds": 2.5,
        }

    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator.config is not None
        assert generator.chart_generator is not None
        assert len(generator.sections) == 0
        assert generator.metadata["total_wells"] == 0

    def test_results_to_dataframe_conversion(
        self, generator, sample_comparison_results
    ):
        """Test conversion of comparison results to DataFrame."""
        df = generator._results_to_dataframe(sample_comparison_results)

        assert len(df) == 50
        assert "API12" in df.columns
        assert "Status" in df.columns
        assert "Drilling_Diff" in df.columns
        assert "Completion_Diff" in df.columns

        # Check data integrity
        assert df["API12"].nunique() == 50  # All unique wells
        assert set(df["Status"].unique()).issubset({"OK", "REVIEW", "ERROR"})

    def test_executive_summary_generation(
        self,
        generator,
        sample_comparison_results,
        sample_statistical_summary,
        sample_processing_stats,
    ):
        """Test executive summary generation."""
        results_df = generator._results_to_dataframe(sample_comparison_results)

        generator._generate_executive_summary(
            results_df, sample_statistical_summary, sample_processing_stats
        )

        assert len(generator.sections) == 1
        section = generator.sections[0]
        assert section.title == "Executive Summary"
        assert "50 wells" in section.content
        assert "Key Performance Indicators" in section.content
        assert "Executive Recommendations" in section.content
        assert section.priority == 1

    def test_key_findings_generation(
        self, generator, sample_comparison_results, sample_statistical_summary
    ):
        """Test key findings generation."""
        results_df = generator._results_to_dataframe(sample_comparison_results)

        generator._generate_key_findings(results_df, sample_statistical_summary)

        assert len(generator.sections) == 1
        section = generator.sections[0]
        assert section.title == "Key Findings"
        assert "Method Agreement Analysis" in section.content
        assert "Outlier Detection Results" in section.content
        assert "Statistical Significance" in section.content

    def test_summary_tables_generation(self, generator, sample_comparison_results):
        """Test summary tables generation."""
        results_df = generator._results_to_dataframe(sample_comparison_results)

        generator._generate_summary_tables(results_df)

        assert len(generator.sections) == 1
        section = generator.sections[0]
        assert section.title == "Summary Tables"
        assert (
            "Top 5 Drilling Days Discrepancies" in section.content
        )  # Using summary_top_n=5
        assert "Top 5 Completion Days Discrepancies" in section.content
        assert "Method Comparison Statistics" in section.content

    def test_conditional_detailed_analysis_no_issues(self, generator):
        """Test detailed analysis when no wells need attention."""
        # Create results with all OK status
        ok_results = []
        for i in range(10):
            result = ComparisonResult(
                api12=f"60812400{i:04d}",
                well_name=f"Well {i+1}",
                lease_drilling_days=45.0,
                api12_drilling_days=46.0,
                lease_completion_days=15.0,
                api12_completion_days=15.5,
                drilling_diff=1.0,
                completion_diff=0.5,
                drilling_pct_diff=2.2,
                completion_pct_diff=3.3,
                overall_status="OK",
                outlier_flags=[],
                statistical_significance={},
            )
            ok_results.append(result)

        results_df = generator._results_to_dataframe(ok_results)
        generator._generate_conditional_detailed_analysis(results_df)

        assert len(generator.sections) == 1
        section = generator.sections[0]
        assert section.title == "Detailed Analysis"
        assert "Excellent News!" in section.content
        assert "No detailed analysis of problem wells is needed" in section.content

    def test_conditional_detailed_analysis_with_issues(
        self, generator, sample_comparison_results
    ):
        """Test detailed analysis when wells need attention."""
        results_df = generator._results_to_dataframe(sample_comparison_results)

        generator._generate_conditional_detailed_analysis(results_df)

        assert len(generator.sections) == 1
        section = generator.sections[0]
        assert section.title == "Detailed Analysis"

        # Should contain sections for REVIEW and ERROR wells
        review_count = len(results_df[results_df["Status"] == "REVIEW"])
        error_count = len(results_df[results_df["Status"] == "ERROR"])

        if review_count > 0:
            assert "Wells Requiring Review" in section.content
        if error_count > 0:
            assert "Wells with Errors" in section.content

    def test_appendix_generation_disabled(
        self, generator, sample_comparison_results, sample_statistical_summary
    ):
        """Test that appendix is not generated when disabled."""
        results_df = generator._results_to_dataframe(sample_comparison_results)

        generator._generate_appendix(results_df, sample_statistical_summary)

        # Should not add any sections since appendix is disabled in config
        assert len(generator.sections) == 0

    def test_appendix_generation_enabled(
        self, temp_dir, sample_comparison_results, sample_statistical_summary
    ):
        """Test appendix generation when enabled."""
        config = ReportConfig(enable_appendix=True, results_directory=temp_dir)
        generator = StrategicReportGenerator(config)

        results_df = generator._results_to_dataframe(sample_comparison_results)
        generator._generate_appendix(results_df, sample_statistical_summary)

        assert len(generator.sections) == 1
        section = generator.sections[0]
        assert section.title == "Appendix"
        assert "Complete Data Reference" in section.content
        assert "Statistical Test Details" in section.content
        assert "Methodology Notes" in section.content

    def test_table_of_contents_generation(self, generator):
        """Test table of contents generation."""
        # Add some test sections
        generator.sections = [
            ReportSection("Executive Summary", "Content 1", level=2, priority=1),
            ReportSection("Key Findings", "Content 2", level=2, priority=2),
            ReportSection("Statistical Analysis", "Content 3", level=2, priority=3),
        ]

        toc = generator._generate_table_of_contents(generator.sections)

        assert "## Table of Contents" in toc
        assert "Executive Summary" in toc
        assert "Key Findings" in toc
        assert "Statistical Analysis" in toc
        assert "#executive-summary" in toc

    def test_comprehensive_report_generation(
        self,
        generator,
        sample_comparison_results,
        sample_statistical_summary,
        sample_processing_stats,
    ):
        """Test comprehensive report generation."""
        report_path = generator.generate_comprehensive_report(
            sample_comparison_results,
            sample_statistical_summary,
            sample_processing_stats,
        )

        # Verify report file was created
        assert os.path.exists(report_path)
        assert report_path.endswith(".md")

        # Read and verify report content
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()

        # Check for key sections
        assert (
            "# Multiple Wells Drilling and Completion Days Comparison Report"
            in report_content
        )
        assert "## Table of Contents" in report_content
        assert "## Executive Summary" in report_content
        assert "## Key Findings" in report_content
        assert "## Statistical Analysis" in report_content
        assert "## Summary Tables" in report_content
        assert "## Detailed Analysis" in report_content

        # Check metadata
        assert "50" in report_content  # Total wells
        assert "Generated:" in report_content

        # Verify sections were generated
        assert len(generator.sections) >= 5  # At least the main sections

    def test_large_dataset_report_optimization(self, temp_dir):
        """Test report optimization for large datasets (120+ wells)."""
        config = ReportConfig(
            max_detailed_wells=15,  # Limit detailed wells
            summary_top_n=10,
            include_charts=False,
            enable_appendix=False,
            results_directory=temp_dir,
        )

        generator = StrategicReportGenerator(config)

        # Create 125 wells dataset
        large_results = []
        np.random.seed(123)

        for i in range(122):
            # Create mix of statuses with some problematic wells
            if i < 100:
                status = "OK"
                outlier_flags = []
                drilling_diff = np.random.normal(0, 2)
                completion_diff = np.random.normal(0, 1)
            elif i < 115:
                status = "REVIEW"
                outlier_flags = ["drilling_absolute_outlier"]
                drilling_diff = np.random.normal(7, 2)
                completion_diff = np.random.normal(1, 1)
            else:
                status = "ERROR"
                outlier_flags = [
                    "drilling_absolute_outlier",
                    "completion_percentage_outlier",
                ]
                drilling_diff = np.random.normal(12, 3)
                completion_diff = np.random.normal(5, 2)

            result = ComparisonResult(
                api12=f"60812400{i:04d}",
                well_name=f"Well {i+1}",
                lease_drilling_days=45.0,
                api12_drilling_days=45.0 + drilling_diff,
                lease_completion_days=15.0,
                api12_completion_days=15.0 + completion_diff,
                drilling_diff=drilling_diff,
                completion_diff=completion_diff,
                drilling_pct_diff=(drilling_diff / 45.0) * 100,
                completion_pct_diff=(completion_diff / 15.0) * 100,
                overall_status=status,
                outlier_flags=outlier_flags,
                statistical_significance={},
            )

            large_results.append(result)

        # Create corresponding statistical summary
        statistical_summary = StatisticalSummary(
            total_wells=125,
            successful_matches=125,
            drilling_days_stats={"lease_method": {}, "api12_method": {}},
            completion_days_stats={"lease_method": {}, "api12_method": {}},
            outlier_wells=[r.api12 for r in large_results if r.outlier_flags],
            cluster_analysis={},
            correlation_analysis={"drilling_days": 0.82, "completion_days": 0.75},
            distribution_comparison={},
        )

        processing_stats = {"total_wells_analyzed": 125, "processing_time_seconds": 5.2}

        # Generate report
        report_path = generator.generate_comprehensive_report(
            large_results, statistical_summary, processing_stats
        )

        # Verify report was generated
        assert os.path.exists(report_path)

        # Read report and verify it's not overwhelming
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()

        # Should mention 125 wells
        assert "125" in report_content

        # Should limit detailed wells to config limit
        lines = report_content.split("\n")
        report_length = len(lines)

        # Report should be manageable size despite 125 wells
        assert report_length < 500  # Should be concise, not overwhelming

        # Should contain strategic limiting language
        assert (
            "Showing top" in report_content
            or "Complete data available in exported CSV" in report_content
            or "wells requiring attention" in report_content
        )


@pytest.mark.skipif(
    not GENERATOR_AVAILABLE, reason="Strategic report generator not available"
)
class TestStrategicReportIntegration:
    """Integration tests for strategic report generation."""

    def test_120_plus_wells_report_generation(self):
        """Test report generation with 120+ wells without information overload."""
        config = ReportConfig(
            max_detailed_wells=20,
            summary_top_n=10,
            include_charts=False,  # Disable for performance
            enable_appendix=False,
        )

        generator = StrategicReportGenerator(config)

        # Create 124 wells (120+)
        np.random.seed(456)
        results = []

        for i in range(122):
            api12 = f"60812400{i:05d}"
            well_name = f"Well {i+1}"

            # Create realistic data with some systematic patterns
            lease_drilling = np.random.normal(50, 12)
            api12_drilling = np.random.normal(52, 10)  # Slight systematic difference
            lease_completion = np.random.normal(18, 5)
            api12_completion = np.random.normal(19, 4)  # Slight systematic difference

            drilling_diff = api12_drilling - lease_drilling
            completion_diff = api12_completion - lease_completion

            # Status determination
            issues = 0
            outlier_flags = []

            if abs(drilling_diff) > 8:
                issues += 1
                outlier_flags.append("drilling_outlier")
            if abs(completion_diff) > 4:
                issues += 1
                outlier_flags.append("completion_outlier")

            status = "ERROR" if issues >= 2 else "REVIEW" if issues >= 1 else "OK"

            result = ComparisonResult(
                api12=api12,
                well_name=well_name,
                lease_drilling_days=lease_drilling,
                api12_drilling_days=api12_drilling,
                lease_completion_days=lease_completion,
                api12_completion_days=api12_completion,
                drilling_diff=drilling_diff,
                completion_diff=completion_diff,
                drilling_pct_diff=(
                    (drilling_diff / lease_drilling) * 100 if lease_drilling != 0 else 0
                ),
                completion_pct_diff=(
                    (completion_diff / lease_completion) * 100
                    if lease_completion != 0
                    else 0
                ),
                overall_status=status,
                outlier_flags=outlier_flags,
                statistical_significance={},
            )

            results.append(result)

        # Create statistical summary
        outliers = [r.api12 for r in results if r.outlier_flags]
        statistical_summary = StatisticalSummary(
            total_wells=124,
            successful_matches=124,
            drilling_days_stats={
                "lease_method": {"mean": 50.0, "std": 12.0},
                "api12_method": {"mean": 52.0, "std": 10.0},
            },
            completion_days_stats={
                "lease_method": {"mean": 18.0, "std": 5.0},
                "api12_method": {"mean": 19.0, "std": 4.0},
            },
            outlier_wells=outliers,
            cluster_analysis={"method": "clustering", "outlier_count": len(outliers)},
            correlation_analysis={"drilling_days": 0.87, "completion_days": 0.82},
            distribution_comparison={},
        )

        processing_stats = {
            "total_wells_analyzed": 124,
            "successful_comparisons": 124,
            "processing_time_seconds": 3.8,
        }

        # Generate report
        report_path = generator.generate_comprehensive_report(
            results, statistical_summary, processing_stats
        )

        # Verify report generation
        assert os.path.exists(report_path)

        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()

        # Verify 124 wells are mentioned
        assert "124" in report_content

        # Verify strategic organization
        assert "## Executive Summary" in report_content
        assert "Key Performance Indicators" in report_content
        assert "## Summary Tables" in report_content
        assert "Top 10" in report_content  # Should limit to top N

        # Verify it avoids information overload
        lines = report_content.split("\n")

        # Should be well-structured but not overwhelming
        assert len(lines) < 600  # Reasonable length for 124 wells

        # Should have strategic limiting
        detailed_wells_shown = report_content.count(
            "60812400"
        )  # Count API12 occurrences
        assert (
            detailed_wells_shown <= 70
        )  # Should not list all 124 wells individually (allows for summary tables)

    def test_report_performance_large_dataset(self):
        """Test report generation performance with large dataset."""
        import time

        config = ReportConfig(
            max_detailed_wells=25,
            include_charts=False,  # Disable for performance testing
            enable_appendix=False,
        )

        generator = StrategicReportGenerator(config)

        # Create 150 wells dataset
        results = []
        for i in range(150):
            result = ComparisonResult(
                api12=f"60812400{i:05d}",
                well_name=f"Well {i+1}",
                lease_drilling_days=45.0,
                api12_drilling_days=47.0,
                lease_completion_days=15.0,
                api12_completion_days=16.0,
                drilling_diff=2.0,
                completion_diff=1.0,
                drilling_pct_diff=4.4,
                completion_pct_diff=6.7,
                overall_status="OK",
                outlier_flags=[],
                statistical_significance={},
            )
            results.append(result)

        statistical_summary = StatisticalSummary(
            total_wells=150,
            successful_matches=150,
            drilling_days_stats={},
            completion_days_stats={},
            outlier_wells=[],
            cluster_analysis={},
            correlation_analysis={"drilling_days": 0.9, "completion_days": 0.85},
            distribution_comparison={},
        )

        processing_stats = {"total_wells_analyzed": 150, "processing_time_seconds": 4.5}

        # Measure performance
        start_time = time.time()

        report_path = generator.generate_comprehensive_report(
            results, statistical_summary, processing_stats
        )

        end_time = time.time()
        generation_time = end_time - start_time

        # Verify performance
        assert os.path.exists(report_path)
        assert generation_time < 10  # Should complete within 10 seconds

        # Verify content quality despite size
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "150" in content
        assert "## Executive Summary" in content
        assert len(content.split("\n")) < 700  # Should remain manageable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
