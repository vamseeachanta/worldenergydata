"""Annual INC aggregation contract for issue 1683.

All dates, counts and identifying fields below are synthetic test inputs.
Expected totals are independently hand-calculated in the summation test.
"""

import csv
import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import MappingProxyType

import pandas as pd
import pytest

from worldenergydata.hse.enforcement import annual_inc_counts


@pytest.fixture
def normalized_rows():
    """Supply category counts across two nonconsecutive calendar years."""
    return [
        {
            "incident_date": datetime(2021, 1, 1),
            "violation_type": "warning",
            "inc_count": 2,
        },
        {
            "incident_date": datetime(2021, 12, 31),
            "violation_type": "warning",
            "inc_count": 5,
        },
        {
            "incident_date": datetime(2021, 3, 1),
            "violation_type": "comp_shutin",
            "inc_count": 3,
        },
        {
            "incident_date": datetime(2021, 4, 1),
            "violation_type": "comp_shutin",
            "inc_count": 4,
        },
        {
            "incident_date": datetime(2021, 5, 1),
            "violation_type": "fac_shutin",
            "inc_count": 6,
        },
        {
            "incident_date": datetime(2023, 1, 1),
            "violation_type": "warning",
            "inc_count": 11,
        },
        {
            "incident_date": datetime(2023, 12, 31),
            "violation_type": "warning",
            "inc_count": 2,
        },
        {
            "incident_date": datetime(2023, 3, 1),
            "violation_type": "comp_shutin",
            "inc_count": 4,
        },
        {
            "incident_date": datetime(2023, 4, 1),
            "violation_type": "fac_shutin",
            "inc_count": 8,
        },
        {
            "incident_date": datetime(2023, 5, 1),
            "violation_type": "fac_shutin",
            "inc_count": 1,
        },
    ]


@pytest.fixture
def expected_counts():
    """Use the independent arithmetic recorded in the summation test."""
    return [
        {"year": 2021, "action": "comp_shutin", "count": 7, "unit": "INCs"},
        {"year": 2021, "action": "fac_shutin", "count": 6, "unit": "INCs"},
        {"year": 2021, "action": "warning", "count": 7, "unit": "INCs"},
        {"year": 2023, "action": "comp_shutin", "count": 4, "unit": "INCs"},
        {"year": 2023, "action": "fac_shutin", "count": 9, "unit": "INCs"},
        {"year": 2023, "action": "warning", "count": 13, "unit": "INCs"},
    ]


def test_annual_inc_counts_sum_category_counts(normalized_rows, expected_counts):
    """Hand calculation: 2021 warning=2+5=7, comp=3+4=7, fac=6.

    For 2023 warning=11+2=13, comp=4, fac=8+1=9.
    Year totals are 7+7+6=20 and 13+4+9=26, hence 46 INCs overall.
    Ten category records therefore represent 46 INCs, not ten INCs.
    """
    result = annual_inc_counts(normalized_rows)
    assert result == expected_counts
    assert sum(row["count"] for row in result) == 46
    assert all(type(row["count"]) is int for row in result)


def test_annual_inc_counts_publish_only_aggregate_fields(normalized_rows):
    """An explicit field allowlist excludes every source identifier and text."""
    private_fields = {
        "operator": "withheld-operator",
        "operator_code": "withheld-code",
        "bsee_incident_id": "withheld-incident",
        "inc_number": "withheld-number",
        "description": "withheld-description",
        "unrecognized_extra": {"nested": "withheld-nested"},
    }
    for row in normalized_rows:
        row.update(private_fields)
    result = annual_inc_counts(normalized_rows)
    assert result
    assert all(set(row) == {"year", "action", "count", "unit"} for row in result)
    assert "withheld" not in json.dumps(result)


def test_annual_inc_counts_preserve_inputs(normalized_rows):
    before = deepcopy(normalized_rows)
    result = annual_inc_counts(normalized_rows)
    assert normalized_rows == before
    result.clear()
    assert normalized_rows == before
    assert annual_inc_counts(map(MappingProxyType, normalized_rows))


def test_annual_inc_counts_ignore_input_order(normalized_rows, expected_counts):
    assert annual_inc_counts(reversed(normalized_rows)) == expected_counts
    assert annual_inc_counts(iter(normalized_rows)) == expected_counts
    assert (
        annual_inc_counts(normalized_rows[5:] + normalized_rows[:5]) == expected_counts
    )


def test_annual_inc_counts_empty_input():
    assert annual_inc_counts([]) == []
    assert annual_inc_counts(iter(())) == []


