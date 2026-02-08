"""
Economic chart generation for comprehensive financial reports
Contains Plotly-based visualization functions for waterfall, dashboard, tornado, and time series charts
"""

from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from .economic_models import WaterfallComponent


def create_empty_chart(message: str = "No data available") -> str:
    """Create empty chart with message"""
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        xanchor="center",
        yanchor="middle",
        font=dict(size=16, color="gray"),
    )

    fig.update_layout(
        title="Chart Not Available",
        height=300,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return pio.to_html(fig, include_plotlyjs="cdn")


def generate_waterfall_chart(
    waterfall_components: List[WaterfallComponent],
    title: str = "Economic Waterfall Analysis",
) -> str:
    """Generate waterfall chart showing revenue to net income flow"""

    if not waterfall_components:
        return create_empty_chart("No data available for waterfall chart")

    # Prepare data for Plotly waterfall chart
    names = [component.name for component in waterfall_components]
    values = [component.value for component in waterfall_components]

    # Create measures array - 'relative' for flow items, 'total' for final result
    measures = []
    colors = []

    for component in waterfall_components:
        if component.component_type == "profit":
            measures.append("total")
            colors.append("#2E86AB")  # Blue for final result
        elif component.component_type == "revenue":
            measures.append("relative")
            colors.append("#A23B72")  # Purple for revenue
        elif component.component_type == "cost":
            measures.append("relative")
            colors.append("#F18F01")  # Orange for costs
        else:
            measures.append("relative")
            colors.append("#C73E1D")  # Red for other

    # Create waterfall chart
    fig = go.Figure(
        go.Waterfall(
            name="Economic Flow",
            orientation="v",
            measure=measures,
            x=names,
            textposition="outside",
            text=[
                f"${val/1000000:.1f}M" if abs(val) >= 1000000 else f"${val/1000:.0f}K"
                for val in values
            ],
            y=values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#A23B72"}},  # Revenue color
            decreasing={"marker": {"color": "#F18F01"}},  # Cost color
            totals={"marker": {"color": "#2E86AB"}},  # Net income color
        )
    )

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "color": "#2F4F4F"},
        },
        xaxis_title="Economic Components",
        yaxis_title="Value (USD)",
        yaxis_tickformat="$,.0f",
        height=500,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    # Format y-axis with million/thousand suffixes
    fig.update_yaxes(tickformat="$,.0f", gridcolor="lightgray", gridwidth=0.5)

    # Rotate x-axis labels if too many components
    if len(names) > 6:
        fig.update_xaxes(tickangle=45)

    return pio.to_html(fig, include_plotlyjs="cdn", div_id="waterfall-chart")


