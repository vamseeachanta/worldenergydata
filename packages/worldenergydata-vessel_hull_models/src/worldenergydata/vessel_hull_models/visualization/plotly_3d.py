# ABOUTME: Plotly 3D visualization for vessel hull models
# ABOUTME: Creates interactive mesh3d figures from OBJ geometry

"""
Plotly 3D Visualization for Vessel Hull Models

Creates interactive 3D visualizations of vessel hulls using Plotly mesh3d.
"""

from pathlib import Path
from typing import Dict, Optional

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from worldenergydata.vessel_hull_models.exceptions import VisualizationError
from worldenergydata.vessel_hull_models.geometry.obj_parser import (
    OBJMesh,
    parse_obj_file,
)


def _check_plotly():
    """Check if Plotly is available"""
    if not PLOTLY_AVAILABLE:
        raise VisualizationError(
            "Plotly is required for visualization. Install with: pip install plotly"
        )


def create_hull_figure(
    mesh: OBJMesh,
    title: str = "Vessel Hull",
    color_by: str = "depth",
    colorscale: str = "Viridis",
    show_waterline: bool = True,
    waterline_z: float = 0.0,
    background_color: str = "rgb(230, 240, 250)",
    width: int = 1000,
    height: int = 700,
) -> "go.Figure":
    """
    Create a Plotly figure from OBJ mesh data.

    Args:
        mesh: OBJMesh object with parsed geometry
        title: Figure title
        color_by: Coloring mode ("depth", "uniform", "x", "y")
        colorscale: Plotly colorscale name
        show_waterline: Show waterline plane
        waterline_z: Z-coordinate of waterline (default 0)
        background_color: Plot background color
        width: Figure width in pixels
        height: Figure height in pixels

    Returns:
        Plotly Figure object
    """
    _check_plotly()

    vertices = mesh.vertices
    faces = mesh.faces

    # Extract coordinate arrays
    x = vertices[:, 0]
    y = vertices[:, 1]
    z = vertices[:, 2]

    # Extract face indices for mesh3d
    i = faces[:, 0]
    j = faces[:, 1]
    k = faces[:, 2]

    # Determine intensity values for coloring
    if color_by == "depth":
        # Color by Z coordinate (depth)
        intensity = z
        colorbar_title = "Depth (m)"
    elif color_by == "x":
        intensity = x
        colorbar_title = "X (m)"
    elif color_by == "y":
        intensity = y
        colorbar_title = "Y (m)"
    else:
        # Uniform color
        intensity = None
        colorbar_title = None

    # Create mesh3d trace
    mesh_trace = go.Mesh3d(
        x=x,
        y=y,
        z=z,
        i=i,
        j=j,
        k=k,
        intensity=intensity,
        colorscale=colorscale if intensity is not None else None,
        color="steelblue" if intensity is None else None,
        opacity=0.9,
        flatshading=True,
        lighting=dict(
            ambient=0.4,
            diffuse=0.6,
            specular=0.2,
            roughness=0.5,
        ),
        lightposition=dict(x=100, y=100, z=200),
        colorbar=dict(title=colorbar_title) if colorbar_title else None,
        name="Hull",
        hovertemplate=(
            "X: %{x:.2f}m<br>"
            "Y: %{y:.2f}m<br>"
            "Z: %{z:.2f}m<br>"
            "<extra>Hull</extra>"
        ),
    )

    traces = [mesh_trace]

    # Add waterline plane
    if show_waterline:
        dims = mesh.dimensions
        center = mesh.center

        # Create waterline plane slightly larger than hull
        pad = 5.0  # meters padding
        wl_x = [
            center[0] - dims["length"] / 2 - pad,
            center[0] + dims["length"] / 2 + pad,
            center[0] + dims["length"] / 2 + pad,
            center[0] - dims["length"] / 2 - pad,
        ]
        wl_y = [
            center[1] - dims["width"] / 2 - pad,
            center[1] - dims["width"] / 2 - pad,
            center[1] + dims["width"] / 2 + pad,
            center[1] + dims["width"] / 2 + pad,
        ]
        wl_z = [waterline_z] * 4

        waterline = go.Mesh3d(
            x=wl_x,
            y=wl_y,
            z=wl_z,
            i=[0, 0],
            j=[1, 2],
            k=[2, 3],
            color="rgba(100, 150, 255, 0.3)",
            name="Waterline",
            hoverinfo="skip",
        )
        traces.append(waterline)

    # Create figure
    fig = go.Figure(data=traces)

    # Calculate camera position
    dims = mesh.dimensions
    max_dim = max(dims["length"], dims["width"], dims["height"])
    camera_distance = max_dim * 1.5

    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            font=dict(size=18),
        ),
        scene=dict(
            xaxis=dict(title="X (m)", showgrid=True, gridcolor="lightgray"),
            yaxis=dict(title="Y (m)", showgrid=True, gridcolor="lightgray"),
            zaxis=dict(title="Z (m)", showgrid=True, gridcolor="lightgray"),
            aspectmode="data",  # Preserve aspect ratio
            camera=dict(
                eye=dict(
                    x=camera_distance / max_dim * 1.2,
                    y=-camera_distance / max_dim * 1.2,
                    z=camera_distance / max_dim * 0.8,
                ),
            ),
            bgcolor=background_color,
        ),
        width=width,
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=True,
        legend=dict(x=0.02, y=0.98),
    )

    # Add dimension annotations
    stats = mesh.get_stats()
    annotation_text = (
        f"<b>Dimensions:</b><br>"
        f"Length: {stats['length']:.1f}m<br>"
        f"Beam: {stats['width']:.1f}m<br>"
        f"Depth: {stats['height']:.1f}m<br>"
        f"<b>Mesh:</b><br>"
        f"Vertices: {stats['vertex_count']:,}<br>"
        f"Faces: {stats['face_count']:,}"
    )

    fig.add_annotation(
        text=annotation_text,
        xref="paper",
        yref="paper",
        x=0.02,
        y=0.02,
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="lightgray",
        borderwidth=1,
    )

    return fig


