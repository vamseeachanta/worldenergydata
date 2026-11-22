# ABOUTME: Annual incident-count tests using an independently hand-tabulated fixture.
# ABOUTME: Keeps unknown years and person counts distinct from measured incidents.

"""All dates and counts below are synthetic, not public incident measurements.

Hand calculation for the fixture (one incident per distinct id):
    2023: injury = a + c = 2; spill = b = 1; annual total = 3.
    2024: equipment_failure = f = 1; injury = e = 1; spill = d = 1;
          annual total = 3. Overall total = 6.
Coverage is deliberately declared as 2023-04-01 through 2024-09-30 inclusive,
so both observed calendar years have partial coverage. Other test dates are
explicit synthetic calendar-boundary and invalid-input cases.
"""

from copy import deepcopy
from datetime import date, datetime

import pytest

from worldenergydata.hse.annual_statistics import build_annual_statistics


@pytest.fixture
def incidents():
    """Shuffled rows make sorting independent of the supplied record order."""
    return [
        {"incident_id": "d", "incident_date": "2024-01-01", "incident_type": "spill"},
        {"incident_id": "c", "incident_date": "2023-12-31", "incident_type": "injury"},
        {
            "incident_id": "f",
            "incident_date": "2024-09-30",
            "incident_type": "equipment_failure",
        },
        {"incident_id": "a", "incident_date": "2023-04-01", "incident_type": "injury"},
        {"incident_id": "e", "incident_date": "2024-06-15", "incident_type": "injury"},
        {"incident_id": "b", "incident_date": "2023-08-10", "incident_type": "spill"},
    ]


@pytest.fixture
def source_metadata():
    return {"source": "synthetic fixture", "provenance": {"basis": "hand calculation"}}


def build(incidents, source_metadata, **coverage):
    return build_annual_statistics(
        incidents,
        coverage_start=coverage.get("coverage_start", "2023-04-01"),
        coverage_end=coverage.get("coverage_end", "2024-09-30"),
        source_metadata=source_metadata,
    )


def test_annual_type_counts_match_hand_table(incidents, source_metadata):
    result = build(iter(incidents), source_metadata)

    assert [
        (row.year, row.incident_type, row.count, row.unit) for row in result.rows
    ] == [
        (2023, "injury", 2, "incidents"),
        (2023, "spill", 1, "incidents"),
        (2024, "equipment_failure", 1, "incidents"),
        (2024, "injury", 1, "incidents"),
        (2024, "spill", 1, "incidents"),
    ]
    assert sum(row.count for row in result.rows) == 6 == len(incidents)
    assert result.status == "observed_incidents"


def test_boundary_years_are_flagged(incidents, source_metadata):
    result = build(incidents, source_metadata)

    assert result.coverage_start == date(2023, 4, 1)
    assert result.coverage_end == date(2024, 9, 30)
    assert [
        (row.year, row.coverage_start, row.coverage_end, row.partial_coverage)
        for row in result.rows
    ] == [
        (2023, date(2023, 4, 1), date(2023, 12, 31), True),
        (2023, date(2023, 4, 1), date(2023, 12, 31), True),
        (2024, date(2024, 1, 1), date(2024, 9, 30), True),
        (2024, date(2024, 1, 1), date(2024, 9, 30), True),
        (2024, date(2024, 1, 1), date(2024, 9, 30), True),
    ]


def test_complete_calendar_years_are_not_flagged(incidents, source_metadata):
    result = build(
        incidents,
        source_metadata,
        coverage_start=date(2023, 1, 1),
        coverage_end=date(2024, 12, 31),
    )

    assert [row.partial_coverage for row in result.rows] == [False] * 5
    assert result.rows[0].coverage_start == date(2023, 1, 1)
    assert result.rows[-1].coverage_end == date(2024, 12, 31)


def test_single_day_coverage_is_partial(source_metadata):
    result = build(
        [{"incident_id": "a", "incident_date": "2024-02-29", "incident_type": "spill"}],
        source_metadata,
        coverage_start="2024-02-29",
        coverage_end="2024-02-29",
    )

    assert result.rows[0].count == 1  # One supplied id, counted by hand.
    assert result.rows[0].partial_coverage is True
    assert (
        result.rows[0].coverage_start
        == result.rows[0].coverage_end
        == date(2024, 2, 29)
    )