def generate_economic_dashboard(
    context: Dict[str, Any],
    netback_analysis: Dict[str, Any],
    title: str = "Economic Performance Dashboard",
) -> str:
    """Generate comprehensive economic dashboard with multiple charts"""

    # Create subplot dashboard
    fig = make_subplots(
        rows=3,
        cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "pie"}],
            [{"type": "bar"}, {"type": "scatter"}],
            [{"colspan": 2, "type": "bar"}, None],
        ],
        subplot_titles=[
            "Key Performance Indicators",
            "Revenue Mix",
            "Cost Breakdown",
            "NPV Sensitivity",
            "Production Economics Comparison",
        ],
        vertical_spacing=0.1,
        horizontal_spacing=0.1,
    )

    # 1. KPI Indicators (Row 1, Col 1)
    profitability = context.get("profitability_metrics", {})
    profit_margin = profitability.get("profit_margin", 0)

    fig.add_trace(
        go.Indicator(
            mode="number+gauge+delta",
            value=profit_margin,
            domain={"x": [0, 1], "y": [0.7, 1]},
            title={"text": "Profit Margin (%)"},
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [None, 50]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 15], "color": "lightgray"},
                    {"range": [15, 30], "color": "gray"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 25,
                },
            },
        ),
        row=1,
        col=1,
    )

    # 2. Revenue Mix Pie Chart (Row 1, Col 2)
    revenue_breakdown = context.get("revenue_breakdown", {})

    pie_labels = []
    pie_values = []
    pie_colors = ["#A23B72", "#F18F01", "#C73E1D", "#2E86AB"]

    if revenue_breakdown.get("oil_revenue", 0) > 0:
        pie_labels.append("Oil Revenue")
        pie_values.append(revenue_breakdown["oil_revenue"])

    if revenue_breakdown.get("gas_revenue", 0) > 0:
        pie_labels.append("Gas Revenue")
        pie_values.append(revenue_breakdown["gas_revenue"])

    if revenue_breakdown.get("ngl_revenue", 0) > 0:
        pie_labels.append("NGL Revenue")
        pie_values.append(revenue_breakdown["ngl_revenue"])

    if pie_values:
        fig.add_trace(
            go.Pie(
                labels=pie_labels,
                values=pie_values,
                marker=dict(colors=pie_colors[: len(pie_labels)]),
                textinfo="label+percent",
                hole=0.3,
            ),
            row=1,
            col=2,
        )

    # 3. Cost Breakdown Bar Chart (Row 2, Col 1)
    cost_analysis = context.get("cost_analysis", {})

    cost_categories = ["Operating", "Royalties", "Severance Tax", "Capital"]
    cost_values = [
        cost_analysis.get("operating_costs", 0),
        cost_analysis.get("royalties", 0),
        cost_analysis.get("severance_tax", 0),
        cost_analysis.get("capital_costs", 0),
    ]

    # Filter out zero values
    filtered_costs = [
        (cat, val) for cat, val in zip(cost_categories, cost_values) if val > 0
    ]
    if filtered_costs:
        cost_cats, cost_vals = zip(*filtered_costs)

        fig.add_trace(
            go.Bar(
                x=cost_cats,
                y=cost_vals,
                marker_color="#F18F01",
                text=[
                    f"${val/1000000:.1f}M" if val >= 1000000 else f"${val/1000:.0f}K"
                    for val in cost_vals
                ],
                textposition="auto",
            ),
            row=2,
            col=1,
        )

    # 4. NPV Sensitivity Analysis (Row 2, Col 2)
    sensitivity_data = context.get("sensitivity_analysis", {})
    oil_sensitivity = sensitivity_data.get("oil_price_sensitivity", [])

    if oil_sensitivity:
        price_changes = [item["price_change_pct"] for item in oil_sensitivity]
        npvs = [
            item["npv"] / 1000000 for item in oil_sensitivity
        ]  # Convert to millions

        fig.add_trace(
            go.Scatter(
                x=price_changes,
                y=npvs,
                mode="lines+markers",
                line=dict(color="#2E86AB", width=3),
                marker=dict(size=8, color="#A23B72"),
                name="NPV vs Oil Price",
            ),
            row=2,
            col=2,
        )

    # 5. Production Economics Comparison (Row 3, spanning both columns)
    metrics = ["Revenue/BOE", "Operating Cost/BOE", "Royalties/BOE", "Net/BOE"]
    values = [
        netback_analysis["revenue_per_boe_breakdown"].get("total_revenue_per_boe", 0),
        netback_analysis["cost_per_boe_breakdown"].get("operating_cost_per_boe", 0),
        netback_analysis["cost_per_boe_breakdown"].get("royalties_per_boe", 0),
        netback_analysis["netback_calculation"].get("full_netback_per_boe", 0),
    ]

    colors = ["#A23B72", "#F18F01", "#C73E1D", "#2E86AB"]

    fig.add_trace(
        go.Bar(
            x=metrics,
            y=values,
            marker_color=colors,
            text=[f"${val:.2f}" for val in values],
            textposition="auto",
        ),
        row=3,
        col=1,
    )

    # Update layout
    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 22, "color": "#2F4F4F"},
        },
        height=900,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    # Update axes
    fig.update_yaxes(tickformat="$,.0f", row=2, col=1)
    fig.update_yaxes(title_text="NPV ($M)", row=2, col=2)
    fig.update_xaxes(title_text="Oil Price Change (%)", row=2, col=2)
    fig.update_yaxes(title_text="Value per BOE ($)", tickformat="$,.2f", row=3, col=1)

    return pio.to_html(fig, include_plotlyjs="cdn", div_id="economic-dashboard")


