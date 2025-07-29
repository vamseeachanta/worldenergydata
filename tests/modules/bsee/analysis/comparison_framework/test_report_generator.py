"""
Test cases for ReportGenerator class.

Tests the report generation functionality for drilling days comparison analysis.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from typing import Dict, Any, List, Optional

# Import the modules we're testing
from .report_generator import HTMLReportGenerator, CSVReportGenerator, ReportManager
from .comparison_engine import ComparisonResult, WellCoverageAnalysis


class TestHTMLReportGenerator:
    """Test cases for HTMLReportGenerator."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.generator = HTMLReportGenerator()
        
        # Create sample comparison result
        self.sample_coverage = WellCoverageAnalysis(
            total_lease_wells=100,
            total_api12_wells=95,
            common_wells=90,
            lease_only_wells=10,
            api12_only_wells=5,
            coverage_percentage=90.0
        )
        
        self.sample_statistics = {
            'drilling_days': {
                'count': 90,
                'mean': 1.5,
                'std': 2.3,
                'median': 1.0,
                'min': -5,
                'max': 8,
                'mean_abs_diff': 2.1,
                'max_abs_diff': 8,
                'q25': 0.5,
                'q75': 2.5
            },
            'completion_days': {
                'count': 90,
                'mean': -0.8,
                'std': 3.1,
                'median': -1.0,
                'min': -10,
                'max': 12,
                'mean_abs_diff': 2.8,
                'max_abs_diff': 12,
                'q25': -2.0,
                'q75': 1.5
            }
        }
        
        self.sample_matched_data = pd.DataFrame({
            'api_normalized': ['420030123450', '420030456780', '420030789010'],
            'drilling_days_lease': [36, 34, 36],
            'completion_days_lease': [45, 42, 48],
            'drilling_days_api12': [36, 33, 37],
            'completion_days_api12': [44, 43, 47],
            'drilling_days_diff': [0, 1, -1],
            'completion_days_diff': [1, -1, 1],
            'drilling_days_abs_diff': [0, 1, 1],
            'completion_days_abs_diff': [1, 1, 1]
        })
        
        self.sample_discrepancies = pd.DataFrame({
            'api_normalized': ['420030456780', '420030789010'],
            'drilling_days_lease': [34, 36],
            'completion_days_lease': [42, 48],
            'drilling_days_api12': [30, 40],
            'completion_days_api12': [38, 52],
            'drilling_days_diff': [4, -4],
            'completion_days_diff': [4, -4],
            'drilling_days_abs_diff': [4, 4],
            'completion_days_abs_diff': [4, 4]
        })
        
        self.sample_result = ComparisonResult(
            total_common_wells=90,
            statistics=self.sample_statistics,
            well_coverage=self.sample_coverage,
            matched_data=self.sample_matched_data,
            discrepancies=self.sample_discrepancies
        )

    def test_initialization(self):
        """Test HTMLReportGenerator initialization."""
        generator = HTMLReportGenerator()
        assert generator is not None
        
        # Test with custom template path
        custom_path = Path("custom/templates")
        generator_custom = HTMLReportGenerator(template_path=custom_path)
        assert generator_custom.template_path == custom_path

    def test_generate_summary_section(self):
        """Test HTML summary section generation."""
        summary_html = self.generator._generate_summary_section(self.sample_result)
        
        assert isinstance(summary_html, str)
        assert "Well Coverage Analysis" in summary_html
        assert "90" in summary_html  # The number appears in the stat cards
        assert "90.0%" in summary_html
        assert "Executive Summary" in summary_html

    def test_generate_statistics_table(self):
        """Test statistics table generation."""
        stats_html = self.generator._generate_statistics_table(self.sample_statistics)
        
        assert isinstance(stats_html, str)
        assert "<table" in stats_html
        assert "Drilling Days" in stats_html
        assert "Completion Days" in stats_html
        assert "1.5" in stats_html  # mean for drilling days
        assert "2.3" in stats_html  # std for drilling days

    def test_generate_discrepancy_table(self):
        """Test discrepancy table generation."""
        disc_html = self.generator._generate_discrepancy_table(self.sample_discrepancies)
        
        assert isinstance(disc_html, str)
        assert "<table" in disc_html
        assert "420030456780" in disc_html
        assert "420030789010" in disc_html
        assert "discrepancy" in disc_html.lower()

    @patch('matplotlib.pyplot.savefig')
    def test_generate_visualizations(self, mock_savefig):
        """Test visualization generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            charts = self.generator._generate_visualizations(
                self.sample_result, 
                output_dir
            )
            
            assert len(charts) > 0
            assert all(isinstance(chart, dict) for chart in charts)
            assert all('path' in chart and 'title' in chart for chart in charts)
            assert mock_savefig.called

    def test_generate_full_report(self):
        """Test full HTML report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.html"
            
            self.generator.generate_report(
                self.sample_result,
                output_path,
                title="Test Comparison Report"
            )
            
            assert output_path.exists()
            
            # Read and verify content
            with open(output_path, 'r') as f:
                content = f.read()
                
            assert "Test Comparison Report" in content
            assert "Well Coverage Analysis" in content
            assert "Statistical Summary" in content
            assert "<!DOCTYPE html>" in content

    def test_custom_styling(self):
        """Test custom CSS styling options."""
        generator = HTMLReportGenerator(custom_css="body { background-color: #f0f0f0; }")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "styled_report.html"
            generator.generate_report(self.sample_result, output_path)
            
            with open(output_path, 'r') as f:
                content = f.read()
                
            assert "background-color: #f0f0f0" in content

    def test_error_handling_empty_data(self):
        """Test handling of empty comparison results."""
        empty_result = ComparisonResult(
            total_common_wells=0,
            statistics={},
            well_coverage=WellCoverageAnalysis(0, 0, 0, 0, 0, 0.0),
            matched_data=pd.DataFrame(),
            discrepancies=pd.DataFrame()
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "empty_report.html"
            
            # Should not raise an exception
            self.generator.generate_report(empty_result, output_path)
            assert output_path.exists()


class TestCSVReportGenerator:
    """Test cases for CSVReportGenerator."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.generator = CSVReportGenerator()
        
        # Use same sample data as HTML tests
        self.sample_matched_data = pd.DataFrame({
            'api_normalized': ['420030123450', '420030456780', '420030789010'],
            'drilling_days_lease': [36, 34, 36],
            'completion_days_lease': [45, 42, 48],
            'drilling_days_api12': [36, 33, 37],
            'completion_days_api12': [44, 43, 47],
            'drilling_days_diff': [0, 1, -1],
            'completion_days_diff': [1, -1, 1]
        })
        
        self.sample_result = ComparisonResult(
            total_common_wells=3,
            statistics={},
            well_coverage=WellCoverageAnalysis(3, 3, 3, 0, 0, 100.0),
            matched_data=self.sample_matched_data,
            discrepancies=pd.DataFrame()
        )

    def test_initialization(self):
        """Test CSVReportGenerator initialization."""
        generator = CSVReportGenerator()
        assert generator is not None
        
        # Test with custom options
        generator_custom = CSVReportGenerator(include_statistics=False)
        assert not generator_custom.include_statistics

    def test_generate_summary_csv(self):
        """Test CSV summary generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.csv"
            
            self.generator.generate_summary(
                self.sample_result,
                output_path
            )
            
            assert output_path.exists()
            
            # Read and verify content
            df = pd.read_csv(output_path)
            assert len(df) == 3  # 3 wells
            assert 'api_normalized' in df.columns
            assert 'drilling_days_diff' in df.columns

    def test_generate_detailed_csv(self):
        """Test detailed CSV generation with all columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "detailed.csv"
            
            self.generator.generate_detailed_report(
                self.sample_result,
                output_path,
                include_all_columns=True
            )
            
            assert output_path.exists()
            
            df = pd.read_csv(output_path)
            # Should have all original columns
            assert 'drilling_days_lease' in df.columns
            assert 'drilling_days_api12' in df.columns
            assert 'drilling_days_diff' in df.columns

    def test_generate_statistics_csv(self):
        """Test statistics CSV export."""
        statistics = {
            'drilling_days': {'mean': 1.5, 'std': 2.3, 'median': 1.0},
            'completion_days': {'mean': -0.8, 'std': 3.1, 'median': -1.0}
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "statistics.csv"
            
            self.generator.export_statistics(statistics, output_path)
            
            assert output_path.exists()
            
            df = pd.read_csv(output_path)
            assert len(df) == 2  # 2 metrics
            assert df['metric'].tolist() == ['drilling_days', 'completion_days']

    def test_column_filtering(self):
        """Test column filtering functionality."""
        selected_columns = ['api_normalized', 'drilling_days_diff']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "filtered.csv"
            
            self.generator.generate_summary(
                self.sample_result,
                output_path,
                columns=selected_columns
            )
            
            df = pd.read_csv(output_path)
            assert list(df.columns) == selected_columns


class TestReportManager:
    """Test cases for ReportManager orchestrator."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.manager = ReportManager()
        
        # Create sample comparison result
        self.sample_result = ComparisonResult(
            total_common_wells=10,
            statistics={'drilling_days': {'mean': 1.0}},
            well_coverage=WellCoverageAnalysis(10, 10, 10, 0, 0, 100.0),
            matched_data=pd.DataFrame({
                'api_normalized': ['test1', 'test2'],
                'drilling_days_diff': [1, 2]
            }),
            discrepancies=pd.DataFrame()
        )

    def test_initialization(self):
        """Test ReportManager initialization."""
        manager = ReportManager()
        assert manager is not None
        assert isinstance(manager.html_generator, HTMLReportGenerator)
        assert isinstance(manager.csv_generator, CSVReportGenerator)

    def test_generate_all_reports(self):
        """Test generation of all report types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            report_paths = self.manager.generate_all_reports(
                self.sample_result,
                output_dir,
                report_name="test_comparison"
            )
            
            assert 'html_report' in report_paths
            assert 'csv_summary' in report_paths
            assert 'csv_detailed' in report_paths
            
            # Verify all files exist
            for report_type, path in report_paths.items():
                assert Path(path).exists()

    def test_custom_output_configuration(self):
        """Test custom output path configuration."""
        config = {
            'html': {'enabled': True, 'filename': 'custom.html'},
            'csv_summary': {'enabled': True, 'filename': 'summary.csv'},
            'csv_detailed': {'enabled': False}
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            report_paths = self.manager.generate_all_reports(
                self.sample_result,
                output_dir,
                config=config
            )
            
            assert (output_dir / 'custom.html').exists()
            assert (output_dir / 'summary.csv').exists()
            assert 'csv_detailed' not in report_paths

    def test_report_metadata(self):
        """Test report metadata generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            metadata = self.manager.generate_reports_with_metadata(
                self.sample_result,
                output_dir,
                metadata={
                    'analysis_date': '2025-07-29',
                    'analyst': 'Test User',
                    'description': 'Test comparison run'
                }
            )
            
            assert 'reports' in metadata
            assert 'summary' in metadata
            assert metadata['summary']['total_wells'] == 10

    def test_error_handling_invalid_directory(self):
        """Test handling of invalid output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a subdirectory that doesn't exist
            invalid_dir = Path(tmpdir) / "nonexistent" / "path"
            
            # The code will create the directory if it doesn't exist
            # So this test should check if files are created successfully
            report_paths = self.manager.generate_all_reports(
                self.sample_result,
                invalid_dir
            )
            
            # Directory should be created and reports generated
            assert invalid_dir.exists()  # Directory gets created
            assert len(report_paths) > 0  # Reports are generated

    def teardown_method(self):
        """Clean up after each test method."""
        pass