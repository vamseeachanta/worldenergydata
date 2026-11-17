"""Offline fields-theme contract using explicitly synthetic snapshots."""

import hashlib
import json

import pytest

from worldenergydata.ukcs.field_metadata import read_field_metadata

SOURCE = {
    "source_url": "https://example.invalid/fields/0",
    "retrieved_at": "2026-11-16T00:00:00Z",
}


def snapshot(*records):
    return json.dumps({"features": [{"attributes": row} for row in records]}).encode()


def read(raw, name="Synthetic Alpha"):
    return read_field_metadata(raw, name, **SOURCE)


def test_enriched_snapshot_keeps_raw_dates_and_byte_provenance():
    raw = snapshot(
        {
            "FIELDNAME": "SYNTHETIC ALPHA",
            "OBJECTID": 7,
            "CURR_OPER": 'Synthetic "Operator"',
            "STATUS": "Producing",
            "PROD_DATE": "not a calendar date",
            "DISC_DATE": "1980?",
        }
    )
    meta = read(raw)
    assert meta["operator"] == 'Synthetic "Operator"'
    assert meta["field_status"] == "Producing"
    assert meta["startup_raw"] == "not a calendar date"
    assert meta["discovery_raw"] == "1980?"
    evidence = meta["metadata_evidence"]
    assert evidence["coverage"] == dict.fromkeys(
        ["operator", "field_status", "startup_raw", "discovery_raw"], True
    )
    assert evidence["source_ids"] == [7]
    assert evidence["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert evidence["source_url"] == SOURCE["source_url"]
    assert evidence["retrieved_at"] == SOURCE["retrieved_at"]
    assert evidence["recommendation_ready"] is False
    assert evidence["fdp_consent"] == "NOT_EVALUATED"
    spaced = b" \n" + raw + b"\n"
    assert read(spaced)["metadata_evidence"]["raw_sha256"] != evidence["raw_sha256"]
    assert raw == snapshot(
        {
            "FIELDNAME": "SYNTHETIC ALPHA",
            "OBJECTID": 7,
            "CURR_OPER": 'Synthetic "Operator"',
            "STATUS": "Producing",
            "PROD_DATE": "not a calendar date",
            "DISC_DATE": "1980?",
        }
    )


@pytest.mark.parametrize("name", ["synthetic alpha", "  SYNTHETIC ALPHA \t"])
def test_exact_normalized_match_and_identical_duplicates(name):
    row = {
        "FIELDNAME": " Synthetic Alpha ",
        "OBJECTID": 2,
        "CURR_OPER": "Synthetic Operator",
    }
    meta = read(snapshot(row, dict(row, OBJECTID=1)), name)
    assert meta["operator"] == "Synthetic Operator"
    assert meta["metadata_evidence"]["source_ids"] == [1, 2]
    reordered = read(snapshot(dict(row, OBJECTID=1), row), name)
    assert reordered["operator"] == meta["operator"]
    evidence = reordered["metadata_evidence"]
    assert evidence.pop("raw_sha256") != meta["metadata_evidence"]["raw_sha256"]
    assert evidence == {
        k: v for k, v in meta["metadata_evidence"].items() if k != "raw_sha256"
    }


@pytest.mark.parametrize(
    "records", [[], [{"FIELDNAME": "Synthetic Alphabet", "OBJECTID": 1}]]
)
def test_no_match_is_explicit_and_not_fuzzy(records):
    meta = read(snapshot(*records))
    assert meta["field_name"] == "Synthetic Alpha"
    assert meta["operator"] is None
    assert meta["metadata_evidence"]["source_ids"] == []
    assert not any(meta["metadata_evidence"]["coverage"].values())
    assert meta["metadata_evidence"]["match_status"] == "no_match"
    assert meta["metadata_evidence"]["recommendation_ready"] is False


def test_sparse_and_blank_values_stay_null():
    meta = read(
        snapshot(
            {
                "FIELDNAME": "Synthetic Alpha",
                "OBJECTID": 1,
                "CURR_OPER": "  ",
                "PROD_DATE": None,
            }
        )
    )
    assert all(
        meta[key] is None
        for key in ["operator", "field_status", "startup_raw", "discovery_raw"]
    )
    assert meta["metadata_evidence"]["match_status"] == "matched"
    assert not any(meta["metadata_evidence"]["coverage"].values())


@pytest.mark.parametrize(
    "key,value", [("CURR_OPER", "Other"), ("STATUS", "Other"), ("OTHER", 3)]
)
def test_conflicting_non_id_attributes_fail(key, value):
    row = {"FIELDNAME": "Synthetic Alpha", "OBJECTID": 1}
    with pytest.raises(ValueError, match="conflicting"):
        read(snapshot(row, dict(row, OBJECTID=2, **{key: value})))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"features":[],"features":[]}',
        b'{"features":[],"x":{"a":1,"a":2}}',
        b'{"features":[],"x":NaN}',
        b'{"features":[],"x":Infinity}',
        b'{"features":[],"x":-Infinity}',
        b'{"features":[],"x":1e999}',
        b"[]",
        b"{}",
        b'{"features":{}}',
        b'{"features":[null]}',
        b'{"features":[{}]}',
        b'{"features":[{"attributes":[]}]}',
        b"\xff",
        b"{} trailing",
    ],
)
def test_invalid_json_and_feature_shapes_fail(raw):
    with pytest.raises(ValueError):
        read(raw)


@pytest.mark.parametrize(
    "row",
    [
        {"OBJECTID": 1},
        {"FIELDNAME": 3, "OBJECTID": 1},
        {"FIELDNAME": " ", "OBJECTID": 1},
        {"FIELDNAME": "Other"},
        {"FIELDNAME": "Other", "OBJECTID": True},
        {"FIELDNAME": "Other", "OBJECTID": 1, "CURR_OPER": 42},
        {"FIELDNAME": "Other", "OBJECTID": 1, "PROD_DATE": 1234},
    ],
)
def test_malformed_attributes_fail_even_outside_requested_field(row):
    with pytest.raises(ValueError):
        read(snapshot(row))


def test_requires_bytes_and_nonblank_request_and_provenance():
    with pytest.raises(TypeError):
        read('{"features":[]}')
    for key in ["source_url", "retrieved_at"]:
        with pytest.raises(ValueError):
            read_field_metadata(
                snapshot(), "Synthetic Alpha", **dict(SOURCE, **{key: " "})
            )
    with pytest.raises(ValueError):
        read(snapshot(), " ")
