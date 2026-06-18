#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["plotly"]
# ///
"""Generate the demo Plotly 3D well-path HTML from synthetic data.

Run with:

    uv run python scripts/bsee/demo_well_path_plotly.py

Uses ``demo_payload()`` (three synthetic deviated wells, no external data or
BSEE pickle required) and writes a standalone interactive HTML page to
``reports/bsee/demo_well_path_plotly.html``.
"""

from __future__ import annotations

from pathlib import Path

from worldenergydata.bsee.visualization.well_path_export import demo_payload
from worldenergydata.bsee.visualization.well_path_plotly import (
    render_well_paths_plotly,
)

OUTPUT = Path("reports/bsee/demo_well_path_plotly.html")


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = demo_payload()
    out = render_well_paths_plotly(
        payload,
        str(OUTPUT),
        title=f"Demo Well Paths - {payload['field']['name']}",
    )
    print(f"Wrote interactive 3D well-path HTML to: {out}")


if __name__ == "__main__":
    main()
