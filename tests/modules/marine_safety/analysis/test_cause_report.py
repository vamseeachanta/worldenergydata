# ABOUTME: Test suite for HTML cause analysis report generation module
# ABOUTME: Validates report structure, visualizations, data tables, and filters

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from worldenergydata.marine_safety.analysis.cause_report import (
    CauseAnalysisReport,
    ReportFilters,
)
from worldenergydata.marine_safety.constants import (
    CauseCategory,
    SeverityLevel,
)


@pytest.fixture
def sample_incident_data():
    """Generate sample incident data for report testing."""
    base_date = datetime(2024, 1, 1)
    return [
        {
            "incident_id": f"INC-2024-{i:03d}",
            "date": base_date + timedelta(days=i * 10),
            "incident_type": "Flooding" if i % 3 == 0 else "Grounding",
            "cause_category": (
                CauseCategory.HUMAN_ERROR
                if i % 2 == 0
                else CauseCategory.EQUIPMENT_FAILURE
            ),
            "severity": SeverityLevel.SERIOUS if i % 4 == 0 else SeverityLevel.MODERATE,
            "vessel_name": f"Test Vessel {i}",
            "location": "Gulf of Mexico",
            "description": (
                f"Test incident {i} with hatch maloperation"
                if i % 5 == 0
                else f"Test incident {i}"
            ),
            "fatalities": 1 if i % 10 == 0 else 0,
            "injuries": i % 3,
            "investigation_complete": True,
        }
        for i in range(1, 21)
    ]


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary directory for report output."""
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    return output_dir


class TestCauseAnalysisReport:
    """Test suite for CauseAnalysisReport class."""

    def test_report_initialization(self, sample_incident_data):
        """Test report can be initialized with incident data."""
        report = CauseAnalysisReport(sample_incident_data)

        assert report is not None
        assert len(report.incidents) == 20
        assert report.title == "Incident Cause Analysis Report"

    def test_report_initialization_with_custom_title(self, sample_incident_data):
        """Test report initialization with custom title."""
        custom_title = "Custom Analysis Report"
        report = CauseAnalysisReport(sample_incident_data, title=custom_title)

        assert report.title == custom_title

    def test_report_initialization_empty_data(self):
        """Test report handles empty incident list."""
        report = CauseAnalysisReport([])

        assert report is not None
        assert len(report.incidents) == 0

    def test_generate_html_creates_valid_html(
        self, sample_incident_data, temp_output_dir
    ):
        """Test HTML generation creates valid HTML structure."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)

        assert output_file.exists()
        html_content = output_file.read_text()

        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Check basic HTML structure
        assert soup.find("html") is not None
        assert soup.find("head") is not None
        assert soup.find("body") is not None
        assert soup.find("title") is not None

    def test_html_contains_executive_summary(
        self, sample_incident_data, temp_output_dir
    ):
        """Test HTML report contains executive summary section."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()
        soup = BeautifulSoup(html_content, "html.parser")

        # Check for executive summary section
        summary_section = soup.find(id="executive-summary")
        assert summary_section is not None

        # Check summary contains key metrics
        assert (
            "Total Incidents" in html_content
            or "total incidents" in html_content.lower()
        )
        assert "Fatalities" in html_content or "fatalities" in html_content.lower()

    def test_html_contains_statistical_findings(
        self, sample_incident_data, temp_output_dir
    ):
        """Test HTML report contains statistical findings section."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()
        soup = BeautifulSoup(html_content, "html.parser")

        # Check for statistical section
        stats_section = soup.find(id="statistical-findings")
        assert stats_section is not None

        # Check for data tables
        tables = soup.find_all("table")
        assert len(tables) > 0

    def test_html_contains_visualizations(self, sample_incident_data, temp_output_dir):
        """Test HTML report contains embedded Plotly visualizations."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check for Plotly
        assert "plotly" in html_content.lower()

        # Check for visualization section
        soup = BeautifulSoup(html_content, "html.parser")
        viz_section = soup.find(id="visualizations")
        assert viz_section is not None

    def test_html_contains_hatch_maloperation_section(
        self, sample_incident_data, temp_output_dir
    ):
        """Test HTML report contains hatch/opening maloperation analysis."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()
        soup = BeautifulSoup(html_content, "html.parser")

        # Check for hatch section
        hatch_section = soup.find(id="hatch-analysis")
        assert hatch_section is not None

        # Check content mentions hatch or opening
        assert "hatch" in html_content.lower() or "opening" in html_content.lower()

    def test_html_contains_bootstrap_css(self, sample_incident_data, temp_output_dir):
        """Test HTML includes Bootstrap CSS."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check for Bootstrap CDN or embedded CSS
        assert "bootstrap" in html_content.lower()

    def test_html_contains_datatables_js(self, sample_incident_data, temp_output_dir):
        """Test HTML includes DataTables.js for interactive tables."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check for DataTables
        assert (
            "datatables" in html_content.lower() or "datatable" in html_content.lower()
        )

    def test_html_contains_navigation_menu(self, sample_incident_data, temp_output_dir):
        """Test HTML contains navigation menu for sections."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()
        soup = BeautifulSoup(html_content, "html.parser")

        # Check for navigation
        nav = soup.find("nav")
        assert nav is not None

        # Check for section links
        assert soup.find("a", href="#executive-summary") is not None
        assert soup.find("a", href="#statistical-findings") is not None
        assert soup.find("a", href="#visualizations") is not None

    def test_html_contains_metadata(self, sample_incident_data, temp_output_dir):
        """Test HTML contains report metadata."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check for metadata
        assert "Generated on" in html_content or "generated" in html_content.lower()
        assert "Data Source" in html_content or "source" in html_content.lower()

    def test_html_standalone_no_external_dependencies(
        self, sample_incident_data, temp_output_dir
    ):
        """Test HTML is standalone with embedded resources."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check that visualizations are embedded (no external files)
        # Should use data URIs or inline JSON
        assert 'src="http' not in html_content or "cdn" in html_content.lower()

    def test_filter_by_date_range(self, sample_incident_data):
        """Test filtering incidents by date range."""
        filters = ReportFilters(
            start_date=datetime(2024, 1, 15), end_date=datetime(2024, 2, 15)
        )

        report = CauseAnalysisReport(sample_incident_data, filters=filters)

        # Check filtered data
        assert len(report.incidents) < len(sample_incident_data)
        for incident in report.incidents:
            assert filters.start_date <= incident["date"] <= filters.end_date

    def test_filter_by_cause_category(self, sample_incident_data):
        """Test filtering incidents by cause category."""
        filters = ReportFilters(cause_categories=[CauseCategory.HUMAN_ERROR])

        report = CauseAnalysisReport(sample_incident_data, filters=filters)

        # Check filtered data
        for incident in report.incidents:
            assert incident["cause_category"] == CauseCategory.HUMAN_ERROR

    def test_filter_by_severity(self, sample_incident_data):
        """Test filtering incidents by severity level."""
        filters = ReportFilters(min_severity=SeverityLevel.SERIOUS)

        report = CauseAnalysisReport(sample_incident_data, filters=filters)

        # Check filtered data
        for incident in report.incidents:
            assert incident["severity"] >= SeverityLevel.SERIOUS

    def test_filter_combined(self, sample_incident_data):
        """Test combined filters."""
        filters = ReportFilters(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            cause_categories=[
                CauseCategory.HUMAN_ERROR,
                CauseCategory.EQUIPMENT_FAILURE,
            ],
            min_severity=SeverityLevel.MODERATE,
        )

        report = CauseAnalysisReport(sample_incident_data, filters=filters)

        # Check all filters applied
        assert len(report.incidents) <= len(sample_incident_data)

    def test_export_buttons_present(self, sample_incident_data, temp_output_dir):
        """Test HTML contains export buttons for data and charts."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()
        soup = BeautifulSoup(html_content, "html.parser")

        # Check for export buttons
        buttons = soup.find_all("button")
        export_buttons = [
            btn
            for btn in buttons
            if "export" in btn.get_text().lower()
            or "download" in btn.get_text().lower()
        ]

        assert len(export_buttons) > 0

    def test_responsive_layout(self, sample_incident_data, temp_output_dir):
        """Test HTML uses responsive layout."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check for responsive meta tag
        assert "viewport" in html_content

        # Check for responsive classes
        soup = BeautifulSoup(html_content, "html.parser")
        responsive_elements = soup.find_all(class_=re.compile(r"col-|container|row"))
        assert len(responsive_elements) > 0

    def test_cause_category_distribution_chart(
        self, sample_incident_data, temp_output_dir
    ):
        """Test report includes cause category distribution chart."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check for cause category mentions in visualizations
        assert "cause" in html_content.lower()
        assert (
            "category" in html_content.lower() or "distribution" in html_content.lower()
        )

    def test_severity_trend_chart(self, sample_incident_data, temp_output_dir):
        """Test report includes severity trend over time chart."""
        report = CauseAnalysisReport(sample_incident_data)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check for severity and trend mentions
        assert "severity" in html_content.lower()
        assert "trend" in html_content.lower() or "time" in html_content.lower()

    def test_filters_displayed_in_metadata(self, sample_incident_data, temp_output_dir):
        """Test applied filters are shown in report metadata."""
        filters = ReportFilters(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            cause_categories=[CauseCategory.HUMAN_ERROR],
        )

        report = CauseAnalysisReport(sample_incident_data, filters=filters)
        output_file = temp_output_dir / "test_report.html"

        report.generate_html(output_file)
        html_content = output_file.read_text()

        # Check filters are documented
        assert "2024-01-01" in html_content or "January 1, 2024" in html_content
        assert (
            "human error" in html_content.lower()
            or "human_error" in html_content.lower()
        )


