"""Unit tests for the Plotly 3D well-path renderer.

Driven entirely by ``demo_payload()`` so the tests never touch the ~300MB BSEE
pickle or any external data.
"""

from __future__ import annotations

import copy

from worldenergydata.bsee.visualization.well_path_export import demo_payload
from worldenergydata.bsee.visualization.well_path_plotly import (
    render_well_paths_plotly,
)


def test_renders_html_file(tmp_path):
    payload = demo_payload()
    out = tmp_path / "well_paths.html"

    result = render_well_paths_plotly(payload, str(out))

    assert result == str(out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "<html" in content.lower()


def test_contains_every_well_label(tmp_path):
    payload = demo_payload()
    out = tmp_path / "labels.html"

    render_well_paths_plotly(payload, str(out))
    content = out.read_text(encoding="utf-8")

    for well in payload["wells"]:
        assert well["label"] in content


def test_line_trace_count_matches_well_count(tmp_path):
    payload = demo_payload()
    out = tmp_path / "traces.html"

    render_well_paths_plotly(payload, str(out))
    content = out.read_text(encoding="utf-8")

    # One "lines"-mode Scatter3d trace per well (surface markers use "markers").
    line_traces = content.count('"mode":"lines"')
    assert line_traces == payload["well_count"]


def test_title_override(tmp_path):
    payload = demo_payload()
    out = tmp_path / "titled.html"

    render_well_paths_plotly(payload, str(out), title="Custom 3D Title")
    content = out.read_text(encoding="utf-8")

    assert "Custom 3D Title" in content


def test_reversed_depth_axis(tmp_path):
    payload = demo_payload()
    out = tmp_path / "depth.html"

    render_well_paths_plotly(payload, str(out))
    content = out.read_text(encoding="utf-8")

    # Depth must increase downward -> z-axis autorange reversed.
    assert "reversed" in content


def test_empty_payload_writes_placeholder(tmp_path):
    payload = {
        "schema_version": "1.0",
        "units": "ft",
        "field": {"name": "EMPTY FIELD"},
        "well_count": 0,
        "bounds": {"x": [0.0, 0.0], "y": [0.0, 0.0], "z": [0.0, 0.0]},
        "wells": [],
    }
    out = tmp_path / "empty.html"

    result = render_well_paths_plotly(payload, str(out))

    assert result == str(out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "<html" in content.lower()
    assert "No well-path data" in content
    # A placeholder must not embed any 3D scatter traces.
    assert "Scatter3d" not in content


def test_wells_with_no_points_fall_back_to_placeholder(tmp_path):
    payload = copy.deepcopy(demo_payload())
    for well in payload["wells"]:
        well["points"] = []
    out = tmp_path / "nopoints.html"

    render_well_paths_plotly(payload, str(out))
    content = out.read_text(encoding="utf-8")

    assert "No well-path data" in content
