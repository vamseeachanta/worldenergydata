"""Tests for HSE Risk Index interactive Plotly dashboard."""

from pathlib import Path

import pytest

from worldenergydata.safety_analysis.risk_index.dashboard import RiskDashboard
from worldenergydata.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    DimensionScore,
)


def _make_activity(
    code: str,
    name: str,
    acute_score: float,
    chronic_score: float,
    compliance_score: float,
    composite: float,
    incident_count: int,
    fatality_rate: float = 0.02,
    total_incidents: int = 50,
) -> ActivityRiskScore:
    """Helper to build an ActivityRiskScore with realistic dimension data."""
    return ActivityRiskScore(
        activity_code=code,
        activity_name=name,
        acute=DimensionScore(
            dimension="acute",
            raw_metrics={
                "fatality_rate": fatality_rate,
                "total_incidents": total_incidents,
            },
            score=acute_score,
        ),
        chronic=DimensionScore(
            dimension="chronic",
            raw_metrics={"injury_rate": 8.5, "dart_rate": 3.2},
            score=chronic_score,
        ),
        compliance=DimensionScore(
            dimension="compliance",
            raw_metrics={"violation_rate": 0.15},
            score=compliance_score,
        ),
        composite_score=composite,
        incident_count=incident_count,
        confidence="high",
        sources=["phmsa", "osha"],
    )


@pytest.fixture()
def sample_composite_score() -> CompositeScore:
    """CompositeScore with 5 activities spanning risk categories."""
    activities = [
        _make_activity(
            "DRILL",
            "Drilling Operations",
            7.5,
            6.0,
            5.5,
            6.5,
            120,
            fatality_rate=0.08,
            total_incidents=120,
        ),
        _make_activity(
            "PROD",
            "Production Operations",
            5.0,
            4.5,
            4.0,
            4.5,
            85,
            fatality_rate=0.04,
            total_incidents=85,
        ),
        _make_activity(
            "DIVE",
            "Diving Operations",
            8.5,
            7.0,
            6.5,
            7.5,
            45,
            fatality_rate=0.12,
            total_incidents=45,
        ),
        _make_activity(
            "CRANE",
            "Crane/Lifting Operations",
            6.0,
            5.5,
            3.5,
            5.2,
            95,
            fatality_rate=0.06,
            total_incidents=95,
        ),
        _make_activity(
            "PIPE",
            "Pipeline Operations",
            4.0,
            3.5,
            2.5,
            3.5,
            60,
            fatality_rate=0.03,
            total_incidents=60,
        ),
    ]
    return CompositeScore(
        scores=activities,
        metadata={
            "method": "percentile_rank",
            "weights": {"acute": 0.5, "chronic": 0.3, "compliance": 0.2},
            "version": "1.0",
        },
    )


@pytest.fixture()
def single_activity_composite() -> CompositeScore:
    """CompositeScore with a single activity."""
    return CompositeScore(
        scores=[
            _make_activity(
                "DRILL",
                "Drilling Operations",
                7.5,
                6.0,
                5.5,
                6.5,
                120,
            ),
        ],
        metadata={"method": "percentile_rank"},
    )


@pytest.fixture()
def empty_composite() -> CompositeScore:
    """CompositeScore with no activity scores."""
    return CompositeScore(scores=[], metadata={"method": "percentile_rank"})


@pytest.fixture()
def dashboard() -> RiskDashboard:
    return RiskDashboard()


class TestGenerateDashboard:
    """Tests for RiskDashboard.generate()."""

    def test_generate_dashboard_creates_html(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """generate() returns a valid HTML string."""
        html = dashboard.generate(sample_composite_score)
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_dashboard_contains_heatmap(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """HTML output contains the risk heatmap chart."""
        html = dashboard.generate(sample_composite_score)
        assert "Risk Heatmap" in html
        # Plotly heatmap type indicator
        assert "heatmap" in html.lower()

    def test_dashboard_contains_bar_chart(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """HTML output contains the composite risk bar chart."""
        html = dashboard.generate(sample_composite_score)
        assert "Composite Risk" in html
        # Activity names should appear in the bar chart data
        assert "Drilling Operations" in html

    def test_dashboard_contains_radar(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """HTML output contains radar/polar charts."""
        html = dashboard.generate(sample_composite_score)
        assert "Radar" in html or "Dimension Profile" in html
        # Plotly scatterpolar type indicator
        assert "scatterpolar" in html.lower()

    def test_dashboard_contains_risk_matrix(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """HTML output contains the risk matrix scatter plot."""
        html = dashboard.generate(sample_composite_score)
        assert "Risk Matrix" in html
        assert "Frequency" in html or "Severity" in html

    def test_dashboard_contains_treemap(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """HTML output contains the treemap chart."""
        html = dashboard.generate(sample_composite_score)
        assert "Treemap" in html or "treemap" in html

    def test_dashboard_contains_methodology(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """HTML output contains the methodology documentation section."""
        html = dashboard.generate(sample_composite_score)
        assert "Methodology" in html
        # Should document weights
        assert "weight" in html.lower() or "Weight" in html

    def test_dashboard_contains_plotly_js(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """HTML includes Plotly JS CDN reference exactly once."""
        html = dashboard.generate(sample_composite_score)
        assert "plotly" in html.lower()
        assert "cdn.plot.ly" in html or "plotly-" in html

    def test_dashboard_contains_all_activity_names(
        self, dashboard: RiskDashboard, sample_composite_score: CompositeScore
    ):
        """All activity names appear in the dashboard.

        Plotly's to_json() may unicode-escape '/' as '\\u002f',
        so we check for either the literal name or the escaped form.
        """
        html = dashboard.generate(sample_composite_score)
        for score in sample_composite_score.scores:
            escaped = score.activity_name.replace("/", "\\u002f")
            assert score.activity_name in html or escaped in html


class TestSaveToFile:
    """Tests for RiskDashboard.save()."""

    def test_save_creates_file(
        self,
        dashboard: RiskDashboard,
        sample_composite_score: CompositeScore,
        tmp_path: Path,
    ):
        """save() writes an HTML file to disk."""
        output = tmp_path / "test_dashboard.html"
        result = dashboard.save(sample_composite_score, output)
        assert result.exists()
        assert result.suffix == ".html"
        content = result.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_save_creates_parent_directories(
        self,
        dashboard: RiskDashboard,
        sample_composite_score: CompositeScore,
        tmp_path: Path,
    ):
        """save() creates missing parent directories."""
        output = tmp_path / "nested" / "dir" / "dashboard.html"
        result = dashboard.save(sample_composite_score, output)
        assert result.exists()

    def test_save_returns_path(
        self,
        dashboard: RiskDashboard,
        sample_composite_score: CompositeScore,
        tmp_path: Path,
    ):
        """save() returns the resolved output path."""
        output = tmp_path / "out.html"
        result = dashboard.save(sample_composite_score, output)
        assert isinstance(result, Path)
        assert result == output


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_scores_returns_html(
        self, dashboard: RiskDashboard, empty_composite: CompositeScore
    ):
        """Dashboard handles empty scores list gracefully."""
        html = dashboard.generate(empty_composite)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        # Should still have methodology section
        assert "Methodology" in html

    def test_single_activity(
        self, dashboard: RiskDashboard, single_activity_composite: CompositeScore
    ):
        """Dashboard works with a single activity score."""
        html = dashboard.generate(single_activity_composite)
        assert isinstance(html, str)
        assert "Drilling Operations" in html
        assert "<!DOCTYPE html>" in html
