"""Three.js (WebGL) interactive 3D well-path renderer for the BSEE module.

This module is the Python side of an *Option 2* renderer: it consumes the
renderer-agnostic payload produced by
``worldenergydata.bsee.visualization.well_path_export`` and emits a single,
self-contained HTML file. All WebGL rendering happens in the browser via
Three.js loaded from a pinned CDN; the Python side only serialises the payload
into an HTML template and writes the file.

Usage
-----
    from worldenergydata.bsee.visualization.well_path_export import demo_payload
    from worldenergydata.bsee.visualization.well_path_threejs import (
        render_well_paths_threejs,
    )

    payload = demo_payload()
    render_well_paths_threejs(payload, "well_paths.html", title="DEMO FIELD")

Coordinate convention
---------------------
The payload is field-relative East-North-Down with ``z`` positive *downward*
(True Vertical Depth). The browser maps that to a Three.js Y-up world; see the
JS comment in the template for the exact axis mapping.
"""

from __future__ import annotations

import json
import os

# Placeholder tokens replaced when the template is materialised. The payload
# token sits inside a JS comment so the raw template is still valid JavaScript.
_PAYLOAD_TOKEN = "/*__WELL_PATH_PAYLOAD__*/"
_TITLE_TOKEN = "__WELL_PATH_TITLE__"

_TEMPLATE_FILENAME = "well_path_threejs.html"


def _template_path() -> str:
    """Return the absolute path to the bundled HTML/JS template."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "templates", _TEMPLATE_FILENAME)


def _load_template() -> str:
    """Read the HTML template text from disk."""
    with open(_template_path(), encoding="utf-8") as fh:
        return fh.read()


def _empty_html(title: str) -> str:
    """Return a clear, standalone 'no data' page for empty payloads."""
    safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{safe_title}</title>\n"
        "<style>\n"
        "  body { margin: 0; font-family: system-ui, sans-serif; "
        "background: #0b0f14; color: #e6edf3; "
        "display: flex; align-items: center; justify-content: center; "
        "height: 100vh; }\n"
        "  .msg { text-align: center; max-width: 32rem; padding: 2rem; }\n"
        "  h1 { font-size: 1.4rem; font-weight: 600; }\n"
        "  p { color: #9aa7b4; line-height: 1.5; }\n"
        "</style>\n</head>\n<body>\n"
        '<div class="msg">\n'
        f"  <h1>{safe_title}</h1>\n"
        "  <p>No well paths to display. The payload contained zero wells "
        "(<code>well_count == 0</code>). Provide a payload with at least one "
        "well that has survey points.</p>\n"
        "</div>\n</body>\n</html>\n"
    )


def render_well_paths_threejs(
    payload: dict,
    output_path: str,
    *,
    title: str | None = None,
) -> str:
    """Render ``payload`` to a self-contained Three.js HTML file.

    Args:
        payload: A dict following the ``well_path_export`` schema (version 1.0).
        output_path: Destination HTML path. Parent dirs are created if missing.
        title: Optional page/scene title. Defaults to the field name, then to
            a generic label.

    Returns:
        The ``output_path`` that was written.
    """
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict following the well-path schema")

    field_name = ""
    field = payload.get("field")
    if isinstance(field, dict):
        field_name = str(field.get("name") or "")
    resolved_title = title or field_name or "BSEE Well Paths (3D)"

    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    well_count = int(payload.get("well_count", 0) or 0)
    if well_count == 0 or not payload.get("wells"):
        html = _empty_html(resolved_title)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(html)
        return output_path

    template = _load_template()
    # Serialise the payload. ``</`` is escaped so an embedded string can never
    # prematurely close the <script> block.
    payload_json = json.dumps(payload).replace("</", "<\\/")
    safe_title = resolved_title.replace("<", "&lt;").replace(">", "&gt;")

    html = template.replace(_PAYLOAD_TOKEN, payload_json)
    html = html.replace(_TITLE_TOKEN, safe_title)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path
