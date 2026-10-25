"""Synthetic preflight examples; no production code set or date range is implied.

All dates, identifiers and code tokens below are arbitrary fixture inputs.
Expected counts are independent hand calculations documented beside each case.
"""

import copy
import csv
import json
from datetime import date, datetime

import pytest

from worldenergydata.hse.importers.input_quality import (
    export_input_quality,
    summarize_input_quality,
)


@pytest.fixture
def options():
    """Explicit caller policy for an arbitrary synthetic calendar year."""
    return {
        "fields": {
            "key": "record_key",
            "date": "occurred",
            "code": "category",
            "source_row_id": "source_id",
        },
        "date_window": (date(2024, 1, 1), date(2024, 12, 31)),
        "date_format": "%Y-%m-%d",
        "allowed_codes": {"synthetic_allowed"},
        "rules": {
            "duplicate_key": "flagged",
            "missing_key": "dropped",
            "invalid_date": "dropped",
            "out_of_window_date": "flagged",
            "unknown_code": "kept",
            "reversed_interval": "flagged",
        },
    }


@pytest.fixture
def records():
    """Hand tally: duplicates a/b/f; missing c/d; invalid dates b/f;
    outside window c/d; unknown codes b/c/f. Row e is clean.
    The boundary dates on a/e are inside the supplied inclusive window.
    """
    return [
        dict(
            source_id="a",
            record_key="repeat",
            occurred="2024-01-01",
            category="synthetic_allowed",
        ),
        dict(
            source_id="b",
            record_key="repeat",
            occurred="unparseable",
            category="synthetic_unlisted",
        ),
        dict(
            source_id="c",
            record_key="",
            occurred="2023-12-31",
            category="synthetic_unlisted",
        ),
        dict(source_id="d", occurred="2025-01-01", category="synthetic_allowed"),
        dict(
            source_id="e",
            record_key="unique",
            occurred="2024-12-31",
            category="synthetic_allowed",
        ),
        dict(
            source_id="f",
            record_key="repeat",
            occurred="2024-02-30",
            category="synthetic_unlisted",
        ),
    ]


@pytest.fixture
def expected_table():
    """Independent table from the record membership tally above.

    Totals overlap: a row can contribute to several defects. These are not
    mutually exclusive row dispositions, and rules do not remove input rows.
    """
    return [
        {
            "defect": "duplicate_key",
            "count": 3,
            "example_source_row_id": "a",
            "rule": "flagged",
        },
        {
            "defect": "invalid_date",
            "count": 2,
            "example_source_row_id": "b",
            "rule": "dropped",
        },
        {
            "defect": "missing_key",
            "count": 2,
            "example_source_row_id": "c",
            "rule": "dropped",
        },
        {
            "defect": "out_of_window_date",
            "count": 2,
            "example_source_row_id": "c",
            "rule": "flagged",
        },
        {
            "defect": "unknown_code",
            "count": 3,
            "example_source_row_id": "b",
            "rule": "kept",
        },
    ]


def test_quality_table_has_exact_counts_examples_and_rules(
    records, options, expected_table
):
    original = copy.deepcopy(records)
    assert summarize_input_quality(records, **options) == expected_table
    assert records == original
    # Reordering and one-pass iterables must preserve the independent table.
    assert summarize_input_quality(iter(reversed(records)), **options) == expected_table


def test_unruled_defect_blocks_export(tmp_path, records, options):
    del options["rules"]["unknown_code"]
    destination = tmp_path / "unruled"
    with pytest.raises(ValueError, match="unknown_code"):
        export_input_quality(records, destination, **options)
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_quality_csv_json_match(tmp_path, records, options, expected_table):
    original = copy.deepcopy(records)
    destination = tmp_path / "quality"
    csv_path, json_path = export_input_quality(records, destination, **options)
    assert csv_path.parent == json_path.parent == destination
    assert {path.name for path in destination.iterdir()} == {
        "input_quality.csv",
        "input_quality.json",
    }
    with csv_path.open(encoding="utf-8", newline="") as stream:
        csv_table = list(csv.DictReader(stream))
    for row in csv_table:
        row["count"] = int(row["count"])
    assert csv_table == json.loads(json_path.read_text(encoding="utf-8"))
    assert csv_table == expected_table
    assert records == original
    before = (csv_path.read_bytes(), json_path.read_bytes())
    export_input_quality(reversed(records), destination, **options)
    assert before == (csv_path.read_bytes(), json_path.read_bytes())


