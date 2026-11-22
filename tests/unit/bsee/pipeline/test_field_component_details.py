"""Offline component navigation through the package read/write interface."""

import json
from xml.etree import ElementTree as ET

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.field_package import build_field_package


def _build(tmp_path, segments, components):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("field_context", "engineering_summary"):
        (bundle / f"{name}.json").write_text(json.dumps({"field_name": "Synthetic"}))
    for name, rows in (
        ("pipeline_segments", segments),
        ("appurtenances", components),
        ("structures", []),
        ("documents", []),
    ):
        pd.DataFrame(rows, columns=None if rows else ["segment_number"]).to_csv(
            bundle / f"{name}.csv", index=False
        )
    original = {p.name: p.read_bytes() for p in bundle.iterdir()}
    paths = build_field_package(bundle, tmp_path / "output")
    first = {k: p.read_bytes() for k, p in paths.items()}
    assert build_field_package(bundle, tmp_path / "output") == paths
    assert {k: p.read_bytes() for k, p in paths.items()} == first
    assert {p.name: p.read_bytes() for p in bundle.iterdir()} == original
    page = paths["html_report"].read_text()
    marker = '<section id="pipeline-components"'
    assert marker in page, "Package must expose expandable component details"
    section = ET.fromstring(
        page[page.index(marker) :].split("</section>", 1)[0] + "</section>"
    )
    ids = [e.attrib["id"] for e in section.iter() if "id" in e.attrib]
    assert len(ids) == len(set(ids))
    return page, section


def _members(group):
    return [
        dict(
            zip((e.text for e in dl.findall("dt")), (e.text for e in dl.findall("dd")))
        )
        for dl in group.findall(".//details[@class='component']/dl")
    ]


def test_exact_membership_repeated_rows_and_unresolved_records(tmp_path):
    segments = [{"segment_number": key} for key in ["101", "202", "303", "101", None]]
    components = [
        {
            "segment_number": "101.0",
            "appurtenance_type": "RISER",
            "asbuilt_sequence": "1",
        },
        {
            "segment_number": "101",
            "appurtenance_type": "MANIFOLD",
            "asbuilt_sequence": "2",
        },
        {"segment_number": "202", "appurtenance_type": "WELL", "asbuilt_sequence": "3"},
        {"segment_number": "999", "appurtenance_type": "UNMATCHED"},
        {"segment_number": None, "appurtenance_type": "MISSING KEY"},
    ]
    components.append(components[0].copy())
    _, section = _build(tmp_path, segments, components)
    groups = section.findall("details[@class='segment']")
    assert [g.findtext("summary") for g in groups] == [
        "Segment 101",
        "Segment 202",
        "Segment 303",
    ]
    assert [[r["appurtenance_type"] for r in _members(g)] for g in groups] == [
        ["RISER", "MANIFOLD", "RISER"],
        ["WELL"],
        [],
    ]
    assert "No component records" in "".join(groups[2].itertext())
    unresolved = section.find("details[@class='unresolved']")
    assert [r["appurtenance_type"] for r in _members(unresolved)] == [
        "UNMATCHED",
        "MISSING KEY",
    ]
    assert len(section.findall(".//div[@class='segment-record']")) == len(segments)
    assert len(section.findall(".//details[@class='component']")) == len(components)


def test_conflicting_segment_endpoints_do_not_assign_components(tmp_path):
    segments = [
        {"segment_number": "1", "origin_name": "Endpoint A"},
        {"segment_number": "1.0", "origin_name": "Endpoint B"},
    ]
    _, section = _build(
        tmp_path, segments, [{"segment_number": "1", "appurtenance_type": "RISER"}]
    )
    assert _members(section.find("details[@class='segment']")) == []
    unresolved = section.find("details[@class='unresolved']")
    assert [r["appurtenance_type"] for r in _members(unresolved)] == ["RISER"]
    assert "ambiguous" in "".join(unresolved.itertext()).lower()


@pytest.mark.parametrize(
    "column",
    [
        "origin_lease",
        "origin_area",
        "origin_block",
        "destination_lease",
        "destination_area",
        "destination_block",
    ],
)
def test_conflicting_endpoint_locations_with_blank_names_are_unresolved(
    tmp_path, column
):
    segments = [
        {
            "segment_number": "1",
            "origin_name": "",
            "destination_name": "",
            column: value,
        }
        for value in ["10", "11"]
    ]
    _, section = _build(tmp_path, segments, [{"segment_number": "1"}])
    assert _members(section.find("details[@class='segment']")) == []
    unresolved = section.find("details[@class='unresolved']")
    assert unresolved is not None
    assert len(_members(unresolved)) == 1
    assert "Ambiguous segment inventory" in "".join(unresolved.itertext())
    assert len(section.findall(".//details[@class='component']")) == 1


