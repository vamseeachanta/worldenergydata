"""Offline synthetic geometry checks; no coordinates describe actual leases."""

import re
import socket
from copy import deepcopy
from xml.etree import ElementTree as ET

import pytest

REQUESTED = {
    ("WR", "758"): "Group A",
    ("WR", "759"): "Group A",
    ("WR", "678"): "Group B",
    ("WR", "540"): "Group C",
    ("WR", "583"): "Group C",
    ("WR", "584"): "Group C",
    ("WR", "627"): "Group C",
    ("WR", "628"): "Group C",
}
SVG = {"s": "http://www.w3.org/2000/svg"}


def select_blocks(*args, **kwargs):
    from worldenergydata.bsee.visualization.block_map import select_blocks

    return select_blocks(*args, **kwargs)


def render_svg(*args, **kwargs):
    from worldenergydata.bsee.visualization.block_map import render_svg

    return render_svg(*args, **kwargs)


def rectangle(x=0, y=0):
    return [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("Network access is forbidden in synthetic map tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def collection():
    return {
        "type": "FeatureCollection",
        "source": {
            "source_id": "synthetic fixture",
            "release": "fixture version 1",
            "sha256": "a" * 64,
            "terms": "Synthetic test input only",
            "crs": "EPSG:4326",
            "units": "degrees",
        },
        "features": [
            {
                "type": "Feature",
                "properties": {"area": area, "block": block},
                "geometry": {"type": "Polygon", "coordinates": [rectangle(i)]},
            }
            for i, (area, block) in enumerate(REQUESTED)
        ],
    }


def test_selects_all_eight_exact_keys_without_mutation(collection):
    decoy = deepcopy(collection["features"][0])
    decoy["properties"]["area"] = "OTHER"
    collection["features"].insert(0, decoy)
    before = deepcopy(collection)
    result = select_blocks(collection, REQUESTED)
    assert [
        (f["properties"]["area"], f["properties"]["block"]) for f in result["features"]
    ] == list(REQUESTED)
    assert [f["properties"]["group"] for f in result["features"]] == list(
        REQUESTED.values()
    )
    assert result["source"] == collection["source"]
    result["features"][0]["geometry"]["coordinates"][0][0][0] = 99
    assert collection == before


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "wrong-area", "numeric-block"]
)
def test_rejects_incomplete_or_ambiguous_selection(collection, fault):
    if fault == "missing":
        collection["features"].pop()
    elif fault == "duplicate":
        collection["features"].append(deepcopy(collection["features"][0]))
    elif fault == "wrong-area":
        collection["features"][0]["properties"]["area"] = "OTHER"
    else:
        collection["features"][0]["properties"]["block"] = 758
    with pytest.raises(ValueError):
        select_blocks(collection, REQUESTED)
    with pytest.raises(ValueError):
        render_svg(collection, REQUESTED)


@pytest.mark.parametrize(
    "key", ["source_id", "release", "sha256", "terms", "crs", "units"]
)
def test_source_evidence_is_required(collection, key):
    del collection["source"][key]
    with pytest.raises(ValueError):
        select_blocks(collection, REQUESTED)


@pytest.mark.parametrize(
    "key,value",
    [("crs", "EPSG:3857"), ("units", "metres"), ("sha256", "unknown"), ("terms", " ")],
)
def test_source_contract_is_explicit(collection, key, value):
    collection["source"][key] = value
    with pytest.raises(ValueError):
        select_blocks(collection, REQUESTED)


def test_rejects_legacy_crs_declaration(collection):
    collection["crs"] = {"type": "name", "properties": {"name": "EPSG:3857"}}
    with pytest.raises(ValueError):
        select_blocks(collection, REQUESTED)


@pytest.mark.parametrize(
    "geometry",
    [
        None,
        {"type": "Point", "coordinates": [0, 0]},
        {"type": "Polygon", "coordinates": []},
        {"type": "MultiPolygon", "coordinates": []},
        {"type": "MultiPolygon", "coordinates": [[]]},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 0]]]},
        {"type": "Polygon", "coordinates": [rectangle()[:-1]]},
        {"type": "Polygon", "coordinates": [[[0, 0]] * 4]},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [2, 2], [0, 0]]]},
    ],
)
def test_rejects_malformed_geometry(collection, geometry):
    collection["features"][0]["geometry"] = geometry
    with pytest.raises(ValueError):
        select_blocks(collection, REQUESTED)


@pytest.mark.parametrize(
    "point",
    [
        [float("nan"), 0],
        [0, float("inf")],
        [181, 0],
        [0, 91],
        ["1", 0],
        [True, 0],
        [0],
        [0, 0, 1],
    ],
)
def test_rejects_invalid_coordinate_values(collection, point):
    collection["features"][0]["geometry"]["coordinates"][0][1] = point
    with pytest.raises(ValueError):
        select_blocks(collection, REQUESTED)


@pytest.mark.parametrize(
    "document", [None, [], {}, {"type": "FeatureCollection", "features": None}]
)
def test_rejects_malformed_collection(document):
    with pytest.raises(ValueError):
        select_blocks(document, REQUESTED)


