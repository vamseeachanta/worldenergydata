"""Tests for dashboard_builder DashboardBuilder and related classes."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.reports.comprehensive.visualizations.dashboard_builder import (
    ChartConfig,
    DashboardBuilder,
    DashboardConfig,
)


# ---------------------------------------------------------------------------
# DashboardConfig dataclass
# ---------------------------------------------------------------------------

class TestDashboardConfig:
    def test_defaults(self):
        cfg = DashboardConfig(title="Test Dashboard")
        assert cfg.title == "Test Dashboard"
        assert cfg.theme == "plotly_white"
        assert cfg.auto_refresh is False
        assert cfg.refresh_interval == 60000
        assert cfg.enable_export is True
        assert cfg.enable_filters is True
        assert cfg.responsive is True

    def test_custom(self):
        cfg = DashboardConfig(
            title="Custom", theme="plotly_dark", auto_refresh=True,
            refresh_interval=30000, enable_export=False,
        )
        assert cfg.theme == "plotly_dark"
        assert cfg.auto_refresh is True
        assert cfg.refresh_interval == 30000


# ---------------------------------------------------------------------------
# ChartConfig dataclass
# ---------------------------------------------------------------------------

class TestChartConfig:
    def test_required_fields(self):
        cc = ChartConfig(
            chart_id="chart1", chart_type="line",
            title="Test Chart", data_source="production",
        )
        assert cc.chart_id == "chart1"
        assert cc.update_callback is None
        assert cc.filters is None

    def test_with_filters(self):
        cc = ChartConfig(
            chart_id="chart2", chart_type="bar",
            title="Bar", data_source="revenue",
            filters=["field", "year"],
        )
        assert cc.filters == ["field", "year"]


# ---------------------------------------------------------------------------
# DashboardBuilder init
# ---------------------------------------------------------------------------

class TestDashboardBuilderInit:
    def test_default(self):
        builder = DashboardBuilder()
        assert builder.config.title == "Dashboard"
        assert builder.charts == []
        assert builder.filters == {}
        assert builder.data_sources == {}
        assert builder.app is None

    def test_custom_config(self):
        cfg = DashboardConfig(title="My Dashboard")
        builder = DashboardBuilder(config=cfg)
        assert builder.config.title == "My Dashboard"


# ---------------------------------------------------------------------------
# add_chart / add_filter / set_data_source
# ---------------------------------------------------------------------------

class TestBuilderMethods:
    def test_add_chart(self):
        builder = DashboardBuilder()
        cc = ChartConfig("c1", "line", "Title", "src")
        builder.add_chart(cc)
        assert len(builder.charts) == 1
        assert builder.charts[0].chart_id == "c1"

    def test_add_multiple_charts(self):
        builder = DashboardBuilder()
        builder.add_chart(ChartConfig("c1", "line", "T1", "s1"))
        builder.add_chart(ChartConfig("c2", "bar", "T2", "s2"))
        assert len(builder.charts) == 2

    def test_add_filter(self):
        builder = DashboardBuilder()
        builder.add_filter("field", ["Field A", "Field B"], default="Field A")
        assert "field" in builder.filters
        assert builder.filters["field"]["default"] == "Field A"
        assert builder.filters["field"]["options"] == ["Field A", "Field B"]

    def test_add_filter_no_default(self):
        builder = DashboardBuilder()
        builder.add_filter("year", [2023, 2024])
        assert builder.filters["year"]["default"] == 2023  # first option

    def test_add_filter_empty_options(self):
        builder = DashboardBuilder()
        builder.add_filter("empty", [])
        assert builder.filters["empty"]["default"] is None

    def test_set_data_source(self):
        builder = DashboardBuilder()
        df = pd.DataFrame({"col": [1, 2, 3]})
        builder.set_data_source("production", df)
        assert "production" in builder.data_sources


# ---------------------------------------------------------------------------
# create_kpi_cards
# ---------------------------------------------------------------------------

class TestCreateKpiCards:
    @pytest.mark.skip(reason="Requires Dash installed; MockHtml returns None")
    def test_basic_kpis(self):
        builder = DashboardBuilder()
        kpis = {
            "Production": {"value": 10000, "change": 5.2, "unit": "BBL"},
            "Efficiency": {"value": 87.5, "change": -2.1, "unit": "%"},
            "Safety": {"value": 0.5, "change": 0, "unit": "TRIR"},
        }
        result = builder.create_kpi_cards(kpis)
        assert result is not None

    @pytest.mark.skip(reason="Requires Dash installed; MockHtml returns None")
    def test_empty_kpis(self):
        builder = DashboardBuilder()
        result = builder.create_kpi_cards({})
        assert result is not None


# ---------------------------------------------------------------------------
# create_filter_panel
# ---------------------------------------------------------------------------

class TestCreateFilterPanel:
    @pytest.mark.skip(reason="Requires Dash installed; MockHtml missing Label")
    def test_with_dropdown(self):
        builder = DashboardBuilder()
        builder.add_filter("field", ["Field A", "Field B"])
        result = builder.create_filter_panel()
        assert result is not None

    @pytest.mark.skip(reason="Requires Dash installed; MockHtml missing Label")
    def test_with_date_filter(self):
        builder = DashboardBuilder()
        builder.add_filter("start_date", ["2024-01-01", "2024-12-31"])
        result = builder.create_filter_panel()
        assert result is not None

    @pytest.mark.skip(reason="Requires Dash installed; MockHtml missing Label")
    def test_empty_filters(self):
        builder = DashboardBuilder()
        result = builder.create_filter_panel()
        assert result is not None


# ---------------------------------------------------------------------------
# export_dashboard
# ---------------------------------------------------------------------------

class TestExportDashboard:
    def test_no_app_returns_false(self):
        builder = DashboardBuilder()
        result = builder.export_dashboard(format="html")
        assert result is False

    def test_png_format_no_app(self):
        builder = DashboardBuilder()
        result = builder.export_dashboard(format="png")
        assert result is False

    def test_unknown_format(self):
        builder = DashboardBuilder()
        result = builder.export_dashboard(format="docx")
        assert result is False


# ---------------------------------------------------------------------------
# add_drill_down / enable_cross_filtering (no app)
# ---------------------------------------------------------------------------

class TestDrillDownAndCrossFilter:
    def test_drill_down_no_app(self):
        builder = DashboardBuilder()
        # Should not raise when app is None
        builder.add_drill_down("chart1", lambda x: None)

    def test_cross_filtering_no_app(self):
        builder = DashboardBuilder()
        builder.enable_cross_filtering(["chart1", "chart2"])
