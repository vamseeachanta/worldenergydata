"""Tests for economic_charts EconomicMetrics and EconomicChart."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.bsee.reports.comprehensive.visualizations.economic_charts import (
    EconomicChart,
    EconomicMetrics,
)

# ---------------------------------------------------------------------------
# EconomicMetrics dataclass
# ---------------------------------------------------------------------------


class TestEconomicMetrics:
    def test_init(self):
        em = EconomicMetrics(
            revenue=1000000,
            operating_costs=400000,
            capital_costs=200000,
            net_income=400000,
            roi=20.0,
            payback_period=3.5,
            npv=500000,
            irr=18.0,
        )
        assert em.revenue == 1000000
        assert em.roi == 20.0
        assert em.irr == 18.0


# ---------------------------------------------------------------------------
# EconomicChart init
# ---------------------------------------------------------------------------


class TestEconomicChartInit:
    def test_default(self):
        chart = EconomicChart()
        assert chart.currency == "USD"
        assert chart.theme == "plotly_white"

    def test_custom(self):
        chart = EconomicChart(currency="NOK", theme="plotly_dark")
        assert chart.currency == "NOK"


# ---------------------------------------------------------------------------
# create_waterfall_chart
# ---------------------------------------------------------------------------


class TestCreateWaterfallChart:
    def test_basic(self):
        chart = EconomicChart()
        categories = ["Revenue", "OPEX", "CAPEX", "Net Income"]
        values = [1000000, -400000, -200000, 400000]
        fig = chart.create_waterfall_chart(categories, values)
        assert isinstance(fig, go.Figure)

    def test_with_measure(self):
        chart = EconomicChart()
        categories = ["Revenue", "OPEX", "CAPEX", "Total"]
        values = [1000000, -400000, -200000, 400000]
        measure = ["absolute", "relative", "relative", "total"]
        fig = chart.create_waterfall_chart(categories, values, measure=measure)
        assert isinstance(fig, go.Figure)

    def test_custom_title(self):
        chart = EconomicChart()
        fig = chart.create_waterfall_chart(["A", "B"], [100, -50], title="Custom Title")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_roi_analysis
# ---------------------------------------------------------------------------


class TestCreateRoiAnalysis:
    def test_basic(self):
        chart = EconomicChart()
        metrics = EconomicMetrics(
            revenue=10_000_000,
            operating_costs=4_000_000,
            capital_costs=2_000_000,
            net_income=4_000_000,
            roi=20.0,
            payback_period=3.5,
            npv=5_000_000,
            irr=22.0,
        )
        fig = chart.create_roi_analysis(metrics)
        assert isinstance(fig, go.Figure)

    def test_with_benchmarks(self):
        chart = EconomicChart()
        metrics = EconomicMetrics(
            revenue=5_000_000,
            operating_costs=2_000_000,
            capital_costs=1_000_000,
            net_income=2_000_000,
            roi=12.0,
            payback_period=4.5,
            npv=2_000_000,
            irr=16.0,
        )
        benchmarks = {"roi": 15, "npv": 3_000_000, "irr": 18, "payback": 3}
        fig = chart.create_roi_analysis(metrics, benchmarks=benchmarks)
        assert isinstance(fig, go.Figure)

    def test_low_performance(self):
        chart = EconomicChart()
        metrics = EconomicMetrics(
            revenue=2_000_000,
            operating_costs=1_500_000,
            capital_costs=1_000_000,
            net_income=-500_000,
            roi=5.0,
            payback_period=7.0,
            npv=-1_000_000,
            irr=8.0,
        )
        fig = chart.create_roi_analysis(metrics)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_cashflow_projection
# ---------------------------------------------------------------------------


class TestCreateCashflowProjection:
    def test_basic(self):
        chart = EconomicChart()
        idx = pd.date_range("2024-01-01", periods=12, freq="MS")
        data = pd.DataFrame(
            {
                "net_cashflow": [
                    -500000,
                    -200000,
                    100000,
                    200000,
                    300000,
                    350000,
                    400000,
                    380000,
                    360000,
                    340000,
                    320000,
                    300000,
                ],
            },
            index=idx,
        )
        fig = chart.create_cashflow_projection(data)
        assert isinstance(fig, go.Figure)

    def test_no_cumulative(self):
        chart = EconomicChart()
        idx = pd.date_range("2024-01-01", periods=6, freq="MS")
        data = pd.DataFrame({"net_cashflow": [100000] * 6}, index=idx)
        fig = chart.create_cashflow_projection(data, show_cumulative=False)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_cost_breakdown
# ---------------------------------------------------------------------------


class TestCreateCostBreakdown:
    def test_pie_chart(self):
        chart = EconomicChart()
        costs = {"Labor": 500000, "Materials": 300000, "Equipment": 200000}
        fig = chart.create_cost_breakdown(costs, chart_type="pie")
        assert isinstance(fig, go.Figure)

    def test_sunburst_chart(self):
        chart = EconomicChart()
        costs = {"Labor": 500000, "Materials": 300000, "Equipment": 200000}
        fig = chart.create_cost_breakdown(costs, chart_type="sunburst")
        assert isinstance(fig, go.Figure)
