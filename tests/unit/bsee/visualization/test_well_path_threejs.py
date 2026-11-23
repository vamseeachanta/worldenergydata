"""Static tests for the Three.js well-path HTML renderer.

These validate the emitted HTML/JSON without a headless browser: the embedded
JSON is extracted and parsed, and the HTML is checked for the required CDN
import, controls, well labels, and that no placeholder token survives.
"""

from __future__ import annotations

import json
import re

import pytest

from worldenergydata.bsee.visualization.well_path_export import demo_payload
from worldenergydata.bsee.visualization.well_path_threejs import (
    render_well_paths_threejs,
)

_PAYLOAD_TOKEN = "__WELL_PATH_PAYLOAD__"
_TITLE_TOKEN = "__WELL_PATH_TITLE__"


def _extract_payload(html: str) -> dict:
    """Pull the embedded JSON out of the `const PAYLOAD = <json> null;` line."""
    m = re.search(r"const PAYLOAD =\s*(\{.*?\})\s*null;", html, re.DOTALL)
    assert m, "embedded PAYLOAD JSON not found in HTML"
    return json.loads(m.group(1))


def test_render_writes_nonempty_html(tmp_path):
    out = tmp_path / "wells.html"
    result = render_well_paths_threejs(demo_payload(), str(out), title="DEMO")
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_html_is_html_with_three_and_controls(tmp_path):
    out = tmp_path / "wells.html"
    render_well_paths_threejs(demo_payload(), str(out))
    html = out.read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "three" in html  # CDN import / module
    assert "OrbitControls" in html


def test_no_placeholder_tokens_remain(tmp_path):
    out = tmp_path / "wells.html"
    render_well_paths_threejs(demo_payload(), str(out), title="My Field")
    html = out.read_text(encoding="utf-8")
    assert _PAYLOAD_TOKEN not in html
    assert _TITLE_TOKEN not in html
    assert "My Field" in html


def test_embedded_json_parses_and_matches_payload(tmp_path):
    payload = demo_payload()
    out = tmp_path / "wells.html"
    render_well_paths_threejs(payload, str(out))
    html = out.read_text(encoding="utf-8")
    embedded = _extract_payload(html)

    assert embedded["well_count"] == payload["well_count"]
    assert len(embedded["wells"]) == payload["well_count"]
    for well in payload["wells"]:
        assert well["label"] in html
        labels = [w["label"] for w in embedded["wells"]]
        assert well["label"] in labels


def test_title_defaults_to_field_name(tmp_path):
    payload = demo_payload()
    out = tmp_path / "wells.html"
    render_well_paths_threejs(payload, str(out))
    html = out.read_text(encoding="utf-8")
    assert payload["field"]["name"] in html


def test_empty_payload_writes_no_data_page(tmp_path):
    empty = {
        "schema_version": "1.0",
        "units": "ft",
        "field": {"name": "EMPTY FIELD"},
        "well_count": 0,
        "bounds": {"x": [0, 0], "y": [0, 0], "z": [0, 0]},
        "wells": [],
    }
    out = tmp_path / "empty.html"
    render_well_paths_threejs(empty, str(out))
    html = out.read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "No well paths" in html
    assert _PAYLOAD_TOKEN not in html
    assert "EMPTY FIELD" in html


def test_creates_missing_parent_dirs(tmp_path):
    out = tmp_path / "nested" / "deep" / "wells.html"
    render_well_paths_threejs(demo_payload(), str(out))
    assert out.exists()


def test_rejects_non_dict_payload(tmp_path):
    with pytest.raises(TypeError):
        render_well_paths_threejs(["not", "a", "dict"], str(tmp_path / "x.html"))
