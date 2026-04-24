"""
Plotly Dash web application — BSEE production and FDAS incident dashboard.

Layout:
  Tab 1 (Production)  — oil / gas / water trend charts, selectable by field /
                         lease / operator
  Tab 2 (Platforms)   — interactive GOM scatter-mapbox coloured by status
  Tab 3 (Incidents)   — FDAS severity heatmap (type vs year), filterable

Usage (programmatic):
    from worldenergydata.dashboard.app import app, run_server

    run_server(port=8050, debug=True)

CLI (via worldenergydata dashboard):
    worldenergydata dashboard [--port 8050] [--debug]
"""

from __future__ import annotations

import logging
from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, callback, dcc, html

from worldenergydata.dashboard.data_loader import (
    load_incident_data,
    load_platform_data,
    load_production_data,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = Dash(
    __name__,
    title="WorldEnergyData Dashboard",
    suppress_callback_exceptions=True,
)

# ---------------------------------------------------------------------------
# Pre-load data at module level so callbacks share one copy
# ---------------------------------------------------------------------------

_production_df: pd.DataFrame = load_production_data()
_platform_df: pd.DataFrame = load_platform_data()
_incident_df: pd.DataFrame = load_incident_data()


# ---------------------------------------------------------------------------
# Helper: build option lists for dropdowns
# ---------------------------------------------------------------------------


def _field_options(df: pd.DataFrame) -> List[dict]:
    """Return sorted dropdown options from FIELD_NAME column."""
    fields = sorted(df["FIELD_NAME"].dropna().unique().tolist())
    return [{"label": "All Fields", "value": "ALL"}] + [
        {"label": f, "value": f} for f in fields
    ]


def _area_options(df: pd.DataFrame) -> List[dict]:
    """Return sorted dropdown options from AREA_NAME column."""
    areas = sorted(df["AREA_NAME"].dropna().unique().tolist())
    return [{"label": "All Areas", "value": "ALL"}] + [
        {"label": a, "value": a} for a in areas
    ]


def _operator_options(df: pd.DataFrame) -> List[dict]:
    """Return sorted dropdown options from OPERATOR column."""
    col = "OPERATOR" if "OPERATOR" in df.columns else None
    if col is None:
        return [{"label": "All Operators", "value": "ALL"}]
    ops = sorted(df[col].dropna().unique().tolist())
    return [{"label": "All Operators", "value": "ALL"}] + [
        {"label": o, "value": o} for o in ops
    ]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app.layout = html.Div(
    [
        # Header
        html.Div(
            [
                html.H1(
                    "WorldEnergyData — GOM Dashboard",
                    style={"color": "#ecf0f1", "marginBottom": "4px"},
                ),
                html.P(
                    "BSEE production data • Platform locations • FDAS incidents",
                    style={"color": "#95a5a6", "marginTop": "0"},
                ),
            ],
            style={
                "backgroundColor": "#2c3e50",
                "padding": "20px 30px",
                "marginBottom": "0",
            },
        ),
        # Tabs
        dcc.Tabs(
            id="main-tabs",
            value="tab-production",
            style={"backgroundColor": "#34495e"},
            colors={
                "border": "#2c3e50",
                "primary": "#3498db",
                "background": "#2c3e50",
            },
            children=[
                # ---- Tab 1: Production ----
                dcc.Tab(
                    label="Production Trends",
                    value="tab-production",
                    style={"color": "#ecf0f1"},
                    selected_style={"color": "#ecf0f1", "backgroundColor": "#3498db"},
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Label(
                                            "Field / Area",
                                            style={"color": "#bdc3c7"},
                                        ),
                                        dcc.Dropdown(
                                            id="prod-field-dropdown",
                                            options=_field_options(_production_df),
                                            value="ALL",
                                            clearable=False,
                                            style={"width": "300px"},
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "12px",
                                        "marginBottom": "16px",
                                    },
                                ),
                                dcc.Graph(id="prod-oil-chart"),
                                dcc.Graph(id="prod-gas-water-chart"),
                            ],
                            style={"padding": "20px 30px"},
                        ),
                    ],
                ),
                # ---- Tab 2: Platforms ----
                dcc.Tab(
                    label="Platform Map",
                    value="tab-platforms",
                    style={"color": "#ecf0f1"},
                    selected_style={"color": "#ecf0f1", "backgroundColor": "#3498db"},
                    children=[
                        html.Div(
                            [
                                html.Label(
                                    "Colour by",
                                    style={"color": "#bdc3c7"},
                                ),
                                dcc.RadioItems(
                                    id="map-colour-by",
                                    options=[
                                        {
                                            "label": "Well Status",
                                            "value": "WELL_STATUS",
                                        },
                                        {
                                            "label": "Water Depth",
                                            "value": "WATER_DEPTH",
                                        },
                                    ],
                                    value="WELL_STATUS",
                                    inline=True,
                                    style={"color": "#ecf0f1", "margin": "8px 0"},
                                ),
                                dcc.Graph(
                                    id="platform-map",
                                    style={"height": "600px"},
                                ),
                            ],
                            style={"padding": "20px 30px"},
                        ),
                    ],
                ),
                # ---- Tab 3: Incidents ----
                dcc.Tab(
                    label="Incident Heatmap",
                    value="tab-incidents",
                    style={"color": "#ecf0f1"},
                    selected_style={"color": "#ecf0f1", "backgroundColor": "#3498db"},
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Label(
                                            "Area",
                                            style={
                                                "color": "#bdc3c7",
                                                "marginRight": "8px",
                                            },
                                        ),
                                        dcc.Dropdown(
                                            id="incident-area-dropdown",
                                            options=_area_options(_incident_df),
                                            value="ALL",
                                            clearable=False,
                                            style={"width": "260px"},
                                        ),
                                        html.Label(
                                            "Operator",
                                            style={
                                                "color": "#bdc3c7",
                                                "marginLeft": "20px",
                                                "marginRight": "8px",
                                            },
                                        ),
                                        dcc.Dropdown(
                                            id="incident-operator-dropdown",
                                            options=_operator_options(_incident_df),
                                            value="ALL",
                                            clearable=False,
                                            style={"width": "260px"},
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "16px",
                                    },
                                ),
                                dcc.Graph(id="incident-heatmap"),
                            ],
                            style={"padding": "20px 30px"},
                        ),
                    ],
                ),
            ],
        ),
    ],
    style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#1a252f"},
)


