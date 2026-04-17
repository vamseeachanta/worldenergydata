"""
Executive Template Chart Generation.

This module provides chart creation functions for executive dashboards
including gauges, sparklines, radar charts, and multi-panel layouts.
"""

from typing import Any, Dict, List, Optional

# Import Plotly for visualizations
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def get_status_color(status: str) -> str:
    """
    Get color for status.

    Args:
        status: Status string (green/yellow/red/gray)

    Returns:
        HTML color code
    """
    colors = {
        "green": "#28a745",
        "yellow": "#ffc107",
        "red": "#dc3545",
        "gray": "#6c757d",
    }
    return colors.get(status, "#6c757d")


def create_kpi_summary_chart(kpis: List[Dict]) -> Optional[Any]:
    """
    Create KPI summary bar chart.

    Args:
        kpis: List of KPI dictionaries

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    categories = []
    values = []
    colors = []

    for kpi in kpis[:6]:  # Top 6 KPIs
        categories.append(kpi["name"])
        values.append(kpi.get("value", 0))
        colors.append(get_status_color(kpi.get("status", "gray")))

    fig = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker_color=colors,
                text=values,
                textposition="outside",
            )
        ]
    )

    fig.update_layout(
        title="Key Performance Indicators",
        xaxis_title="KPI",
        yaxis_title="Value",
        height=400,
        showlegend=False,
    )

    return fig


def create_trend_chart(metric: str, values: List, periods: List) -> Optional[Any]:
    """
    Create trend chart for a metric.

    Args:
        metric: Metric name
        values: List of values
        periods: List of period labels

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=periods if periods else list(range(len(values))),
            y=values,
            mode="lines+markers",
            name=metric,
            line=dict(width=2),
            marker=dict(size=8),
        )
    )

    fig.update_layout(
        title=f"{metric} Trend",
        xaxis_title="Period",
        yaxis_title="Value",
        height=300,
        showlegend=False,
    )

    return fig


def create_kpi_gauge_chart(kpi_data: Dict) -> Optional[Any]:
    """
    Create KPI gauge chart.

    Args:
        kpi_data: KPI data dictionary with keys:
            - name: KPI name
            - value: Current value
            - target: Target value (optional)
            - min: Minimum gauge value (optional, default 0)
            - max: Maximum gauge value (optional, default 100)

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    fig = go.Figure(
        data=[
            go.Indicator(
                mode="gauge+number+delta",
                value=kpi_data["value"],
                title={"text": kpi_data["name"]},
                delta={"reference": kpi_data.get("target", 0)},
                gauge={
                    "axis": {
                        "range": [kpi_data.get("min", 0), kpi_data.get("max", 100)]
                    },
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {
                            "range": [
                                kpi_data.get("min", 0),
                                kpi_data.get("target", 50) * 0.9,
                            ],
                            "color": "lightgray",
                        },
                        {
                            "range": [
                                kpi_data.get("target", 50) * 0.9,
                                kpi_data.get("target", 50),
                            ],
                            "color": "yellow",
                        },
                        {
                            "range": [
                                kpi_data.get("target", 50),
                                kpi_data.get("max", 100),
                            ],
                            "color": "green",
                        },
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": kpi_data.get("target", 50),
                    },
                },
            )
        ]
    )

    fig.update_layout(height=300)

    return fig


def create_trend_sparkline(trend_data: Dict) -> Optional[Any]:
    """
    Create trend sparkline.

    Args:
        trend_data: Trend data dictionary with keys:
            - values: List of values
            - periods: List of period labels (optional)

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=trend_data.get("periods", list(range(len(trend_data["values"])))),
            y=trend_data["values"],
            mode="lines",
            line=dict(width=2, color="blue"),
            fill="tozeroy",
            fillcolor="rgba(0, 100, 200, 0.2)",
        )
    )

    fig.update_layout(
        height=100,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        showlegend=False,
    )

    return fig


