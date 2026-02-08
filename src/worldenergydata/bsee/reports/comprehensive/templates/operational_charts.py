"""
Operational visualization charts for BSEE operational performance reporting.

This module contains all Plotly-based chart generation functions for
operational reporting including:
- Well status distribution charts
- Production efficiency gauges
- Equipment reliability charts
- KPI dashboards
- Failure analysis charts
"""

from typing import Any, Dict, List

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_well_status_chart(summary: Dict[str, Any]) -> str:
    """
    Create well status distribution pie chart.

    Args:
        summary: Operational summary dictionary with well counts

    Returns:
        JSON string of the Plotly figure
    """
    labels = ["Producing", "Drilling", "Offline", "Other"]
    values = [
        summary.get("wells_producing", 0),
        summary.get("wells_drilling", 0),
        summary.get("wells_offline", 0),
        summary.get("total_wells", 0)
        - summary.get("wells_producing", 0)
        - summary.get("wells_drilling", 0)
        - summary.get("wells_offline", 0),
    ]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                marker_colors=["#2ecc71", "#3498db", "#e74c3c", "#95a5a6"],
            )
        ]
    )

    fig.update_layout(title="Well Status Distribution", showlegend=True, height=400)

    return fig.to_json()


def create_efficiency_gauge(efficiency: Dict[str, Any]) -> str:
    """
    Create production efficiency gauge chart.

    Args:
        efficiency: Production efficiency dictionary

    Returns:
        JSON string of the Plotly figure
    """
    value = efficiency.get("efficiency_percentage", 0)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Production Efficiency (%)"},
            delta={"reference": 85, "increasing": {"color": "green"}},
            gauge={
                "axis": {"range": [None, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "darkblue"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 50], "color": "#ffcccc"},
                    {"range": [50, 75], "color": "#fff4cc"},
                    {"range": [75, 90], "color": "#ffffcc"},
                    {"range": [90, 100], "color": "#ccffcc"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 85,
                },
            },
        )
    )

    fig.update_layout(height=400)

    return fig.to_json()


def create_reliability_chart(reliability: Dict[str, Any]) -> str:
    """
    Create equipment reliability bar chart.

    Args:
        reliability: Equipment reliability dictionary

    Returns:
        JSON string of the Plotly figure
    """
    equipment_details = reliability.get("equipment_details", [])

    if not equipment_details:
        return "{}"

    names = [e["name"] for e in equipment_details]
    availabilities = [e["availability"] for e in equipment_details]
    reliabilities = [e["reliability"] for e in equipment_details]

    fig = go.Figure(
        data=[
            go.Bar(
                name="Availability", x=names, y=availabilities, marker_color="#3498db"
            ),
            go.Bar(
                name="Reliability", x=names, y=reliabilities, marker_color="#2ecc71"
            ),
        ]
    )

    fig.update_layout(
        title="Equipment Performance Metrics",
        xaxis_title="Equipment",
        yaxis_title="Percentage (%)",
        barmode="group",
        height=400,
        showlegend=True,
    )

    return fig.to_json()


def create_kpi_dashboard(kpis: List[Dict[str, Any]]) -> str:
    """
    Create KPI dashboard with multiple indicators.

    Args:
        kpis: List of KPI dictionaries

    Returns:
        JSON string of the Plotly figure
    """
    if not kpis:
        return "{}"

    # Create subplots for KPIs
    rows = (len(kpis) + 2) // 3  # 3 KPIs per row
    fig = make_subplots(
        rows=rows,
        cols=3,
        subplot_titles=[kpi["name"] for kpi in kpis],
        specs=[[{"type": "indicator"}] * 3 for _ in range(rows)],
    )

    for i, kpi in enumerate(kpis):
        row = (i // 3) + 1
        col = (i % 3) + 1

        color = (
            "#2ecc71"
            if kpi["status"] == "good"
            else "#f39c12" if kpi["status"] == "warning" else "#e74c3c"
        )

        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=kpi["actual"],
                delta={"reference": kpi["target"], "relative": True},
                number={"suffix": f" {kpi['unit']}", "font": {"color": color}},
                domain={"x": [0, 1], "y": [0, 1]},
            ),
            row=row,
            col=col,
        )

    fig.update_layout(
        title="Operational KPI Dashboard", height=200 * rows, showlegend=False
    )

    return fig.to_json()


def create_failure_chart(failures: Dict[str, Any]) -> str:
    """
    Create failure analysis chart.

    Args:
        failures: Failure analysis dictionary

    Returns:
        JSON string of the Plotly figure
    """
    by_type = failures.get("by_type", {})

    if not by_type:
        return "{}"

    fig = go.Figure(
        data=[
            go.Bar(
                x=list(by_type.keys()),
                y=list(by_type.values()),
                marker_color="#e74c3c",
                text=list(by_type.values()),
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title="Failures by Type",
        xaxis_title="Failure Type",
        yaxis_title="Count",
        height=400,
    )

    return fig.to_json()


def generate_operational_visualizations(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate all operational visualizations using Plotly.

    Args:
        context: Report context with operational data

    Returns:
        Dictionary of Plotly figure JSONs
    """
    visualizations = {}

    # Create well status distribution chart
    if "operational_summary" in context:
        summary = context["operational_summary"]
        visualizations["well_status_chart"] = create_well_status_chart(summary)

    # Create production efficiency gauge
    if "production_efficiency" in context:
        efficiency = context["production_efficiency"]
        visualizations["efficiency_gauge"] = create_efficiency_gauge(efficiency)

    # Create equipment reliability chart
    if "equipment_reliability" in context:
        reliability = context["equipment_reliability"]
        visualizations["reliability_chart"] = create_reliability_chart(reliability)

    # Create KPI dashboard
    if "operational_kpis" in context:
        kpis = context["operational_kpis"]
        visualizations["kpi_dashboard"] = create_kpi_dashboard(kpis)

    # Create failure analysis chart
    if "failure_analysis" in context:
        failures = context["failure_analysis"]
        visualizations["failure_chart"] = create_failure_chart(failures)

    return visualizations


# Export all public names
__all__ = [
    "create_well_status_chart",
    "create_efficiency_gauge",
    "create_reliability_chart",
    "create_kpi_dashboard",
    "create_failure_chart",
    "generate_operational_visualizations",
]
