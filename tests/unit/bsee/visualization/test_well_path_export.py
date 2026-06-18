"""Unit tests for the shared well-path export contract.

Covers the renderer-agnostic payload both 3D renderers (Plotly, Three.js)
consume, plus the dependency-light minimum-curvature helper and demo data.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from worldenergydata.bsee.visualization.well_path_export import (
    SCHEMA_VERSION,
    build_well_paths_payload,
    color_for_index,
    demo_payload,
    minimum_curvature,
    well_paths_to_json_file,
)


def test_minimum_curvature_vertical_well_has_no_lateral_offset():
    stations = [
        {"md": 0, "inc": 0, "az": 0},
        {"md": 1000, "inc": 0, "az": 0},
        {"md": 2000, "inc": 0, "az": 0},
    ]
    pts = minimum_curvature(stations)
    assert len(pts) == 3
    # A vertical well: x,y stay ~0 and TVD tracks MD.
    assert pts[-1]["x"] == pytest.approx(0.0, abs=1e-6)
    assert pts[-1]["y"] == pytest.approx(0.0, abs=1e-6)
    assert pts[-1]["z"] == pytest.approx(2000.0, abs=1e-6)


def test_minimum_curvature_45deg_hold_splits_offset_equally():
    # Holding 45 deg inclination on a 45 deg azimuth -> equal x and y growth,
    # and TVD < MD because the hole is deviated.
    stations = [
        {"md": 0, "inc": 45, "az": 45},
        {"md": 1000, "inc": 45, "az": 45},
    ]
    pts = minimum_curvature(stations)
    last = pts[-1]
    assert last["x"] == pytest.approx(last["y"], rel=1e-6)
    assert last["z"] < 1000.0


def test_demo_payload_shape_and_schema():
    payload = demo_payload()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["units"] == "ft"
    assert payload["well_count"] == len(payload["wells"]) == 3
    for well in payload["wells"]:
        assert {"api12", "label", "color", "surface", "points"} <= set(well)
        assert well["points"], "each well must carry vertices"
        first = well["points"][0]
        assert set(first) >= {"md", "inc", "az", "x", "y", "z", "dls"}
    # Bounds enclose every vertex.
    b = payload["bounds"]
    xs = [p["x"] for w in payload["wells"] for p in w["points"]]
    assert b["x"][0] == pytest.approx(min(xs))
    assert b["x"][1] == pytest.approx(max(xs))


def test_color_assignment_is_stable_and_wraps():
    assert color_for_index(0) == color_for_index(10)  # palette length 10
    assert color_for_index(0) != color_for_index(1)


def test_build_payload_from_pipeline_like_dataframe():
    # Mimic the columns WellAPI12.process_survey_xyz emits.
    df = pd.DataFrame(
        {
            "md": [0.0, 1000.0],
            "inc": [0.0, 30.0],
            "az": [90.0, 90.0],
            "x_coor": [10.0, 10.0],
            "y_coor": [20.0, 270.0],
            "z_coor": [0.0, 980.0],
            "dls": [0.0, 0.9],
        }
    )
    payload = build_well_paths_payload(
        {608124000401: df},
        labels={608124000401: "TEST A-001-ST00"},
        field_name="TEST FIELD",
    )
    assert payload["well_count"] == 1
    well = payload["wells"][0]
    assert well["api12"] == "608124000401"
    assert well["label"] == "TEST A-001-ST00"
    assert well["points"][1]["x"] == 10.0
    assert well["points"][1]["z"] == 980.0
    assert well["surface"] == {"x": 10.0, "y": 20.0, "z": 0.0}


def test_build_payload_empty_input():
    payload = build_well_paths_payload({})
    assert payload["well_count"] == 0
    assert payload["wells"] == []
    assert payload["bounds"]["z"] == [0.0, 0.0]


def test_json_roundtrip_to_file(tmp_path):
    payload = demo_payload()
    out = tmp_path / "wp.json"
    written = well_paths_to_json_file(payload, str(out))
    assert written == str(out)
    reloaded = json.loads(out.read_text())
    assert reloaded["well_count"] == payload["well_count"]
    assert reloaded["wells"][0]["label"] == payload["wells"][0]["label"]
