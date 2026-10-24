"""Offline synthetic cases; no regulator well records are embedded.

Expected medians follow Python 3.11 Library Reference, statistics.median
(retrieved 2026): https://docs.python.org/3.11/library/statistics.html#statistics.median.
The hand calculations below are independent of the implementation.
"""

import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

from worldenergydata.canada.development_wells import (
    DevelopmentWell,
    development_wells_manifest,
    summarize_water_depth,
)


def well(uwi="synthetic-a", depth=20.0, **changes):
    """Synthetic input, with depth in metres and an arbitrary named datum."""
    values = {
        "uwi": uwi,
        "field_name": "synthetic-field",
        "water_depth_m": depth,
        "depth_unit": "m",
        "depth_datum": "synthetic-datum",
        "source": "synthetic:offline",
    }
    values.update(changes)
    return DevelopmentWell(**values)


def test_nullable_record_is_immutable():
    record = well(depth=None)
    assert record.water_depth_m is None
    with pytest.raises(FrozenInstanceError):
        record.water_depth_m = 12.0


@pytest.mark.parametrize("depth", [-1.0, float("nan"), float("inf"), True, "20"])
def test_invalid_depth_rejected(depth):
    """Nonnegative criterion: FieldConcept.must_be_non_negative; finite input only."""
    with pytest.raises(ValueError, match="depth"):
        well(depth=depth)


@pytest.mark.parametrize("depth", [10**400, -(10**400)], ids=["positive", "negative"])
def test_out_of_range_integer_depth_rejected(depth):
    with pytest.raises(ValueError, match="depth"):
        well(depth=depth)


@pytest.mark.parametrize("key", ["uwi", "field_name", "depth_datum", "source"])
@pytest.mark.parametrize("value", ["", " ", None, 12, " untrimmed "])
def test_required_identifiers(key, value):
    with pytest.raises(ValueError, match=key):
        well(**{key: value})


@pytest.mark.parametrize("unit", [None, "", "ft", "metres"])
def test_units_are_required_and_never_inferred(unit):
    with pytest.raises(ValueError, match="unit"):
        well(depth_unit=unit)


@pytest.mark.parametrize(
    ("depths", "expected"),
    [([30.0, 10.0, 20.0], 20.0), ([40.0, 10.0, 20.0, 30.0], 25.0)],
)
def test_odd_and_even_medians(depths, expected):
    """Sort 10,20,30 -> 20; sort 10,20,30,40 -> (20+30)/2 = 25 m."""
    records = [well(f"synthetic-{index}", depth) for index, depth in enumerate(depths)]
    result = summarize_water_depth("synthetic-field", records)
    assert result.water_depth_m == expected
    assert result.depth_datum == "synthetic-datum"
    assert result.contributing_uwis == tuple(sorted(record.uwi for record in records))
    assert result.sources == ("synthetic:offline",)


def test_nulls_and_other_fields_are_excluded_but_zero_is_retained():
    """Linked depths are None, 0, 20; median(0,20) = (0+20)/2 = 10 m."""
    result = summarize_water_depth(
        "synthetic-field",
        [
            well("synthetic-null", None),
            well("synthetic-zero", 0.0),
            well("synthetic-positive", 20.0),
            well("synthetic-other", 999.0, field_name="another-synthetic-field"),
        ],
    )
    assert result.water_depth_m == 10.0
    assert result.linked_well_count == 3
    assert result.contributing_uwis == ("synthetic-positive", "synthetic-zero")


@pytest.mark.parametrize("records", [[], [well(depth=None)]])
def test_missing_depth_is_not_a_measurement(records):
    result = summarize_water_depth("synthetic-field", records)
    assert result.water_depth_m is None
    assert result.depth_datum is None
    assert result.contributing_uwis == ()
    assert result.sources == ()


def test_no_fuzzy_linkage():
    assert summarize_water_depth("Synthetic-field", [well()]).water_depth_m is None


