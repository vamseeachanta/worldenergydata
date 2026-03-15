"""
Geographic visualizations for comprehensive reports.

Provides maps with well locations, field boundaries, and production density.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


@dataclass
class WellLocation:
    """Well location data."""

    well_name: str
    latitude: float
    longitude: float
    field: str
    status: str
    production: Optional[float] = None
    depth: Optional[float] = None


@dataclass
class FieldBoundary:
    """Field boundary data."""

    field_name: str
    coordinates: List[Tuple[float, float]]
    area: float
    block_number: str


class GeographicChart:
    """
    Creates geographic visualizations for comprehensive reports.

    Supports well location maps, field boundaries, production heat maps.
    """

    def __init__(self, mapbox_token: Optional[str] = None):
        """
        Initialize geographic chart generator.

        Args:
            mapbox_token: Optional Mapbox access token for satellite imagery
        """
        self.mapbox_token = mapbox_token
        if mapbox_token:
            px.set_mapbox_access_token(mapbox_token)

    def create_well_location_map(
        self,
        wells: List[WellLocation],
        boundaries: Optional[List[FieldBoundary]] = None,
        title: str = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
    ) -> go.Figure:
        """
        Create map showing well locations.

        Args:
            wells: List of well locations
            boundaries: Optional field boundaries
            title: Map title
            center_lat: Center latitude
            center_lon: Center longitude

        Returns:
            Plotly figure with well location map
        """
        # Calculate center if not provided
        if center_lat is None:
            center_lat = np.mean([w.latitude for w in wells])
        if center_lon is None:
            center_lon = np.mean([w.longitude for w in wells])

        fig = go.Figure()

        # Add field boundaries if provided
        if boundaries:
            for boundary in boundaries:
                lats, lons = zip(*boundary.coordinates)

                fig.add_trace(
                    go.Scattermapbox(
                        mode="lines",
                        lon=list(lons) + [lons[0]],  # Close the polygon
                        lat=list(lats) + [lats[0]],
                        name=boundary.field_name,
                        line=dict(width=2, color="blue"),
                        hovertemplate=f"<b>{boundary.field_name}</b><br>"
                        + f"Block: {boundary.block_number}<br>"
                        + f"Area: {boundary.area:.2f} km²<br>"
                        + "<extra></extra>",
                    )
                )

        # Group wells by status for different colors
        status_colors = {
            "Active": "green",
            "Producing": "green",
            "Idle": "orange",
            "Suspended": "yellow",
            "Abandoned": "red",
            "Planned": "blue",
        }

        for status in set(w.status for w in wells):
            status_wells = [w for w in wells if w.status == status]

            # Prepare hover text
            hover_texts = []
            for well in status_wells:
                hover_text = (
                    f"<b>{well.well_name}</b><br>"
                    + f"Field: {well.field}<br>"
                    + f"Status: {well.status}<br>"
                    + f"Lat: {well.latitude:.4f}<br>"
                    + f"Lon: {well.longitude:.4f}"
                )

                if well.production:
                    hover_text += f"<br>Production: {well.production:.0f} BBL/day"
                if well.depth:
                    hover_text += f"<br>Depth: {well.depth:.0f} ft"

                hover_texts.append(hover_text)

            # Add well markers
            fig.add_trace(
                go.Scattermapbox(
                    mode="markers",
                    lon=[w.longitude for w in status_wells],
                    lat=[w.latitude for w in status_wells],
                    marker=dict(size=10, color=status_colors.get(status, "gray")),
                    name=f"{status} Wells ({len(status_wells)})",
                    text=[w.well_name for w in status_wells],
                    hovertemplate="%{hovertext}<extra></extra>",
                    hovertext=hover_texts,
                )
            )

        # Update layout
        fig.update_layout(
            mapbox=dict(
                style="open-street-map" if not self.mapbox_token else "satellite",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=9,
            ),
            title=title or "Well Locations Map",
            height=700,
            width=1200,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.8)",
            ),
        )

        return fig

    def create_production_density_map(
        self,
        data: pd.DataFrame,
        lat_col: str = "latitude",
        lon_col: str = "longitude",
        value_col: str = "production",
        title: str = None,
    ) -> go.Figure:
        """
        Create production density heat map.

        Args:
            data: DataFrame with location and production data
            lat_col: Column name for latitude
            lon_col: Column name for longitude
            value_col: Column name for values to map
            title: Map title

        Returns:
            Plotly figure with density map
        """
        fig = go.Figure()

        # Create density map
        fig.add_trace(
            go.Densitymapbox(
                lat=data[lat_col],
                lon=data[lon_col],
                z=data[value_col],
                radius=20,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title=value_col.capitalize(), titleside="right"),
                hovertemplate="Lat: %{lat:.4f}<br>"
                + "Lon: %{lon:.4f}<br>"
                + f"{value_col}: %{{z:.0f}}<br>"
                + "<extra></extra>",
            )
        )

        # Add well markers
        fig.add_trace(
            go.Scattermapbox(
                mode="markers",
                lon=data[lon_col],
                lat=data[lat_col],
                marker=dict(size=5, color="white", opacity=0.3),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Calculate center
        center_lat = data[lat_col].mean()
        center_lon = data[lon_col].mean()

        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=9,
            ),
            title=title or f"{value_col.capitalize()} Density Map",
            height=700,
            width=1200,
        )

        return fig

    def create_field_comparison_map(
        self,
        fields: Dict[str, List[WellLocation]],
        boundaries: Optional[Dict[str, FieldBoundary]] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create map comparing multiple fields.

        Args:
            fields: Dictionary of field names to well locations
            boundaries: Optional dictionary of field boundaries
            title: Map title

        Returns:
            Plotly figure with field comparison
        """
        fig = go.Figure()

        # Color palette for fields
        colors = px.colors.qualitative.Plotly

        all_lats = []
        all_lons = []

        # Add boundaries if provided
        if boundaries:
            for i, (field_name, boundary) in enumerate(boundaries.items()):
                lats, lons = zip(*boundary.coordinates)
                all_lats.extend(lats)
                all_lons.extend(lons)

                fig.add_trace(
                    go.Scattermapbox(
                        mode="lines",
                        lon=list(lons) + [lons[0]],
                        lat=list(lats) + [lats[0]],
                        name=f"{field_name} Boundary",
                        line=dict(width=2, color=colors[i % len(colors)]),
                        fill="toself",
                        fillcolor=colors[i % len(colors)],
                        opacity=0.1,
                        showlegend=False,
                    )
                )

        # Add wells by field
        for i, (field_name, wells) in enumerate(fields.items()):
            color = colors[i % len(colors)]

            lats = [w.latitude for w in wells]
            lons = [w.longitude for w in wells]
            all_lats.extend(lats)
            all_lons.extend(lons)

            # Calculate field statistics
            active_count = sum(1 for w in wells if w.status in ["Active", "Producing"])
            total_production = sum(w.production for w in wells if w.production)

            fig.add_trace(
                go.Scattermapbox(
                    mode="markers",
                    lon=lons,
                    lat=lats,
                    marker=dict(size=12, color=color),
                    name=f"{field_name} ({len(wells)} wells)",
                    text=[w.well_name for w in wells],
                    hovertemplate=f"<b>{field_name}</b><br>"
                    + "Well: %{text}<br>"
                    + "Lat: %{lat:.4f}<br>"
                    + "Lon: %{lon:.4f}<br>"
                    + f"Active Wells: {active_count}<br>"
                    + f"Total Production: {total_production:.0f} BBL/day<br>"
                    + "<extra></extra>",
                )
            )

        # Calculate center
        center_lat = np.mean(all_lats)
        center_lon = np.mean(all_lons)

        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=8,
            ),
            title=title or "Field Comparison Map",
            height=700,
            width=1200,
            showlegend=True,
        )

        return fig

    def create_3d_subsurface_view(
        self, wells: List[Dict[str, Any]], title: str = None
    ) -> go.Figure:
        """
        Create 3D subsurface visualization of wells.

        Args:
            wells: List of well dictionaries with x, y, z coordinates
            title: Chart title

        Returns:
            Plotly figure with 3D view
        """
        fig = go.Figure()

        # Extract coordinates
        x_coords = [w["x"] for w in wells]
        y_coords = [w["y"] for w in wells]
        z_coords = [-w.get("depth", 0) for w in wells]  # Negative for depth

        # Add well trajectories
        for well in wells:
            if "trajectory" in well:
                traj = well["trajectory"]
                fig.add_trace(
                    go.Scatter3d(
                        x=traj["x"],
                        y=traj["y"],
                        z=[-z for z in traj["z"]],
                        mode="lines",
                        name=well["name"],
                        line=dict(width=4),
                        hovertemplate="<b>%{text}</b><br>"
                        + "X: %{x:.0f}<br>"
                        + "Y: %{y:.0f}<br>"
                        + "Depth: %{z:.0f} ft<br>"
                        + "<extra></extra>",
                        text=well["name"],
                    )
                )

        # Add well bottom markers
        fig.add_trace(
            go.Scatter3d(
                x=x_coords,
                y=y_coords,
                z=z_coords,
                mode="markers",
                marker=dict(
                    size=8,
                    color=z_coords,
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Depth (ft)"),
                ),
                text=[w["name"] for w in wells],
                hovertemplate="<b>%{text}</b><br>"
                + "X: %{x:.0f}<br>"
                + "Y: %{y:.0f}<br>"
                + "Depth: %{z:.0f} ft<br>"
                + "<extra></extra>",
            )
        )

        # Add surface plane
        x_range = [min(x_coords), max(x_coords)]
        y_range = [min(y_coords), max(y_coords)]
        xx, yy = np.meshgrid(x_range, y_range)
        zz = np.zeros_like(xx)

        fig.add_trace(
            go.Surface(
                x=xx,
                y=yy,
                z=zz,
                showscale=False,
                opacity=0.3,
                colorscale="gray",
                name="Surface",
            )
        )

        fig.update_layout(
            title=title or "3D Subsurface View",
            scene=dict(
                xaxis_title="X (ft)",
                yaxis_title="Y (ft)",
                zaxis_title="Depth (ft)",
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
                aspectmode="manual",
                aspectratio=dict(x=1, y=1, z=0.5),
            ),
            height=700,
            width=1000,
        )

        return fig

    def create_trajectory_comparison(
        self, wells: List[Dict[str, Any]], title: str = None
    ) -> go.Figure:
        """
        Create well trajectory comparison in 2D views.

        Args:
            wells: List of well dictionaries with trajectory data
            title: Chart title

        Returns:
            Plotly figure with trajectory comparison
        """
        from plotly.subplots import make_subplots

        # Create subplots
        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Vertical Section", "Plan View"),
            specs=[[{"type": "scatter"}, {"type": "scatter"}]],
        )

        colors = px.colors.qualitative.Plotly

        for i, well in enumerate(wells):
            if "trajectory" in well:
                traj = well["trajectory"]
                color = colors[i % len(colors)]

                # Vertical section (MD vs TVD)
                fig.add_trace(
                    go.Scatter(
                        x=traj.get("departure", traj.get("x", [])),
                        y=[-z for z in traj.get("tvd", traj.get("z", []))],
                        name=well["name"],
                        mode="lines",
                        line=dict(color=color, width=2),
                        hovertemplate="<b>%{text}</b><br>"
                        + "Departure: %{x:.0f} ft<br>"
                        + "TVD: %{y:.0f} ft<br>"
                        + "<extra></extra>",
                        text=well["name"],
                        showlegend=True,
                    ),
                    row=1,
                    col=1,
                )

                # Plan view (X vs Y)
                fig.add_trace(
                    go.Scatter(
                        x=traj.get("x", []),
                        y=traj.get("y", []),
                        name=well["name"],
                        mode="lines",
                        line=dict(color=color, width=2),
                        hovertemplate="<b>%{text}</b><br>"
                        + "X: %{x:.0f} ft<br>"
                        + "Y: %{y:.0f} ft<br>"
                        + "<extra></extra>",
                        text=well["name"],
                        showlegend=False,
                    ),
                    row=1,
                    col=2,
                )

        fig.update_xaxes(title_text="Departure (ft)", row=1, col=1)
        fig.update_yaxes(title_text="TVD (ft)", row=1, col=1)
        fig.update_xaxes(title_text="X (ft)", row=1, col=2)
        fig.update_yaxes(title_text="Y (ft)", row=1, col=2)

        fig.update_layout(
            title=title or "Well Trajectory Comparison",
            height=600,
            width=1200,
            showlegend=True,
        )

        return fig

    def create_field_infrastructure_map(
        self, infrastructure: Dict[str, Any], title: str = None
    ) -> go.Figure:
        """
        Create map showing field infrastructure.

        Args:
            infrastructure: Dictionary with platforms, pipelines, etc.
            title: Map title

        Returns:
            Plotly figure with infrastructure map
        """
        fig = go.Figure()

        # Add platforms
        if "platforms" in infrastructure:
            platforms = infrastructure["platforms"]
            fig.add_trace(
                go.Scattermapbox(
                    mode="markers+text",
                    lon=[p["longitude"] for p in platforms],
                    lat=[p["latitude"] for p in platforms],
                    marker=dict(size=15, color="red", symbol="square"),
                    text=[p["name"] for p in platforms],
                    textposition="top right",
                    name="Platforms",
                    hovertemplate="<b>%{text}</b><br>"
                    + "Type: Platform<br>"
                    + "Lat: %{lat:.4f}<br>"
                    + "Lon: %{lon:.4f}<br>"
                    + "<extra></extra>",
                )
            )

        # Add pipelines
        if "pipelines" in infrastructure:
            for pipeline in infrastructure["pipelines"]:
                fig.add_trace(
                    go.Scattermapbox(
                        mode="lines",
                        lon=pipeline["coordinates"]["lon"],
                        lat=pipeline["coordinates"]["lat"],
                        name=pipeline["name"],
                        line=dict(width=3, color="blue"),
                        hovertemplate=f'<b>{pipeline["name"]}</b><br>'
                        + f"Type: Pipeline<br>"
                        + f'Diameter: {pipeline.get("diameter", "N/A")}<br>'
                        + "<extra></extra>",
                    )
                )

        # Add wells
        if "wells" in infrastructure:
            wells = infrastructure["wells"]
            fig.add_trace(
                go.Scattermapbox(
                    mode="markers",
                    lon=[w["longitude"] for w in wells],
                    lat=[w["latitude"] for w in wells],
                    marker=dict(size=8, color="green"),
                    name=f"Wells ({len(wells)})",
                    text=[w["name"] for w in wells],
                    hovertemplate="<b>%{text}</b><br>"
                    + "Type: Well<br>"
                    + "Lat: %{lat:.4f}<br>"
                    + "Lon: %{lon:.4f}<br>"
                    + "<extra></extra>",
                )
            )

        # Calculate center
        all_lats = []
        all_lons = []

        if "platforms" in infrastructure:
            all_lats.extend([p["latitude"] for p in infrastructure["platforms"]])
            all_lons.extend([p["longitude"] for p in infrastructure["platforms"]])
        if "wells" in infrastructure:
            all_lats.extend([w["latitude"] for w in infrastructure["wells"]])
            all_lons.extend([w["longitude"] for w in infrastructure["wells"]])

        center_lat = np.mean(all_lats) if all_lats else 0
        center_lon = np.mean(all_lons) if all_lons else 0

        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=10,
            ),
            title=title or "Field Infrastructure Map",
            height=700,
            width=1200,
            showlegend=True,
        )

        return fig