def test_annual_inc_counts_preserve_explicit_zero_without_filling_coverage():
    """Zero is an explicit synthetic observation; absent pairs stay absent."""
    rows = [
        {"incident_date": date(2021, 1, 1), "violation_type": "warning", "inc_count": 0}
    ]
    assert annual_inc_counts(rows) == [
        {"year": 2021, "action": "warning", "count": 0, "unit": "INCs"}
    ]


def test_annual_inc_counts_use_incident_calendar_year():
    """A synthetic date near New Year retains its supplied calendar year."""
    rows = [
        {
            "incident_date": date(2021, 12, 31),
            "violation_type": "warning",
            "inc_count": 1,
        },
        {
            "incident_date": datetime(2023, 1, 1, tzinfo=timezone(timedelta(hours=14))),
            "violation_type": "warning",
            "inc_count": 1,
        },
    ]
    assert annual_inc_counts(rows) == [
        {"year": 2021, "action": "warning", "count": 1, "unit": "INCs"},
        {"year": 2023, "action": "warning", "count": 1, "unit": "INCs"},
    ]


@pytest.mark.parametrize("field", ["incident_date", "violation_type", "inc_count"])
def test_annual_inc_counts_reject_missing_fields(field, normalized_rows):
    row = normalized_rows[0].copy()
    del row[field]
    with pytest.raises(ValueError, match=field):
        annual_inc_counts([row])


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "not-a-date",
        "2021-02-29",
        "2021-01-01",
        2021,
        True,
        float("nan"),
        pd.NaT,
        [],
    ],
)
def test_annual_inc_counts_reject_invalid_dates(value, normalized_rows):
    row = {**normalized_rows[0], "incident_date": value}
    with pytest.raises(ValueError, match="incident_date"):
        annual_inc_counts([row])


@pytest.mark.parametrize(
    "value", [None, "", "other", "WARNING", " warning", 1, True, [], {}]
)
def test_annual_inc_counts_reject_invalid_actions(value, normalized_rows):
    row = {**normalized_rows[0], "violation_type": value}
    with pytest.raises(ValueError, match="violation_type"):
        annual_inc_counts([row])


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        -1,
        1.5,
        2.0,
        float("nan"),
        float("inf"),
        -float("inf"),
        "2",
        "",
        Decimal("2"),
        [],
        {},
    ],
)
def test_annual_inc_counts_reject_invalid_counts(value, normalized_rows):
    row = {**normalized_rows[0], "inc_count": value}
    with pytest.raises(ValueError, match="inc_count"):
        annual_inc_counts([row])


@pytest.mark.parametrize("row", [None, [], "", "warning", 1, True])
def test_annual_inc_counts_reject_non_mapping_rows(row):
    with pytest.raises(ValueError, match="mapping"):
        annual_inc_counts([row])


@pytest.mark.parametrize("rows", [None, 1, True, "", b"", {}, {"inc_count": 1}])
def test_annual_inc_counts_reject_invalid_input_container(rows):
    with pytest.raises(TypeError):
        annual_inc_counts(rows)


def test_annual_inc_counts_preserve_large_integer_counts(normalized_rows):
    """Hand calculation: two synthetic counts of 10**100 sum to 2*10**100."""
    rows = [{**normalized_rows[0], "inc_count": 10**100}] * 2
    assert annual_inc_counts(rows) == [
        {"year": 2021, "action": "warning", "count": 2 * 10**100, "unit": "INCs"}
    ]


def test_annual_inc_counts_reject_late_invalid_row(normalized_rows):
    """An invalid observation cannot become a silently truncated aggregate."""
    before = deepcopy(normalized_rows)
    with pytest.raises(ValueError, match="inc_count"):
        annual_inc_counts([*normalized_rows, {**normalized_rows[0], "inc_count": -1}])
    assert normalized_rows == before


def test_annual_inc_counts_exact_json_csv_roundtrips(
    normalized_rows, expected_counts, tmp_path
):
    result = annual_inc_counts(normalized_rows)
    json_path = tmp_path / "annual.json"
    with json_path.open("w", encoding="utf-8") as stream:
        json.dump(result, stream, allow_nan=False)
    with json_path.open(encoding="utf-8") as stream:
        assert json.load(stream) == expected_counts

    csv_path = tmp_path / "annual.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["year", "action", "count", "unit"])
        writer.writeheader()
        writer.writerows(result)
    with csv_path.open(encoding="utf-8", newline="") as stream:
        restored = [
            {**row, "year": int(row["year"]), "count": int(row["count"])}
            for row in csv.DictReader(stream)
        ]
    assert restored == expected_counts