@pytest.mark.parametrize("field_name", ["", None, " untrimmed "])
def test_summary_requires_explicit_field_name(field_name):
    with pytest.raises(ValueError, match="field_name"):
        summarize_water_depth(field_name, [])


@pytest.mark.parametrize("other_field", ["synthetic-field", "another-synthetic-field"])
def test_duplicate_identifiers_refused(other_field):
    with pytest.raises(ValueError, match="duplicate"):
        summarize_water_depth("synthetic-field", [well(), well(field_name=other_field)])


def test_incompatible_datums_refused():
    with pytest.raises(ValueError, match="datum"):
        summarize_water_depth(
            "synthetic-field",
            [well(), well("synthetic-b", depth_datum="another-synthetic-datum")],
        )


def test_null_or_unlinked_datum_does_not_change_median_basis():
    """Only one contributor at 20 m, so the median is 20 m."""
    result = summarize_water_depth(
        "synthetic-field",
        [well(), well("synthetic-null", None, depth_datum="another-synthetic-datum")],
    )
    assert result.water_depth_m == 20.0


def test_manifest_has_independent_canonical_digest_and_no_payload():
    """Hash independently specified canonical JSON; there is no physical constant."""
    records = [well("synthetic-b", None), well()]
    expected_rows = [
        {
            "uwi": "synthetic-a",
            "field_name": "synthetic-field",
            "water_depth_m": 20.0,
            "depth_unit": "m",
            "depth_datum": "synthetic-datum",
            "source": "synthetic:offline",
        },
        {
            "uwi": "synthetic-b",
            "field_name": "synthetic-field",
            "water_depth_m": None,
            "depth_unit": "m",
            "depth_datum": "synthetic-datum",
            "source": "synthetic:offline",
        },
    ]
    canonical = json.dumps(
        expected_rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    manifest = development_wells_manifest(records)
    assert manifest == {
        "schema_version": "1",
        "record_count": 2,
        "depth_unit": "m",
        "sources": ["synthetic:offline"],
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }
    assert development_wells_manifest(reversed(records)) == manifest
    assert development_wells_manifest([well(depth=21.0)]) != manifest


def test_integer_and_float_depths_have_identical_manifest():
    assert development_wells_manifest([well(depth=20)]) == development_wells_manifest(
        [well(depth=20.0)]
    )


def test_manifest_refuses_duplicate_identifiers():
    with pytest.raises(ValueError, match="duplicate"):
        development_wells_manifest([well(), well()])


def test_median_is_independent_of_decimal_context():
    """Synthetic 11 and 12 m -> (11+12)/2 = 11.5 m at any ambient precision."""
    from decimal import localcontext

    with localcontext() as context:
        context.prec = 1
        result = summarize_water_depth(
            "synthetic-field", [well(depth=11.0), well("synthetic-b", 12.0)]
        )
    assert result.water_depth_m == 11.5


def test_large_finite_depths_do_not_overflow_median():
    """For equal finite x from float_info, the hand median is (x+x)/2 = x."""
    import sys

    depth = sys.float_info.max
    result = summarize_water_depth(
        "synthetic-field", [well(depth=depth), well("synthetic-b", depth)]
    )
    assert result.water_depth_m == depth


@pytest.mark.parametrize(
    "changes",
    [
        {"uwi": "synthetic-new"},
        {"field_name": "another-synthetic-field"},
        {"source": "synthetic:changed"},
        {"depth_datum": "another-synthetic-datum"},
        {"water_depth_m": None},
    ],
)
def test_manifest_digest_binds_linkage_nulls_and_basis(changes):
    from dataclasses import replace

    record = well()
    assert (
        development_wells_manifest([record])["sha256"]
        != development_wells_manifest([replace(record, **changes)])["sha256"]
    )


def test_raw_dict_is_not_a_normalized_record():
    with pytest.raises(TypeError, match="normalized"):
        summarize_water_depth("synthetic-field", [{"WaterDepth": 20.0}])
