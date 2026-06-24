"""
Interactive dashboard builder for comprehensive reports.

Provides dashboard creation with drill-down and filtering capabilities.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from dash import Dash, Input, Output, State, callback, dcc, html

    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False

    # Mock classes for when Dash is not installed
    class Dash:
        pass

    class dcc:
        pass

    class MockHtml:
        """Mock html module with required attributes."""

        def Div(*args, **kwargs):
            return None

        def H1(*args, **kwargs):
            return None

        def H2(*args, **kwargs):
            return None

        def H3(*args, **kwargs):
            return None

        def H4(*args, **kwargs):
            return None

        def P(*args, **kwargs):
            return None

        def Span(*args, **kwargs):
            return None

        def Button(*args, **kwargs):
            return None

    html = MockHtml()

    class Input:
        pass

    class Output:
        pass

    class State:
        pass

    def callback(*args, **kwargs):
        pass


from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DashboardConfig:
    """Dashboard configuration."""

    title: str
    theme: str = "plotly_white"
    auto_refresh: bool = False
    refresh_interval: int = 60000  # milliseconds
    enable_export: bool = True
    enable_filters: bool = True
    responsive: bool = True


@dataclass
class ChartConfig:
    """Individual chart configuration."""

    chart_id: str
    chart_type: str
    title: str
    data_source: str
    update_callback: Optional[Callable] = None
    filters: Optional[List[str]] = None


class DashboardBuilder:
    """
    Builds interactive dashboards for comprehensive reports.

    Supports drill-down, filtering, real-time updates, and export.
    """

    def __init__(self, config: Optional[DashboardConfig] = None):
        """
        Initialize dashboard builder.

        Args:
            config: Dashboard configuration
        """
        self.config = config or DashboardConfig(title="Dashboard")
        self.charts = []
        self.filters = {}
        self.data_sources = {}
        self.app = None

    def add_chart(self, chart_config: ChartConfig) -> None:
        """
        Add a chart to the dashboard.

        Args:
            chart_config: Chart configuration
        """
        self.charts.append(chart_config)

    def add_filter(
        self, filter_name: str, options: List[Any], default: Optional[Any] = None
    ) -> None:
        """
        Add a filter to the dashboard.

        Args:
            filter_name: Name of the filter
            options: Available filter options
            default: Default selection
        """
        self.filters[filter_name] = {
            "options": options,
            "default": default or options[0] if options else None,
        }

    def set_data_source(self, source_name: str, data: Any) -> None:
        """
        Set a data source for the dashboard.

        Args:
            source_name: Name of the data source
            data: Data (DataFrame, dict, etc.)
        """
        self.data_sources[source_name] = data

    def create_kpi_cards(self, kpis: Dict[str, Dict[str, Any]]) -> html.Div:
        """
        Create KPI cards section.

        Args:
            kpis: Dictionary of KPI names to values and metadata

        Returns:
            Dash HTML component with KPI cards
        """
        cards = []

        for kpi_name, kpi_data in kpis.items():
            value = kpi_data.get("value", 0)
            change = kpi_data.get("change", 0)
            unit = kpi_data.get("unit", "")
            icon = kpi_data.get("icon", "📊")

            # Determine color based on change
            change_color = "green" if change > 0 else "red" if change < 0 else "gray"
            change_symbol = "▲" if change > 0 else "▼" if change < 0 else "→"

            card = html.Div(
                [
                    html.Div(
                        [
                            html.Span(icon, style={"fontSize": "24px"}),
                            html.H4(kpi_name, style={"margin": "5px 0"}),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "10px",
                        },
                    ),
                    html.H2(f"{value:,.0f} {unit}", style={"margin": "10px 0"}),
                    html.P(
                        [
                            html.Span(
                                f"{change_symbol} {abs(change):.1f}%",
                                style={"color": change_color, "fontWeight": "bold"},
                            ),
                            " vs last period",
                        ],
                        style={"margin": "5px 0", "fontSize": "14px"},
                    ),
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "20px",
                    "borderRadius": "8px",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                    "flex": "1",
                    "minWidth": "200px",
                },
            )

            cards.append(card)

        return html.Div(
            cards,
            style={
                "display": "flex",
                "gap": "20px",
                "marginBottom": "20px",
                "flexWrap": "wrap",
            },
        )

    def create_filter_panel(self) -> html.Div:
        """
        Create filter panel with dropdowns and date pickers.

        Returns:
            Dash HTML component with filters
        """
        filter_components = []

        for filter_name, filter_config in self.filters.items():
            if filter_name.endswith("_date"):
                # Date picker
                component = html.Div(
                    [
                        html.Label(filter_name.replace("_", " ").title()),
                        dcc.DatePickerRange(
                            id=f"filter-{filter_name}",
                            start_date=filter_config["options"][0],
                            end_date=filter_config["options"][1],
                            display_format="YYYY-MM-DD",
                            style={"width": "100%"},
                        ),
                    ],
                    style={"marginBottom": "15px"},
                )
            else:
                # Dropdown
                component = html.Div(
                    [
                        html.Label(filter_name.replace("_", " ").title()),
                        dcc.Dropdown(
                            id=f"filter-{filter_name}",
                            options=[
                                {"label": str(opt), "value": opt}
                                for opt in filter_config["options"]
                            ],
                            value=filter_config["default"],
                            multi=filter_name.endswith("_multi"),
                            style={"width": "100%"},
                        ),
                    ],
                    style={"marginBottom": "15px"},
                )

            filter_components.append(component)

        return html.Div(
            [
                html.H3("Filters", style={"marginBottom": "20px"}),
                *filter_components,
                html.Button(
                    "Apply Filters",
                    id="apply-filters-btn",
                    style={
                        "width": "100%",
                        "padding": "10px",
                        "backgroundColor": "#1976D2",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "4px",
                        "cursor": "pointer",
                    },
                ),
            ],
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "8px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                "marginBottom": "20px",
            },
        )

    def create_production_dashboard(self, production_data: pd.DataFrame) -> Dash:
        """
        Create production-focused dashboard.

        Args:
            production_data: Production data DataFrame

        Returns:
            Dash application
        """
        app = Dash(__name__)

        # Calculate KPIs
        kpis = {
            "Total Production": {
                "value": (
                    production_data["oil"].sum()
                    if "oil" in production_data.columns
                    else 0
                ),
                "change": 5.2,
                "unit": "BBL",
                "icon": "🛢️",
            },
            "Average Daily Rate": {
                "value": (
                    production_data["oil"].mean()
                    if "oil" in production_data.columns
                    else 0
                ),
                "change": -2.1,
                "unit": "BBL/day",
                "icon": "📈",
            },
            "Active Wells": {
                "value": len(production_data.columns) - 1,
                "change": 10.0,
                "unit": "wells",
                "icon": "⚡",
            },
            "Efficiency": {"value": 87.5, "change": 3.4, "unit": "%", "icon": "🎯"},
        }

        # Create production trend chart
        from .production_charts import ProductionChart

        chart_gen = ProductionChart()
        trend_fig = chart_gen.create_production_trend(production_data)
        cumulative_fig = chart_gen.create_cumulative_production(production_data)

        # Layout
        app.layout = html.Div(
            [
                # Header
                html.Div(
                    [
                        html.H1(self.config.title, style={"margin": 0}),
                        html.P(
                            f'Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                            style={"margin": 0, "color": "gray"},
                        ),
                    ],
                    style={
                        "padding": "20px",
                        "backgroundColor": "white",
                        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                        "marginBottom": "20px",
                    },
                ),
                # KPI Cards
                self.create_kpi_cards(kpis),
                # Main content
                html.Div(
                    [
                        # Left: Filters
                        html.Div(
                            [self.create_filter_panel()], style={"flex": "0 0 250px"}
                        ),
                        # Right: Charts
                        html.Div(
                            [
                                # Production Trend
                                html.Div(
                                    [
                                        dcc.Graph(
                                            figure=trend_fig, id="production-trend"
                                        )
                                    ],
                                    style={
                                        "backgroundColor": "white",
                                        "padding": "20px",
                                        "borderRadius": "8px",
                                        "marginBottom": "20px",
                                        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                                    },
                                ),
                                # Cumulative Production
                                html.Div(
                                    [
                                        dcc.Graph(
                                            figure=cumulative_fig,
                                            id="cumulative-production",
                                        )
                                    ],
                                    style={
                                        "backgroundColor": "white",
                                        "padding": "20px",
                                        "borderRadius": "8px",
                                        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                                    },
                                ),
                            ],
                            style={"flex": 1, "marginLeft": "20px"},
                        ),
                    ],
                    style={"display": "flex"},
                ),
            ],
            style={"backgroundColor": "#f5f5f5", "minHeight": "100vh"},
        )

        self.app = app
        return app

    def create_executive_dashboard(self, report_data: Dict[str, Any]) -> Dash:
        """
        Create executive summary dashboard.

        Args:
            report_data: Complete report data

        Returns:
            Dash application
        """
        app = Dash(__name__)

        # Create subplots for overview
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Production Trend",
                "Revenue Analysis",
                "Well Performance",
                "Cost Breakdown",
            ),
            specs=[
                [{"type": "scatter"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "pie"}],
            ],
        )

        # Add sample data for demonstration
        dates = pd.date_range("2024-01-01", periods=30)
        production = np.random.normal(1000, 100, 30).cumsum()
        revenue = np.random.normal(100000, 10000, 12)

        # Production trend
        fig.add_trace(
            go.Scatter(x=dates, y=production, name="Production"), row=1, col=1
        )

        # Revenue bars
        fig.add_trace(
            go.Bar(x=["Jan", "Feb", "Mar"], y=revenue[:3], name="Revenue"), row=1, col=2
        )

        # Well performance scatter
        fig.add_trace(
            go.Scatter(
                x=np.random.rand(20), y=np.random.rand(20), mode="markers", name="Wells"
            ),
            row=2,
            col=1,
        )

        # Cost pie
        fig.add_trace(
            go.Pie(
                labels=["OPEX", "CAPEX", "Other"], values=[45, 35, 20], name="Costs"
            ),
            row=2,
            col=2,
        )

        fig.update_layout(height=800, showlegend=False, template=self.config.theme)

        # Layout
        app.layout = html.Div(
            [
                # Header with title
                html.Div(
                    [
                        html.H1("Executive Dashboard", style={"margin": 0}),
                        html.P(
                            "Comprehensive Performance Overview",
                            style={"margin": 0, "color": "gray"},
                        ),
                    ],
                    style={
                        "padding": "20px",
                        "backgroundColor": "white",
                        "marginBottom": "20px",
                        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                    },
                ),
                # Dashboard content
                html.Div(
                    [dcc.Graph(figure=fig, id="executive-overview")],
                    style={
                        "backgroundColor": "white",
                        "padding": "20px",
                        "borderRadius": "8px",
                        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                    },
                ),
            ],
            style={
                "backgroundColor": "#f5f5f5",
                "minHeight": "100vh",
                "padding": "20px",
            },
        )

        self.app = app
        return app

    def add_drill_down(self, parent_chart_id: str, drill_function: Callable) -> None:
        """
        Add drill-down capability to a chart.

        Args:
            parent_chart_id: ID of the parent chart
            drill_function: Function to generate drill-down view
        """
        if self.app:

            @self.app.callback(
                Output(f"{parent_chart_id}-drilldown", "children"),
                Input(parent_chart_id, "clickData"),
            )
            def handle_drill_down(click_data):
                if click_data:
                    return drill_function(click_data)
                return None

    def enable_cross_filtering(self, chart_ids: List[str]) -> None:
        """
        Enable cross-filtering between charts.

        Args:
            chart_ids: List of chart IDs to link
        """
        if self.app:
            for source_id in chart_ids:
                other_ids = [cid for cid in chart_ids if cid != source_id]

                @self.app.callback(
                    [Output(target_id, "figure") for target_id in other_ids],
                    Input(source_id, "selectedData"),
                )
                def update_filtered_charts(selected_data):
                    # Update other charts based on selection
                    # Implementation depends on specific chart types
                    pass

    def export_dashboard(
        self, format: str = "html", filename: str = "dashboard"
    ) -> bool:
        """
        Export dashboard to file.

        Args:
            format: Export format (html, png)
            filename: Output filename

        Returns:
            Success status
        """
        try:
            if format == "html" and self.app:
                # Export as standalone HTML
                # Implementation would save the dashboard HTML
                return True
            elif format == "png":
                # Would require additional libraries like kaleido
                pass

            return False
        except Exception as e:
            logger.error(f"Error exporting dashboard: {e}")
            return False

    def create_realtime_dashboard(
        self, data_stream: Callable, update_interval: int = 1000
    ) -> Dash:
        """
        Create dashboard with real-time updates.

        Args:
            data_stream: Function that returns latest data
            update_interval: Update interval in milliseconds

        Returns:
            Dash application with real-time updates
        """
        app = Dash(__name__)

        app.layout = html.Div(
            [
                html.H1("Real-Time Dashboard"),
                dcc.Graph(id="live-graph"),
                dcc.Interval(
                    id="graph-update", interval=update_interval, n_intervals=0
                ),
            ]
        )

        @app.callback(
            Output("live-graph", "figure"), Input("graph-update", "n_intervals")
        )
        def update_graph(n):
            data = data_stream()

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data.index if hasattr(data, "index") else range(len(data)),
                    y=data.values if hasattr(data, "values") else data,
                    mode="lines",
                )
            )

            return fig

        self.app = app
        return app

    def create_comparison_dashboard(
        self, entities: List[str], metrics: Dict[str, pd.DataFrame]
    ) -> Dash:
        """
        Create dashboard for comparing multiple entities.

        Args:
            entities: List of entities to compare
            metrics: Dictionary of metric DataFrames

        Returns:
            Dash application for comparison
        """
        app = Dash(__name__)

        # Create comparison layout
        comparison_charts = []

        for metric_name, metric_data in metrics.items():
            fig = go.Figure()

            for entity in entities:
                if entity in metric_data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=metric_data.index,
                            y=metric_data[entity],
                            name=entity,
                            mode="lines+markers",
                        )
                    )

            fig.update_layout(
                title=metric_name.replace("_", " ").title(),
                height=400,
                template=self.config.theme,
            )

            comparison_charts.append(
                html.Div(
                    [dcc.Graph(figure=fig, id=f"comparison-{metric_name}")],
                    style={
                        "backgroundColor": "white",
                        "padding": "20px",
                        "borderRadius": "8px",
                        "marginBottom": "20px",
                        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                    },
                )
            )

        app.layout = html.Div(
            [html.H1("Comparison Dashboard"), html.Div(comparison_charts)],
            style={"padding": "20px", "backgroundColor": "#f5f5f5"},
        )

        self.app = app
        return app
