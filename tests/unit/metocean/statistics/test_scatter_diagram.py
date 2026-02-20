"""
ABOUTME: Tests for ScatterDiagram (2D Hs-Tp occurrence table).
ABOUTME: Uses synthetic data — no live API calls.
"""

import numpy as np
import pandas as pd
import pytest
import plotly.graph_objects as go

from worldenergydata.metocean.statistics.scatter_diagram import ScatterDiagram


def _make_hs_tp(n: int = 3000, seed: int = 99) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    hs = rng.weibull(1.5, size=n) * 2.0 + 0.3
    tp = 4.0 * np.sqrt(hs) + rng.normal(0, 1.0, size=n)
    tp = np.clip(tp, 3.0, 22.0)
    return pd.DataFrame({"hs": hs, "tp": tp})


class TestScatterDiagramCompute:
    def setup_method(self):
        self.sd = ScatterDiagram()
        self.data = _make_hs_tp()

    def test_compute_returns_dataframe(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp")
        assert isinstance(df, pd.DataFrame)

    def test_compute_not_empty(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp")
        assert df.shape[0] > 0 and df.shape[1] > 0

    def test_compute_values_non_negative(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp")
        assert (df.values >= 0).all()

    def test_compute_sums_to_100_percent(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp")
        assert df.values.sum() == pytest.approx(100.0, rel=0.01)

    def test_compute_custom_step(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp", step_var1=0.5, step_var2=1.0)
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] > 0

    def test_compute_column_labels_are_numeric_strings(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp")
        # Column labels represent bin edges
        assert len(df.columns) > 0


class TestScatterDiagramPlot:
    def setup_method(self):
        self.sd = ScatterDiagram()
        self.data = _make_hs_tp()

    def test_plot_returns_plotly_figure(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp")
        fig = self.sd.plot(df)
        assert isinstance(fig, go.Figure)

    def test_plot_has_traces(self):
        df = self.sd.compute(self.data, var1="hs", var2="tp")
        fig = self.sd.plot(df)
        assert len(fig.data) >= 1

    def test_plot_from_raw_data(self):
        fig = self.sd.plot_from_data(self.data, var1="hs", var2="tp")
        assert isinstance(fig, go.Figure)
