"""Local synthetic evidence validates metadata, never engineering qualification."""

import hashlib
import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict

import pytest

from worldenergydata.fdas.adapters.datavic_evidence import read_datavic_evidence
from worldenergydata.fdas.data.country_drilling import build_drilling_timeline


def inputs(empty=False):
    features = (
        []
        if empty
        else [
            {
                "type": "Feature",
                "id": "pet_wells.7",
                "properties": {
                    "siteid": 7,
                    "spud_date": "2024-01-30",
                    "abswaterdepth": 100,
                    "rig_release_date": "2024-02-03",
                },
            }
        ]
    )
    raw = json.dumps(
        {
            "type": "FeatureCollection",
            "features": features,
            "numberMatched": len(features),
            "numberReturned": len(features),
        }
    ).encode()
    metadata = {
        "schema_version": 1,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "query_url": "https://example.invalid/wfs?typeNames=pet_wells",
        "retrieved_at_utc": "2026-11-16T12:00:00Z",
        "source_vintage": None,
        "licence_identifier": "synthetic-licence",
        "licence_source": "citation:synthetic-licence",
        "development_links": (
            []
            if empty
            else [
                {
                    "site_id": "7",
                    "development": "Example",
                    "evidence": "citation:link-7",
                }
            ]
        ),
        "water_depth_unit": None,
        "water_depth_unit_evidence": None,
    }
    return raw, metadata


def test_retains_bytes_metadata_identity_and_immutable_snapshot():
    raw, metadata = inputs()
    original = deepcopy(metadata)
    result = read_datavic_evidence(raw, metadata)
    assert result.raw == raw
    assert result.normalized.raw_sha256 == metadata["raw_sha256"]
    assert result.normalized.source_record_ids == ("pet_wells.7",)
    assert result.normalized.wells[0].key == ("AU", "datavic-pet-wells", "7")
    assert result.normalized.wells[0].development == "Example"
    assert result.normalized.wells[0].water_depth_m is None
    assert asdict(result)["source_vintage"] is None
    for name in original.keys() - {"development_links"}:
        assert getattr(result, name) == original[name]
    assert asdict(result.development_links[0]) == original["development_links"][0]
    metadata["development_links"][0]["development"] = "Altered"
    assert result.development_links[0].development == "Example"
    with pytest.raises(FrozenInstanceError):
        result.source_vintage = "Altered"
    with pytest.raises(FrozenInstanceError):
        result.development_links[0].evidence = "Altered"


@pytest.mark.parametrize("unit,depth", [("m", 100), ("ft", 30.48)])
def test_evidenced_unit_and_known_vintage(unit, depth):
    raw, metadata = inputs()
    metadata.update(
        water_depth_unit=unit,
        water_depth_unit_evidence="citation:unit",
        source_vintage="synthetic revision 2",
    )
    result = read_datavic_evidence(raw, metadata)
    assert result.normalized.wells[0].water_depth_m == depth
    assert result.source_vintage == "synthetic revision 2"
    assert result.water_depth_unit_evidence == "citation:unit"


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("raw_sha256", "0" * 64),
        ("query_url", ""),
        ("query_url", "not a URL"),
        ("retrieved_at_utc", "2026-11-16"),
        ("retrieved_at_utc", "2026-11-16T12:00:00"),
        ("retrieved_at_utc", "2026-11-16T12:00:00+01:00"),
        ("retrieved_at_utc", "invalid"),
        ("retrieved_at_utc", None),
        ("source_vintage", ""),
        ("licence_identifier", " "),
        ("licence_source", None),
        ("water_depth_unit", "unknown"),
        ("water_depth_unit", []),
        ("water_depth_unit", "m"),
        ("water_depth_unit_evidence", ""),
        ("development_links", {}),
        ("development_links", []),
        ("development_links", [None]),
    ],
)
def test_bad_metadata_fails_before_normalization(monkeypatch, key, value):
    raw, metadata = inputs()
    metadata[key] = value

    def forbidden(*args, **kwargs):
        pytest.fail("Normalization called before evidence validation")

    monkeypatch.setattr(
        "worldenergydata.fdas.adapters.datavic_evidence.read_datavic_wells", forbidden
    )
    with pytest.raises(ValueError):
        read_datavic_evidence(raw, metadata)


@pytest.mark.parametrize("key", list(inputs()[1]))
def test_every_metadata_field_is_explicit(key):
    raw, metadata = inputs()
    del metadata[key]
    with pytest.raises(ValueError):
        read_datavic_evidence(raw, metadata)


@pytest.mark.parametrize(
    "change",
    [
        {"site_id": "8"},
        {"site_id": 7},
        {"site_id": "07"},
        {"development": ""},
        {"evidence": ""},
        {"evidence": None},
        {"typo": "value"},
    ],
)
def test_altered_or_malformed_link_is_rejected(change):
    raw, metadata = inputs()
    metadata["development_links"][0].update(change)
    with pytest.raises(ValueError):
        read_datavic_evidence(raw, metadata)


def test_duplicate_extra_links_and_unknown_metadata_are_rejected():
    raw, metadata = inputs()
    for extra in [
        dict(metadata["development_links"][0]),
        {"site_id": "8", "development": "Example", "evidence": "citation:8"},
    ]:
        changed = deepcopy(metadata)
        changed["development_links"].append(extra)
        with pytest.raises(ValueError):
            read_datavic_evidence(raw, changed)
    with pytest.raises(ValueError):
        read_datavic_evidence(raw, metadata | {"typo": "value"})
    with pytest.raises(ValueError):
        read_datavic_evidence(raw, None)


def test_altered_export_is_rejected_before_parsing():
    raw, metadata = inputs()
    with pytest.raises(ValueError, match="digest"):
        read_datavic_evidence(raw + b"invalid", metadata)
    with pytest.raises(ValueError, match="bytes"):
        read_datavic_evidence(bytearray(raw), metadata)


def test_empty_export_and_opaque_references():
    raw, metadata = inputs(empty=True)
    metadata["licence_source"] = "citation:never-open-this"
    result = read_datavic_evidence(raw, metadata)
    assert result.raw == raw
    assert result.normalized.wells == ()
    assert result.development_links == ()
    assert result.licence_source == "citation:never-open-this"


def test_metadata_does_not_supply_measured_activity():
    raw, metadata = inputs()
    result = read_datavic_evidence(raw, metadata)
    timeline = build_drilling_timeline(
        result.normalized.wells, [], development="Example"
    )
    assert timeline.status == "NOT_EVALUATED"
    assert timeline.drilling_monthly is None
    with pytest.raises(ValueError, match="NOT_EVALUATED"):
        timeline.as_cashflow_input()