def generate_sensitivity_tornado_chart(
    tornado_data: List[Dict[str, Any]], title: str = "NPV Sensitivity Analysis"
) -> str:
    """Generate tornado chart for sensitivity analysis"""

    if not tornado_data:
        return create_empty_chart("No sensitivity data available")

    # Prepare data for tornado chart
    variables = [item["variable"] for item in tornado_data]
    low_values = [
        item["low_case"] / 1000000 for item in tornado_data
    ]  # Convert to millions
    high_values = [item["high_case"] / 1000000 for item in tornado_data]

    # Calculate ranges for sorting (already sorted in tornado_data)
    ranges = [high - low for high, low in zip(high_values, low_values)]

    # Create horizontal bar chart (tornado style)
    fig = go.Figure()

    # Add bars for negative impact (low case)
    fig.add_trace(
        go.Bar(
            y=variables,
            x=[-r / 2 for r in ranges],  # Negative half of range
            orientation="h",
            name="Downside Impact",
            marker_color="#F18F01",
            text=[f"${low:.1f}M" for low in low_values],
            textposition="auto",
            width=0.6,
        )
    )

    # Add bars for positive impact (high case)
    fig.add_trace(
        go.Bar(
            y=variables,
            x=[r / 2 for r in ranges],  # Positive half of range
            orientation="h",
            name="Upside Impact",
            marker_color="#A23B72",
            text=[f"${high:.1f}M" for high in high_values],
            textposition="auto",
            width=0.6,
        )
    )

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#2F4F4F"},
        },
        xaxis_title="NPV Impact ($M)",
        yaxis_title="Variables",
        barmode="relative",
        height=400,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Add vertical line at zero
    fig.add_vline(x=0, line_width=2, line_color="black")

    return pio.to_html(fig, include_plotlyjs="cdn", div_id="tornado-chart")


def generate_production_economics_time_series(
    context: Dict[str, Any],
    netback_analysis: Dict[str, Any],
    title: str = "Production Economics Over Time",
) -> str:
    """Generate time series chart showing production and economics trends"""

    # Mock time series data - in real implementation, this would come from historical data
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    # Generate sample data based on current production with some variability
    production_metrics = context.get("production_metrics", {})
    base_oil = production_metrics.get("oil_bbls", 1000000) / 12  # Monthly
    base_gas = production_metrics.get("gas_mcf", 6000000) / 12  # Monthly

    # Add some monthly variation
    oil_production = [base_oil * (0.85 + 0.3 * (i % 4) / 4) for i in range(12)]
    gas_production = [base_gas * (0.9 + 0.2 * (i % 3) / 3) for i in range(12)]

    # Calculate monthly netback (simplified)
    base_netback = netback_analysis["netback_calculation"].get(
        "full_netback_per_boe", 30
    )
    monthly_netback = [base_netback * (0.8 + 0.4 * (i % 5) / 5) for i in range(12)]

    # Create subplot with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add oil production
    fig.add_trace(
        go.Scatter(
            x=months,
            y=oil_production,
            mode="lines+markers",
            name="Oil Production (bbls/month)",
            line=dict(color="#A23B72", width=3),
            marker=dict(size=8),
        ),
        secondary_y=False,
    )

    # Add gas production
    fig.add_trace(
        go.Scatter(
            x=months,
            y=gas_production,
            mode="lines+markers",
            name="Gas Production (Mcf/month)",
            line=dict(color="#F18F01", width=3),
            marker=dict(size=8),
        ),
        secondary_y=False,
    )

    # Add netback on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=months,
            y=monthly_netback,
            mode="lines+markers",
            name="Netback ($/BOE)",
            line=dict(color="#2E86AB", width=3, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
        ),
        secondary_y=True,
    )

    # Update axes labels
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Production Volume", secondary_y=False)
    fig.update_yaxes(title_text="Netback ($/BOE)", secondary_y=True)

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#2F4F4F"},
        },
        height=500,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return pio.to_html(fig, include_plotlyjs="cdn", div_id="time-series-chart")
