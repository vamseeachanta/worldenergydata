"""Plotly visualizations for BSEE decline curve analysis.

Generates interactive charts: historical + model overlays, forecast with
confidence envelope, residual analysis, and EUR comparison bar chart.
"""

import html as html_mod
import logging
from typing import Dict, Optional

import numpy as np

from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
    ProductionTimeSeries,
)
from worldenergydata.bsee.analysis.forecasting.decline_analysis import (
    ModelComparison,
)
from worldenergydata.sodir.forecasting import ForecastResult

logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
except ImportError:
    go = None
    logger.warning("plotly not installed — visualization disabled")

_PAL = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"]
_MODEL_COLORS = {
    "exponential": "#3B82F6",
    "hyperbolic": "#EF4444",
    "harmonic": "#10B981",
}


def plot_model_fits(
    ts: ProductionTimeSeries,
    comparison: ModelComparison,
) -> "go.Figure":
    """Historical production with all fitted model curves overlaid.

    Args:
        ts: Production time series data.
        comparison: Model comparison results.

    Returns:
        Plotly Figure.
    """
    if go is None:
        raise ImportError("plotly required for visualization")

    fig = go.Figure()

    # Historical data
    fig.add_trace(
        go.Scatter(
            x=list(range(len(ts.rates))),
            y=ts.rates,
            name="Historical",
            mode="markers",
            marker=dict(color="#374151", size=7),
            hovertemplate=(
                "<b>Historical</b><br>"
                "Period: %{x}<br>"
                "Rate: %{y:,.0f}<extra></extra>"
            ),
        )
    )

    # Model fits
    time_range = list(range(len(ts.rates)))
    for model_name, fit in comparison.fits.items():
        color = _MODEL_COLORS.get(model_name, "#6B7280")
        is_best = model_name == comparison.best_model
        fig.add_trace(
            go.Scatter(
                x=time_range,
                y=fit.predicted,
                name=f"{model_name} (R²={fit.curve.r_squared:.3f})",
                mode="lines",
                line=dict(
                    color=color,
                    width=3 if is_best else 1.5,
                    dash="solid" if is_best else "dash",
                ),
                hovertemplate=(
                    f"<b>{model_name}</b><br>"
                    "Period: %{x}<br>"
                    "Rate: %{y:,.0f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=f"Decline Curve Fits — {ts.field_name} ({ts.product_type})",
        xaxis_title="Time Period",
        yaxis_title=f"Rate ({ts.unit})",
        height=500,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


def plot_forecast(
    ts: ProductionTimeSeries,
    comparison: ModelComparison,
    forecast: ForecastResult,
) -> "go.Figure":
    """Historical data + best-fit forecast with confidence envelope.

    Args:
        ts: Production time series data.
        comparison: Model comparison results.
        forecast: Forecast results from DeclineAnalysis.forecast().

    Returns:
        Plotly Figure.
    """
    if go is None:
        raise ImportError("plotly required for visualization")

    fig = go.Figure()
    best_color = _MODEL_COLORS.get(comparison.best_model, "#3B82F6")

    # Historical
    fig.add_trace(
        go.Scatter(
            x=list(range(len(ts.rates))),
            y=ts.rates,
            name="Historical",
            mode="lines+markers",
            line=dict(color="#374151", width=2),
            marker=dict(size=5),
        )
    )

    # Best fit on historical
    best_fit = comparison.best_fit
    fig.add_trace(
        go.Scatter(
            x=list(range(len(ts.rates))),
            y=best_fit.predicted,
            name=f"Fit ({comparison.best_model})",
            mode="lines",
            line=dict(color=best_color, width=2),
        )
    )

    # Forecast
    fig.add_trace(
        go.Scatter(
            x=list(forecast.forecast_periods),
            y=forecast.forecast_values,
            name="Forecast",
            mode="lines",
            line=dict(color=best_color, width=2, dash="dot"),
        )
    )

    # Confidence interval
    if forecast.confidence_intervals:
        lower = forecast.confidence_intervals.get("lower_95")
        upper = forecast.confidence_intervals.get("upper_95")
        if lower is not None and upper is not None:
            periods = list(forecast.forecast_periods)
            fig.add_trace(
                go.Scatter(
                    x=periods + periods[::-1],
                    y=list(upper) + list(lower[::-1]),
                    fill="toself",
                    fillcolor=f"rgba(59,130,246,0.15)",
                    line=dict(width=0),
                    name="95% CI",
                    hoverinfo="skip",
                )
            )

    fig.update_layout(
        title=(
            f"Production Forecast — {ts.field_name} "
            f"({comparison.best_model})"
        ),
        xaxis_title="Time Period",
        yaxis_title=f"Rate ({ts.unit})",
        height=500,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


def plot_residuals(
    ts: ProductionTimeSeries,
    comparison: ModelComparison,
) -> "go.Figure":
    """Residual plot for the best-fit model.

    Args:
        ts: Production time series data.
        comparison: Model comparison results.

    Returns:
        Plotly Figure with residuals scatter and zero line.
    """
    if go is None:
        raise ImportError("plotly required for visualization")

    residuals = comparison.best_fit.residuals
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=list(range(len(residuals))),
            y=residuals,
            mode="markers",
            marker=dict(color="#3B82F6", size=7),
            name="Residuals",
            hovertemplate="Period: %{x}<br>Residual: %{y:,.0f}<extra></extra>",
        )
    )

    fig.add_hline(y=0, line_dash="dash", line_color="#9CA3AF")

    fig.update_layout(
        title=f"Residuals — {comparison.best_model} fit ({ts.field_name})",
        xaxis_title="Time Period",
        yaxis_title="Residual (actual - predicted)",
        height=400,
        template="plotly_white",
    )
    return fig


def plot_eur_comparison(
    eur_results: Dict[str, float],
    field_name: str,
) -> "go.Figure":
    """Bar chart comparing EUR across models.

    Args:
        eur_results: Dict mapping model name to EUR value.
        field_name: Field name for title.

    Returns:
        Plotly Figure.
    """
    if go is None:
        raise ImportError("plotly required for visualization")

    models = list(eur_results.keys())
    values = list(eur_results.values())
    colors = [_MODEL_COLORS.get(m, "#6B7280") for m in models]

    fig = go.Figure(
        go.Bar(
            x=models,
            y=values,
            marker_color=colors,
            text=[f"{v:,.0f}" for v in values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>EUR: %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"Estimated Ultimate Recovery — {field_name}",
        xaxis_title="Model",
        yaxis_title="EUR (cumulative units)",
        height=400,
        template="plotly_white",
    )
    return fig


def generate_html_report(
    ts: ProductionTimeSeries,
    comparison: ModelComparison,
    forecast: ForecastResult,
    eur_results: Dict[str, float],
) -> str:
    """Generate a complete HTML report with all charts.

    Args:
        ts: Production time series.
        comparison: Model comparison.
        forecast: Forecast results.
        eur_results: EUR by model.

    Returns:
        HTML string with embedded Plotly charts.
    """
    if go is None:
        raise ImportError("plotly required for visualization")

    figs = [
        plot_model_fits(ts, comparison),
        plot_forecast(ts, comparison, forecast),
        plot_residuals(ts, comparison),
        plot_eur_comparison(eur_results, ts.field_name),
    ]

    config = {"displayModeBar": True, "responsive": True}
    chart_divs = []
    for i, fig in enumerate(figs):
        html = fig.to_html(
            full_html=False,
            include_plotlyjs=(i == 0),
            config=config,
        )
        chart_divs.append(html)

    summary = comparison.summary_table()
    summary_html = summary.to_html(index=False, float_format="%.4f")

    # HTML-escape user-derived strings to prevent XSS
    esc_field = html_mod.escape(ts.field_name)
    esc_product = html_mod.escape(ts.product_type)
    esc_best = html_mod.escape(comparison.best_model)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Decline Curve Analysis — {esc_field}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2937; }}
h1 {{ color: #111827; border-bottom: 2px solid #3B82F6; padding-bottom: 0.5rem; }}
h2 {{ color: #374151; margin-top: 2rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: right; }}
th {{ background: #f3f4f6; font-weight: 600; }}
.best {{ background: #ecfdf5; font-weight: 600; }}
.meta {{ color: #6b7280; font-size: 0.875rem; }}
</style></head><body>
<h1>Decline Curve Analysis — {esc_field}</h1>
<p class="meta">Product: {esc_product} | Data points: {ts.n_after_filter}
 (of {ts.n_original}) | Shut-in excluded: {ts.shut_in_periods}
 | Best model: {esc_best}</p>

<h2>Model Comparison</h2>
{summary_html}

<h2>Model Fits</h2>
{chart_divs[0]}

<h2>Forecast ({esc_best})</h2>
{chart_divs[1]}

<h2>Residual Analysis</h2>
{chart_divs[2]}

<h2>Estimated Ultimate Recovery</h2>
{chart_divs[3]}

</body></html>"""
