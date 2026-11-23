# BSEE 3D Well-Path Renderer (Plotly)

Interactive, self-contained 3D visualization of BSEE well trajectories rendered
with [Plotly](https://plotly.com/python/). Each well is drawn as its **full**
minimum-curvature polyline (not just a straight surface-to-TD line), so deviated
and horizontal wells are shown faithfully.

- Module: `src/worldenergydata/bsee/visualization/well_path_plotly.py`
- Public API: `render_well_paths_plotly(payload, output_path, *, title=None) -> str`
- Demo: `scripts/bsee/demo_well_path_plotly.py`
- Tests: `tests/unit/bsee/visualization/test_well_path_plotly.py`

## What it does

Given a renderer-agnostic payload, it produces a standalone HTML page
(`include_plotlyjs="cdn"`) with:

- One `Scatter3d` line trace per well (color and label from the payload).
- A diamond surface-wellhead marker per well.
- Per-vertex hover text showing **MD, Inc, Az, TVD, DLS**.
- A reversed z-axis (`autorange="reversed"`) so depth increases downward.
- Equal x/y aspect (computed from `bounds`) so plan-view shapes aren't distorted.
- A legend (toggle wells on/off) and a title from `title` or the field name.

An empty payload (`well_count == 0`, no wells, or wells with no points) writes a
graceful placeholder HTML page instead of an empty plot.

## Input contract

The payload is the frozen schema produced by
`src/worldenergydata/bsee/visualization/well_path_export.py`
(`build_well_paths_payload(...)` for real pipeline data, or `demo_payload()` for
synthetic data). Key fields the renderer reads:

```
{
  "units": "ft",
  "field": {"name": str},
  "well_count": int,
  "bounds": {"x":[min,max], "y":[min,max], "z":[min,max]},
  "wells": [
    {"label": str, "color": "#hex",
     "surface": {"x":float, "y":float, "z":float},
     "points": [{"md":f,"inc":f,"az":f,"x":f,"y":f,"z":f,"dls":f}, ...]}
  ]
}
```

Coordinates are field-relative feet, East-North-Down, with `z` = TVD
**positive-down**. The renderer never mutates the numbers; it only reverses the
display z-axis.

## How to regenerate the demo

```bash
uv run python scripts/bsee/demo_well_path_plotly.py
```

This writes `reports/bsee/demo_well_path_plotly.html` (three synthetic deviated
wells) and prints the output path. No external data or BSEE pickle is required.

To render real data, build a payload from the pipeline result and pass it in:

```python
from worldenergydata.bsee.visualization.well_path_export import (
    build_well_paths_payload,
)
from worldenergydata.bsee.visualization.well_path_plotly import (
    render_well_paths_plotly,
)

payload = build_well_paths_payload(well.output_data_well_path, field_name="...")
render_well_paths_plotly(payload, "reports/bsee/my_field_paths.html")
```

## Interactions

Open the generated HTML in any modern browser. No server is needed.

- **Rotate** — left-click and drag to orbit the 3D scene.
- **Zoom** — scroll wheel (or pinch) to zoom in/out.
- **Pan** — right-click and drag.
- **Hover** — hover any vertex to read MD, Inc, Az, TVD and DLS for that station.
- **Legend toggle** — click a well in the legend to hide it; double-click to
  isolate a single well.
- Plotly's modebar (top-right) offers reset-camera, orthographic/perspective and
  PNG snapshot.

## When to prefer this over the Three.js renderer

Use this **Plotly** renderer when you want:

- A zero-build, single-file HTML deliverable that opens anywhere (the Plotly JS
  is pulled from a CDN, no bundler or local assets).
- Built-in scientific niceties: axis titles/ticks in feet, hover tooltips, a
  modebar with PNG export, and legend-driven filtering — all for free.
- Quick analyst-facing reports and notebooks consistent with the rest of the
  repo's Plotly visualizations.

Prefer the **Three.js** renderer when you need a richer, fully custom WebGL
experience (bespoke camera controls, large well counts where you want
GPU-tuned rendering, or embedding into a larger interactive web app). Both
consume the identical `well_path_export` payload, so you can switch renderers
without changing any data plumbing.
