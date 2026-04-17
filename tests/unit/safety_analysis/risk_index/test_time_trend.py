"""Tests for the time-trend chart in the risk dashboard."""

import pandas as pd
import pytest

from worldenergydata.safety_analysis.risk_index.dashboard import RiskDashboard
from worldenergydata.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    DimensionScore,
)


def _make_dimension(name: str, score: float) -> DimensionScore:
    return DimensionScore(
        dimension=name,
        raw_metrics={"test": 1.0},
        score=score,
    )


def _make_composite_with_scores() -> CompositeScore:
    """Create a minimal CompositeScore for testing."""
    scores = [
        ActivityRiskScore(
            activity_code="TEST",
            activity_name="Test Activity",
            acute=_make_dimension("acute", 5.0),
            chronic=_make_dimension("chronic", 3.0),
            compliance=_make_dimension("compliance", 4.0),
            composite_score=4.25,
            incident_count=50,
            confidence="high",
            sources=["bsee"],
        ),
    ]
    return CompositeScore(scores=scores)


class TestTimeTrendChart:
    """Time-trend chart generation."""

    def test_dashboard_with_time_series_contains_trend(self):
        composite = _make_composite_with_scores()
        time_series = pd.DataFrame(
            {
                "year": [2018, 2019, 2020, 2021, 2022],
                "composite_score": [3.5, 4.0, 5.2, 4.8, 6.1],
            }
        )
        dashboard = RiskDashboard()
        html = dashboard.generate(composite, time_series=time_series)
        assert "chart-trend" in html
        assert "Risk Trend Over Time" in html

    def test_dashboard_without_time_series_no_trend(self):
        composite = _make_composite_with_scores()
        dashboard = RiskDashboard()
        html = dashboard.generate(composite)
        assert "chart-trend" not in html

    def test_empty_time_series_no_trend(self):
        composite = _make_composite_with_scores()
        time_series = pd.DataFrame(columns=["year", "composite_score"])
        dashboard = RiskDashboard()
        html = dashboard.generate(composite, time_series=time_series)
        assert "chart-trend" not in html

    def test_trend_chart_contains_rolling_avg(self):
        composite = _make_composite_with_scores()
        time_series = pd.DataFrame(
            {
                "year": list(range(2015, 2025)),
                "composite_score": [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 5.5, 5.0, 4.5],
            }
        )
        dashboard = RiskDashboard()
        html = dashboard.generate(composite, time_series=time_series)
        assert "3-Year Rolling Avg" in html

    def test_short_time_series_no_rolling(self):
        composite = _make_composite_with_scores()
        time_series = pd.DataFrame(
            {
                "year": [2022, 2023],
                "composite_score": [4.0, 5.0],
            }
        )
        dashboard = RiskDashboard()
        html = dashboard.generate(composite, time_series=time_series)
        assert "chart-trend" in html
        # Only 2 points: no rolling average trace
        assert "3-Year Rolling Avg" not in html

    def test_save_with_time_series(self, tmp_path):
        composite = _make_composite_with_scores()
        time_series = pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023],
                "composite_score": [3.0, 4.0, 5.0, 4.5],
            }
        )
        dashboard = RiskDashboard()
        out_path = dashboard.save(
            composite, tmp_path / "test.html", time_series=time_series
        )
        assert out_path.exists()
        content = out_path.read_text()
        assert "Risk Trend Over Time" in content