@pytest.mark.parametrize(
    "rule_change",
    [
        {"unknown_defect": "flagged"},
        {"unknown_code": "drop"},
        {"unknown_code": None},
    ],
)
def test_unknown_defect_or_invalid_rule_blocks_export(
    tmp_path, records, options, rule_change
):
    options["rules"].update(rule_change)
    with pytest.raises(ValueError):
        export_input_quality(records, tmp_path / "invalid", **options)
    assert list(tmp_path.iterdir()) == []


def test_failed_export_preserves_existing_files(tmp_path, records, options):
    csv_path, json_path = export_input_quality(records, tmp_path, **options)
    before = (csv_path.read_bytes(), json_path.read_bytes())
    del options["rules"]["invalid_date"]
    with pytest.raises(ValueError):
        export_input_quality(records, tmp_path, **options)
    assert before == (csv_path.read_bytes(), json_path.read_bytes())


def test_interval_check_requires_explicit_fields(options):
    row = dict(
        source_id="interval",
        record_key="unique",
        occurred="2024-06-01",
        category="synthetic_allowed",
        opened="2024-06-02",
        closed="2024-06-01",
    )
    assert summarize_input_quality([row], **options) == []
    options["fields"].update(interval_start="opened", interval_end="closed")
    # Only this row has a reversed interval: one occurrence.
    assert summarize_input_quality([row], **options) == [
        {
            "defect": "reversed_interval",
            "count": 1,
            "example_source_row_id": "interval",
            "rule": "flagged",
        }
    ]
    options["rules"].pop("reversed_interval")
    with pytest.raises(ValueError, match="reversed_interval"):
        summarize_input_quality([row], **options)


@pytest.mark.parametrize("role", ["interval_start", "interval_end"])
def test_partial_interval_mapping_is_rejected(options, role):
    options["fields"][role] = "endpoint"
    with pytest.raises(ValueError, match="both interval"):
        summarize_input_quality([], **options)


def test_multiple_bad_dates_count_once_per_defect_per_record(options):
    options["fields"].update(interval_start="opened", interval_end="closed")
    rows = [
        dict(
            source_id="dates",
            record_key="unique",
            occurred="bad",
            opened="also bad",
            closed="2025-01-01",
            category="synthetic_allowed",
        )
    ]
    # The same row has two invalid dates and one outside date: one per defect.
    assert summarize_input_quality(rows, **options) == [
        {
            "defect": "invalid_date",
            "count": 1,
            "example_source_row_id": "dates",
            "rule": "dropped",
        },
        {
            "defect": "out_of_window_date",
            "count": 1,
            "example_source_row_id": "dates",
            "rule": "flagged",
        },
    ]


def test_empty_and_clean_inputs_export_empty_table(tmp_path, options):
    assert summarize_input_quality([], **options) == []
    csv_path, json_path = export_input_quality([], tmp_path, **options)
    assert json.loads(json_path.read_text()) == []
    with csv_path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["defect", "count", "example_source_row_id", "rule"]
        assert list(reader) == []


@pytest.mark.parametrize("value", [None, "", "   ", float("nan")])
def test_missing_key_values_are_not_duplicate_keys(options, value):
    row = dict(
        source_id="blank",
        record_key=value,
        occurred="2024-06-01",
        category="synthetic_allowed",
    )
    # Repeated missing keys are two missing occurrences, never duplicates.
    assert summarize_input_quality([row, row], **options) == [
        {
            "defect": "missing_key",
            "count": 2,
            "example_source_row_id": "blank",
            "rule": "dropped",
        }
    ]


@pytest.mark.parametrize("value", [None, "", "   ", float("nan"), []])
def test_missing_or_nontext_codes_are_unknown(options, value):
    row = dict(
        source_id="code", record_key="unique", occurred="2024-06-01", category=value
    )
    assert summarize_input_quality([row], **options) == [
        {
            "defect": "unknown_code",
            "count": 1,
            "example_source_row_id": "code",
            "rule": "kept",
        }
    ]


@pytest.mark.parametrize("value", [None, "", "   ", float("nan"), []])
def test_missing_or_invalid_date_is_detected(options, value):
    row = dict(
        source_id="date",
        record_key="unique",
        occurred=value,
        category="synthetic_allowed",
    )
    assert summarize_input_quality([row], **options) == [
        {
            "defect": "invalid_date",
            "count": 1,
            "example_source_row_id": "date",
            "rule": "dropped",
        }
    ]


@pytest.mark.parametrize("value", [date(2024, 6, 1), datetime(2024, 6, 1)])
def test_calendar_date_objects_are_supported(options, value):
    row = dict(
        source_id="date",
        record_key="unique",
        occurred=value,
        category="synthetic_allowed",
    )
    assert summarize_input_quality([row], **options) == []


