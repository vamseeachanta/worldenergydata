# ABOUTME: Tests for dashboard.py — Plotly HTML dashboard generation.

"""Tests for MetoceanDashboard Plotly output generation."""

from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.metocean.unified.dashboard import MetoceanDashboard
from worldenergydata.metocean.unified.unified_query import MetoceanQuery, MetoceanResult


def _make_multi_source_df():
    rows = []
    for h in range(24):
        ts = datetime(2023, 6, 1, h, 0)
        for source, base in [("ndbc", 1.0), ("open_meteo", 1.1), ("met_norway", 0.9)]:
            rows.extend(
                [
                    {"timestamp": ts, "parameter": "Hs", "value": base + h * 0.05,
                     "source": source, "unit": "m"},
                    {"timestamp": ts, "parameter": "wind_speed",
                     "value": 5.0 + h * 0.1, "source": source, "unit": "m/s"},
                ]
            )
    return pd.DataFrame(rows)


def _make_query():
    return MetoceanQuery(
        lat=28.5,
        lon=-88.5,
        start_date=datetime(2023, 6, 1),
        end_date=datetime(2023, 6, 2),
    )


def _make_result(df=None):
    if df is None:
        df = _make_multi_source_df()
    return MetoceanResult(
        query=_make_query(),
        data=df,
        sources_used=["ndbc", "open_meteo", "met_norway"],
        coverage_gaps=[],
    )


class TestMetoceanDashboardCreation:
    def test_dashboard_can_be_instantiated(self):
        d = MetoceanDashboard()
        assert d is not None

    def test_build_dashboard_returns_string(self):
        d = MetoceanDashboard()
        result = _make_result()
        html = d.build(result)
        assert isinstance(html, str)

    def test_build_dashboard_html_not_empty(self):
        d = MetoceanDashboard()
        html = d.build(_make_result())
        assert len(html) > 100

    def test_build_dashboard_contains_html_tag(self):
        d = MetoceanDashboard()
        html = d.build(_make_result())
        assert "<html" in html.lower() or "plotly" in html.lower()


class TestMetoceanDashboardPanels:
    def test_build_includes_time_series_panel(self):
        d = MetoceanDashboard()
        fig = d.build_time_series(_make_result())
        assert fig is not None

    def test_time_series_returns_plotly_figure(self):
        """build_time_series should return a plotly Figure or dict."""
        import plotly.graph_objects as go

        d = MetoceanDashboard()
        fig = d.build_time_series(_make_result())
        assert isinstance(fig, (go.Figure, dict))

    def test_build_source_comparison_returns_figure(self):
        import plotly.graph_objects as go

        d = MetoceanDashboard()
        fig = d.build_source_comparison(_make_result(), parameter="Hs")
        assert isinstance(fig, (go.Figure, dict))

    def test_build_coverage_map_returns_figure(self):
        import plotly.graph_objects as go

        d = MetoceanDashboard()
        fig = d.build_coverage_map(_make_result())
        assert isinstance(fig, (go.Figure, dict))

    def test_build_summary_stats_returns_dataframe(self):
        d = MetoceanDashboard()
        stats = d.build_summary_stats(_make_result())
        assert isinstance(stats, pd.DataFrame)
        assert len(stats) > 0


class TestMetoceanDashboardEdgeCases:
    def test_empty_data_does_not_crash(self):
        d = MetoceanDashboard()
        empty_df = pd.DataFrame(
            columns=["timestamp", "parameter", "value", "source", "unit"]
        )
        result = MetoceanResult(
            query=_make_query(),
            data=empty_df,
            sources_used=[],
            coverage_gaps=[],
        )
        html = d.build(result)
        assert isinstance(html, str)

    def test_single_source_dashboard(self):
        d = MetoceanDashboard()
        rows = [
            {"timestamp": datetime(2023, 6, 1, h, 0), "parameter": "Hs",
             "value": 1.5, "source": "ndbc", "unit": "m"}
            for h in range(5)
        ]
        df = pd.DataFrame(rows)
        result = MetoceanResult(
            query=_make_query(), data=df, sources_used=["ndbc"], coverage_gaps=[]
        )
        html = d.build(result)
        assert isinstance(html, str)

    def test_save_dashboard_to_file(self, tmp_path):
        d = MetoceanDashboard()
        out_path = tmp_path / "dashboard.html"
        d.save(_make_result(), str(out_path))
        assert out_path.exists()
        content = out_path.read_text()
        assert len(content) > 100
