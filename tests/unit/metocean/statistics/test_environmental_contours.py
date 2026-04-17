"""
ABOUTME: Tests for EnvironmentalContour (IFORM/ISORM contour wrapper).
ABOUTME: Uses synthetic Hs-Tp data — no live API calls.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.metocean.statistics.environmental_contours import (
    ContourResult,
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.joint_probability import (
    JointModel,
    JointProbabilityModel,
)


def _make_hs_tp(n: int = 5000, seed: int = 42) -> tuple[pd.Series, pd.Series]:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2010-01-01", periods=n, freq="h")
    hs = rng.weibull(1.5, size=n) * 2.0 + 0.3
    tp = 4.0 * np.sqrt(hs) + rng.normal(0, 1.0, size=n)
    tp = np.clip(tp, 3.0, 25.0)
    return (
        pd.Series(hs, index=dates, name="hs"),
        pd.Series(tp, index=dates, name="tp"),
    )


@pytest.fixture
def joint_model():
    hs, tp = _make_hs_tp()
    jpm = JointProbabilityModel()
    return jpm.fit(hs, tp)


@pytest.fixture
def hs_tp_data():
    return _make_hs_tp()


class TestContourResult:
    def test_contour_result_has_required_fields(self):
        contour = ContourResult(
            method="IFORM",
            return_period=50,
            hs_values=np.array([3.0, 4.0, 5.0]),
            tp_values=np.array([10.0, 12.0, 14.0]),
        )
        assert contour.method == "IFORM"
        assert contour.return_period == 50
        assert len(contour.hs_values) == 3
        assert len(contour.tp_values) == 3

    def test_contour_result_arrays_equal_length(self):
        hs = np.array([3.0, 4.0, 5.0])
        tp = np.array([10.0, 12.0, 14.0])
        contour = ContourResult(
            method="ISORM", return_period=100, hs_values=hs, tp_values=tp
        )
        assert len(contour.hs_values) == len(contour.tp_values)


class TestEnvironmentalContourIFORM:
    def setup_method(self):
        self.ec = EnvironmentalContour()

    def test_iform_returns_contour_result(self, joint_model):
        result = self.ec.iform(joint_model, return_period=50)
        assert isinstance(result, ContourResult)

    def test_iform_method_label(self, joint_model):
        result = self.ec.iform(joint_model, return_period=50)
        assert result.method == "IFORM"

    def test_iform_return_period_stored(self, joint_model):
        result = self.ec.iform(joint_model, return_period=100)
        assert result.return_period == 100

    def test_iform_has_hs_values(self, joint_model):
        result = self.ec.iform(joint_model, return_period=50)
        assert len(result.hs_values) > 0

    def test_iform_has_tp_values(self, joint_model):
        result = self.ec.iform(joint_model, return_period=50)
        assert len(result.tp_values) > 0

    def test_iform_hs_values_positive(self, joint_model):
        result = self.ec.iform(joint_model, return_period=50)
        assert (result.hs_values > 0).all()

    def test_iform_tp_values_positive(self, joint_model):
        result = self.ec.iform(joint_model, return_period=50)
        assert (result.tp_values > 0).all()


class TestEnvironmentalContourISORMM:
    def setup_method(self):
        self.ec = EnvironmentalContour()

    def test_isorm_returns_contour_result(self, joint_model):
        result = self.ec.isorm(joint_model, return_period=50)
        assert isinstance(result, ContourResult)

    def test_isorm_method_label(self, joint_model):
        result = self.ec.isorm(joint_model, return_period=50)
        assert result.method == "ISORM"

    def test_isorm_has_values(self, joint_model):
        result = self.ec.isorm(joint_model, return_period=50)
        assert len(result.hs_values) > 0
        assert len(result.tp_values) > 0


class TestPlotContour:
    def setup_method(self):
        self.ec = EnvironmentalContour()

    def test_plot_contour_returns_plotly_figure(self, joint_model):
        contour = self.ec.iform(joint_model, return_period=50)
        fig = self.ec.plot_contour(contour)
        assert isinstance(fig, go.Figure)

    def test_plot_contour_has_traces(self, joint_model):
        contour = self.ec.iform(joint_model, return_period=50)
        fig = self.ec.plot_contour(contour)
        assert len(fig.data) >= 1

    def test_plot_contour_with_data_overlay(self, joint_model, hs_tp_data):
        hs, tp = hs_tp_data
        data_df = pd.DataFrame({"hs": hs.values, "tp": tp.values})
        contour = self.ec.iform(joint_model, return_period=50)
        fig = self.ec.plot_contour(contour, data=data_df)
        assert isinstance(fig, go.Figure)
        # Should have more traces with data overlay
        assert len(fig.data) >= 2