def create_executive_summary_chart(summary_data: Dict) -> Optional[Any]:
    """
    Create executive summary chart.

    Args:
        summary_data: Summary data dictionary with keys:
            - categories: List of category names
            - scores: List of actual scores
            - targets: List of target scores

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    fig = go.Figure()

    # Actual vs Target bars
    fig.add_trace(
        go.Bar(
            name="Actual",
            x=summary_data["categories"],
            y=summary_data["scores"],
            marker_color="lightblue",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Target",
            x=summary_data["categories"],
            y=summary_data["targets"],
            marker_color="gray",
            opacity=0.5,
        )
    )

    fig.update_layout(
        title="Performance vs Target",
        xaxis_title="Category",
        yaxis_title="Score",
        barmode="group",
        height=400,
    )

    return fig


def create_traffic_light_grid(metrics: List[Dict]) -> Optional[Any]:
    """
    Create traffic light grid visualization.

    Args:
        metrics: List of metric dictionaries with 'name' and 'status' keys

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    # Create grid layout
    rows = (len(metrics) - 1) // 3 + 1
    cols = min(3, len(metrics))

    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=[m["name"] for m in metrics],
        specs=[[{"type": "scatter"}] * cols for _ in range(rows)],
    )

    for i, metric in enumerate(metrics):
        row = i // 3 + 1
        col = i % 3 + 1

        color = get_status_color(metric["status"])

        fig.add_trace(
            go.Scatter(
                x=[0.5],
                y=[0.5],
                mode="markers",
                marker=dict(size=50, color=color),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=row,
            col=col,
        )

    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])

    fig.update_layout(height=100 * rows, title="Status Indicators", showlegend=False)

    return fig


def create_multi_panel_dashboard(panels: List[Dict], data: Dict) -> Optional[Any]:
    """
    Create multi-panel executive dashboard.

    Args:
        panels: Panel configuration list with keys:
            - position: (row, col) tuple
            - type: Panel type (kpi_grid, trend_chart, traffic_lights)
            - title: Panel title (optional)
        data: Dashboard data with 'kpis' and 'trends' keys

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    # Determine grid dimensions
    max_row = max(p["position"][0] for p in panels)
    max_col = max(p["position"][1] for p in panels)

    # Create subplots
    fig = make_subplots(
        rows=max_row,
        cols=max_col,
        subplot_titles=[p.get("title", "") for p in panels],
        specs=[[{"type": "scatter"}] * max_col for _ in range(max_row)],
    )

    # Add panels
    for panel in panels:
        row, col = panel["position"]
        panel_type = panel["type"]

        if panel_type == "kpi_grid" and "kpis" in data:
            # Add KPI bars
            kpis = data["kpis"][:6]
            fig.add_trace(
                go.Bar(
                    x=[k["name"] for k in kpis],
                    y=[k.get("value", 0) for k in kpis],
                    marker_color=[
                        get_status_color(k.get("status", "gray")) for k in kpis
                    ],
                ),
                row=row,
                col=col,
            )

        elif panel_type == "trend_chart" and "trends" in data:
            # Add trend line
            if "revenue" in data["trends"]:
                fig.add_trace(
                    go.Scatter(
                        x=data["trends"].get(
                            "periods", list(range(len(data["trends"]["revenue"])))
                        ),
                        y=data["trends"]["revenue"],
                        mode="lines+markers",
                    ),
                    row=row,
                    col=col,
                )

        elif panel_type == "traffic_lights" and "kpis" in data:
            # Add traffic light indicators
            for i, kpi in enumerate(data["kpis"][:3]):
                fig.add_trace(
                    go.Scatter(
                        x=[i],
                        y=[1],
                        mode="markers",
                        marker=dict(
                            size=30, color=get_status_color(kpi.get("status", "gray"))
                        ),
                        text=kpi["name"],
                        showlegend=False,
                    ),
                    row=row,
                    col=col,
                )

    fig.update_layout(height=600, title="Executive Dashboard")

    return fig


def create_benchmark_radar_chart(benchmark_data: Dict) -> Optional[Any]:
    """
    Create competitive benchmark radar chart.

    Args:
        benchmark_data: Benchmark data with keys:
            - company_metrics: Dict of company metric values
            - industry_benchmarks: Dict with p50 (median) values

    Returns:
        Plotly figure or None if Plotly unavailable
    """
    if not PLOTLY_AVAILABLE:
        return None

    company_metrics = benchmark_data.get("company_metrics", {})
    industry_benchmarks = benchmark_data.get("industry_benchmarks", {})

    categories = list(company_metrics.keys())
    company_values = list(company_metrics.values())

    # Get median benchmarks
    benchmark_values = []
    for cat in categories:
        if cat in industry_benchmarks:
            benchmark_values.append(industry_benchmarks[cat].get("p50", 0))
        else:
            benchmark_values.append(0)

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=company_values, theta=categories, fill="toself", name="Company"
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=benchmark_values,
            theta=categories,
            fill="toself",
            name="Industry Median",
            opacity=0.5,
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, max(company_values + benchmark_values) * 1.1]
            )
        ),
        showlegend=True,
        title="Competitive Benchmark Analysis",
    )

    return fig
