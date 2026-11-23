# BSEE Well Paths — 3D Three.js (WebGL) Renderer

Interactive 3D rendering of directional well trajectories in the browser using
[Three.js](https://threejs.org/) (WebGL). This is **Option 2** of the BSEE
3D well-path renderers; the sibling **Option 1** uses Plotly.

## What it does

`render_well_paths_threejs(payload, output_path, *, title=None)` emits a single,
**self-contained HTML file**. The file embeds the JSON payload and loads Three.js
(r160) plus `OrbitControls` from a pinned CDN (unpkg ES modules). All rendering
happens in the browser; the Python side only serialises the payload into an HTML
template and writes the file.

- Module: `src/worldenergydata/bsee/visualization/well_path_threejs.py`
- Template: `src/worldenergydata/bsee/visualization/templates/well_path_threejs.html`
- Three.js version pinned: **0.160.0** (r160)

## Input contract

The renderer consumes the frozen, renderer-agnostic payload built by
`worldenergydata.bsee.visualization.well_path_export` (schema version `1.0`):

```python
from worldenergydata.bsee.visualization.well_path_export import (
    build_well_paths_payload, demo_payload,
)
```

Key fields it reads: `well_count`, `units`, `field.name`, `bounds.{x,y,z}`, and
each well's `label`, `color`, `surface`, and `points[]` (`md, inc, az, x, y, z,
dls`, with `z` = TVD **positive-down**). An empty payload (`well_count == 0`)
produces a clear "no data" page instead of an empty scene.

## How to regenerate the demo

No BSEE pickle or external data needed — `demo_payload()` provides three
synthetic deviated wells produced by the real minimum-curvature helper:

```bash
uv run python scripts/bsee/demo_well_path_threejs.py
```

Output: `reports/bsee/demo_well_path_threejs.html`. Open it in a browser (needs
internet for the Three.js CDN import).

## Coordinate mapping

The payload is **field-relative East-North-Down with `z` positive downward**
(True Vertical Depth). The browser maps it to a Three.js **Y-up** world so that
depth points downward on screen:

```
sceneX =  payload.x   (East)
sceneY = -payload.z   (TVD negated -> deeper = lower on screen)
sceneZ =  payload.y   (North)
```

The scene is **recentred on the bounds centroid** and **scaled** to a fixed view
box (~100 units) so large absolute feet do not cause float jitter. The camera and
`OrbitControls.target` are framed on the centroid. A grid is placed at the
surface (payload `z = 0`) to anchor the depth direction, and an `AxesHelper`
shows East (red) / up (green) / North (blue).

## Interactions

- **Orbit**: left-drag to rotate the camera around the centroid.
- **Zoom**: scroll wheel.
- **Pan**: right-drag.
- **Hover**: a raycaster highlights the nearest survey vertex on a well path and
  shows a tooltip with the well **label** and that vertex's **MD / TVD / Inc /
  Az / DLS**.
- **Legend toggle**: the legend overlay lists every well with a color swatch;
  click an entry to hide/show that well (hover ignores hidden wells).

Debug output uses `console.log` only — no `alert()`/`confirm()` (they block
automation).

## When to prefer this over Plotly

Prefer the **Three.js** renderer when you need:

- **Scale** — many wells / dense surveys where a low-level WebGL scene graph
  stays smoother than Plotly's higher-level traces.
- **Custom geometry** — tube/thickness, custom markers, geological surfaces, or
  other bespoke 3D primitives not expressible as Plotly traces.
- **Bespoke interaction** — custom raycasting, per-object visibility, camera
  framing, or animation loops under your direct control.

Prefer the **Plotly** renderer for quick, dependency-light interactive plots,
notebook embedding, and when the built-in Plotly hover/legend behaviour is
sufficient.