def test_caller_date_format_and_field_mapping_are_used(options):
    options["fields"] = dict(key="id", date="when", code="kind", source_row_id="row")
    options["date_format"] = "%m/%d/%Y"
    # Zero is an explicit valid identity, not a missing key or source id.
    row = {"row": 0, "id": 0, "when": "06/01/2024", "kind": "synthetic_allowed"}
    assert summarize_input_quality([row], **options) == []
    row["kind"] = "SYNTHETIC_ALLOWED"
    assert summarize_input_quality([row], **options) == [
        {
            "defect": "unknown_code",
            "count": 1,
            "example_source_row_id": "0",
            "rule": "kept",
        }
    ]


@pytest.mark.parametrize("value", [None, "", " ", [], True])
def test_source_row_identity_is_required_before_export(tmp_path, options, value):
    row = dict(
        source_id=value,
        record_key="unique",
        occurred="2024-06-01",
        category="synthetic_allowed",
    )
    with pytest.raises(ValueError, match="source_row_id"):
        export_input_quality([row], tmp_path / "bad-id", **options)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "mutation",
    [
        {"fields": {"key": "id"}},
        {"date_window": (date(2024, 12, 31), date(2024, 1, 1))},
        {"allowed_codes": "synthetic_allowed"},
        {"allowed_codes": {None}},
        {"date_format": ""},
    ],
)
def test_invalid_configuration_fails_even_without_records(options, mutation):
    options.update(mutation)
    with pytest.raises(ValueError):
        summarize_input_quality([], **options)


@pytest.mark.parametrize(
    "defect",
    [
        "duplicate_key",
        "missing_key",
        "invalid_date",
        "out_of_window_date",
        "unknown_code",
    ],
)
def test_each_observed_defect_requires_a_rule(tmp_path, records, options, defect):
    del options["rules"][defect]
    with pytest.raises(ValueError, match=defect):
        export_input_quality(records, tmp_path / "blocked", **options)
    assert list(tmp_path.iterdir()) == []


def test_multiple_duplicate_groups_count_all_members(options):
    # Two pairs give four affected records; the singleton and missing keys
    # are excluded. Example 'a' belongs to the second pair in source order.
    rows = [
        dict(
            source_id=source,
            record_key=key,
            occurred="2024-06-01",
            category="synthetic_allowed",
        )
        for source, key in [
            ("z", 0),
            ("y", 0),
            ("b", "0"),
            ("a", "0"),
            ("single", "unique"),
        ]
    ]
    assert summarize_input_quality(rows, **options) == [
        {
            "defect": "duplicate_key",
            "count": 4,
            "example_source_row_id": "a",
            "rule": "flagged",
        }
    ]


@pytest.mark.parametrize("key", [[], {}, True])
def test_unsupported_key_types_block_export(tmp_path, options, key):
    row = dict(
        source_id="unsupported",
        record_key=key,
        occurred="2024-06-01",
        category="synthetic_allowed",
    )
    with pytest.raises(ValueError, match="key"):
        export_input_quality([row], tmp_path / "blocked", **options)
    assert list(tmp_path.iterdir()) == []


def test_equal_interval_endpoints_are_not_reversed(options):
    options["fields"].update(interval_start="opened", interval_end="closed")
    row = dict(
        source_id="equal",
        record_key="unique",
        occurred="2024-06-01",
        opened="2024-06-01",
        closed="2024-06-01",
        category="synthetic_allowed",
    )
    assert summarize_input_quality([row], **options) == []


def test_source_identifier_survives_csv_and_json_escaping(tmp_path, options):
    row = dict(
        source_id='synthetic,"row"\nα',
        record_key=None,
        occurred="2024-06-01",
        category="synthetic_allowed",
    )
    csv_path, json_path = export_input_quality([row], tmp_path, **options)
    with csv_path.open(encoding="utf-8", newline="") as stream:
        csv_table = list(csv.DictReader(stream))
    json_table = json.loads(json_path.read_text(encoding="utf-8"))
    assert csv_table[0]["example_source_row_id"] == row["source_id"]
    assert json_table[0]["example_source_row_id"] == row["source_id"]


def test_clean_records_need_no_rules(options):
    options["rules"] = {}
    row = dict(
        source_id="clean",
        record_key="unique",
        occurred="2024-06-01",
        category="synthetic_allowed",
    )
    assert summarize_input_quality([row], **options) == []
