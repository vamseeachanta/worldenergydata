"""Offline documented-source schema and lease-attribution checks."""

import csv
import io
from pathlib import Path

import pytest

from worldenergydata.bsee.borehole_status import aggregate_status, load_boreholes
from worldenergydata.common.fields_registry import FieldsRegistry, load_fields

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "tests/fixtures/bsee/borehole_status/5010_sample.txt"


def changed_row(index, value):
    row = next(csv.reader(io.StringIO(FIXTURE.read_text())))
    row[index] = value
    stream = io.StringIO()
    csv.writer(stream).writerow(row)
    stream.seek(0)
    return stream


def test_source_schema_and_leading_zero_api():
    rows = load_boreholes(io.StringIO(FIXTURE.read_text()))
    assert len(rows) == 5
    assert rows[-1]["API Well Number"].startswith("0")
    assert rows[0]["Bottom Lease Number"] == "G16942"
    assert rows[0]["Status Code"] == "COM"


@pytest.mark.parametrize(
    "index,value", [(0, "608123"), (15, "20261340"), (19, "NaN"), (7, "deep")]
)
def test_malformed_values_rejected(index, value):
    with pytest.raises(ValueError):
        load_boreholes(changed_row(index, value))


def test_wrong_width_and_duplicate_api_rejected():
    with pytest.raises(ValueError, match="29"):
        load_boreholes(io.StringIO('"123","TA"\n'))
    line = FIXTURE.read_text().splitlines()[0]
    with pytest.raises(ValueError, match="Duplicate API"):
        load_boreholes(io.StringIO(line + "\n" + line + "\n"))


def test_join_counts_unmatched_and_empty_fields():
    rows = load_boreholes(io.StringIO(FIXTURE.read_text()))
    result = aggregate_status(rows, load_fields(FIXTURE.parent / "registry.yml"))
    assert result["joined_boreholes"] == 4
    fields = {f["field_id"]: f for f in result["fields"]}
    assert fields["big_foot"]["status_counts"] == {"COM": 1, "ST": 1}
    assert fields["anchor"]["status_counts"] == {"COM": 1}
    assert fields["buckskin"]["status_counts"] == {"PA": 1}
    assert fields["julia"]["availability"] == "no_boreholes_on_registered_leases"
    assert fields["julia"]["borehole_count"] == 0
    assert result["unmatched"][0]["reason"] == "lease_not_in_registry"
    assert result["source_boreholes"] == result["joined_boreholes"] + len(
        result["unmatched"]
    )


def test_variant_bottom_lease_no_surface_fallback_and_unknown_status():
    rows = load_boreholes(io.StringIO(FIXTURE.read_text()))[:3]
    rows[0]["Bottom Lease Number"] = "OCS-G 16942"
    rows[0]["Status Code"] = "NEW"
    rows[1]["Bottom Lease Number"] = ""
    rows[1]["Surface Lease Number"] = "G16942"
    rows[2]["Status Code"] = ""
    result = aggregate_status(rows, load_fields(FIXTURE.parent / "registry.yml"))
    assert result["joined_boreholes"] == 2
    assert result["unmatched"][0]["reason"] == "missing_bottom_lease"
    assert result["attributed"][0]["status_meaning"] == "undocumented_status_code"
    assert result["attributed"][1]["status_meaning"] == "missing_status_code"


def test_non_lower_tertiary_is_explicit():
    registry = load_fields(FIXTURE.parent / "registry.yml")
    from dataclasses import replace

    registry = FieldsRegistry([replace(registry.fields[0], play="Miocene")])
    rows = load_boreholes(io.StringIO(FIXTURE.read_text()))[:1]
    result = aggregate_status(rows, registry)
    assert result["unmatched"][0]["reason"] == "field_outside_lower_tertiary"
    assert result["fields"] == []


def test_recorded_source_numeric_masks_remain_explicit():
    masked = FIXTURE.parent / "5010_masked.txt"
    rows = load_boreholes(io.StringIO(masked.read_text()))
    assert rows[0]["BH Total MD"] == "#####"
    assert rows[0]["Bottom Latitude"] == "################"
    result = aggregate_status(rows, load_fields(FIXTURE.parent / "registry.yml"))
    assert result["masked_numeric_cells"] == {
        "BH Total MD": 1,
        "True Vertical Depth": 1,
        "Bottom Longitude": 1,
        "Bottom Latitude": 1,
    }


def test_non_default_play_filter():
    rows = load_boreholes(io.StringIO(FIXTURE.read_text()))[:1]
    rows[0]["Bottom Lease Number"] = "G11111"
    result = aggregate_status(
        rows, load_fields(FIXTURE.parent / "registry.yml"), play_filter="miocene"
    )
    assert result["joined_boreholes"] == 1
    assert result["fields"][0]["field_id"] == "other"
    assert result["play_filter"] == "miocene"
