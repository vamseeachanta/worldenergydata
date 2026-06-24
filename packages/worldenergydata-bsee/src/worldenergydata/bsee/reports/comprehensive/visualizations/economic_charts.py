"""
Economic visualizations for comprehensive reports.

Provides waterfall charts, ROI analysis, cashflow visualizations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class EconomicMetrics:
    """Economic performance metrics."""

    revenue: float
    operating_costs: float
    capital_costs: float
    net_income: float
    roi: float
    payback_period: float
    npv: float
    irr: float


class EconomicChart:
    """
    Creates economic visualizations for comprehensive reports.

    Supports waterfall charts, ROI analysis, cashflow projections.
    """

    def __init__(self, currency: str = "USD", theme: str = "plotly_white"):
        """
        Initialize economic chart generator.

        Args:
            currency: Currency symbol/code
            theme: Plotly theme
        """
        self.currency = currency
        self.theme = theme

    def create_waterfall_chart(
        self,
        categories: List[str],
        values: List[float],
        title: str = None,
        measure: Optional[List[str]] = None,
    ) -> go.Figure:
        """
        Create waterfall chart for financial breakdown.

        Args:
            categories: Category names
            values: Values for each category
            title: Chart title
            measure: List of measure types (relative, total, absolute)

        Returns:
            Plotly figure with waterfall chart
        """
        if measure is None:
            # Auto-detect measure types
            measure = []
            for i, cat in enumerate(categories):
                if i == 0:
                    measure.append("absolute")
                elif (
                    "total" in cat.lower()
                    or "net" in cat.lower()
                    and i == len(categories) - 1
                ):
                    measure.append("total")
                else:
                    measure.append("relative")

        # Format text values
        text_values = [f"{self.currency} {abs(v):,.0f}" for v in values]

        fig = go.Figure(
            go.Waterfall(
                name="Financial Breakdown",
                orientation="v",
                measure=measure,
                x=categories,
                y=values,
                text=text_values,
                textposition="outside",
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                decreasing={"marker": {"color": "#EF553B"}},
                increasing={"marker": {"color": "#00CC96"}},
                totals={"marker": {"color": "#636EFA"}},
                hovertemplate="<b>%{x}</b><br>"
                + f"{self.currency} %{{y:,.0f}}<br>"
                + "<extra></extra>",
            )
        )

        fig.update_layout(
            title=title or "Financial Waterfall Analysis",
            xaxis_title="Category",
            yaxis_title=f"Amount ({self.currency})",
            height=600,
            width=1000,
            template=self.theme,
            showlegend=False,
        )

        return fig

    def create_roi_analysis(
        self,
        metrics: EconomicMetrics,
        benchmarks: Optional[Dict[str, float]] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create ROI analysis visualization.

        Args:
            metrics: Economic metrics
            benchmarks: Optional benchmark values
            title: Chart title

        Returns:
            Plotly figure with ROI analysis
        """
        # Create gauge charts for key metrics
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=("ROI (%)", "NPV", "IRR (%)", "Payback Period"),
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "indicator"}],
            ],
        )

        # ROI Gauge
        roi_color = (
            "green" if metrics.roi > 15 else "orange" if metrics.roi > 10 else "red"
        )
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=metrics.roi,
                title={"text": "ROI (%)"},
                delta={"reference": benchmarks.get("roi", 15) if benchmarks else 15},
                gauge={
                    "axis": {"range": [None, 50]},
                    "bar": {"color": roi_color},
                    "steps": [
                        {"range": [0, 10], "color": "lightgray"},
                        {"range": [10, 20], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 4},
                        "thickness": 0.75,
                        "value": 25,
                    },
                },
            ),
            row=1,
            col=1,
        )

        # NPV Gauge
        npv_millions = metrics.npv / 1_000_000
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=npv_millions,
                title={"text": f"NPV ({self.currency}M)"},
                delta={
                    "reference": (
                        benchmarks.get("npv", 100) / 1_000_000 if benchmarks else 100
                    )
                },
                number={"valueformat": ",.1f"},
                domain={"x": [0.5, 1], "y": [0.5, 1]},
            ),
            row=1,
            col=2,
        )

        # IRR Gauge
        irr_color = (
            "green" if metrics.irr > 20 else "orange" if metrics.irr > 15 else "red"
        )
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=metrics.irr,
                title={"text": "IRR (%)"},
                delta={"reference": benchmarks.get("irr", 18) if benchmarks else 18},
                gauge={
                    "axis": {"range": [None, 40]},
                    "bar": {"color": irr_color},
                    "steps": [
                        {"range": [0, 15], "color": "lightgray"},
                        {"range": [15, 25], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 4},
                        "thickness": 0.75,
                        "value": 30,
                    },
                },
            ),
            row=2,
            col=1,
        )

        # Payback Period Gauge
        payback_color = (
            "green"
            if metrics.payback_period < 3
            else "orange" if metrics.payback_period < 5 else "red"
        )
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=metrics.payback_period,
                title={"text": "Payback (Years)"},
                delta={
                    "reference": benchmarks.get("payback", 4) if benchmarks else 4,
                    "decreasing": {"color": "green"},
                    "increasing": {"color": "red"},
                },
                gauge={
                    "axis": {"range": [0, 10]},
                    "bar": {"color": payback_color},
                    "steps": [
                        {"range": [0, 3], "color": "lightgreen"},
                        {"range": [3, 5], "color": "lightyellow"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 7,
                    },
                },
            ),
            row=2,
            col=2,
        )

        fig.update_layout(
            title=title or "ROI Analysis Dashboard",
            height=600,
            width=900,
            template=self.theme,
            showlegend=False,
        )

        return fig

    def create_cashflow_projection(
        self,
        cashflow_data: pd.DataFrame,
        title: str = None,
        show_cumulative: bool = True,
    ) -> go.Figure:
        """
        Create cashflow projection visualization.

        Args:
            cashflow_data: DataFrame with cashflow projections
            title: Chart title
            show_cumulative: Whether to show cumulative cashflow

        Returns:
            Plotly figure with cashflow projection
        """
        fig = go.Figure()

        # Monthly/Quarterly cashflow bars
        colors = ["green" if x >= 0 else "red" for x in cashflow_data["net_cashflow"]]

        fig.add_trace(
            go.Bar(
                x=cashflow_data.index,
                y=cashflow_data["net_cashflow"],
                name="Net Cashflow",
                marker_color=colors,
                hovertemplate="<b>Period: %{x}</b><br>"
                + f"Cashflow: {self.currency} %{{y:,.0f}}<br>"
                + "<extra></extra>",
            )
        )

        # Add cumulative line if requested
        if show_cumulative:
            cumulative = cashflow_data["net_cashflow"].cumsum()

            fig.add_trace(
                go.Scatter(
                    x=cashflow_data.index,
                    y=cumulative,
                    name="Cumulative Cashflow",
                    mode="lines+markers",
                    line=dict(color="blue", width=2),
                    yaxis="y2",
                    hovertemplate="<b>Period: %{x}</b><br>"
                    + f"Cumulative: {self.currency} %{{y:,.0f}}<br>"
                    + "<extra></extra>",
                )
            )

        # Add break-even line
        fig.add_hline(
            y=0, line_dash="dash", line_color="gray", annotation_text="Break-even"
        )

        fig.update_layout(
            title=title or "Cashflow Projection",
            xaxis_title="Period",
            yaxis_title=f"Net Cashflow ({self.currency})",
            yaxis2=dict(
                title=f"Cumulative Cashflow ({self.currency})",
                overlaying="y",
                side="right",
            ),
            height=600,
            width=1200,
            template=self.theme,
            hovermode="x unified",
            showlegend=True,
        )

        return fig

    def create_cost_breakdown(
        self, costs: Dict[str, float], title: str = None, chart_type: str = "pie"
    ) -> go.Figure:
        """
        Create cost breakdown visualization.

        Args:
            costs: Dictionary of cost categories and values
            title: Chart title
            chart_type: 'pie' or 'sunburst'

        Returns:
            Plotly figure with cost breakdown
        """
        if chart_type == "sunburst":
            # Prepare data for sunburst
            labels = []
            parents = []
            values = []
            colors = []

            total = sum(costs.values())
            labels.append("Total Costs")
            parents.append("")
            values.append(total)
            colors.append("#636EFA")

            # Add main categories
            color_palette = px.colors.qualitative.Set3
            for i, (category, value) in enumerate(costs.items()):
                labels.append(category)
                parents.append("Total Costs")
                values.append(value)
                colors.append(color_palette[i % len(color_palette)])

            fig = go.Figure(
                go.Sunburst(
                    labels=labels,
                    parents=parents,
                    values=values,
                    marker=dict(colors=colors),
                    hovertemplate="<b>%{label}</b><br>"
                    + f"{self.currency} %{{value:,.0f}}<br>"
                    + "Percentage: %{percentParent}<br>"
                    + "<extra></extra>",
                )
            )
        else:
            # Pie chart
            fig = go.Figure(
                go.Pie(
                    labels=list(costs.keys()),
                    values=list(costs.values()),
                    hole=0.3,
                    textposition="auto",
                    textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>"
                    + f"{self.currency} %{{value:,.0f}}<br>"
                    + "Percentage: %{percent}<br>"
                    + "<extra></extra>",
                )
            )

        fig.update_layout(
            title=title or "Cost Breakdown Analysis",
            height=600,
            width=800,
            template=self.theme,
        )

        return fig

    def create_revenue_streams(
        self, revenue_data: pd.DataFrame, streams: List[str] = None, title: str = None
    ) -> go.Figure:
        """
        Create stacked area chart for revenue streams.

        Args:
            revenue_data: DataFrame with revenue stream data
            streams: List of revenue streams to include
            title: Chart title

        Returns:
            Plotly figure with revenue streams
        """
        if streams is None:
            streams = [col for col in revenue_data.columns if col != "total"]

        fig = go.Figure()

        # Add area traces for each stream
        for stream in streams:
            if stream in revenue_data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=revenue_data.index,
                        y=revenue_data[stream],
                        name=stream.replace("_", " ").title(),
                        mode="lines",
                        stackgroup="revenue",
                        fillcolor=None,
                        hovertemplate="<b>%{text}</b><br>"
                        + "Period: %{x}<br>"
                        + f"Revenue: {self.currency} %{{y:,.0f}}<br>"
                        + "<extra></extra>",
                        text=stream.replace("_", " ").title(),
                    )
                )

        fig.update_layout(
            title=title or "Revenue Streams Analysis",
            xaxis_title="Period",
            yaxis_title=f"Revenue ({self.currency})",
            height=600,
            width=1200,
            template=self.theme,
            hovermode="x unified",
            showlegend=True,
        )

        return fig

    def create_sensitivity_analysis(
        self,
        base_npv: float,
        sensitivities: Dict[str, List[Tuple[float, float]]],
        title: str = None,
    ) -> go.Figure:
        """
        Create tornado chart for sensitivity analysis.

        Args:
            base_npv: Base case NPV
            sensitivities: Dict of parameter names to (low, high) NPV values
            title: Chart title

        Returns:
            Plotly figure with tornado chart
        """
        # Sort by impact magnitude
        sorted_params = sorted(
            sensitivities.items(), key=lambda x: abs(x[1][1] - x[1][0]), reverse=True
        )

        fig = go.Figure()

        # Add bars for each parameter
        for i, (param, (low_val, high_val)) in enumerate(sorted_params):
            # Low scenario (negative impact)
            fig.add_trace(
                go.Bar(
                    y=[param],
                    x=[low_val - base_npv],
                    orientation="h",
                    name="Downside",
                    marker_color="red",
                    showlegend=(i == 0),
                    hovertemplate=f"<b>{param}</b><br>"
                    + f"Downside NPV: {self.currency} {low_val:,.0f}<br>"
                    + f"Impact: {self.currency} {low_val - base_npv:,.0f}<br>"
                    + "<extra></extra>",
                )
            )

            # High scenario (positive impact)
            fig.add_trace(
                go.Bar(
                    y=[param],
                    x=[high_val - base_npv],
                    orientation="h",
                    name="Upside",
                    marker_color="green",
                    showlegend=(i == 0),
                    hovertemplate=f"<b>{param}</b><br>"
                    + f"Upside NPV: {self.currency} {high_val:,.0f}<br>"
                    + f"Impact: {self.currency} {high_val - base_npv:,.0f}<br>"
                    + "<extra></extra>",
                )
            )

        # Add base case line
        fig.add_vline(
            x=0,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Base NPV: {self.currency} {base_npv:,.0f}",
        )

        fig.update_layout(
            title=title or "NPV Sensitivity Analysis",
            xaxis_title=f"NPV Impact ({self.currency})",
            yaxis_title="Parameter",
            height=max(400, len(sensitivities) * 50),
            width=900,
            template=self.theme,
            barmode="overlay",
            showlegend=True,
        )

        return fig

    def create_investment_comparison(
        self, investments: Dict[str, Dict[str, float]], title: str = None
    ) -> go.Figure:
        """
        Create comparison chart for multiple investment options.

        Args:
            investments: Dictionary of investment names to metrics
            title: Chart title

        Returns:
            Plotly figure with investment comparison
        """
        # Create radar chart for comparison
        categories = ["NPV", "IRR", "ROI", "Risk Score", "Payback"]

        fig = go.Figure()

        for inv_name, metrics in investments.items():
            # Normalize metrics to 0-100 scale for comparison
            values = [
                min(100, metrics.get("npv", 0) / 1_000_000),  # NPV in millions
                min(100, metrics.get("irr", 0) * 2),  # IRR scaled
                min(100, metrics.get("roi", 0) * 2),  # ROI scaled
                100 - metrics.get("risk_score", 50),  # Risk inverted
                100 - min(100, metrics.get("payback", 5) * 10),  # Payback inverted
            ]

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill="toself",
                    name=inv_name,
                    hovertemplate="<b>%{text}</b><br>"
                    + "%{theta}: %{r:.1f}<br>"
                    + "<extra></extra>",
                    text=inv_name,
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=title or "Investment Options Comparison",
            height=600,
            width=600,
            template=self.theme,
            showlegend=True,
        )

        return fig

    def create_breakeven_analysis(
        self,
        production_data: pd.DataFrame,
        price_scenarios: Dict[str, float],
        fixed_costs: float,
        variable_costs: float,
        title: str = None,
    ) -> go.Figure:
        """
        Create breakeven analysis chart.

        Args:
            production_data: DataFrame with production volumes
            price_scenarios: Dictionary of scenario names to prices
            fixed_costs: Fixed costs
            variable_costs: Variable costs per unit
            title: Chart title

        Returns:
            Plotly figure with breakeven analysis
        """
        fig = go.Figure()

        # Production volume range
        volumes = (
            production_data["volume"]
            if "volume" in production_data.columns
            else production_data.iloc[:, 0]
        )

        # Add revenue lines for different price scenarios
        for scenario, price in price_scenarios.items():
            revenue = volumes * price
            fig.add_trace(
                go.Scatter(
                    x=volumes,
                    y=revenue,
                    name=f"Revenue @ {self.currency}{price}",
                    mode="lines",
                    line=dict(width=2),
                    hovertemplate=f"<b>{scenario}</b><br>"
                    + "Volume: %{x:,.0f}<br>"
                    + f"Revenue: {self.currency} %{{y:,.0f}}<br>"
                    + "<extra></extra>",
                )
            )

        # Add total cost line
        total_costs = fixed_costs + (volumes * variable_costs)
        fig.add_trace(
            go.Scatter(
                x=volumes,
                y=total_costs,
                name="Total Costs",
                mode="lines",
                line=dict(color="red", width=2, dash="dash"),
                hovertemplate="<b>Total Costs</b><br>"
                + "Volume: %{x:,.0f}<br>"
                + f"Cost: {self.currency} %{{y:,.0f}}<br>"
                + "<extra></extra>",
            )
        )

        # Calculate and mark breakeven points
        for scenario, price in price_scenarios.items():
            if price > variable_costs:
                breakeven_volume = fixed_costs / (price - variable_costs)
                breakeven_revenue = breakeven_volume * price

                fig.add_trace(
                    go.Scatter(
                        x=[breakeven_volume],
                        y=[breakeven_revenue],
                        mode="markers",
                        marker=dict(size=12, symbol="x"),
                        name=f"Breakeven @ {self.currency}{price}",
                        hovertemplate="<b>Breakeven Point</b><br>"
                        + f"Price: {self.currency}{price}<br>"
                        + f"Volume: {breakeven_volume:,.0f}<br>"
                        + f"Revenue: {self.currency} {breakeven_revenue:,.0f}<br>"
                        + "<extra></extra>",
                    )
                )

        fig.update_layout(
            title=title or "Breakeven Analysis",
            xaxis_title="Production Volume",
            yaxis_title=f"Amount ({self.currency})",
            height=600,
            width=1000,
            template=self.theme,
            hovermode="closest",
            showlegend=True,
        )

        return fig
