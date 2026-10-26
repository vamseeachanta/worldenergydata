"""Independent literal-row checks for the diagnostic contract in issue #1681.

All dates, codes and keys below are synthetic. Counts and shares are hand
calculations from the literal rows, never reference outputs from the module.
"""

import csv
import io
import json

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_quality_table import (
    quality_to_csv,
    quality_to_json,
    summarize_quality,
)

COLUMNS = [
    "year",
    "defect_type",
    "count",
    "example_id",
    "applied_rule",
    "affected_share",
]
INPUT_COLUMNS = [
    "API_WELL_NUMBER",
    "WAR_START_DT",
    "WAR_END_DT",
    "WELL_ACTIVITY_CD",
]
KNOWN_CODES = {"DRL", "COM"}


@pytest.fixture
def literal_rows():
    # Issue #1681 acceptance example: four rows in one year. Row A is
    # reversed; rows B and C lack keys; row D has an unknown activity.
    return pd.DataFrame(
        [
            ["key-a", "2024-01-07", "2024-01-01", "DRL"],
            [None, "2024-02-01", "2024-02-07", "COM"],
            ["  ", "2024-03-01", "2024-03-07", "DRL"],
            ["key-d", "2024-04-01", "2024-04-07", "UNLISTED"],
        ],
        columns=INPUT_COLUMNS,
        index=["source-a", "source-b", "source-c", "source-d"],
    )


def test_quality_counts_and_shares_match_literal_rows(literal_rows):
    table = summarize_quality(literal_rows, KNOWN_CODES)
    assert list(table.columns) == COLUMNS
    assert table["year"].tolist() == [2024, 2024, 2024]
    assert str(table["year"].dtype) == "Int64"
    findings = table.set_index("defect_type")
    # Hand calculation: two missing keys / four rows; one reversed / four;
    # one unknown activity / four. The three findings are independent.
    assert findings["count"].to_dict() == {
        "missing_well_key": 2,
        "reversed_dates": 1,
        "unknown_activity_code": 1,
    }
    assert findings["affected_share"].to_dict() == {
        "missing_well_key": 0.5,
        "reversed_dates": 0.25,
        "unknown_activity_code": 0.25,
    }
    assert table["applied_rule"].tolist() == ["flagged"] * 3


def test_overlapping_defects_keep_row_denominator():
    frame = pd.DataFrame(
        [
            [None, "2024-01-07", "2024-01-01", "UNLISTED"],
            ["", "2024-02-07", "2024-02-01", "UNLISTED"],
            ["key-c", "2024-03-01", "2024-03-07", "DRL"],
            ["key-d", "2024-04-01", "2024-04-07", "COM"],
        ],
        columns=INPUT_COLUMNS,
        # Duplicate source labels must not collapse distinct input rows.
        index=["duplicate"] * 4,
    )
    table = summarize_quality(frame, KNOWN_CODES)
    # Each of three defects affects the first two of four rows: 2 / 4.
    # Summing defects gives six, which is deliberately NOT the denominator.
    assert table["count"].tolist() == [2, 2, 2]
    assert table["affected_share"].tolist() == [0.5, 0.5, 0.5]
    assert table["example_id"].nunique() == 1


def test_unknown_years_are_explicit_and_have_their_own_denominator():
    frame = pd.DataFrame(
        [
            [None, None, "2025-01-07", "DRL"],
            ["key-b", "unparseable", "2025-02-07", "UNLISTED"],
            ["key-c", "2023-01-01", None, "UNLISTED"],
        ],
        columns=INPUT_COLUMNS,
    )
    table = summarize_quality(frame, KNOWN_CODES)
    # Unknown start years stay unknown even when the end has a usable year.
    # Known group: one unknown code / one row. Unknown group: each defect
    # affects one of two rows. Invalid bounds never count as reversed.
    assert table["defect_type"].tolist() == [
        "unknown_activity_code",
        "missing_well_key",
        "unknown_activity_code",
    ]
    assert table["year"].iloc[0] == 2023
    assert table["year"].iloc[1:].isna().all()
    assert table["count"].tolist() == [1, 1, 1]
    assert table["affected_share"].tolist() == [1.0, 0.5, 0.5]


def test_each_year_uses_all_its_rows():
    frame = pd.DataFrame(
        [
            [None, "2023-01-01", "2023-01-07", "DRL"],
            [None, "2024-01-01", "2024-01-07", "DRL"],
            ["key-c", "2024-02-01", "2024-02-07", "COM"],
        ],
        columns=INPUT_COLUMNS,
    )
    table = summarize_quality(frame, KNOWN_CODES)
    # Hand calculation: missing keys are 1 / 1 in 2023 and 1 / 2 in 2024.
    assert table["year"].tolist() == [2023, 2024]
    assert table["affected_share"].tolist() == [1.0, 0.5]


