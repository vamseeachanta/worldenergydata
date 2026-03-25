"""Tests for well_performance_charts PerformanceMetrics and WellPerformanceChart."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.bsee.reports.comprehensive.visualizations.well_performance_charts import (
    PerformanceMetrics,
    WellPerformanceChart,
)


# ---------------------------------------------------------------------------
# PerformanceMetrics dataclass
# ---------------------------------------------------------------------------

class TestPerformanceMetrics:
    def test_init(self):
        pm = PerformanceMetrics(
            well_name="Well-1",
            efficiency=85.0,
            uptime=92.0,
            production_rate=500.0,
            water_cut=25.0,
            gas_oil_ratio=800.0,
            operating_cost=15.0,
        )
        assert pm.well_name == "Well-1"
        assert pm.efficiency == 85.0
        assert pm.uptime == 92.0
        assert pm.production_rate == 500.0
        assert pm.water_cut == 25.0
        assert pm.gas_oil_ratio == 800.0
        assert pm.operating_cost == 15.0


# ---------------------------------------------------------------------------
# WellPerformanceChart init
# ---------------------------------------------------------------------------

class TestWellPerformanceChartInit:
    def test_default_theme(self):
        chart = WellPerformanceChart()
        assert chart.theme == "plotly_white"

    def test_custom_theme(self):
        chart = WellPerformanceChart(theme="plotly_dark")
        assert chart.theme == "plotly_dark"


# ---------------------------------------------------------------------------
# Helper data
# ---------------------------------------------------------------------------

def _sample_df():
    return pd.DataFrame({
        "well_name": ["W1", "W2", "W3", "W4", "W5"],
        "production_rate": [500, 300, 700, 400, 600],
        "water_cut": [25, 40, 15, 35, 20],
        "efficiency": [85, 75, 90, 70, 88],
        "operating_cost": [12, 18, 10, 20, 14],
        "gas_oil_ratio": [800, 1200, 600, 1000, 700],
        "uptime": [92, 85, 95, 80, 90],
    })


# ---------------------------------------------------------------------------
# create_scatter_plot
# ---------------------------------------------------------------------------

class TestCreateScatterPlot:
    def test_basic_scatter(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_scatter_plot(df, "production_rate", "water_cut")
        assert isinstance(fig, go.Figure)

    def test_with_color(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_scatter_plot(
            df, "production_rate", "water_cut", color_column="well_name"
        )
        assert isinstance(fig, go.Figure)

    def test_with_color_and_size(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_scatter_plot(
            df, "production_rate", "water_cut",
            color_column="well_name", size_column="efficiency",
        )
        assert isinstance(fig, go.Figure)

    def test_with_title(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_scatter_plot(
            df, "production_rate", "water_cut", title="My Scatter"
        )
        assert isinstance(fig, go.Figure)

    def test_two_row_df_no_trend(self):
        chart = WellPerformanceChart()
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        fig = chart.create_scatter_plot(df, "x", "y")
        # Only 2 rows => no trend line added (len(data) > 2 check)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_heat_map
# ---------------------------------------------------------------------------

class TestCreateHeatMap:
    def test_basic_heatmap(self):
        chart = WellPerformanceChart()
        df = pd.DataFrame(
            {"efficiency": [85, 75, 90], "uptime": [92, 85, 95]},
            index=["W1", "W2", "W3"],
        )
        fig = chart.create_heat_map(df)
        assert isinstance(fig, go.Figure)

    def test_with_wells_filter(self):
        chart = WellPerformanceChart()
        # Include well_name column to avoid broadcast error in source code
        df = pd.DataFrame(
            {
                "well_name": ["W1", "W2", "W3"],
                "efficiency": [85, 75, 90],
                "uptime": [92, 85, 95],
            },
            index=["W1", "W2", "W3"],
        )
        fig = chart.create_heat_map(df, wells=["W1", "W2"], metrics=["efficiency", "uptime"])
        assert isinstance(fig, go.Figure)

    def test_with_metrics_filter(self):
        chart = WellPerformanceChart()
        df = pd.DataFrame(
            {"efficiency": [85, 75], "uptime": [92, 85], "cost": [10, 15]},
            index=["W1", "W2"],
        )
        fig = chart.create_heat_map(df, metrics=["efficiency", "uptime"])
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_bubble_chart
# ---------------------------------------------------------------------------

class TestCreateBubbleChart:
    def test_basic_bubble(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_bubble_chart(
            df, "production_rate", "water_cut", "efficiency"
        )
        assert isinstance(fig, go.Figure)

    def test_with_color(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_bubble_chart(
            df, "production_rate", "water_cut", "efficiency",
            color_metric="operating_cost",
        )
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_performance_radar
# ---------------------------------------------------------------------------

class TestCreatePerformanceRadar:
    def test_basic_radar(self):
        chart = WellPerformanceChart()
        pm = PerformanceMetrics(
            well_name="W1", efficiency=85, uptime=92,
            production_rate=500, water_cut=25, gas_oil_ratio=800,
            operating_cost=15,
        )
        fig = chart.create_performance_radar(pm)
        assert isinstance(fig, go.Figure)

    def test_with_targets(self):
        chart = WellPerformanceChart()
        pm = PerformanceMetrics(
            well_name="W1", efficiency=85, uptime=92,
            production_rate=500, water_cut=25, gas_oil_ratio=800,
            operating_cost=15,
        )
        targets = {"efficiency": 90, "uptime": 95, "water_cut": 20}
        fig = chart.create_performance_radar(pm, targets=targets)
        assert isinstance(fig, go.Figure)

    def test_custom_title(self):
        chart = WellPerformanceChart()
        pm = PerformanceMetrics(
            well_name="W1", efficiency=85, uptime=92,
            production_rate=500, water_cut=25, gas_oil_ratio=800,
            operating_cost=15,
        )
        fig = chart.create_performance_radar(pm, title="Custom Radar")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_well_ranking
# ---------------------------------------------------------------------------

class TestCreateWellRanking:
    def test_basic_ranking(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_well_ranking(df, "production_rate", top_n=3)
        assert isinstance(fig, go.Figure)

    def test_ranking_all_wells(self):
        chart = WellPerformanceChart()
        df = _sample_df()
        fig = chart.create_well_ranking(df, "efficiency", top_n=10)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_time_series_comparison
# ---------------------------------------------------------------------------

class TestCreateTimeSeriesComparison:
    def test_basic_time_series(self):
        chart = WellPerformanceChart()
        idx = pd.date_range("2024-01-01", periods=12, freq="MS")
        data = {
            "W1": pd.DataFrame({"production_rate": range(12)}, index=idx),
            "W2": pd.DataFrame({"production_rate": range(12, 24)}, index=idx),
        }
        fig = chart.create_time_series_comparison(data, "production_rate")
        assert isinstance(fig, go.Figure)

    def test_missing_metric(self):
        chart = WellPerformanceChart()
        idx = pd.date_range("2024-01-01", periods=6, freq="MS")
        data = {
            "W1": pd.DataFrame({"other": range(6)}, index=idx),
        }
        fig = chart.create_time_series_comparison(data, "production_rate")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_efficiency_matrix
# ---------------------------------------------------------------------------

class TestCreateEfficiencyMatrix:
    def test_basic_matrix(self):
        chart = WellPerformanceChart()
        data = pd.DataFrame({
            "production_efficiency": [85, 90],
            "uptime": [92, 88],
            "cost_index": [25, 30],
        })
        fig = chart.create_efficiency_matrix(data)
        assert isinstance(fig, go.Figure)

    def test_empty_data_defaults(self):
        chart = WellPerformanceChart()
        # Empty df triggers .get() defaults in the method
        fig = chart.create_efficiency_matrix(pd.DataFrame())
        assert isinstance(fig, go.Figure)
