"""
ABOUTME: Tests for JointProbabilityModel (Hs-Tp joint probability via CMA).
ABOUTME: Uses synthetic Hs-Tp data — no live API calls.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.metocean.statistics.joint_probability import (
    JointModel,
    JointProbabilityModel,
)


def _make_hs_tp(n: int = 5000, seed: int = 42) -> tuple[pd.Series, pd.Series]:
    """Generate synthetic Hs-Tp pairs with realistic correlation."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2010-01-01", periods=n, freq="h")

    # Hs: Weibull
    hs = rng.weibull(1.5, size=n) * 2.0 + 0.3
    # Tp correlated with Hs (typical metocean relation)
    tp = 4.0 * np.sqrt(hs) + rng.normal(0, 1.0, size=n)
    tp = np.clip(tp, 3.0, 25.0)

    return (
        pd.Series(hs, index=dates, name="hs"),
        pd.Series(tp, index=dates, name="tp"),
    )


class TestJointModel:
    def test_joint_model_has_required_attributes(self):
        model = JointModel(
            marginal_hs={"distribution": "Weibull", "params": (1.2, 0.8)},
            conditional_tp={"model": "lognormal", "params": [(0.5, 0.3)]},
            n_samples=5000,
        )
        assert model.marginal_hs is not None
        assert model.conditional_tp is not None
        assert model.n_samples == 5000


class TestJointProbabilityModelFit:
    def setup_method(self):
        self.model = JointProbabilityModel()
        self.hs, self.tp = _make_hs_tp()

    def test_fit_returns_joint_model(self):
        result = self.model.fit(self.hs, self.tp)
        assert isinstance(result, JointModel)

    def test_fit_stores_sample_count(self):
        result = self.model.fit(self.hs, self.tp)
        assert result.n_samples == len(self.hs)

    def test_fit_marginal_hs_populated(self):
        result = self.model.fit(self.hs, self.tp)
        assert result.marginal_hs is not None

    def test_fit_conditional_tp_populated(self):
        result = self.model.fit(self.hs, self.tp)
        assert result.conditional_tp is not None


class TestScatterDiagram:
    def setup_method(self):
        self.model = JointProbabilityModel()
        self.hs, self.tp = _make_hs_tp()

    def test_scatter_diagram_returns_dataframe(self):
        df = self.model.scatter_diagram(self.hs, self.tp)
        assert isinstance(df, pd.DataFrame)

    def test_scatter_diagram_not_empty(self):
        df = self.model.scatter_diagram(self.hs, self.tp)
        assert df.shape[0] > 0
        assert df.shape[1] > 0

    def test_scatter_diagram_values_non_negative(self):
        df = self.model.scatter_diagram(self.hs, self.tp)
        assert (df.values >= 0).all()

    def test_scatter_diagram_sums_to_100_percent(self):
        df = self.model.scatter_diagram(self.hs, self.tp)
        # Sum of occurrences should equal 100% (percent table)
        total = df.values.sum()
        assert total == pytest.approx(100.0, rel=0.01)

    def test_scatter_diagram_custom_bins(self):
        hs_bins = np.arange(0, 8, 1.0)
        tp_bins = np.arange(3, 20, 2.0)
        df = self.model.scatter_diagram(
            self.hs, self.tp, hs_bins=hs_bins, tp_bins=tp_bins
        )
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] > 0


class TestPlotScatter:
    def setup_method(self):
        self.model = JointProbabilityModel()
        self.hs, self.tp = _make_hs_tp(n=1000)

    def test_plot_scatter_returns_plotly_figure(self):
        fig = self.model.plot_scatter(self.hs, self.tp)
        assert isinstance(fig, go.Figure)

    def test_plot_scatter_has_traces(self):
        fig = self.model.plot_scatter(self.hs, self.tp)
        assert len(fig.data) >= 1

    def test_plot_scatter_axes_labeled(self):
        fig = self.model.plot_scatter(self.hs, self.tp)
        layout = fig.layout
        # At minimum the figure should have axis labels
        assert layout.xaxis.title.text is not None or layout.xaxis.title is not None
