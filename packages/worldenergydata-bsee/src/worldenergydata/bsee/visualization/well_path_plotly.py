"""Interactive Plotly 3D well-path renderer for the BSEE module.

Consumes the frozen renderer-agnostic payload produced by
``well_path_export.build_well_paths_payload`` / ``demo_payload`` (see
``well_path_export`` for the schema) and writes a standalone, self-contained
HTML page with one interactive 3D trajectory per well.

Unlike the legacy ``field_visualization.generate_3d_view`` (which only draws a
straight surface->TD line), this renderer draws the **full** minimum-curvature
polyline from each well's ``points`` list, so deviated and horizontal wells are
shown faithfully.

Coordinate convention (from the payload)
---------------------------------------
* ``x`` = Easting (ft, field-relative)
* ``y`` = Northing (ft, field-relative)
* ``z`` = True Vertical Depth, **positive downward**

Plotly's z-axis is reversed (``autorange="reversed"``) so depth increases
visually downward while the payload numbers stay faithful to the survey.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# HTML helpers (mirror field_visualization conventions, self-contained).
# ---------------------------------------------------------------------------
def _placeholder_html(title: str, message: str) -> str:
    """Return a placeholder HTML page with a centered message."""
    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{title}</title>"
        "</head><body>"
        f'<h1 style="text-align:center;font-family:sans-serif">{title}</h1>'
        f'<p style="text-align:center;font-family:sans-serif;color:#888">'
        f"{message}</p>"
        "</body></html>"
    )


def _write(path: str, content: str) -> str:
    """Write content to path, creating parent dirs as needed. Returns path."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Trace / hover construction
# ---------------------------------------------------------------------------
def _hover_text(point: dict[str, float]) -> str:
    """Per-vertex hover string showing MD, Inc, Az, TVD and DLS."""
    return (
        f"MD: {point.get('md', 0.0):,.1f} ft<br>"
        f"Inc: {point.get('inc', 0.0):.2f}&#176;<br>"
        f"Az: {point.get('az', 0.0):.2f}&#176;<br>"
        f"TVD: {point.get('z', 0.0):,.1f} ft<br>"
        f"DLS: {point.get('dls', 0.0):.2f}&#176;/100ft"
    )


def _well_traces(well: dict[str, Any]) -> list[go.Scatter3d]:
    """Build the line trace + surface marker for a single well."""
    points = well.get("points", [])
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    zs = [p["z"] for p in points]
    color = well.get("color", "#0AA0AF")
    label = well.get("label", well.get("api12", "well"))

    line_trace = go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        line=dict(color=color, width=5),
        name=label,
        legendgroup=label,
        text=[_hover_text(p) for p in points],
        hovertemplate=f"<b>{label}</b><br>%{{text}}<extra></extra>",
    )

    surface = well.get("surface", {})
    sx = surface.get("x", xs[0] if xs else 0.0)
    sy = surface.get("y", ys[0] if ys else 0.0)
    sz = surface.get("z", zs[0] if zs else 0.0)
    surface_trace = go.Scatter3d(
        x=[sx],
        y=[sy],
        z=[sz],
        mode="markers",
        marker=dict(size=5, color=color, symbol="diamond", line=dict(width=1)),
        name=f"{label} (surface)",
        legendgroup=label,
        showlegend=False,
        hovertemplate=(
            f"<b>{label}</b><br>Surface wellhead<br>"
            f"X: {sx:,.1f} ft<br>Y: {sy:,.1f} ft<extra></extra>"
        ),
    )
    return [line_trace, surface_trace]


def _aspect_from_bounds(bounds: dict[str, list[float]]) -> dict[str, float]:
    """Compute aspect ratios so x/y share one scale (no horizontal distortion).

    The largest of the x/y horizontal spans defines the unit so trajectories
    keep their true plan-view shape; z is scaled independently (depth ranges
    are typically far larger than offsets and would otherwise flatten the view).
    """
    x = bounds.get("x", [0.0, 0.0])
    y = bounds.get("y", [0.0, 0.0])
    z = bounds.get("z", [0.0, 0.0])
    dx = max(x[1] - x[0], 1.0)
    dy = max(y[1] - y[0], 1.0)
    dz = max(z[1] - z[0], 1.0)
    horiz = max(dx, dy)
    return {
        "x": dx / horiz,
        "y": dy / horiz,
        "z": min(2.0, max(0.5, dz / horiz)),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def render_well_paths_plotly(
    payload: dict[str, Any],
    output_path: str,
    *,
    title: str | None = None,
) -> str:
    """Render an interactive Plotly 3D well-path HTML page.

    Args:
        payload: Dict following ``well_path_export`` schema 1.0 (e.g. from
            ``build_well_paths_payload`` or ``demo_payload``).
        output_path: Destination ``.html`` path. Parent dirs are created.
        title: Optional page/plot title. Defaults to the field name.

    Returns:
        The ``output_path`` that was written.
    """
    field_name = (payload.get("field") or {}).get("name", "")
    page_title = title or (
        f"Well Paths - {field_name}" if field_name else "Well Paths (3D)"
    )

    wells = payload.get("wells", [])
    if payload.get("well_count", len(wells)) == 0 or not wells:
        return _write(
            output_path,
            _placeholder_html(page_title, "No well-path data available to render."),
        )

    traces: list[go.Scatter3d] = []
    for well in wells:
        if not well.get("points"):
            continue
        traces.extend(_well_traces(well))

    if not traces:
        return _write(
            output_path,
            _placeholder_html(page_title, "No well-path data available to render."),
        )

    units = payload.get("units", "ft")
    aspect = _aspect_from_bounds(payload.get("bounds", {}))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text=page_title, x=0.5, xanchor="center"),
        scene=dict(
            xaxis=dict(title=f"Easting/X ({units})"),
            yaxis=dict(title=f"Northing/Y ({units})"),
            zaxis=dict(title=f"TVD ({units})", autorange="reversed"),
            aspectmode="manual",
            aspectratio=aspect,
        ),
        legend=dict(title="Wells"),
        showlegend=True,
        margin=dict(l=0, r=0, t=50, b=0),
    )

    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    return _write(output_path, html)
