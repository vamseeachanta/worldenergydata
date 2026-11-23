#!/usr/bin/env python
"""Generate a demo Three.js 3D well-path HTML from synthetic BSEE data.

Run with uv (no external data or BSEE pickle required):

    uv run python scripts/bsee/demo_well_path_threejs.py

Writes ``reports/bsee/demo_well_path_threejs.html`` and prints its path.
"""

from __future__ import annotations

import os

from worldenergydata.bsee.visualization.well_path_export import demo_payload
from worldenergydata.bsee.visualization.well_path_threejs import (
    render_well_paths_threejs,
)


def main() -> str:
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    out_dir = os.path.join(repo_root, "reports", "bsee")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "demo_well_path_threejs.html")

    payload = demo_payload()
    written = render_well_paths_threejs(
        payload, out_path, title=payload["field"]["name"]
    )
    print(f"Wrote Three.js well-path demo: {written}")
    print(f"  wells: {payload['well_count']}  units: {payload['units']}")
    print("  open in a browser (needs internet for the Three.js CDN import)")
    return written


if __name__ == "__main__":
    main()
