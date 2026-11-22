"""Synthetic contract inputs; numerical expectations are hand counts below."""

from datetime import date

import pytest

from worldenergydata.fdas.adapters.wells import WellRecord


def well(**changes):
    """Synthetic well, with a caller-selected depth of 100 m."""
    values = {
        "country": "AU",
        "source": "example",
        "well_id": "1",
        "development": "Example",
        "spud_date": date(2024, 1, 30),
        "water_depth_m": 100.0,
    }
    return WellRecord(**(values | changes))


def test_nullable_metadata_preserves_missing_and_zero():
    assert well(spud_date=None, water_depth_m=None).water_depth_m is None
    assert well(water_depth_m=0).water_depth_m == 0


@pytest.mark.parametrize("field", ["country", "source", "well_id", "development"])
@pytest.mark.parametrize("value", ["", " ", None, 12])
def test_identity_required(field, value):
    with pytest.raises(ValueError):
        well(**{field: value})


@pytest.mark.parametrize("depth", [-1, float("nan"), float("inf"), True, "100"])
def test_invalid_depth(depth):
    with pytest.raises(ValueError):
        well(water_depth_m=depth)


def test_spud_is_calendar_date():
    with pytest.raises(ValueError):
        well(spud_date="2024-01-30")
