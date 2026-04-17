# ABOUTME: WRK-019 cost report generator — HTML/Plotly charts for drilling,
# ABOUTME: completion, and intervention cost summaries by region and environment.

"""Cost report generator (WRK-019).

Produces HTML reports with Plotly charts for cost analysis outputs.

Charts produced:
- Cost breakdown by activity type (stacked bar per field)
- Regional cost comparison (grouped bar)
- Cost trend over time (line chart)
- Water depth vs cost scatter plot

Exports:
    generate_cost_report — write HTML report to disk
    build_breakdown_chart — stacked bar of drilling/completion/intervention
    build_regional_comparison_chart — grouped bar by region
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pandas as pd

if TYPE_CHECKING:
    import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def generate_cost_report(
    comparison_df: pd.DataFrame,
    output_path: Path,
    title: str = "Drilling, Completion & Intervention Cost Analysis",
) -> Path:
    """Generate an HTML cost report with Plotly charts.

    Args:
        comparison_df: DataFrame from ``build_comparison_dataframe``.
            Must contain: field_name, region, total_cost_usd_mm,
            deviation_pct, is_outlier, cost_per_well_usd_mm.
        output_path: Destination path for the HTML file.
        title: Report title displayed in HTML.

    Returns:
        Path to the written HTML file.

    Raises:
        ImportError: If plotly is not installed.
        ValueError: If comparison_df is missing required columns.
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as exc:
        raise ImportError(
            "plotly is required for report generation. "
            "Install with: pip install plotly"
        ) from exc

    required_cols = {
        "field_name",
        "region",
        "total_cost_usd_mm",
        "deviation_pct",
    }
    missing = required_cols - set(comparison_df.columns)
    if missing:
        raise ValueError(f"comparison_df missing required columns: {sorted(missing)}")

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Total Cost by Field (USD MM)",
            "Deviation from Regional Average (%)",
            "Cost per Well (USD MM)",
            "Cost Distribution",
        ),
    )

    # Panel 1 — total cost bar chart
    fig.add_trace(
        go.Bar(
            x=comparison_df["field_name"],
            y=comparison_df["total_cost_usd_mm"],
            name="Total Cost",
            marker_color="steelblue",
        ),
        row=1,
        col=1,
    )

    # Panel 2 — deviation from regional average
    colors = [
        "red" if x else "green"
        for x in comparison_df.get("is_outlier", [False] * len(comparison_df))
    ]
    fig.add_trace(
        go.Bar(
            x=comparison_df["field_name"],
            y=comparison_df["deviation_pct"],
            name="Deviation %",
            marker_color=colors,
        ),
        row=1,
        col=2,
    )

    # Panel 3 — cost per well
    if "cost_per_well_usd_mm" in comparison_df.columns:
        fig.add_trace(
            go.Bar(
                x=comparison_df["field_name"],
                y=comparison_df["cost_per_well_usd_mm"],
                name="Cost/Well",
                marker_color="darkorange",
            ),
            row=2,
            col=1,
        )

    # Panel 4 — histogram of total costs
    fig.add_trace(
        go.Histogram(
            x=comparison_df["total_cost_usd_mm"],
            name="Cost Distribution",
            marker_color="teal",
        ),
        row=2,
        col=2,
    )

    fig.update_layout(
        title_text=title,
        showlegend=False,
        height=800,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))
    logger.info("Cost report written to %s", output_path)
    return output_path


def build_breakdown_chart(
    field_name: str,
    drilling_cost_mm: float,
    completion_cost_mm: float,
    intervention_cost_mm: float,
) -> "go.Figure":  # type: ignore[name-defined]
    """Build a stacked bar chart of cost breakdown by activity.

    Args:
        field_name: Field identifier for chart title.
        drilling_cost_mm: Drilling total in USD MM.
        completion_cost_mm: Completion total in USD MM.
        intervention_cost_mm: Intervention total in USD MM.

    Returns:
        Plotly Figure object.

    Raises:
        ImportError: If plotly is not installed.
    """
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError("plotly required for charting") from exc

    fig = go.Figure(
        data=[
            go.Bar(name="Drilling", x=[field_name], y=[drilling_cost_mm]),
            go.Bar(name="Completion", x=[field_name], y=[completion_cost_mm]),
            go.Bar(name="Intervention", x=[field_name], y=[intervention_cost_mm]),
        ]
    )
    fig.update_layout(
        barmode="stack",
        title=f"Cost Breakdown — {field_name}",
        yaxis_title="USD MM",
    )
    return fig


def build_regional_comparison_chart(
    comparison_df: pd.DataFrame,
) -> "go.Figure":  # type: ignore[name-defined]
    """Build a grouped bar chart comparing costs across regions.

    Args:
        comparison_df: DataFrame from ``build_comparison_dataframe``.

    Returns:
        Plotly Figure object.

    Raises:
        ImportError: If plotly is not installed.
        ValueError: If required columns are missing.
    """
    try:
        import plotly.express as px
    except ImportError as exc:
        raise ImportError("plotly required for charting") from exc

    required = {"field_name", "region", "total_cost_usd_mm"}
    missing = required - set(comparison_df.columns)
    if missing:
        raise ValueError(f"comparison_df missing required columns: {sorted(missing)}")

    fig = px.bar(
        comparison_df,
        x="field_name",
        y="total_cost_usd_mm",
        color="region",
        title="Cross-Regional Cost Comparison",
        labels={"total_cost_usd_mm": "Total Cost (USD MM)"},
        barmode="group",
    )
    return fig
