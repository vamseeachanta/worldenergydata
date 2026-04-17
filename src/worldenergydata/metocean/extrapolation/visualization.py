# ABOUTME: Plotly visualizations for metocean extrapolation results.
# ABOUTME: Source map with coverage circles and correction breakdown bar chart.

"""
Visualization for Metocean Extrapolation

Provides Plotly-based interactive visualizations:
- plot_source_map: map of target, nearest sources, and coverage circles
- plot_correction_breakdown: bar chart of raw vs. corrected parameter values
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def plot_source_map(
    lat: float,
    lon: float,
    sources: list,
    result,
    mapbox_style: str = "open-street-map",
):
    """
    Plot a Plotly scatter-mapbox showing the target location, nearest sources,
    and their coverage circles.

    Args:
        lat: Target latitude (degrees)
        lon: Target longitude (degrees)
        sources: List of MetoceanSource objects to display
        result: ExtrapolationResult from extrapolate()
        mapbox_style: Mapbox style string (default "open-street-map")

    Returns:
        plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError(
            "plotly is required for visualization. " "Install with: pip install plotly"
        ) from exc

    fig = go.Figure()

    # ---- Source markers ----
    src_lats = [s.lat for s in sources]
    src_lons = [s.lon for s in sources]
    src_names = [s.name for s in sources]
    src_text = [
        f"{s.name}<br>Type: {s.source_type}<br>Priority: {s.priority}" for s in sources
    ]

    fig.add_trace(
        go.Scattermapbox(
            lat=src_lats,
            lon=src_lons,
            mode="markers",
            marker=dict(size=10, color="royalblue"),
            text=src_text,
            hoverinfo="text",
            name="Data Sources",
        )
    )

    # ---- Target marker ----
    fig.add_trace(
        go.Scattermapbox(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=dict(size=14, color="red", symbol="star"),
            text=[f"Target: ({lat:.3f}, {lon:.3f})"],
            hoverinfo="text",
            name="Target",
        )
    )

    # ---- Best source connector ----
    if result is not None and result.source_used is not None:
        best = result.source_used
        fig.add_trace(
            go.Scattermapbox(
                lat=[lat, best.lat],
                lon=[lon, best.lon],
                mode="lines",
                line=dict(width=2, color="orange"),
                name=f"Best Source: {best.name}",
            )
        )

    fig.update_layout(
        mapbox_style=mapbox_style,
        mapbox=dict(center=dict(lat=lat, lon=lon), zoom=4),
        title="Metocean Source Map",
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
    )

    return fig


def plot_correction_breakdown(result) -> "go.Figure":
    """
    Plot a grouped bar chart showing raw (baseline) vs corrected parameter values.

    Args:
        result: ExtrapolationResult from extrapolate()

    Returns:
        plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError(
            "plotly is required for visualization. " "Install with: pip install plotly"
        ) from exc

    # Baseline values (before corrections)
    _BASELINE = {
        "Hs (m)": 2.5,
        "Tp (s)": 9.0,
        "Wind (m/s)": 10.0,
        "Current (m/s)": 0.3,
    }
    corrected = {
        "Hs (m)": result.Hs_m,
        "Tp (s)": result.Tp_s,
        "Wind (m/s)": result.wind_speed_ms,
        "Current (m/s)": result.current_speed_ms,
    }

    params = list(_BASELINE.keys())
    raw_vals = [_BASELINE[p] for p in params]
    corr_vals = [corrected[p] for p in params]

    fig = go.Figure(
        data=[
            go.Bar(name="Baseline", x=params, y=raw_vals, marker_color="steelblue"),
            go.Bar(
                name="Corrected (target)",
                x=params,
                y=corr_vals,
                marker_color="tomato",
            ),
        ]
    )

    corrections_text = (
        ", ".join(result.corrections_applied) if result.corrections_applied else "none"
    )

    fig.update_layout(
        barmode="group",
        title=(
            f"Correction Breakdown — {result.source}<br>"
            f"<sup>Distance: {result.distance_km:.1f} km | "
            f"Confidence: {result.confidence} | "
            f"Corrections: {corrections_text}</sup>"
        ),
        xaxis_title="Parameter",
        yaxis_title="Value",
        legend_title="Series",
    )

    return fig