def render_vessel_hull(
    obj_path: Path,
    title: Optional[str] = None,
    **kwargs,
) -> "go.Figure":
    """
    Render a vessel hull from an OBJ file.

    Args:
        obj_path: Path to OBJ file
        title: Figure title (defaults to filename)
        **kwargs: Additional arguments passed to create_hull_figure

    Returns:
        Plotly Figure object
    """
    _check_plotly()

    obj_path = Path(obj_path)
    mesh = parse_obj_file(obj_path)

    if title is None:
        title = f"Vessel Hull: {obj_path.stem}"

    return create_hull_figure(mesh, title=title, **kwargs)


def export_hull_html(
    obj_path: Path,
    output_path: Path,
    title: Optional[str] = None,
    include_plotlyjs: bool = True,
    **kwargs,
) -> Path:
    """
    Export vessel hull visualization to standalone HTML file.

    Args:
        obj_path: Path to OBJ file
        output_path: Output HTML file path
        title: Figure title
        include_plotlyjs: Include Plotly.js in HTML (larger file, works offline)
        **kwargs: Additional arguments passed to create_hull_figure

    Returns:
        Path to created HTML file
    """
    _check_plotly()

    fig = render_vessel_hull(obj_path, title=title, **kwargs)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig.write_html(
        str(output_path),
        include_plotlyjs=include_plotlyjs,
        full_html=True,
    )

    return output_path


def create_fleet_comparison(
    hulls: Dict[str, Path],
    title: str = "Fleet Comparison",
    width: int = 1200,
    height: int = 800,
) -> "go.Figure":
    """
    Create a comparison figure showing multiple vessel hulls.

    Args:
        hulls: Dict of vessel name -> OBJ path
        title: Figure title
        width: Figure width
        height: Figure height

    Returns:
        Plotly Figure with subplots for each vessel
    """
    _check_plotly()

    n_vessels = len(hulls)
    if n_vessels == 0:
        raise VisualizationError("No hulls provided for comparison")

    # Calculate subplot grid
    cols = min(n_vessels, 3)
    rows = (n_vessels + cols - 1) // cols

    # Create subplot titles
    specs = [[{"type": "scene"} for _ in range(cols)] for _ in range(rows)]

    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=list(hulls.keys()),
        specs=specs,
        horizontal_spacing=0.05,
        vertical_spacing=0.1,
    )

    for idx, (name, obj_path) in enumerate(hulls.items()):
        row = idx // cols + 1
        col = idx % cols + 1

        try:
            mesh = parse_obj_file(obj_path)

            x = mesh.vertices[:, 0]
            y = mesh.vertices[:, 1]
            z = mesh.vertices[:, 2]
            i = mesh.faces[:, 0]
            j = mesh.faces[:, 1]
            k = mesh.faces[:, 2]

            fig.add_trace(
                go.Mesh3d(
                    x=x,
                    y=y,
                    z=z,
                    i=i,
                    j=j,
                    k=k,
                    intensity=z,
                    colorscale="Viridis",
                    showscale=False,
                    name=name,
                ),
                row=row,
                col=col,
            )
        except Exception as e:
            # Add placeholder for failed loads
            fig.add_annotation(
                text=f"Failed to load: {e}",
                xref="paper",
                yref="paper",
                x=(col - 0.5) / cols,
                y=1 - (row - 0.5) / rows,
                showarrow=False,
            )

    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=18)),
        width=width,
        height=height,
        showlegend=False,
    )

    return fig