@pytest.mark.parametrize(
    "requested", [{}, {("WR", 758): "Group A"}, {("WR", "758"): ""}]
)
def test_rejects_invalid_requests(collection, requested):
    with pytest.raises(ValueError):
        select_blocks(collection, requested)


def test_svg_has_every_identity_once_and_distinct_groups(collection, tmp_path):
    destination = tmp_path / "blocks.svg"
    destination.write_text(render_svg(collection, REQUESTED), encoding="utf-8")
    root = ET.parse(destination).getroot()
    blocks = root.findall(".//s:g[@data-block]", SVG)
    assert [(g.attrib["data-area"], g.attrib["data-block"]) for g in blocks] == list(
        REQUESTED
    )
    colors = {}
    for block in blocks:
        path = block.find("s:path", SVG)
        colors.setdefault(block.attrib["data-group"], set()).add(path.attrib["fill"])
        assert path.attrib["fill-rule"] == "evenodd"
        assert (
            block.find("s:text", SVG).text
            == f"{block.attrib['data-area']} {block.attrib['data-block']}"
        )
    assert len(colors) == 3
    assert all(len(c) == 1 for c in colors.values())
    assert len(set.union(*colors.values())) == 3
    text = " ".join(root.itertext())
    assert "Longitude (degrees)" in text and "Latitude (degrees)" in text
    assert "distance or area" in text
    assert root.find("s:metadata", SVG) is not None
    assert not root.findall(".//s:script", SVG)
    assert not root.findall(".//s:image", SVG)


def test_projection_uses_shared_extent_and_uniform_scale(collection):
    # Extent 0..8 longitude, 0..1 latitude. At latitude 0.5 degrees,
    # a 640-pixel width gives 80 pixels per longitude degree; the same
    # scale makes a latitude degree 80/cos(0.5 degrees) pixels high.
    root = ET.fromstring(render_svg(collection, REQUESTED))
    paths = root.findall(".//s:g[@data-block]/s:path", SVG)
    first = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", paths[0].attrib["d"])]
    last = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", paths[-1].attrib["d"])]
    assert first[:4] == pytest.approx([80, 320.0015, 160, 320.0015], abs=0.001)
    assert first[4:8] == pytest.approx([160, 239.9985, 80, 239.9985], abs=0.001)
    assert last[:4] == pytest.approx([640, 320.0015, 720, 320.0015], abs=0.001)


def test_multipolygon_and_holes_are_preserved(collection):
    geometry = collection["features"][0]["geometry"]
    geometry["type"] = "MultiPolygon"
    geometry["coordinates"] = [
        [rectangle(), [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]],
        [rectangle(0, 2)],
    ]
    root = ET.fromstring(render_svg(collection, REQUESTED))
    path = root.find(".//s:g[@data-block]/s:path", SVG)
    assert path.attrib["d"].count("M") == 3
    assert path.attrib["d"].count("Z") == 3
    assert path.attrib["fill-rule"] == "evenodd"


def test_labels_are_escaped(collection):
    requested = {("WR", "758"): '<group & "name">'}
    svg = render_svg(collection, requested, title="<title & text>")
    root = ET.fromstring(svg)
    assert root.find("s:title", SVG).text == "<title & text>"
    assert (
        root.find(".//s:g[@data-block]", SVG).attrib["data-group"] == '<group & "name">'
    )
    assert not root.findall(".//s:group", SVG)


@pytest.mark.parametrize("offset", [20, 85, -180])
def test_rejects_nonregional_or_polar_display(collection, offset):
    collection["features"][0]["geometry"]["coordinates"] = [
        rectangle(offset, offset if offset == 85 else 0)
    ]
    with pytest.raises(ValueError):
        render_svg(collection, REQUESTED)


def test_preserves_thin_polygon_in_shared_extent(collection):
    collection["features"][0]["geometry"]["coordinates"] = [
        [[0, 0], [1e-9, 0], [1e-9, 1], [0, 1], [0, 0]]
    ]
    root = ET.fromstring(render_svg(collection, REQUESTED))
    path = root.find(".//s:g[@data-block]/s:path", SVG)
    points = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.attrib["d"])]
    assert points[2] > points[0]


def test_rejects_ring_that_collapses_at_display_precision(collection):
    collection["features"][0]["geometry"]["coordinates"] = [
        [[0, 0], [1e-15, 0], [1e-15, 1], [0, 1], [0, 0]]
    ]
    with pytest.raises(ValueError, match="display precision"):
        render_svg(collection, REQUESTED)


@pytest.mark.parametrize("reverse", [False, True])
def test_rejects_polygon_whose_hole_cancels_at_display_precision(collection, reverse):
    epsilon = 1e-15
    hole = [
        [epsilon, epsilon],
        [1 - epsilon, epsilon],
        [1 - epsilon, 1 - epsilon],
        [epsilon, 1 - epsilon],
        [epsilon, epsilon],
    ]
    collection["features"][0]["geometry"]["coordinates"].append(
        hole[::-1] if reverse else hole
    )
    with pytest.raises(ValueError, match="display precision"):
        render_svg(collection, REQUESTED)
