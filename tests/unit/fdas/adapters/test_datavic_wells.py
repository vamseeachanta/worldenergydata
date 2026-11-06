"""Synthetic GeoJSON shaped by DataVic pet_wells DescribeFeatureType, 2026.

The artificial depth is 100 m or 100 ft; the latter is 30.48 m by the exact
international-foot definition (NIST, U.S. Survey Foot: Revised Unit Conversion
Factors, 2023 adoption, table row foot; source URL in datavic_wells.py).
"""

import hashlib
import json
from datetime import date

import pytest

from worldenergydata.fdas.adapters.datavic_wells import read_datavic_wells


def payload(**changes):
    feature = {
        "type": "Feature",
        "id": "pet_wells.1",
        "properties": {
            "siteid": 1,
            "well_name": "Synthetic",
            "spud_date": "2024-01-30T00:00:00Z",
            "abswaterdepth": 100,
            "rig_release_date": "2024-02-03T00:00:00Z",
        },
        "geometry": None,
    }
    props = changes.pop("properties", {})
    feature["properties"].update(props)
    return json.dumps(
        {
            "type": "FeatureCollection",
            "numberMatched": 1,
            "numberReturned": 1,
            "features": [feature],
        }
        | changes
    ).encode()


def read(raw=None, **changes):
    return read_datavic_wells(
        payload() if raw is None else raw,
        development_by_site_id={"1": "Example"},
        water_depth_unit=changes.get("water_depth_unit"),
    )


def test_source_identity_digest_dates_and_unknown_depth_units():
    raw = payload()
    result = read(raw)
    row = result.wells[0]
    assert row.key == ("AU", "datavic-pet-wells", "1")
    assert row.spud_date == date(2024, 1, 30)
    assert row.water_depth_m is None
    assert result.raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.source_record_ids == ("pet_wells.1",)


@pytest.mark.parametrize("unit,expected", [("m", 100), ("ft", 30.48)])
def test_explicit_depth_units(unit, expected):
    assert read(water_depth_unit=unit).wells[0].water_depth_m == expected


def test_null_metadata_is_not_fabricated():
    row = read(
        payload(properties={"spud_date": None, "abswaterdepth": None}),
        water_depth_unit="m",
    ).wells[0]
    assert row.spud_date is None
    assert row.water_depth_m is None


@pytest.mark.parametrize(
    "properties",
    [
        {"siteid": None},
        {"siteid": True},
        {"spud_date": "invalid"},
        {"abswaterdepth": -1},
        {"abswaterdepth": True},
    ],
)
def test_invalid_source_values(properties):
    with pytest.raises(ValueError):
        read(payload(properties=properties), water_depth_unit="m")


@pytest.mark.parametrize(
    "changes",
    [
        {"numberMatched": 2},
        {"numberReturned": 0},
        {"numberMatched": "unknown"},
        {"type": "ExceptionReport"},
        {"links": [{"rel": "next", "href": "next"}]},
    ],
)
def test_partial_or_error_export_rejected(changes):
    with pytest.raises(ValueError):
        read(payload(**changes))


def test_explicit_development_link_required():
    with pytest.raises(ValueError, match="development"):
        read_datavic_wells(payload(), development_by_site_id={}, water_depth_unit=None)


def test_duplicate_records_rejected():
    obj = json.loads(payload())
    obj["features"] *= 2
    obj.update(numberMatched=2, numberReturned=2)
    with pytest.raises(ValueError, match="Duplicate"):
        read(json.dumps(obj).encode())


def test_unknown_unit_rejected():
    with pytest.raises(ValueError, match="unit"):
        read(water_depth_unit="unknown")


def test_duplicate_json_keys_are_not_ambiguous_input():
    raw = payload().replace(b'"siteid": 1', b'"siteid": 2, "siteid": 1')
    with pytest.raises(ValueError, match="Duplicate JSON"):
        read(raw)


@pytest.mark.parametrize("properties", [{"spud_date": ""}, {"spud_date": 0}])
def test_empty_or_numeric_spud_is_invalid(properties):
    with pytest.raises(ValueError):
        read(payload(properties=properties))


@pytest.mark.parametrize(
    "changes",
    [{"links": [None]}, {"links": {}}, {"features": [None]}, {"features": None}],
)
def test_malformed_collections_are_rejected(changes):
    with pytest.raises(ValueError):
        read(payload(**changes))


def test_empty_export_has_no_fake_wells():
    result = read(payload(numberMatched=0, numberReturned=0, features=[]))
    assert result.wells == ()