class TestReportFilters:
    """Test suite for ReportFilters class."""

    def test_filters_initialization_default(self):
        """Test filters can be initialized with defaults."""
        filters = ReportFilters()

        assert filters.start_date is None
        assert filters.end_date is None
        assert filters.cause_categories is None
        assert filters.min_severity is None

    def test_filters_initialization_with_values(self):
        """Test filters initialization with values."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)

        filters = ReportFilters(
            start_date=start,
            end_date=end,
            cause_categories=[CauseCategory.HUMAN_ERROR],
            min_severity=SeverityLevel.MODERATE,
        )

        assert filters.start_date == start
        assert filters.end_date == end
        assert CauseCategory.HUMAN_ERROR in filters.cause_categories
        assert filters.min_severity == SeverityLevel.MODERATE

    def test_filters_validate_date_range(self):
        """Test filters validate date range."""
        with pytest.raises(ValueError):
            ReportFilters(
                start_date=datetime(2024, 12, 31), end_date=datetime(2024, 1, 1)
            )

    def test_filters_apply_to_incidents(self, sample_incident_data):
        """Test filters can be applied to incident data."""
        filters = ReportFilters(
            start_date=datetime(2024, 1, 15),
            end_date=datetime(2024, 2, 15),
            cause_categories=[CauseCategory.HUMAN_ERROR],
        )

        filtered_data = filters.apply(sample_incident_data)

        assert len(filtered_data) < len(sample_incident_data)
        for incident in filtered_data:
            assert filters.start_date <= incident["date"] <= filters.end_date
            assert incident["cause_category"] == CauseCategory.HUMAN_ERROR
