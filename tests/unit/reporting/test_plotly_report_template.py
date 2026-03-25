"""Tests for reporting.templates.plotly_report_template PlotlyReportGenerator."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.reporting.templates.plotly_report_template import (
    PlotlyReportGenerator,
)


class TestPlotlyReportGeneratorInit:
    def test_basic_init(self):
        gen = PlotlyReportGenerator("Title", "mod", "repo")
        assert gen.title == "Title"
        assert gen.module_name == "mod"
        assert gen.repository_name == "repo"
        assert gen.figures == []
        assert gen.summary_stats == {}


class TestAddSummaryStat:
    def test_add_stat(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_summary_stat("Records", "100")
        assert "Records" in gen.summary_stats
        assert gen.summary_stats["Records"]["value"] == "100"
        assert gen.summary_stats["Records"]["unit"] == ""

    def test_add_stat_with_unit(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_summary_stat("Volume", "500", "bbl")
        assert gen.summary_stats["Volume"]["unit"] == "bbl"

    def test_add_multiple_stats(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_summary_stat("A", "1")
        gen.add_summary_stat("B", "2")
        assert len(gen.summary_stats) == 2


class TestAddPlots:
    def _sample_df(self):
        return pd.DataFrame({
            "x": [1, 2, 3],
            "y": [10, 20, 30],
            "cat": ["A", "B", "A"],
        })

    def test_add_line_plot(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_line_plot(self._sample_df(), "x", "y", "Line")
        assert len(gen.figures) == 1

    def test_add_line_plot_with_color(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_line_plot(self._sample_df(), "x", "y", "Line", color="cat")
        assert len(gen.figures) == 1

    def test_add_scatter_plot(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_scatter_plot(self._sample_df(), "x", "y", "Scatter")
        assert len(gen.figures) == 1

    def test_add_scatter_with_size(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_scatter_plot(self._sample_df(), "x", "y", "Scatter", size="y")
        assert len(gen.figures) == 1

    def test_add_bar_chart(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_bar_chart(self._sample_df(), "x", "y", "Bar")
        assert len(gen.figures) == 1

    def test_add_histogram(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        gen.add_histogram(self._sample_df(), "y", "Hist")
        assert len(gen.figures) == 1

    def test_add_heatmap(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
        gen.add_heatmap(df, "Heatmap")
        assert len(gen.figures) == 1

    def test_add_custom_figure(self):
        gen = PlotlyReportGenerator("T", "M", "R")
        fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
        gen.add_custom_figure(fig)
        assert len(gen.figures) == 1


class TestGenerateHtml:
    def test_generate_html_writes_file(self, tmp_path):
        gen = PlotlyReportGenerator("Test Report", "test_mod", "test_repo")
        gen.add_summary_stat("Total", "42")
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        gen.add_line_plot(df, "x", "y", "Test Line")
        outfile = tmp_path / "report.html"
        gen.generate_html(str(outfile))
        assert outfile.exists()
        content = outfile.read_text()
        assert "Test Report" in content
        assert "test_mod" in content
        assert "42" in content

    def test_generate_html_creates_dirs(self, tmp_path):
        gen = PlotlyReportGenerator("T", "M", "R")
        outfile = tmp_path / "sub" / "dir" / "report.html"
        gen.generate_html(str(outfile))
        assert outfile.exists()

    def test_generate_html_no_stats(self, tmp_path):
        gen = PlotlyReportGenerator("T", "M", "R")
        outfile = tmp_path / "report.html"
        gen.generate_html(str(outfile))
        content = outfile.read_text()
        assert "<!DOCTYPE html>" in content

    def test_generate_html_multiple_plots(self, tmp_path):
        gen = PlotlyReportGenerator("T", "M", "R")
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        gen.add_line_plot(df, "x", "y", "P1")
        gen.add_bar_chart(df, "x", "y", "P2")
        outfile = tmp_path / "report.html"
        gen.generate_html(str(outfile))
        content = outfile.read_text()
        assert "plot1" in content
        assert "plot2" in content