@pytest.mark.parametrize("missing_key", [None, pd.NA, float("nan"), "", " \t"])
def test_missing_key_representations(missing_key):
    frame = pd.DataFrame(
        [[missing_key, "2024-01-01", "2024-01-07", "DRL"]],
        columns=INPUT_COLUMNS,
    )
    # One missing key in a one-row group: 1 / 1.
    row = summarize_quality(frame, KNOWN_CODES).squeeze()
    assert row["defect_type"] == "missing_well_key"
    assert row["count"] == 1
    assert row["affected_share"] == 1.0


def test_caller_vocabulary_is_normalized_without_inferred_meanings():
    frame = pd.DataFrame(
        [
            ["key-a", "2024-01-01", "2024-01-07", " drl "],
            ["key-b", "2024-02-01", "2024-02-07", "custom"],
            ["key-c", "2024-03-01", "2024-03-07", None],
            ["key-d", "2024-04-01", "2024-04-07", " "],
        ],
        columns=INPUT_COLUMNS,
    )
    # Blank/missing activity has no vocabulary member; two of four rows.
    vocabulary = {"DRL", " CUSTOM "}
    row = summarize_quality(frame, vocabulary).squeeze()
    assert row["defect_type"] == "unknown_activity_code"
    assert row["count"] == 2
    assert row["affected_share"] == 0.5
    assert vocabulary == {"DRL", " CUSTOM "}


def test_empty_vocabulary_flags_every_activity(literal_rows):
    table = summarize_quality(literal_rows, set()).set_index("defect_type")
    # An empty vocabulary admits none of the four literal activity values.
    assert table.loc["unknown_activity_code", "count"] == 4
    assert table.loc["unknown_activity_code", "affected_share"] == 1.0


def test_only_valid_reversed_dates_are_flagged():
    frame = pd.DataFrame(
        [
            ["key-a", "2024-01-07", "2024-01-01", "DRL"],
            ["key-b", "2024-02-01", "invalid", "DRL"],
            ["key-c", "invalid", "2024-03-01", "DRL"],
            ["key-d", "2024-04-01", "2024-04-01", "DRL"],
        ],
        columns=INPUT_COLUMNS,
    )
    table = summarize_quality(frame, KNOWN_CODES)
    # Only row A is reversed. Rows A, B and D have known start years: 1 / 3.
    assert table["defect_type"].tolist() == ["reversed_dates"]
    assert table["count"].tolist() == [1]
    assert table["affected_share"].tolist() == [1 / 3]


@pytest.mark.parametrize(
    "invalid_date",
    [
        "now",
        "today",
        " NoW\t",
        " TODAY ",
        "12:30",
        " 12:30:45 ",
        "12:30+05:00",
        "12:30 AM",
        "January 7",
        "2024-01",
        "2024",
        "01/2024",
        "01/07/24",
        "240107",
    ],
)
@pytest.mark.parametrize("bound", ["start", "end"])
def test_dates_without_explicit_calendar_components_are_invalid(invalid_date, bound):
    start, end = (
        (invalid_date, "2000-01-01")
        if bound == "start"
        else ("2099-01-01", invalid_date)
    )
    frame = pd.DataFrame([[None, start, end, "DRL"]], columns=INPUT_COLUMNS)
    table = summarize_quality(frame, KNOWN_CODES)
    # One missing key / one row; an invalid bound never counts as reversed.
    assert table["defect_type"].tolist() == ["missing_well_key"]
    assert table["count"].tolist() == [1]
    assert table["affected_share"].tolist() == [1.0]
    if bound == "start":
        assert table["year"].isna().all()
    else:
        assert table["year"].tolist() == [2099]


@pytest.mark.parametrize(
    "start,end,year",
    [
        ("2024-01-07", "2024-01-01", 2024),
        ("01/07/2024", "01/01/2024", 2024),
        ("January 7, 2024", "January 1, 2024", 2024),
        ("7 Jan 2024", "1 Jan 2024", 2024),
        ("2024-Jan-07", "2024-Jan-01", 2024),
        ("20240107", "20240101", 2024),
        (20240107, 20240101, 2024),
        (20240107.0, 20240101.0, 2024),
        ("2024-01-07 12:30:00", "2024-01-01 12:30:00", 2024),
        (pd.Timestamp("2024-01-07"), pd.Timestamp("2024-01-01"), 2024),
        ("2024-01-01T00:30:00+01:00", "2023-12-31T22:30:00Z", 2023),
    ],
)
def test_explicit_calendar_dates_preserve_reversal_and_utc_year(start, end, year):
    frame = pd.DataFrame([["key-a", start, end, "DRL"]], columns=INPUT_COLUMNS)
    table = summarize_quality(frame, KNOWN_CODES)
    # One reversed row / one row, including a UTC start in the previous year.
    assert table["defect_type"].tolist() == ["reversed_dates"]
    assert table["year"].tolist() == [year]
    assert table["count"].tolist() == [1]
    assert table["affected_share"].tolist() == [1.0]


