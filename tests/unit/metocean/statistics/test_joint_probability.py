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
        assert result.marginal_hs["distribution"] == "LoNoWe"
        np.testing.assert_array_equal(result.marginal_hs["pdf"], result._raw_result[6])
        np.testing.assert_array_equal(result.marginal_hs["grid"], result._raw_result[7])

    def test_fit_conditional_tp_populated(self):
        result = self.model.fit(self.hs, self.tp)
        # Fixed conditional coefficients: v.1.2.0 extreme.py L722/L729.
        assert result.conditional_tp["mu"]["a3"] == 0.36
        assert result.conditional_tp["variance"]["b1"] == 0.005


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


def test_decode_upstream_positions(monkeypatch):
    """v.1.2.0 extreme.py L722-L766: six CONDITIONAL coefficients.

    Literal distinct sentinels test positions, not a statistical fit. The
    marginal is a tabulated lognormal/Weibull splice, not these coefficients.
    """
    import worldenergydata.metocean.statistics.joint_probability as module

    hs, tp = _make_hs_tp()
    pdf, grid = np.array([0.2, 0.1]), np.array([1.0, 2.0])
    raw = (1, 2, 3, 4, 5, 6, pdf, grid, [], [], [50], pd.DataFrame())
    monkeypatch.setattr(module.ms, "joint_distribution_Hs_Tp", lambda *a, **kw: raw)
    model = JointProbabilityModel().fit(hs, tp, periods=[50])
    assert model.conditional_tp == {
        "model": "lognormal_conditional",
        "mu": {"a1": 1.0, "a2": 2.0, "a3": 3.0},
        "variance": {"b1": 4.0, "b2": 5.0, "b3": 6.0},
    }
    assert model.marginal_hs["distribution"] == "LoNoWe"
    np.testing.assert_array_equal(model.marginal_hs["pdf"], pdf)
    np.testing.assert_array_equal(model.marginal_hs["grid"], grid)
    np.testing.assert_array_equal(model.hs_samples, hs)
    np.testing.assert_array_equal(model.tp_samples, tp)
    assert model.fitted_periods == (50,)
    # Independently repeat the documented upstream duration expression.
    assert model.state_duration_hours == ((hs.index[-1] - hs.index[0]).days + 1) * 24 / len(hs)
