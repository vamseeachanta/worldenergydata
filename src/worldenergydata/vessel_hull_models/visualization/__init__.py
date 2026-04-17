# ABOUTME: Visualization layer for vessel hull models
# ABOUTME: Plotly 3D rendering, PNG export, and HTML report generation

"""
Visualization Layer for Vessel Hull Models Module

Provides interactive 3D visualization using Plotly mesh3d and
static PNG export using matplotlib.
"""

from worldenergydata.vessel_hull_models.visualization.plotly_3d import (
    create_hull_figure,
    export_hull_html,
    render_vessel_hull,
)
from worldenergydata.vessel_hull_models.visualization.png_exporter import (
    create_comparison_grid,
    export_hull_png,
    generate_preview_gallery,
    render_obj_to_png,
)

__all__ = [
    # Plotly exports
    "render_vessel_hull",
    "create_hull_figure",
    "export_hull_html",
    # PNG exports
    "export_hull_png",
    "render_obj_to_png",
    "generate_preview_gallery",
    "create_comparison_grid",
]
