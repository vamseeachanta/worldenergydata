"""
Test module for report generation functions in API12 drilling completion analysis.

This module tests the functionality for generating comprehensive analysis reports
comparing the lease-based and API12-based drilling completion methodologies.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest


class TestReportGeneration:
    """Test class for report generation functionality."""

    @pytest.fixture
    def sample_comparison_data(self):
        """Sample comparison data for testing report generation."""
        return pd.DataFrame(
            {
                "API12": [608124010400, 608124004400, 608124003100, 608124001600],
                "field_name": ["Stones", "St Malo", "Jack", "Cascade"],
                "well_name": ["SN208", "001", "003", "002"],
                "lease_drilling_days": [565, 2, 230, 74],
                "api12_drilling_days": [69, 0, 109, 137],
                "drilling_diff": [496, 2, 121, -63],
                "lease_completion_days": [93, 0, 18, 120],
                "api12_completion_days": [80, 0, 0, 0],
                "completion_diff": [13, 0, 18, 120],
                "total_diff": [509, 2, 139, 183],
            }
        )

    @pytest.fixture
    def sample_methodology_data(self):
        """Sample methodology data for testing."""
        return {
            "lease_method": {
                "approach": "Timeline-based with gap analysis",
                "gap_threshold_drilling": 300,
                "gap_threshold_completion": 8,
                "data_sources": ["WAR main", "Boreholes", "Properties", "Leases"],
            },
            "api12_method": {
                "approach": "Milestone-based phase calculation",
                "framework": "WellRigDays integration",
                "data_sources": [
                    "Well data structure",
                    "WellRigDays",
                    "Directional surveys",
                ],
            },
        }

    def test_generate_executive_summary(
        self, sample_comparison_data, sample_methodology_data
    ):
        """Test generation of executive summary section."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            generate_executive_summary,
        )

        summary = generate_executive_summary(
            sample_comparison_data, sample_methodology_data
        )

        assert isinstance(summary, dict)
        assert "total_wells_analyzed" in summary
        assert "fields_analyzed" in summary
        assert "methodology_comparison" in summary
        assert "key_findings" in summary

        # Verify statistics
        assert summary["total_wells_analyzed"] == 4
        assert len(summary["fields_analyzed"]) == 4

        print("Executive Summary Generated:")
        print(f"  Total wells: {summary['total_wells_analyzed']}")
        print(f"  Fields: {summary['fields_analyzed']}")
        print(f"  Key findings: {len(summary['key_findings'])}")

    def test_analyze_calculation_differences(self, sample_comparison_data):
        """Test analysis of calculation differences between methods."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            analyze_calculation_differences,
        )

        differences = analyze_calculation_differences(sample_comparison_data)

        assert isinstance(differences, dict)
        assert "drilling_differences" in differences
        assert "completion_differences" in differences
        assert "extreme_cases" in differences
        assert "statistical_summary" in differences

        # Verify extreme cases identification
        extreme_cases = differences["extreme_cases"]
        assert "highest_drilling_diff" in extreme_cases
        assert "lowest_drilling_diff" in extreme_cases
        assert "highest_completion_diff" in extreme_cases

        print("Calculation Differences Analysis:")
        print(
            f"  Highest drilling difference: {extreme_cases['highest_drilling_diff']['diff']} days"
        )
        print(
            f"  Lowest drilling difference: {extreme_cases['lowest_drilling_diff']['diff']} days"
        )
        print(
            f"  Highest completion difference: {extreme_cases['highest_completion_diff']['diff']} days"
        )

    def test_generate_field_by_field_analysis(self, sample_comparison_data):
        """Test generation of field-by-field analysis."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            generate_field_analysis,
        )

        field_analysis = generate_field_analysis(sample_comparison_data)

        assert isinstance(field_analysis, dict)
        assert len(field_analysis) > 0

        # Check each field has required analysis
        for field_name, analysis in field_analysis.items():
            assert "wells_count" in analysis
            assert "average_drilling_diff" in analysis
            assert "average_completion_diff" in analysis
            assert "wells_details" in analysis

        print(f"Field Analysis Generated for {len(field_analysis)} fields:")
        for field_name, analysis in field_analysis.items():
            print(
                f"  {field_name}: {analysis['wells_count']} wells, "
                f"avg drilling diff: {analysis['average_drilling_diff']:.1f} days"
            )

    def test_identify_root_causes(
        self, sample_comparison_data, sample_methodology_data
    ):
        """Test identification of root causes for calculation differences."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            identify_root_causes,
        )

        root_causes = identify_root_causes(
            sample_comparison_data, sample_methodology_data
        )

        assert isinstance(root_causes, dict)
        assert "primary_factors" in root_causes
        assert "methodology_impacts" in root_causes
        assert "data_quality_factors" in root_causes
        assert "recommendations" in root_causes

        # Verify root causes are identified
        assert len(root_causes["primary_factors"]) > 0
        assert len(root_causes["methodology_impacts"]) > 0
        assert len(root_causes["recommendations"]) > 0

        print("Root Causes Identified:")
        print(f"  Primary factors: {len(root_causes['primary_factors'])}")
        print(f"  Methodology impacts: {len(root_causes['methodology_impacts'])}")
        print(f"  Recommendations: {len(root_causes['recommendations'])}")

    def test_generate_statistical_analysis(self, sample_comparison_data):
        """Test generation of statistical analysis."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            generate_statistical_analysis,
        )

        stats = generate_statistical_analysis(sample_comparison_data)

        assert isinstance(stats, dict)
        assert "drilling_differences" in stats
        assert "completion_differences" in stats
        assert "total_differences" in stats

        # Check statistical measures
        for diff_type in [
            "drilling_differences",
            "completion_differences",
            "total_differences",
        ]:
            assert "mean" in stats[diff_type]
            assert "median" in stats[diff_type]
            assert "std" in stats[diff_type]
            assert "min" in stats[diff_type]
            assert "max" in stats[diff_type]
            assert "q25" in stats[diff_type]
            assert "q75" in stats[diff_type]

        print("Statistical Analysis:")
        for diff_type, measures in stats.items():
            print(f"  {diff_type}:")
            print(f"    Mean: {measures['mean']:.2f}, Median: {measures['median']:.2f}")
            print(f"    Range: {measures['min']:.1f} to {measures['max']:.1f}")

    def test_create_comparison_tables(self, sample_comparison_data):
        """Test creation of comparison tables for the report."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            create_comparison_tables,
        )

        tables = create_comparison_tables(sample_comparison_data)

        assert isinstance(tables, dict)
        assert "methodology_comparison" in tables
        assert "well_details_table" in tables
        assert "field_summary_table" in tables
        assert "extreme_cases_table" in tables

        # Verify tables are properly formatted
        well_table = tables["well_details_table"]
        assert isinstance(well_table, str)
        assert "API12" in well_table
        assert "Field" in well_table
        assert "Drill Diff" in well_table

        print("Comparison Tables Created:")
        print(f"  Methodology comparison: {len(tables['methodology_comparison'])} rows")
        print(f"  Well details table: {'created' if well_table else 'failed'}")
        print(
            f"  Field summary table: {'created' if tables['field_summary_table'] else 'failed'}"
        )

    def test_generate_recommendations(
        self, sample_comparison_data, sample_methodology_data
    ):
        """Test generation of actionable recommendations."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            generate_recommendations,
        )

        recommendations = generate_recommendations(
            sample_comparison_data, sample_methodology_data
        )

        assert isinstance(recommendations, dict)
        assert "immediate_actions" in recommendations
        assert "methodology_improvements" in recommendations
        assert "validation_steps" in recommendations
        assert "future_research" in recommendations

        # Verify recommendations are provided
        assert len(recommendations["immediate_actions"]) > 0
        assert len(recommendations["methodology_improvements"]) > 0
        assert len(recommendations["validation_steps"]) > 0

        print("Recommendations Generated:")
        for category, items in recommendations.items():
            print(f"  {category}: {len(items)} recommendations")

    def test_compile_comprehensive_report(
        self, sample_comparison_data, sample_methodology_data
    ):
        """Test compilation of comprehensive markdown report."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            compile_comprehensive_report,
        )

        report = compile_comprehensive_report(
            sample_comparison_data, sample_methodology_data
        )

        assert isinstance(report, str)
        assert len(report) > 1000  # Should be a substantial report

        # Check for required sections
        required_sections = [
            "# Root Cause Analysis Report",
            "## Executive Summary",
            "## Methodology Comparison",
            "## Statistical Analysis",
            "## Field-by-Field Analysis",
            "## Root Cause Analysis",
            "## Recommendations",
            "## Conclusion",
        ]

        for section in required_sections:
            assert section in report, f"Missing section: {section}"

        print("Comprehensive Report Compiled:")
        print(f"  Total length: {len(report)} characters")
        print(f"  Sections verified: {len(required_sections)}")

        assert len(report) > 5000  # Should be a substantial report

    def test_save_report_to_file(self, sample_comparison_data, sample_methodology_data):
        """Test saving report to markdown file."""
        # Generate report
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            compile_comprehensive_report,
            save_report_to_file,
        )

        report_content = compile_comprehensive_report(
            sample_comparison_data, sample_methodology_data
        )

        # Save to file
        output_path = "tests/modules/bsee/analysis/api12_drilling_completion_analysis/results/test_report.md"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        success = save_report_to_file(report_content, output_path)

        assert success == True
        assert os.path.exists(output_path)

        # Verify file content
        with open(output_path, "r", encoding="utf-8") as f:
            saved_content = f.read()

        assert len(saved_content) > 0
        assert len(saved_content) == len(report_content)
        assert "Root Cause Analysis Report" in saved_content

        print(f"Report saved successfully to: {output_path}")

        # Clean up test file
        os.remove(output_path)

    def test_generate_methodology_comparison_table(self):
        """Test generation of methodology comparison table."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            generate_methodology_comparison_table,
        )

        table = generate_methodology_comparison_table()

        assert isinstance(table, str)
        assert "|" in table  # Should be markdown table format
        assert "Lease Method" in table
        assert "API12 Method" in table
        assert "Data Sources" in table
        assert "Primary Approach" in table

        print("Methodology Comparison Table:")
        print(table[:200] + "..." if len(table) > 200 else table)

    def test_calculate_accuracy_metrics(self, sample_comparison_data):
        """Test calculation of accuracy metrics for both methods."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            calculate_accuracy_metrics,
        )

        metrics = calculate_accuracy_metrics(sample_comparison_data)

        assert isinstance(metrics, dict)
        assert "agreement_statistics" in metrics
        assert "difference_distribution" in metrics
        assert "outlier_analysis" in metrics

        # Verify metrics are calculated
        agreement = metrics["agreement_statistics"]
        assert "mean_absolute_error" in agreement
        assert "root_mean_squared_error" in agreement
        assert "correlation_coefficient" in agreement

        print("Accuracy Metrics:")
        print(f"  MAE: {agreement['mean_absolute_error']:.2f}")
        print(f"  RMSE: {agreement['root_mean_squared_error']:.2f}")
        print(f"  Correlation: {agreement['correlation_coefficient']:.3f}")

    def test_export_analysis_data(
        self, sample_comparison_data, sample_methodology_data
    ):
        """Test export of analysis data to JSON format."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.report_generator import (
            export_analysis_data,
        )

        output_path = "tests/modules/bsee/analysis/api12_drilling_completion_analysis/results/test_analysis_data.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        success = export_analysis_data(
            sample_comparison_data, sample_methodology_data, output_path
        )

        assert success == True
        assert os.path.exists(output_path)

        # Verify JSON content
        with open(output_path, "r") as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "analysis_date" in data
        assert "comparison_data" in data
        assert "methodology_data" in data
        assert "statistical_analysis" in data

        print(f"Analysis data exported to: {output_path}")

        # Clean up test file
        os.remove(output_path)
