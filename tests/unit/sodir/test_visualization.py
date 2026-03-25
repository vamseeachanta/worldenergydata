"""Tests for SODIR visualization module."""

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for testing

import numpy as np
import pandas as pd
import pytest

from worldenergydata.sodir.visualization import (
    ChartConfig,
    ChartType,
    DashboardGenerator,
    MapVisualization,
    SodirVisualizer,
)


# ---------------------------------------------------------------------------
# ChartType enum
# ---------------------------------------------------------------------------

class TestChartType:
    def test_values(self):
        assert ChartType.LINE.value == "line"
        assert ChartType.BAR.value == "bar"
        assert ChartType.SCATTER.value == "scatter"
        assert ChartType.HEATMAP.value == "heatmap"

    def test_all_members(self):
        assert len(ChartType) == 9


# ---------------------------------------------------------------------------
# ChartConfig
# ---------------------------------------------------------------------------

class TestChartConfig:
    def test_basic(self):
        config = ChartConfig(title="Test", chart_type=ChartType.LINE)
        assert config.title == "Test"
        assert config.chart_type == ChartType.LINE

    def test_string_to_enum(self):
        config = ChartConfig(title="Test", chart_type="bar")
        assert config.chart_type == ChartType.BAR

    def test_defaults(self):
        config = ChartConfig(title="Test", chart_type="line")
        assert config.x_label == ""
        assert config.y_label == ""
        assert config.figsize == (12, 6)
        assert config.show_legend is True
        assert config.show_grid is True


# ---------------------------------------------------------------------------
# MapVisualization
# ---------------------------------------------------------------------------

class TestMapVisualization:
    def test_add_layer(self):
        mv = MapVisualization(figure=None, layers={}, bounds="test")
        mv.add_layer("fields", [1, 2, 3])
        assert "fields" in mv.layers
        assert mv.layers["fields"] == [1, 2, 3]

    def test_save_no_figure(self, tmp_path):
        mv = MapVisualization(figure=None, layers={}, bounds="test")
        # Should not raise even with no figure
        mv.save(str(tmp_path / "test.png"))

    def test_defaults(self):
        mv = MapVisualization(figure=None, layers={}, bounds="ncs")
        assert mv.projection == "mercator"


# ---------------------------------------------------------------------------
# DashboardGenerator
# ---------------------------------------------------------------------------

class TestDashboardGenerator:
    def test_generate_single(self):
        import matplotlib.pyplot as plt
        dg = DashboardGenerator(charts=[None], layout=(1, 1))
        fig = dg.generate()
        assert fig is not None
        assert dg.figure is not None
        plt.close(fig)

    def test_generate_grid(self):
        import matplotlib.pyplot as plt
        dg = DashboardGenerator(charts=[None, None, None, None], layout=(2, 2))
        fig = dg.generate()
        assert fig is not None
        plt.close(fig)

    def test_save_no_figure(self, tmp_path):
        dg = DashboardGenerator(charts=[], layout=(1, 1))
        dg.save(str(tmp_path / "test.png"))  # No figure yet, should not raise


# ---------------------------------------------------------------------------
# SodirVisualizer
# ---------------------------------------------------------------------------

class TestSodirVisualizerInit:
    def test_init(self):
        viz = SodirVisualizer()
        assert viz.figures == []