@pytest.mark.parametrize(
    "column",
    [
        "origin_name",
        "destination_name",
        "origin_lease",
        "origin_area",
        "origin_block",
        "destination_lease",
        "destination_area",
        "destination_block",
        "product_code",
        "pipeline_size_code",
    ],
)
def test_csv_endpoint_identifiers_and_codes_keep_leading_zeros(tmp_path, column):
    segments = [{"segment_number": "1", column: value} for value in ["001", "1"]]
    _, section = _build(tmp_path, segments, [{"segment_number": "1"}])
    group = section.find("details[@class='segment']")
    assert _members(group) == []
    unresolved = section.find("details[@class='unresolved']")
    assert unresolved is not None
    assert len(_members(unresolved)) == 1
    assert len(section.findall(".//details[@class='component']")) == 1
    # Read the actual detail fields, rather than the capped overview table.
    values = [
        dict(
            zip((e.text for e in dl.findall("dt")), (e.text for e in dl.findall("dd")))
        )[column]
        for dl in group.findall("div[@class='segment-record']/dl")
    ]
    assert values == ["001", "1"]


@pytest.mark.parametrize("missing", [None, ""])
def test_missing_endpoint_metadata_does_not_establish_conflict(tmp_path, missing):
    metadata = {
        "origin_name": "001",
        "origin_lease": "001",
        "origin_area": "01",
        "origin_block": "010",
        "destination_name": "002",
        "destination_lease": "002",
        "destination_area": "02",
        "destination_block": "020",
        "product_code": "01",
        "pipeline_size_code": "02",
    }
    segments = [
        {"segment_number": "1", **metadata},
        {"segment_number": "1.0", **dict.fromkeys(metadata, missing)},
    ]
    _, section = _build(tmp_path, segments, [{"segment_number": "1"}])
    assert len(_members(section.find("details[@class='segment']"))) == 1
    assert section.find("details[@class='unresolved']") is None


@pytest.mark.parametrize("key", ["00042.00", "9007199254740993.0", "ABC-7"])
def test_keys_are_normalized_without_float_rounding(tmp_path, key):
    expected = {
        "00042.00": "42",
        "9007199254740993.0": "9007199254740993",
        "ABC-7": "ABC-7",
    }[key]
    _, section = _build(
        tmp_path, [{"segment_number": expected}], [{"segment_number": key}]
    )
    assert len(_members(section.find("details[@class='segment']"))) == 1
    assert section.find("details[@class='unresolved']") is None


def test_evidence_and_markup_are_preserved_as_text(tmp_path):
    hostile = '<script>alert("x")</script>&\' '
    components = [
        {
            "segment_number": hostile,
            "appurtenance_type": hostile,
            "asbuilt_sequence": hostile,
            "source_table": hostile,
            "join_key": hostile,
            "evidence_confidence": confidence,
        }
        for confidence in ["document_index", "inferred", None]
    ]
    page, section = _build(tmp_path, [{"segment_number": hostile}], components)
    group = section.find("details[@class='segment']")
    members = _members(group)
    assert [r["evidence_confidence"] for r in members] == [
        "document_index",
        "inferred",
        "unavailable",
    ]
    for row in members:
        for column in [
            "appurtenance_type",
            "asbuilt_sequence",
            "source_table",
            "join_key",
        ]:
            assert row[column] == hostile.strip()
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert "&quot;" in page and "&#x27;" in page
    assert all(hostile not in e.attrib.get("id", "") for e in section.iter())
    assert "retrieval leads" in "".join(section.itertext())
    assert "engineering review" in "".join(section.itertext())


@pytest.mark.parametrize(
    "segments,components",
    [
        ([], []),
        ([{"unrelated": "record"}], [{"unrelated": "record"}]),
        ([], [{"appurtenance_type": "ORPHAN"}]),
    ],
)
def test_empty_inputs_and_absent_key_columns(tmp_path, segments, components):
    _, section = _build(tmp_path, segments, components)
    assert len(section.findall(".//details[@class='component']")) == len(components)
    assert len(section.findall(".//div[@class='segment-record']")) == len(segments)
    if not segments and not components:
        assert "No segment or component records" in "".join(section.itertext())
    else:
        assert section.find("details[@class='unresolved']") is not None


def test_all_rows_beyond_inventory_caps_remain_visible(tmp_path):
    segments = [{"segment_number": str(i)} for i in range(35)]
    components = [
        {"segment_number": str(i % 35), "asbuilt_sequence": str(i)} for i in range(80)
    ]
    _, section = _build(tmp_path, segments, components)
    assert len(section.findall("details[@class='segment']")) == 35
    assert sorted(int(r["asbuilt_sequence"]) for r in _members(section)) == list(
        range(80)
    )
