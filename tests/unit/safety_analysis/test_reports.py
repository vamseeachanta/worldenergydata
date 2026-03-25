# ABOUTME: Integration tests for safety analysis report generators.
"""
Phase 4 integration tests for BaseReport, IncidentReport,
CorrelationReport, and ClassificationReport.

Tests verify HTML report generation, section/stat management,
and factory classmethod creation from domain data.
"""

import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.safety_analysis.core.models import CorrelationResult
from worldenergydata.safety_analysis.reports.base_report import BaseReport
from worldenergydata.safety_analysis.reports.classification_report import (
    ClassificationReport,
)
from worldenergydata.safety_analysis.reports.correlation_report import (
    CorrelationReport,
)
from worldenergydata.safety_analysis.reports.incident_report import (
    IncidentReport,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_figure():
    """A minimal Plotly figure for testing."""
    fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
    fig.update_layout(title="Test Chart")
    return fig


@pytest.fixture
def standardised_incidents_df():
    """Incident DataFrame with standardised column names expected by IncidentReport."""
    return pd.DataFrame(
        {
            "asset_id": ["RIG-001", "RIG-002", "RIG-001", "RIG-002"],
            "occurred_at": pd.to_datetime(
                ["2024-01-05", "2024-01-10", "2024-01-15", "2024-01-20"]
            ),
            "actual_severity": ["minor", "moderate", "no_hurt", "severe"],
            "potential_severity": ["moderate", "severe", "severe", "fatality"],
            "description": [
                "Worker slipped on wet surface",
                "Minor hand injury during pipe handling",
                "Near miss with dropped object",
                "Chemical splash during mixing",
            ],
        }
    )


@pytest.fixture
def sample_correlation_results():
    """CorrelationResult objects for report generation tests."""
    return [
        CorrelationResult(
            asset_id="RIG-001",
            lag_values=list(range(-5, 6)),
            correlation_values=[
                0.1,
                0.2,
                0.3,
                0.5,
                0.7,
                1.0,
                0.7,
                0.5,
                0.3,
                0.2,
                0.1,
            ],
            peak_correlation=1.0,
            peak_lag=0,
        ),
    ]


@pytest.fixture
def sample_eval_results():
    """Evaluation results dict for ClassificationReport tests."""
    return {
        "model_name": "test_rf",
        "accuracy": 0.85,
        "f1_weighted": 0.85,
        "class_labels": ["safe", "at_risk"],
        "classification_report": {
            "safe": {
                "precision": 0.9,
                "recall": 0.8,
                "f1-score": 0.85,
                "support": 10,
            },
            "at_risk": {
                "precision": 0.8,
                "recall": 0.9,
                "f1-score": 0.85,
                "support": 10,
            },
            "accuracy": 0.85,
            "macro avg": {
                "precision": 0.85,
                "recall": 0.85,
                "f1-score": 0.85,
                "support": 20,
            },
            "weighted avg": {
                "precision": 0.85,
                "recall": 0.85,
                "f1-score": 0.85,
                "support": 20,
            },
        },
        "confusion_matrix": [[8, 2], [1, 9]],
    }


# ---------------------------------------------------------------------------
# TestBaseReport
# ---------------------------------------------------------------------------


class TestBaseReport:
    """Tests for the BaseReport foundation class."""

    def test_create_report(self):
        """BaseReport stores title and subtitle at creation."""
        report = BaseReport(title="Test Report", subtitle="A subtitle")
        assert report.title == "Test Report"
        assert report.subtitle == "A subtitle"

    def test_create_report_default_subtitle(self):
        """BaseReport defaults to an empty subtitle."""
        report = BaseReport(title="Report Only")
        assert report.subtitle == ""

    def test_add_summary_stat(self):
        """add_summary_stat appends to the internal stats list."""
        report = BaseReport(title="Stats Test")
        report.add_summary_stat(label="Total", value="42", unit="incidents")
        assert len(report.summary_stats) == 1
        stat = report.summary_stats[0]
        assert stat.label == "Total"
        assert stat.value == "42"
        assert stat.unit == "incidents"

    def test_add_section(self, sample_figure):
        """add_section appends a section with title, figure, and description."""
        report = BaseReport(title="Section Test")
        report.add_section(
            title="Chart Section",
            figure=sample_figure,
            description="A test chart.",
        )
        assert len(report.sections) == 1
        section = report.sections[0]
        assert section.title == "Chart Section"
        assert section.description == "A test chart."

    def test_generate_html(self, tmp_path, sample_figure):
        """generate_html creates an HTML file at the given path."""
        report = BaseReport(title="HTML Test")
        report.add_section(title="Chart", figure=sample_figure)
        output_path = tmp_path / "report.html"
        result = report.generate_html(output_path)
        assert result.exists()
        content = result.read_text()
        assert "HTML Test" in content

    def test_generate_html_creates_directory(self, tmp_path, sample_figure):
        """generate_html creates parent directories when they do not exist."""
        report = BaseReport(title="Dir Test")
        report.add_section(title="Chart", figure=sample_figure)
        nested_path = tmp_path / "sub" / "dir" / "report.html"
        result = report.generate_html(nested_path)
        assert result.exists()

    def test_html_contains_plotly_cdn(self, tmp_path, sample_figure):
        """Generated HTML includes Plotly CDN reference for rendering."""
        report = BaseReport(title="CDN Test")
        report.add_section(title="Chart", figure=sample_figure)
        output_path = tmp_path / "report.html"
        result = report.generate_html(output_path)
        content = result.read_text()
        assert "plotly" in content.lower()

    def test_html_contains_chart_div(self, tmp_path, sample_figure):
        """Generated HTML includes a div for the Plotly chart."""
        report = BaseReport(title="Chart Div Test")
        report.add_section(title="My Chart", figure=sample_figure)
        output_path = tmp_path / "report.html"
        result = report.generate_html(output_path)
        content = result.read_text()
        # Plotly embeds charts as divs or script blocks
        assert "My Chart" in content or "div" in content

    def test_empty_report(self, tmp_path):
        """An empty report with no sections still generates valid HTML."""
        report = BaseReport(title="Empty Report")
        output_path = tmp_path / "empty.html"
        result = report.generate_html(output_path)
        assert result.exists()
        content = result.read_text()
        assert "Empty Report" in content
        assert "<html" in content.lower() or "<!doctype" in content.lower()


# ---------------------------------------------------------------------------
# TestIncidentReport
# ---------------------------------------------------------------------------


class TestIncidentReport:
    """Tests for the IncidentReport factory and output."""

    def test_from_dataframe(self, standardised_incidents_df):
        """from_dataframe creates an IncidentReport from a DataFrame."""
        report = IncidentReport.from_dataframe(standardised_incidents_df)
        assert isinstance(report, IncidentReport)
        assert report.title is not None

    def test_has_sections(self, standardised_incidents_df):
        """IncidentReport created from data has at least one section."""
        report = IncidentReport.from_dataframe(standardised_incidents_df)
        assert len(report.sections) > 0

    def test_summary_stats_populated(self, standardised_incidents_df):
        """IncidentReport includes summary statistics."""
        report = IncidentReport.from_dataframe(standardised_incidents_df)
        assert len(report.summary_stats) > 0
        labels = [s.label for s in report.summary_stats]
        # Should include total incident count at minimum
        assert any(
            "total" in label.lower() or "incident" in label.lower() for label in labels
        )

    def test_generates_html(self, standardised_incidents_df, tmp_path):
        """IncidentReport produces a valid HTML file."""
        report = IncidentReport.from_dataframe(standardised_incidents_df)
        output_path = tmp_path / "incident_report.html"
        result = report.generate_html(output_path)
        assert result.exists()
        content = result.read_text()
        assert len(content) > 100


# ---------------------------------------------------------------------------
# TestCorrelationReport
# ---------------------------------------------------------------------------


class TestCorrelationReport:
    """Tests for the CorrelationReport factory and output."""

    def test_from_results(self, sample_correlation_results):
        """from_results creates a CorrelationReport from result objects."""
        report = CorrelationReport.from_results(sample_correlation_results)
        assert isinstance(report, CorrelationReport)
        assert report.title is not None

    def test_has_sections(self, sample_correlation_results):
        """CorrelationReport has at least one section (correlation chart)."""
        report = CorrelationReport.from_results(sample_correlation_results)
        assert len(report.sections) > 0

    def test_generates_html(self, sample_correlation_results, tmp_path):
        """CorrelationReport produces a valid HTML file."""
        report = CorrelationReport.from_results(sample_correlation_results)
        output_path = tmp_path / "correlation_report.html"
        result = report.generate_html(output_path)
        assert result.exists()
        content = result.read_text()
        assert len(content) > 100


# ---------------------------------------------------------------------------
# TestClassificationReport
# ---------------------------------------------------------------------------


class TestClassificationReport:
    """Tests for the ClassificationReport factory and output."""

    def test_from_evaluation(self, sample_eval_results):
        """from_evaluation creates a ClassificationReport from eval dict."""
        report = ClassificationReport.from_evaluation(sample_eval_results)
        assert isinstance(report, ClassificationReport)
        assert report.title is not None

    def test_has_sections(self, sample_eval_results):
        """ClassificationReport has at least one section."""
        report = ClassificationReport.from_evaluation(sample_eval_results)
        assert len(report.sections) > 0

    def test_confusion_matrix_section(self, sample_eval_results):
        """ClassificationReport includes a confusion matrix section."""
        report = ClassificationReport.from_evaluation(sample_eval_results)
        section_titles = [s.title.lower() for s in report.sections]
        assert any("confusion" in t or "matrix" in t for t in section_titles)

    def test_generates_html(self, sample_eval_results, tmp_path):
        """ClassificationReport produces a valid HTML file."""
        report = ClassificationReport.from_evaluation(sample_eval_results)
        output_path = tmp_path / "classification_report.html"
        result = report.generate_html(output_path)
        assert result.exists()
        content = result.read_text()
        assert len(content) > 100