# ---------------------------------------------------------------------------
# Callbacks — Production tab
# ---------------------------------------------------------------------------


@callback(
    Output("prod-oil-chart", "figure"),
    Output("prod-gas-water-chart", "figure"),
    Input("prod-field-dropdown", "value"),
)
def update_production_charts(selected_field: str):
    """Redraw oil trend and gas/water trend based on field selection."""
    df = _production_df.copy()
    if selected_field and selected_field != "ALL":
        df = df[df["FIELD_NAME"] == selected_field]

    df["PRODUCTION_DATE"] = pd.to_datetime(df["PRODUCTION_DATE"], errors="coerce")
    monthly = (
        df.groupby("PRODUCTION_DATE")[["OIL_BBL", "GAS_MCF", "WATER_BBL"]]
        .sum()
        .reset_index()
        .sort_values("PRODUCTION_DATE")
    )

    oil_fig = px.line(
        monthly,
        x="PRODUCTION_DATE",
        y="OIL_BBL",
        title="Monthly Oil Production (BBL)",
        labels={"PRODUCTION_DATE": "Date", "OIL_BBL": "Oil (BBL)"},
        template="plotly_dark",
    )
    oil_fig.update_traces(line_color="#e74c3c")

    gas_water_fig = px.line(
        monthly,
        x="PRODUCTION_DATE",
        y=["GAS_MCF", "WATER_BBL"],
        title="Monthly Gas & Water Production",
        labels={"PRODUCTION_DATE": "Date", "value": "Volume"},
        template="plotly_dark",
    )

    return oil_fig, gas_water_fig


# ---------------------------------------------------------------------------
# Callbacks — Platform map tab
# ---------------------------------------------------------------------------


@callback(
    Output("platform-map", "figure"),
    Input("map-colour-by", "value"),
)
def update_platform_map(colour_by: str):
    """Redraw the GOM scatter-mapbox with the selected colour encoding."""
    df = _platform_df.copy().dropna(subset=["LATITUDE", "LONGITUDE"])

    hover = ["WELL_NAME", "OPERATOR_NAME", "FIELD_NAME", "WELL_STATUS", "WATER_DEPTH"]
    hover_cols = [c for c in hover if c in df.columns]

    fig = px.scatter_mapbox(
        df,
        lat="LATITUDE",
        lon="LONGITUDE",
        color=colour_by,
        hover_data=hover_cols,
        title="Gulf of Mexico Platform Locations",
        mapbox_style="open-street-map",
        zoom=4,
        center={"lat": 27.5, "lon": -90.0},
        height=580,
        template="plotly_dark",
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    return fig


# ---------------------------------------------------------------------------
# Callbacks — Incident heatmap tab
# ---------------------------------------------------------------------------


@callback(
    Output("incident-heatmap", "figure"),
    Input("incident-area-dropdown", "value"),
    Input("incident-operator-dropdown", "value"),
)
def update_incident_heatmap(selected_area: str, selected_operator: str):
    """Rebuild the incident type × year heatmap with the chosen filters."""
    df = _incident_df.copy()

    if selected_area and selected_area != "ALL":
        df = df[df["AREA_NAME"] == selected_area]
    if selected_operator and selected_operator != "ALL":
        op_col = "OPERATOR" if "OPERATOR" in df.columns else None
        if op_col:
            df = df[df[op_col] == selected_operator]

    if df.empty:
        return go.Figure().update_layout(
            title="No incidents match the selected filters",
            template="plotly_dark",
        )

    pivot = (
        df.groupby(["INCIDENT_TYPE", "INCIDENT_YEAR"])
        .size()
        .reset_index(name="COUNT")
        .pivot(index="INCIDENT_TYPE", columns="INCIDENT_YEAR", values="COUNT")
        .fillna(0)
    )

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=pivot.index.tolist(),
            colorscale="YlOrRd",
            hoverongaps=False,
            colorbar={"title": "Incidents"},
        )
    )
    fig.update_layout(
        title="Incident Type vs Year",
        xaxis_title="Year",
        yaxis_title="Incident Type",
        template="plotly_dark",
        margin={"t": 50, "b": 50, "l": 160, "r": 20},
    )
    return fig


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------


def run_server(
    host: str = "127.0.0.1",
    port: int = 8050,
    debug: bool = False,
) -> None:
    """
    Start the Dash development server.

    Args:
        host:  Bind address. Defaults to localhost only.
        port:  TCP port. Defaults to 8050.
        debug: Enable Dash debug / hot-reload mode.
    """
    logger.info("Starting dashboard on http://%s:%d/", host, port)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=True)