class TestCreateFieldMap:
    def test_basic(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        df = pd.DataFrame({
            "longitude": [5.0, 7.0],
            "latitude": [60.0, 62.0],
        })
        result = viz.create_field_map(df)
        assert isinstance(result, MapVisualization)
        assert result.bounds == "norwegian_continental_shelf"
        assert len(viz.figures) == 1
        plt.close("all")

    def test_with_config(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        df = pd.DataFrame({
            "longitude": [5.0],
            "latitude": [60.0],
        })
        config = ChartConfig(title="Custom Title", chart_type=ChartType.SCATTER_MAP)
        result = viz.create_field_map(df, config=config)
        assert result is not None
        plt.close("all")

    def test_without_coordinates(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        df = pd.DataFrame({"field_name": ["Troll"]})
        result = viz.create_field_map(df)
        assert isinstance(result, MapVisualization)
        plt.close("all")


class TestCreateProductionChart:
    def test_line_chart(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        data = pd.DataFrame({
            "year": [2020, 2021, 2022],
            "oil": [100.0, 90.0, 80.0],
            "gas": [500.0, 450.0, 400.0],
        })
        chart = viz.create_production_chart(data, chart_type="line")
        assert "figure" in chart
        assert "series" in chart
        plt.close("all")

    def test_stacked_area(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        data = pd.DataFrame({
            "year": [2020, 2021],
            "oil": [100.0, 90.0],
            "gas": [500.0, 450.0],
        })
        chart = viz.create_production_chart(data, chart_type="stacked_area")
        assert chart is not None
        plt.close("all")

    def test_bar_chart(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        data = pd.DataFrame({
            "year": [2020, 2021],
            "oil": [100.0, 90.0],
            "gas": [500.0, 450.0],
        })
        chart = viz.create_production_chart(data, chart_type="bar")
        assert chart is not None
        plt.close("all")

    def test_no_year_column(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        data = pd.DataFrame({"oil": [100.0, 90.0]})
        chart = viz.create_production_chart(data)
        assert chart is not None
        plt.close("all")


class TestCreateComparisonDashboard:
    def test_default_metrics(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        sodir = {"fields": pd.DataFrame({
            "recovery_factor": [0.5, 0.6],
            "water_depth_m": [100.0, 200.0],
            "recoverable_oil_mmbbl": pd.Series([100.0, 200.0]),
            "recoverable_gas_bcf": pd.Series([50.0, 60.0]),
        })}
        bsee = {"fields": pd.DataFrame({
            "recovery_factor": [0.4, 0.3],
            "water_depth_m": [150.0, 250.0],
            "recoverable_oil_mmbbl": pd.Series([80.0, 120.0]),
            "recoverable_gas_bcf": pd.Series([40.0, 55.0]),
        })}
        dashboard = viz.create_comparison_dashboard(sodir, bsee)
        assert isinstance(dashboard, DashboardGenerator)
        assert len(dashboard.charts) == 4
        plt.close("all")

    def test_custom_metrics(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        sodir = {}
        bsee = {}
        dashboard = viz.create_comparison_dashboard(sodir, bsee, metrics=["production_rate"])
        assert len(dashboard.charts) == 1
        plt.close("all")

    def test_layout_selection(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        sodir = {}
        bsee = {}
        # 2 metrics -> (1,2) layout
        d2 = viz.create_comparison_dashboard(sodir, bsee, metrics=["a", "b"])
        assert d2.layout == (1, 2)
        # 6 metrics -> (2,3) layout
        d6 = viz.create_comparison_dashboard(sodir, bsee, metrics=["a","b","c","d","e","f"])
        assert d6.layout == (2, 3)
        # 7+ metrics -> (3,3) layout
        d7 = viz.create_comparison_dashboard(sodir, bsee, metrics=["a","b","c","d","e","f","g"])
        assert d7.layout == (3, 3)
        plt.close("all")


class TestExportChart:
    def test_export_dict_chart(self, tmp_path):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4])
        chart = {"figure": fig}
        viz.export_chart(chart, str(tmp_path / "test.png"))
        assert (tmp_path / "test.png").exists()
        plt.close("all")

    def test_export_creates_parent_dir(self, tmp_path):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        fig, ax = plt.subplots()
        chart = {"figure": fig}
        viz.export_chart(chart, str(tmp_path / "sub" / "test.png"))
        assert (tmp_path / "sub" / "test.png").exists()
        plt.close("all")


class TestFieldRankingChart:
    def test_basic(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        df = pd.DataFrame({
            "field_name": ["Troll", "Ekofisk", "Johan Sverdrup"],
            "recoverable_oil_mmbbl": [1000, 500, 2000],
        })
        chart = viz.create_field_ranking_chart(df, top_n=2)
        assert chart["ranking_metric"] == "recoverable_oil_mmbbl"
        assert len(chart["data"]) == 2
        plt.close("all")


class TestDiscoveryTimeline:
    def test_basic(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        df = pd.DataFrame({
            "discovery_year": [1969, 1969, 1979, 2010],
        })
        chart = viz.create_discovery_timeline(df)
        assert chart["discovery_counts"] is not None
        assert chart["cumulative"] is not None
        plt.close("all")


class TestCorrelationHeatmap:
    def test_basic(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        df = pd.DataFrame({
            "oil": [100, 200, 300],
            "gas": [500, 600, 700],
            "depth": [1000, 2000, 3000],
        })
        chart = viz.create_correlation_heatmap(df)
        assert "correlation_matrix" in chart
        plt.close("all")

    def test_with_columns(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        df = pd.DataFrame({
            "oil": [100, 200, 300],
            "gas": [500, 600, 700],
            "name": ["A", "B", "C"],
        })
        chart = viz.create_correlation_heatmap(df, columns=["oil", "gas"])
        assert chart["correlation_matrix"].shape == (2, 2)
        plt.close("all")


class TestCloseAll:
    def test_close_all(self):
        import matplotlib.pyplot as plt
        viz = SodirVisualizer()
        fig1, _ = plt.subplots()
        fig2, _ = plt.subplots()
        viz.figures = [fig1, fig2]
        viz.close_all()
        assert viz.figures == []