def test_numeric_dates_are_calendar_dates_not_epoch_offsets():
    frame = pd.DataFrame(
        [
            ["key-a", 20240107, 20240101, "DRL"],
            ["key-b", None, 20240207, "DRL"],
        ],
        columns=INPUT_COLUMNS,
    )
    table = summarize_quality(frame, KNOWN_CODES)
    # Integer dates widen to floats beside nulls. Only row A is reversed,
    # and it is the sole row in the known-year denominator: 1 / 1.
    assert table["year"].tolist() == [2024]
    assert table["count"].tolist() == [1]
    assert table["affected_share"].tolist() == [1.0]


def test_exact_duplicate_rows_are_counted_as_separate_records(literal_rows):
    missing_rows = literal_rows.loc[["source-b", "source-b"]]
    table = summarize_quality(missing_rows, KNOWN_CODES)
    # Two physical rows both lack a key, even with identical content: 2 / 2.
    assert table["count"].tolist() == [2]
    assert table["affected_share"].tolist() == [1.0]


def test_examples_and_serialization_are_stable_under_permutation(literal_rows):
    before = literal_rows.copy(deep=True)
    expected = summarize_quality(literal_rows, KNOWN_CODES)
    # Reverse source order, replace index, and reverse the vocabulary order.
    shuffled = literal_rows.iloc[::-1].reset_index(drop=True)
    actual = summarize_quality(shuffled, ["COM", "DRL"])
    pd.testing.assert_frame_equal(actual, expected)
    assert quality_to_csv(actual) == quality_to_csv(expected)
    assert quality_to_json(actual) == quality_to_json(expected)
    pd.testing.assert_frame_equal(literal_rows, before)
    assert expected["example_id"].str.fullmatch(r"record-\d+").all()
    rendered = quality_to_csv(expected) + quality_to_json(expected)
    for label in [*literal_rows.index, "key-a", "key-d", "UNLISTED"]:
        assert label not in rendered


def test_example_labels_ignore_identifiers_and_unrelated_columns(literal_rows):
    before = summarize_quality(literal_rows, KNOWN_CODES)
    altered = literal_rows.copy(deep=True)
    altered.loc["source-a", "API_WELL_NUMBER"] = "replacement-key"
    altered["SN_WAR"] = ["external-a", "external-b", "external-c", "external-d"]
    pd.testing.assert_frame_equal(summarize_quality(altered, KNOWN_CODES), before)


def test_csv_and_json_preserve_values_and_nullable_years(literal_rows):
    frame = literal_rows.copy(deep=True)
    frame.loc["source-b", "WAR_START_DT"] = None
    table = summarize_quality(frame, KNOWN_CODES)
    before = table.copy(deep=True)
    csv_rows = list(csv.DictReader(io.StringIO(quality_to_csv(table))))
    json_rows = json.loads(quality_to_json(table))
    assert list(csv_rows[0]) == COLUMNS
    decoded = [
        {
            **row,
            "year": int(row["year"]) if row["year"] else None,
            "count": int(row["count"]),
            "affected_share": float(row["affected_share"]),
        }
        for row in csv_rows
    ]
    assert decoded == json_rows
    assert any(row["year"] is None for row in json_rows)
    assert all(type(row["count"]) is int for row in json_rows)
    assert all(row["applied_rule"] == "flagged" for row in json_rows)
    # Hand calculation: rows A, C and D remain in the known year, with one
    # row per defect (1 / 3). Row B is the sole unknown-year missing key.
    assert [
        (row["year"], row["defect_type"], row["count"], row["affected_share"])
        for row in json_rows
    ] == [
        (2024, "missing_well_key", 1, 1 / 3),
        (2024, "reversed_dates", 1, 1 / 3),
        (2024, "unknown_activity_code", 1, 1 / 3),
        (None, "missing_well_key", 1, 1.0),
    ]
    pd.testing.assert_frame_equal(table, before)


@pytest.mark.parametrize("valid_rows", [False, True])
def test_empty_or_defect_free_input_has_schema_and_serializes(valid_rows):
    frame = pd.DataFrame(
        [["key-a", "2024-01-01", "2024-01-07", "DRL"]] if valid_rows else [],
        columns=INPUT_COLUMNS,
    )
    table = summarize_quality(frame, KNOWN_CODES)
    assert table.empty
    assert list(table.columns) == COLUMNS
    assert str(table["year"].dtype) == "Int64"
    assert quality_to_json(table) == "[]"
    assert quality_to_csv(table) == ",".join(COLUMNS) + "\n"


@pytest.mark.parametrize("column", INPUT_COLUMNS)
def test_missing_columns_have_an_explicit_error(literal_rows, column):
    with pytest.raises(ValueError, match=column):
        summarize_quality(literal_rows.drop(columns=column), KNOWN_CODES)
