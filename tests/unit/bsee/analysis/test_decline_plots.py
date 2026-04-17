"""Tests for decline curve Plotly visualizations."""

import numpy as np
import pytest

from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
    ProductionTimeSeries,
)
from worldenergydata.bsee.analysis.forecasting.decline_analysis import (
    DeclineAnalysis,
)
from worldenergydata.bsee.analysis.forecasting.decline_plots import (
    generate_html_report,
    plot_eur_comparison,
    plot_forecast,
    plot_model_fits,
    plot_residuals,
)

plotly = pytest.importorskip("plotly")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ts():
    qi = 50000
    D = 0.05
    n = 20
    rng = np.random.default_rng(42)
    rates = np.array([qi * np.exp(-D * t) for t in range(n)])
    rates = rates + rng.normal(0, 500, n)
    rates = np.maximum(rates, 1)
    return ProductionTimeSeries(
        time_indices=np.arange(n, dtype=float),
        rates=rates,
        dates=np.array(list(range(200001, 200001 + n))),
        product_type="oil",
        field_name="TEST_FIELD",
        unit="bbl_per_day",
        n_original=n,
        n_after_filter=n,
        shut_in_periods=0,
    )


@pytest.fixture
def ts():
    return _make_ts()


@pytest.fixture
def comparison(ts):
    analysis = DeclineAnalysis(forecast_periods=5)
    return analysis.fit_all_models(ts)


@pytest.fixture
def forecast(comparison):
    analysis = DeclineAnalysis(forecast_periods=5)
    return analysis.forecast(comparison)


@pytest.fixture
def eur(comparison):
    analysis = DeclineAnalysis()
    return analysis.calculate_eur(comparison)


# ---------------------------------------------------------------------------
# Chart tests
# ---------------------------------------------------------------------------


class TestPlotModelFits:
    def test_returns_figure(self, ts, comparison):
        fig = plot_model_fits(ts, comparison)
        assert fig is not None
        assert hasattr(fig, "data")

    def test_has_historical_trace(self, ts, comparison):
        fig = plot_model_fits(ts, comparison)
        names = [t.name for t in fig.data]
        assert "Historical" in names

    def test_has_model_traces(self, ts, comparison):
        fig = plot_model_fits(ts, comparison)
        names = [t.name for t in fig.data]
        assert any("exponential" in n for n in names)

    def test_trace_count(self, ts, comparison):
        fig = plot_model_fits(ts, comparison)
        # 1 historical + 3 models = 4
        assert len(fig.data) == 4


class TestPlotForecast:
    def test_returns_figure(self, ts, comparison, forecast):
        fig = plot_forecast(ts, comparison, forecast)
        assert fig is not None

    def test_has_forecast_trace(self, ts, comparison, forecast):
        fig = plot_forecast(ts, comparison, forecast)
        names = [t.name for t in fig.data]
        assert "Forecast" in names

    def test_has_confidence_interval(self, ts, comparison, forecast):
        fig = plot_forecast(ts, comparison, forecast)
        names = [t.name for t in fig.data]
        assert "95% CI" in names


class TestPlotResiduals:
    def test_returns_figure(self, ts, comparison):
        fig = plot_residuals(ts, comparison)
        assert fig is not None

    def test_has_residual_trace(self, ts, comparison):
        fig = plot_residuals(ts, comparison)
        names = [t.name for t in fig.data]
        assert "Residuals" in names


class TestPlotEUR:
    def test_returns_figure(self, eur):
        fig = plot_eur_comparison(eur, "TEST_FIELD")
        assert fig is not None

    def test_has_bars(self, eur):
        fig = plot_eur_comparison(eur, "TEST_FIELD")
        assert len(fig.data) == 1  # single bar trace
        assert len(fig.data[0].x) == 3  # 3 models


class TestHTMLReport:
    def test_generates_html(self, ts, comparison, forecast, eur):
        html = generate_html_report(ts, comparison, forecast, eur)
        assert isinstance(html, str)
        assert "<html>" in html
        assert "Decline Curve Analysis" in html

    def test_html_contains_charts(self, ts, comparison, forecast, eur):
        html = generate_html_report(ts, comparison, forecast, eur)
        assert "plotly" in html.lower()
        assert "Model Comparison" in html

    def test_html_contains_field_name(self, ts, comparison, forecast, eur):
        html = generate_html_report(ts, comparison, forecast, eur)
        assert "TEST_FIELD" in html
