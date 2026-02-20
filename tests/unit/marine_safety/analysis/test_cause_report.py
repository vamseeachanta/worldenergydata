"""Tests for marine_safety.analysis.cause_report ReportFilters and CauseAnalysisReport."""

from datetime import datetime

import pytest

from worldenergydata.marine_safety.analysis.cause_report import (
    CauseAnalysisReport,
    ReportFilters,
)
from worldenergydata.marine_safety.constants import CauseCategory, SeverityLevel


def _make_incident(
    incident_id="INC-001",
    date=None,
    cause_category=CauseCategory.HUMAN_ERROR,
    severity=SeverityLevel.MODERATE,
    fatalities=0,
    injuries=0,
    description="test incident",
    vessel_name="MV Test",
):
    return {
        "incident_id": incident_id,
        "date": date or datetime(2024, 6, 15),
        "cause_category": cause_category,
        "severity": severity,
        "fatalities": fatalities,
        "injuries": injuries,
        "description": description,
        "vessel_name": vessel_name,
    }


class TestReportFilters:
    def test_default_filters(self):
        f = ReportFilters()
        assert f.start_date is None
        assert f.end_date is None
        assert f.cause_categories is None
        assert f.min_severity is None

    def test_date_validation(self):
        with pytest.raises(ValueError, match="start_date must be before"):
            ReportFilters(
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2024, 1, 1),
            )

    def test_apply_no_filters(self):
        f = ReportFilters()
        incidents = [_make_incident(), _make_incident(incident_id="INC-002")]
        result = f.apply(incidents)
        assert len(result) == 2

    def test_apply_start_date_filter(self):
        f = ReportFilters(start_date=datetime(2024, 7, 1))
        incidents = [
            _make_incident(date=datetime(2024, 6, 15)),
            _make_incident(incident_id="INC-002", date=datetime(2024, 8, 1)),
        ]
        result = f.apply(incidents)
        assert len(result) == 1

    def test_apply_end_date_filter(self):
        f = ReportFilters(end_date=datetime(2024, 7, 1))
        incidents = [
            _make_incident(date=datetime(2024, 6, 15)),
            _make_incident(incident_id="INC-002", date=datetime(2024, 8, 1)),
        ]
        result = f.apply(incidents)
        assert len(result) == 1

    def test_apply_cause_category_filter(self):
        f = ReportFilters(cause_categories=[CauseCategory.WEATHER])
        incidents = [
            _make_incident(cause_category=CauseCategory.HUMAN_ERROR),
            _make_incident(
                incident_id="INC-002",
                cause_category=CauseCategory.WEATHER,
            ),
        ]
        result = f.apply(incidents)
        assert len(result) == 1
        assert result[0]["cause_category"] == CauseCategory.WEATHER

    def test_apply_severity_filter(self):
        f = ReportFilters(min_severity=SeverityLevel.SERIOUS)
        incidents = [
            _make_incident(severity=SeverityLevel.MINOR),
            _make_incident(
                incident_id="INC-002",
                severity=SeverityLevel.CATASTROPHIC,
            ),
        ]
        result = f.apply(incidents)
        assert len(result) == 1

    def test_apply_combined_filters(self):
        f = ReportFilters(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            cause_categories=[CauseCategory.HUMAN_ERROR],
        )
        incidents = [
            _make_incident(
                date=datetime(2024, 6, 1),
                cause_category=CauseCategory.HUMAN_ERROR,
            ),
            _make_incident(
                incident_id="INC-002",
                date=datetime(2024, 6, 1),
                cause_category=CauseCategory.WEATHER,
            ),
            _make_incident(
                incident_id="INC-003",
                date=datetime(2023, 6, 1),
                cause_category=CauseCategory.HUMAN_ERROR,
            ),
        ]
        result = f.apply(incidents)
        assert len(result) == 1


class TestCauseAnalysisReport:
    def test_init_default(self):
        incidents = [_make_incident()]
        report = CauseAnalysisReport(incidents)
        assert report.title == "Incident Cause Analysis Report"
        assert len(report.incidents) == 1

    def test_init_custom_title(self):
        report = CauseAnalysisReport([], title="Custom Title")
        assert report.title == "Custom Title"

    def test_init_with_filters(self):
        f = ReportFilters(start_date=datetime(2025, 1, 1))
        incidents = [_make_incident(date=datetime(2024, 6, 1))]
        report = CauseAnalysisReport(incidents, filters=f)
        assert len(report.incidents) == 0

    def test_build_html_structure(self):
        incidents = [
            _make_incident(fatalities=1, injuries=2),
        ]
        report = CauseAnalysisReport(incidents)
        html = report._build_html_structure()
        assert "<!DOCTYPE html>" in html
        assert report.title in html

    def test_generate_metadata_section(self):
        report = CauseAnalysisReport([_make_incident()])
        metadata = report._generate_metadata_section()
        assert "Total Incidents" in metadata
        assert "1" in metadata

    def test_generate_navigation(self):
        report = CauseAnalysisReport([])
        nav = report._generate_navigation()
        assert "navbar" in nav

    def test_css_styles(self):
        report = CauseAnalysisReport([])
        css = report._get_css_styles()
        assert "bootstrap" in css

    def test_external_libraries(self):
        report = CauseAnalysisReport([])
        libs = report._get_external_libraries()
        assert "plotly" in libs

    def test_javascript(self):
        report = CauseAnalysisReport([])
        js = report._get_javascript()
        assert "DataTable" in js

    def test_generate_html_writes_file(self, tmp_path):
        incidents = [
            _make_incident(fatalities=1, injuries=2),
        ]
        report = CauseAnalysisReport(incidents)
        outfile = tmp_path / "report.html"
        report.generate_html(outfile)
        assert outfile.exists()
        content = outfile.read_text()
        assert "<!DOCTYPE html>" in content

    def test_metadata_with_date_filters(self):
        f = ReportFilters(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )
        report = CauseAnalysisReport([_make_incident()], filters=f)
        metadata = report._generate_metadata_section()
        assert "2024-01-01" in metadata

    def test_metadata_with_cause_filters(self):
        f = ReportFilters(cause_categories=[CauseCategory.WEATHER])
        report = CauseAnalysisReport([], filters=f)
        metadata = report._generate_metadata_section()
        assert "weather" in metadata.lower()
