"""Tests for PDF exporter validate_data, get_supported_features, generate_html."""

import pytest

from worldenergydata.bsee.reports.comprehensive.exporters.pdf_exporter import (
    PDFExporter,
)


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestPDFExporterInit:
    def test_supported_format(self):
        exporter = PDFExporter()
        assert exporter.supported_format.value == "pdf"

    def test_initial_state(self):
        exporter = PDFExporter()
        assert exporter.html_content == ""
        assert exporter.css_styles == ""


# ---------------------------------------------------------------------------
# validate_data
# ---------------------------------------------------------------------------

class TestValidateData:
    def test_empty_data(self):
        exporter = PDFExporter()
        assert exporter.validate_data({}) is False

    def test_none_data(self):
        exporter = PDFExporter()
        assert exporter.validate_data(None) is False

    def test_with_report_metadata(self):
        exporter = PDFExporter()
        assert exporter.validate_data({"report_metadata": {}}) is True

    def test_with_content(self):
        exporter = PDFExporter()
        assert exporter.validate_data({"content": "text"}) is True

    def test_with_summary(self):
        exporter = PDFExporter()
        assert exporter.validate_data({"summary": {}}) is True

    def test_with_tables(self):
        exporter = PDFExporter()
        assert exporter.validate_data({"tables": []}) is True

    def test_with_charts(self):
        exporter = PDFExporter()
        assert exporter.validate_data({"charts": []}) is True

    def test_with_kpis(self):
        exporter = PDFExporter()
        assert exporter.validate_data({"kpis": {}}) is True

    def test_unrecognized_section(self):
        exporter = PDFExporter()
        assert exporter.validate_data({"other": "data"}) is False


# ---------------------------------------------------------------------------
# get_supported_features
# ---------------------------------------------------------------------------

class TestGetSupportedFeatures:
    def test_returns_list(self):
        exporter = PDFExporter()
        features = exporter.get_supported_features()
        assert isinstance(features, list)

    def test_contains_key_features(self):
        exporter = PDFExporter()
        features = exporter.get_supported_features()
        assert "html_to_pdf" in features
        assert "css_styling" in features
        assert "page_numbers" in features
        assert "embedded_charts" in features

    def test_feature_count(self):
        exporter = PDFExporter()
        assert len(exporter.get_supported_features()) == 9


# ---------------------------------------------------------------------------
# generate_html
# ---------------------------------------------------------------------------

class TestGenerateHtml:
    def test_basic_structure(self):
        exporter = PDFExporter()
        html = exporter.generate_html({"report_metadata": {"title": "Test Report"}})
        assert "<!DOCTYPE html>" in html
        assert "Test Report" in html
        assert "</html>" in html

    def test_with_content(self):
        exporter = PDFExporter()
        html = exporter.generate_html({
            "report_metadata": {"title": "Report"},
            "content": {"executive_summary": "Summary text"},
        })
        assert "Executive Summary" in html

    def test_empty_metadata(self):
        exporter = PDFExporter()
        html = exporter.generate_html({})
        assert "Report" in html  # Default title
