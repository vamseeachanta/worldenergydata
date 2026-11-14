"""Offline ArcGIS contract tests using invented wells, never regulator records.

Protocol: Esri, Query (Feature Service/Layer), JSON response syntax (2026),
https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/.
Numbers below are synthetic inputs. Expected medians follow Python's published
statistics.median examples (2026 documentation) or the hand calculations noted
in each test; no source-layer schema or real depth is asserted here.
"""

import pytest

from worldenergydata.canada.development_wells import (
    DevelopmentWell,
    DevelopmentWellMapping,
    parse_development_wells,
    summarize_field_wells,
)

MAPPING = DevelopmentWellMapping(
    uwi="well_key",
    field_name="field_key",
    water_depth_m="depth_key",
    latitude="lat_key",
    longitude="lon_key",
)
SOURCE = "synthetic-development-wells"


def feature(uwi="example-a", field="Example", depth="3", lat="1", lon="-1"):
    return {
        "attributes": {
            "well_key": uwi,
            "field_key": field,
            "depth_key": depth,
            "lat_key": lat,
            "lon_key": lon,
        }
    }


def parse(*features):
    return parse_development_wells(
        {"features": list(features)}, mapping=MAPPING, source=SOURCE
    )


def test_parse_explicit_mapping_preserves_identity_coordinates_and_source():
    """Direct identity: input strings '3', '1', '-1' become the same numbers."""
    wells = parse(feature(uwi="  example-a  "))
    assert wells == (DevelopmentWell("example-a", "Example", 3.0, 1.0, -1.0, SOURCE),)


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_null_depth_and_coordinates_are_preserved(empty):
    (well,) = parse(feature(depth=empty, lat=empty, lon=empty))
    assert well.water_depth_m is None
    assert well.latitude is None
    assert well.longitude is None


@pytest.mark.parametrize("invalid", ["unknown", "NaN", "inf", True, [], {}])
@pytest.mark.parametrize("key", ["depth_key", "lat_key", "lon_key"])
def test_malformed_numeric_attributes_are_rejected(invalid, key):
    item = feature()
    item["attributes"][key] = invalid
    with pytest.raises(ValueError, match="finite number"):
        parse(item)


def test_negative_depth_is_rejected_but_zero_is_retained():
    """Boundary from FieldConcept.must_be_non_negative, models.py (repo contract)."""
    with pytest.raises(ValueError, match="non-negative"):
        parse(feature(depth="-1"))
    (well,) = parse(feature(depth="0"))
    assert well.water_depth_m == 0.0


@pytest.mark.parametrize(
    "key", ["well_key", "field_key", "depth_key", "lat_key", "lon_key"]
)
def test_missing_mapped_column_is_a_schema_error(key):
    item = feature()
    del item["attributes"][key]
    with pytest.raises(ValueError, match="mapped attribute"):
        parse(item)


@pytest.mark.parametrize("key", ["well_key", "field_key"])
@pytest.mark.parametrize("invalid", [None, "", " ", True, 1])
def test_missing_or_nontext_linkage_is_rejected(key, invalid):
    item = feature()
    item["attributes"][key] = invalid
    with pytest.raises(ValueError, match="non-empty text"):
        parse(item)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"error": {"message": "synthetic failure"}},
        {"features": [], "exceededTransferLimit": True},
        {"features": None},
        {"features": {}},
        {"features": [None]},
        {"features": [{"attributes": None}]},
        {"features": [], "exceededTransferLimit": "true"},
        None,
    ],
)
def test_error_partial_or_malformed_payload_is_rejected(payload):
    with pytest.raises(ValueError):
        parse_development_wells(payload, mapping=MAPPING, source=SOURCE)


def test_empty_complete_result_is_allowed():
    assert (
        parse_development_wells(
            {"features": [], "exceededTransferLimit": False},
            mapping=MAPPING,
            source=SOURCE,
        )
        == ()
    )


def test_duplicate_uwi_does_not_bias_median_or_count():
    """Unique depths [1, 3, 5] have middle 3; repeating the first row adds no well.

    Published example: Python statistics.median([1, 3, 5]) == 3,
    https://docs.python.org/3/library/statistics.html#statistics.median (2026).
    """
    first = feature(uwi="example-a", depth="1")
    wells = parse(
        first,
        first,
        feature(uwi="example-b", depth="3"),
        feature(uwi="example-c", depth="5"),
    )
    summary = summarize_field_wells("  EXAMPLE  ", iter(wells))
    assert summary.water_depth_m == 3.0
    assert summary.num_wells == 3
    assert summary.uwis == ("example-a", "example-b", "example-c")
    assert summary.sources == (SOURCE,)


@pytest.mark.parametrize(
    "change", [{"depth": "7"}, {"field": "Elsewhere"}, {"lat": "2"}]
)
def test_conflicting_duplicate_uwi_is_rejected(change):
    with pytest.raises(ValueError, match="Conflicting UWI"):
        parse(feature(), feature(**change))


def test_even_median_excludes_nulls_and_other_fields():
    """Hand calculation: linked depths [3, 7, null] => (3 + 7) / 2 = 5 m.

    Three linked UWIs are counted; the fourth belongs to a different field.
    Definition: Python statistics.median, 2026 documentation, middle-pair mean.
    """
    wells = parse(
        feature(uwi="example-a", depth="3"),
        feature(uwi="example-b", depth="7"),
        feature(uwi="example-c", depth=None),
        feature(uwi="example-d", field="Elsewhere", depth="1"),
    )
    summary = summarize_field_wells("Example", wells)
    assert summary.water_depth_m == 5.0
    assert summary.num_wells == 3


def test_no_matching_or_no_measured_depth_stays_unknown():
    wells = parse(feature(depth=None))
    assert summarize_field_wells("Example", wells).water_depth_m is None
    summary = summarize_field_wells("Elsewhere", wells)
    assert summary.water_depth_m is None
    assert summary.num_wells == 0
    assert summary.uwis == summary.sources == ()


def test_summary_also_deduplicates_combined_pages_and_is_deterministic():
    """Unique [3, 7] => (3 + 7) / 2 = 5; repeat a row from another page once."""
    first = parse(feature(uwi="example-b", depth="3"))
    second = parse(feature(uwi="example-a", depth="7"))
    forward = summarize_field_wells("Example", first + second + first)
    reverse = summarize_field_wells("Example", second + first)
    assert forward == reverse
    assert forward.num_wells == 2
    assert forward.water_depth_m == 5.0


def test_record_validation_applies_to_direct_construction():
    with pytest.raises(ValueError, match="finite number"):
        DevelopmentWell("example-a", "Example", float("nan"), None, None, SOURCE)
    with pytest.raises(ValueError, match="non-empty text"):
        parse_development_wells({"features": []}, mapping=MAPPING, source="")


def test_combined_pages_with_conflicting_uwi_are_rejected():
    first = parse(feature(depth="3"))
    second = parse(feature(depth="7"))
    with pytest.raises(ValueError, match="Conflicting UWI"):
        summarize_field_wells("Example", first + second)


def test_mapping_requires_nonempty_distinct_attribute_names():
    with pytest.raises(ValueError, match="non-empty text"):
        DevelopmentWellMapping("", "field", "depth", "lat", "lon")
    with pytest.raises(ValueError, match="distinct"):
        DevelopmentWellMapping("uwi", "field", "depth", "lat", "lat")
