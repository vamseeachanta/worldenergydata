"""Independent calendar counts, not milestone-derived drilling estimates."""

from datetime import date

import pytest

from worldenergydata.fdas.adapters.wells import WellRecord
from worldenergydata.fdas.data.country_drilling import (
    DrillingActivity,
    build_drilling_timeline,
)


def well(identifier="1", development="Example", **changes):
    return WellRecord(
        "AU",
        "synthetic",
        identifier,
        development,
        changes.get("spud_date", date(2023, 1, 1)),
        None,
    )


def activity(start, end, identifier="1", **changes):
    return DrillingActivity(
        "AU",
        "synthetic",
        identifier,
        date.fromisoformat(start),
        date.fromisoformat(end),
        changes.get("evidence", "urn:synthetic:activity"),
    )


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ("2024-01-30", "2024-02-03", {"2024-01": 2, "2024-02": 2}),
        ("2024-02-28", "2024-03-02", {"2024-02": 2, "2024-03": 1}),
        ("2023-12-31", "2024-01-02", {"2023-12": 1, "2024-01": 1}),
    ],
)
def test_calendar_split(start, end, expected):
    """Exclusive end: Jan 30+31 / Feb 1+2; Feb 28+29 / Mar 1;
    Dec 31 / Jan 1. Each listed day counts once by hand enumeration.
    """
    result = build_drilling_timeline(
        [well()], [activity(start, end)], development="Example"
    )
    assert result.status == "EVALUATED"
    assert result.as_cashflow_input() == {"drilling_monthly": expected}


def test_concurrent_wells_add_and_adjacent_intervals_do_not_overlap():
    """Well 1: Jan 1 and Jan 2; well 2: Jan 1. Total = 2 + 1 = 3 days."""
    result = build_drilling_timeline(
        [well(), well("2")],
        [
            activity("2024-01-01", "2024-01-02"),
            activity("2024-01-02", "2024-01-03"),
            activity("2024-01-01", "2024-01-02", "2"),
        ],
        development="Example",
    )
    assert result.drilling_monthly == {"2024-01": 3}


def test_partial_coverage_cannot_be_exported_as_zero_capex():
    result = build_drilling_timeline(
        [well(), well("2")],
        [activity("2024-01-01", "2024-01-02")],
        development="Example",
    )
    assert result.status == "NOT_EVALUATED"
    assert result.drilling_monthly is None
    assert result.missing_wells == (("AU", "synthetic", "2"),)
    with pytest.raises(ValueError, match="NOT_EVALUATED"):
        result.as_cashflow_input()


def test_spud_only_has_no_drilling_duration():
    result = build_drilling_timeline([well()], [], development="Example")
    assert result.status == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "activities",
    [
        [activity("2024-01-01", "2024-01-03"), activity("2024-01-02", "2024-01-04")],
        [activity("2024-01-01", "2024-01-02", "unknown")],
        [activity("2022-01-01", "2022-01-02")],
    ],
)
def test_inconsistent_activity_rejected(activities):
    with pytest.raises(ValueError):
        build_drilling_timeline([well()], activities, development="Example")


@pytest.mark.parametrize(
    "start,end,evidence",
    [
        ("2024-01-02", "2024-01-01", "source"),
        ("2024-01-01", "2024-01-01", "source"),
        ("2024-01-01", "2024-01-02", ""),
    ],
)
def test_invalid_activity(start, end, evidence):
    with pytest.raises(ValueError):
        activity(start, end, evidence=evidence)


def test_duplicate_wells_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        build_drilling_timeline([well(), well()], [], development="Example")


def test_unknown_spud_blocks_activity():
    with pytest.raises(ValueError, match="spud"):
        build_drilling_timeline(
            [well(spud_date=None)],
            [activity("2024-01-01", "2024-01-02")],
            development="Example",
        )


def test_development_selection_is_explicit():
    result = build_drilling_timeline(
        [well(), well("2", "Other")],
        [activity("2024-01-01", "2024-01-02")],
        development="Example",
    )
    assert result.status == "EVALUATED"
    with pytest.raises(ValueError, match="development"):
        build_drilling_timeline([well()], [], development="Unknown")


def test_calendar_domain_endpoints():
    """Year 9999 Dec 30 is one day; year 1 Jan 1 is one day.

    Both cases are synthetic calendar boundary probes with exclusive ends.
    """
    for start, end, month in [
        (date(9999, 12, 30), date(9999, 12, 31), "9999-12"),
        (date(1, 1, 1), date(1, 1, 2), "0001-01"),
    ]:
        row = well(spud_date=start)
        interval = DrillingActivity(*row.key, start, end, "urn:synthetic:boundary")
        result = build_drilling_timeline([row], [interval], development="Example")
        assert result.drilling_monthly == {month: 1}


def test_country_and_source_namespace_prevent_collisions():
    """Two different country/source keys each supply Jan 1: 1 + 1 = 2 days."""
    a = well()
    b = WellRecord("NO", "another-source", a.well_id, a.development, a.spud_date, None)
    intervals = [
        DrillingActivity(
            *row.key, date(2024, 1, 1), date(2024, 1, 2), "urn:synthetic:namespace"
        )
        for row in (a, b)
    ]
    result = build_drilling_timeline([a, b], intervals, development="Example")
    assert result.drilling_monthly == {"2024-01": 2}