def test_metadata_and_inputs_are_preserved(incidents, source_metadata):
    original = deepcopy(incidents)
    result = build(incidents, source_metadata)

    assert incidents == original
    assert result.source_metadata == source_metadata
    source_metadata["provenance"]["basis"] = "changed after build"
    assert result.source_metadata == {
        "source": "synthetic fixture",
        "provenance": {"basis": "hand calculation"},
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("incident_id", None, "incident_id"),
        ("incident_id", "", "incident_id"),
        ("incident_id", "  ", "incident_id"),
        ("incident_id", [], "incident_id"),
        ("incident_id", "a", "duplicate incident_id"),
        ("incident_date", None, "incident_date"),
        ("incident_date", "", "incident_date"),
        ("incident_date", "invalid", "incident_date"),
        ("incident_date", "2024-02-30", "incident_date"),
        ("incident_date", float("nan"), "incident_date"),
        ("incident_date", "2023-03-31", "outside declared coverage"),
        ("incident_date", "2024-10-01", "outside declared coverage"),
        ("incident_type", None, "incident_type"),
        ("incident_type", "", "incident_type"),
        ("incident_type", "\t ", "incident_type"),
        ("incident_type", float("nan"), "incident_type"),
    ],
)
def test_duplicate_or_invalid_incidents_are_rejected(
    incidents, source_metadata, field, value, message
):
    # Put the bad record last: no partial result may escape after valid records.
    incidents[-1][field] = value
    with pytest.raises(ValueError, match=message):
        build(incidents, source_metadata)


@pytest.mark.parametrize("field", ["incident_id", "incident_date", "incident_type"])
def test_missing_fields_are_rejected(incidents, source_metadata, field):
    del incidents[-1][field]
    with pytest.raises(ValueError, match=field):
        build(incidents, source_metadata)


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (None, "2024-09-30", "coverage_start"),
        ("2023-04-01", None, "coverage_end"),
        ("invalid", "2024-09-30", "coverage_start"),
        ("2023-04-01", "2024-02-30", "coverage_end"),
        ("2024-09-30", "2023-04-01", "coverage_start.*coverage_end"),
    ],
)
def test_invalid_coverage_is_rejected_even_for_empty_input(
    source_metadata, start, end, message
):
    with pytest.raises(ValueError, match=message):
        build([], source_metadata, coverage_start=start, coverage_end=end)


def test_empty_series_remains_empty(source_metadata):
    result = build([], source_metadata)

    assert result.rows == ()
    assert result.status == "empty_input"
    assert result.coverage_start == date(2023, 4, 1)
    assert result.coverage_end == date(2024, 9, 30)
    assert result.source_metadata == source_metadata
    # Declared coverage alone does not prove zero incidents in any year or type.


def test_unobserved_years_and_types_are_not_filled(incidents, source_metadata):
    # Remove the later year's records; retain declared coverage beyond both years.
    result = build(
        [row for row in incidents if row["incident_id"] in {"a", "b", "c"}],
        source_metadata,
        coverage_start="2022-01-01",
        coverage_end="2025-12-31",
    )

    assert [(row.year, row.incident_type, row.count) for row in result.rows] == [
        (2023, "injury", 2),
        (2023, "spill", 1),
    ]
    assert [row.partial_coverage for row in result.rows] == [False, False]


@pytest.mark.parametrize(
    "incident_date",
    [date(2024, 1, 1), datetime(2024, 1, 1, 12), "2024-01-01 12:00:00"],
)
def test_date_and_importer_datetime_inputs(source_metadata, incident_date):
    result = build(
        [
            {
                "incident_id": "a",
                "incident_date": incident_date,
                "incident_type": "spill",
            }
        ],
        source_metadata,
    )
    assert [(row.year, row.count) for row in result.rows] == [(2024, 1)]


def test_severity_does_not_change_incident_counts(incidents, source_metadata):
    expected = build(incidents, source_metadata)
    for row in incidents:
        row["severity"] = "fatality"
    assert build(incidents, source_metadata) == expected
