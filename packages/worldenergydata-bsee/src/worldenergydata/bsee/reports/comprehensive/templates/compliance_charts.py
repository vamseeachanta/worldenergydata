"""
Compliance Charts for regulatory compliance visualization.

This module contains chart generation functions for compliance dashboards,
production quota charts, environmental trends, safety metrics, and milestone timelines.
"""

from collections.abc import Mapping
from math import isfinite
from numbers import Real
from typing import Any, Dict, List

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from .compliance_models import RegulatoryMilestone


def _chart_number(value: Any, maximum: float | None = None) -> float | None:
    """Accept finite, nonnegative real measurements; unknown stays unknown."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    if not isfinite(number) or number < 0:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def create_compliance_dashboard(compliance_data: Dict[str, Any]) -> str:
    """Create gauges, marking missing or invalid metrics NOT_EVALUATED.

    Production is already a percentage and can exceed full production.
    Environmental and safety scores are fractions within the unit interval.
    The calculated overall fraction can exceed unity during overproduction.
    Numeric strings and booleans are not treated as measurements.
    """
    compliance_data = compliance_data if isinstance(compliance_data, Mapping) else {}
    # Presentation policy retained from this function at d867ba1e (2026).
    # The bands and markers below are not sourced regulatory acceptance limits.
    gauges = [
        ("production_compliance", "Production Compliance", "darkblue", 70, 90, 90),
        ("environmental_score", "Environmental Score", "green", 70, 90, 80),
        ("safety_score", "Safety Score", "orange", 75, 90, 85),
        ("overall_compliance_score", "Overall Compliance", "purple", 80, 95, 90),
    ]
    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, {"type": "indicator"}],
        ],
        subplot_titles=[gauge[1] for gauge in gauges],
    )
    for index, (key, title, color, lower, upper, threshold) in enumerate(gauges):
        row, col = divmod(index, 2)
        production = key == "production_compliance"
        # Only environmental and safety scores use the unit-interval contract.
        # ComplianceTemplate._generate_compliance_summary leaves overall uncapped.
        maximum = 1.0 if key in ("environmental_score", "safety_score") else None
        value = _chart_number(compliance_data.get(key), maximum)
        if value is not None and not production:
            # Percent conversion: NIST SP 811, section 7.10.2, online revision 2025.
            value = _chart_number(value * 100)
        if value is None:
            fig.add_annotation(
                text=f"{title}<br>NOT_EVALUATED",
                x=(col + 0.5) / 2,
                y=1 - (row + 0.5) / 2,
                xref="paper",
                yref="paper",
                showarrow=False,
            )
            continue
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta" if production else "gauge+number",
                value=value,
                title={"text": f"{title} (%)"},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": color},
                    "steps": [
                        {"range": [0, lower], "color": "lightgray"},
                        {"range": [lower, upper], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": threshold,
                    },
                },
            ),
            row=row + 1,
            col=col + 1,
        )
    fig.update_layout(title="Compliance Dashboard", height=600, showlegend=False)
    return pio.to_html(fig, include_plotlyjs="cdn")


def create_production_quota_chart(quota_data: Dict[str, Any]) -> str:
    """Create quota bars with gaps for unavailable measurements."""
    quota_data = quota_data if isinstance(quota_data, Mapping) else {}
    categories = ["Oil Production (bbl)", "Gas Production (thousand Mcf)"]
    # Retain this function's gas display divisor from d867ba1e (2026).
    # Inputs are Mcf per ComplianceTemplate.add_production_quota_analysis;
    # this is display scaling, not a conversion to Mcf.
    values = {
        key: _chart_number(quota_data.get(key))
        for key in ("oil_quota", "gas_quota", "oil_actual", "gas_actual")
    }
    fig = go.Figure()
    for label, suffix, color in (
        ("Quota", "quota", "lightblue"),
        ("Actual", "actual", "darkblue"),
    ):
        gas = values[f"gas_{suffix}"]
        fig.add_trace(
            go.Bar(
                name=label,
                x=categories,
                y=[values[f"oil_{suffix}"], gas / 1000 if gas is not None else None],
                marker_color=color,
            )
        )
    missing = [key for key, value in values.items() if value is None]
    if missing:
        fig.add_annotation(
            text="NOT_EVALUATED: " + ", ".join(missing),
            x=0.5,
            y=1.1,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
    fig.update_layout(
        title="Production Quota vs Actual",
        xaxis_title="Production Type",
        yaxis_title="Volume (units shown by category)",
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
