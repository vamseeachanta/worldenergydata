"""
Compliance Charts for regulatory compliance visualization.

This module contains chart generation functions for compliance dashboards,
production quota charts, environmental trends, safety metrics, and milestone timelines.
"""

from typing import Any, Dict, List

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from .compliance_models import RegulatoryMilestone


def create_compliance_dashboard(compliance_data: Dict[str, Any]) -> str:
    """Create compliance dashboard with gauge charts"""
    # Create subplot with gauge charts
    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, {"type": "indicator"}],
        ],
        subplot_titles=[
            "Production Compliance",
            "Environmental Score",
            "Safety Score",
            "Overall Compliance",
        ],
    )

    # Production Compliance Gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=compliance_data.get("production_compliance", 0),
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Production Compliance (%)"},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 70], "color": "lightgray"},
                    {"range": [70, 90], "color": "gray"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        ),
        row=1,
        col=1,
    )

    # Environmental Score Gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=compliance_data.get("environmental_score", 0) * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Environmental Score (%)"},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "green"},
                "steps": [
                    {"range": [0, 70], "color": "lightgray"},
                    {"range": [70, 90], "color": "gray"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 80,
                },
            },
        ),
        row=1,
        col=2,
    )

    # Safety Score Gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=compliance_data.get("safety_score", 0) * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Safety Score (%)"},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "orange"},
                "steps": [
                    {"range": [0, 75], "color": "lightgray"},
                    {"range": [75, 90], "color": "gray"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 85,
                },
            },
        ),
        row=2,
        col=1,
    )

    # Overall Compliance Gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=compliance_data.get("overall_compliance_score", 0) * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Overall Compliance (%)"},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "purple"},
                "steps": [
                    {"range": [0, 80], "color": "lightgray"},
                    {"range": [80, 95], "color": "gray"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        ),
        row=2,
        col=2,
    )

    fig.update_layout(title="Compliance Dashboard", height=600, showlegend=False)

    return pio.to_html(fig, include_plotlyjs="cdn")


def create_production_quota_chart(quota_data: Dict[str, Any]) -> str:
    """Create production quota vs actual chart"""
    categories = ["Oil Production", "Gas Production"]
    quota_values = [
        quota_data["oil_quota"],
        quota_data["gas_quota"] / 1000,
    ]  # Convert gas to Mcf
    actual_values = [quota_data["oil_actual"], quota_data["gas_actual"] / 1000]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(name="Quota", x=categories, y=quota_values, marker_color="lightblue")
    )

    fig.add_trace(
        go.Bar(name="Actual", x=categories, y=actual_values, marker_color="darkblue")
    )

    fig.update_layout(
        title="Production Quota vs Actual",
        xaxis_title="Production Type",
        yaxis_title="Volume",
        barmode="group",
        height=400,
    )

    return pio.to_html(fig, include_plotlyjs="cdn")


def create_environmental_trends_chart() -> str:
    """Create environmental compliance trends chart"""
    # Placeholder data - in real implementation, this would use historical data
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    spill_incidents = [0, 1, 0, 0, 2, 1]
    environmental_scores = [0.95, 0.88, 0.95, 0.95, 0.82, 0.91]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=months,
            y=spill_incidents,
            mode="lines+markers",
            name="Spill Incidents",
            line=dict(color="red"),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=months,
            y=environmental_scores,
            mode="lines+markers",
            name="Environmental Score",
            line=dict(color="green"),
        ),
        secondary_y=True,
    )

    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Spill Incidents", secondary_y=False)
    fig.update_yaxes(title_text="Environmental Score", secondary_y=True)

    fig.update_layout(title="Environmental Compliance Trends", height=400)

    return pio.to_html(fig, include_plotlyjs="cdn")


def create_safety_metrics_chart(safety_data: Dict[str, Any]) -> str:
    """Create safety metrics chart"""
    metrics = ["TRIR", "LTIR", "Near Misses", "Safety Score"]
    values = [
        safety_data.get("trir", 0),
        safety_data.get("ltir", 0),
        safety_data.get("near_misses", 0),
        safety_data.get("safety_score", 0) * 100,  # Convert to percentage
    ]

    fig = go.Figure(
        go.Bar(x=metrics, y=values, marker_color=["red", "orange", "yellow", "green"])
    )

    fig.update_layout(
        title="Safety Performance Metrics",
        xaxis_title="Metric",
        yaxis_title="Value",
        height=400,
    )

    return pio.to_html(fig, include_plotlyjs="cdn")


def create_milestone_timeline(milestones: List[RegulatoryMilestone]) -> str:
    """Create regulatory milestone timeline"""
    if not milestones:
        # Return empty chart if no milestones
        fig = go.Figure()
        fig.update_layout(
            title="Regulatory Milestones Timeline",
            annotations=[
                dict(text="No milestones to display", showarrow=False, x=0.5, y=0.5)
            ],
        )
        return pio.to_html(fig, include_plotlyjs="cdn")

    # Prepare data for timeline
    milestone_names = [
        m.description[:50] + "..." if len(m.description) > 50 else m.description
        for m in milestones
    ]
    due_dates = [m.due_date for m in milestones if m.due_date]
    completion_dates = [m.completion_date for m in milestones if m.completion_date]

    fig = go.Figure()

    # Add due dates
    if due_dates:
        fig.add_trace(
            go.Scatter(
                x=due_dates,
                y=milestone_names[: len(due_dates)],
                mode="markers",
                name="Due Date",
                marker=dict(color="red", size=10, symbol="x"),
            )
        )

    # Add completion dates
    if completion_dates:
        completed_names = [
            milestone_names[i] for i, m in enumerate(milestones) if m.completion_date
        ]
        fig.add_trace(
            go.Scatter(
                x=completion_dates,
                y=completed_names,
                mode="markers",
                name="Completed",
                marker=dict(color="green", size=10, symbol="circle"),
            )
        )

    fig.update_layout(
        title="Regulatory Milestones Timeline",
        xaxis_title="Date",
        yaxis_title="Milestone",
        height=max(400, len(milestones) * 30),
    )

    return pio.to_html(fig, include_plotlyjs="cdn")


# Public API
__all__ = [
    "create_compliance_dashboard",
    "create_production_quota_chart",
    "create_environmental_trends_chart",
    "create_safety_metrics_chart",
    "create_milestone_timeline",
]
