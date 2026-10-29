"""Synthetic missingness regressions for the packaged importer (issue #1599).

All dates and counts are synthetic inputs. Independent arithmetic supplies the
expectations: 3.0 has integer value 3; 3.5 lies between 3 and 4; a separate 7
stays 7. Zero is the nonnegative boundary and -1 is below it. No source data or
empirical statistics are used. NA is the declared CSV missing token here.
"""

import csv
from datetime import datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

COUNT_FIELDS = (
    "operational_period",
    "total_incidents",
    "fatality_count",
    "lost_time_count",
    "recordable_count",
    "near_miss_count",
    "minor_count",
)
OPTIONAL_FIELDS = {
    "incident_id": "bsee_incident_id",
    "severity": "severity",
    "facility": "facility_name",
    "field": "field_name",
    **{field: field for field in COUNT_FIELDS},
}
MISSING = [None, float("nan"), pd.NA]


def valid_record():
    return {"report_date": "2024-03-31", "operator_name": "  synthetic operator  "}


def write_csv(tmp_path, records):
    path = tmp_path / "statistics.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return path


def assert_unchanged(record, original):
    assert record.keys() == original.keys()
    for key in record:
        # Identity also checks NaN and pd.NA without ambiguous equality.
        assert record[key] is original[key]


@pytest.fixture(params=["canonical", "compatibility"])
def importer(request):
    prefix = (
        "worldenergydata.hse"
        if request.param == "canonical"
        else "worldenergydata.modules.hse"
    )
    module = import_module(f"{prefix}.importers.bsee_statistics_importer")
    root = Path(__file__).resolve().parents[4]
    assert Path(module.__file__).resolve() == (
        root
        / "packages/worldenergydata-bsee/src/worldenergydata/hse/importers"
        / "bsee_statistics_importer.py"
    )
    session = MagicMock()
    instance = module.BSEEStatisticsImporter(session)
    yield instance
    assert session.mock_calls == []


@pytest.mark.parametrize("token", ["", "NA"], ids=["empty-cell", "declared-na"])
def test_csv_missing_tokens_normalize_to_none(importer, tmp_path, token):
    record = {**valid_record(), **dict.fromkeys(OPTIONAL_FIELDS, token)}
    importer.csv_file_path = str(write_csv(tmp_path, [record]))
    (fetched,) = importer.fetch_data()
    original = fetched.copy()
    normalized = importer.normalize_data(fetched)
    for field in OPTIONAL_FIELDS.values():
        assert normalized[field] is None
    assert normalized["operator"] == "  synthetic operator  "
    assert importer.validate_data(normalized) is True
    assert_unchanged(fetched, original)


@pytest.mark.parametrize("missing", MISSING, ids=["none", "nan", "pandas-na"])
def test_direct_dictionary_scalar_nulls(importer, missing):
    record = {**valid_record(), **dict.fromkeys(OPTIONAL_FIELDS, missing)}
    original = record.copy()
    normalized = importer.normalize_data(record)
    for field in OPTIONAL_FIELDS.values():
        assert normalized[field] is None
    assert normalized["operator"] == "  synthetic operator  "
    assert importer.validate_data(normalized) is True
    assert_unchanged(record, original)


@pytest.mark.parametrize(
    "field, mapped", [("operator_name", "operator"), ("report_date", "report_date")]
)
@pytest.mark.parametrize("missing", MISSING, ids=["none", "nan", "pandas-na"])
def test_required_missing_field_is_invalid(importer, field, mapped, missing):
    record = {**valid_record(), field: missing}
    original = record.copy()
    normalized = importer.normalize_data(record)
    assert normalized[mapped] is None
    assert importer.validate_data(normalized) is False
    assert f"Missing required field: {mapped}" in importer.validation_errors
    assert_unchanged(record, original)


@pytest.mark.parametrize("field", ["operator_name", "report_date"])
@pytest.mark.parametrize("token", ["", "NA"], ids=["empty-cell", "declared-na"])
def test_required_csv_missing_field_is_invalid(importer, tmp_path, field, token):
    importer.csv_file_path = str(
        write_csv(tmp_path, [{**valid_record(), field: token}])
    )
    (fetched,) = importer.fetch_data()
    assert importer.validate_data(importer.normalize_data(fetched)) is False
    mapped = "operator" if field == "operator_name" else field
    assert f"Missing required field: {mapped}" in importer.validation_errors


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize(
    "value, expected, valid",
    [
        ("3.0", 3, True),
        ("3", 3, True),
        (3, 3, True),
        (3.0, 3, True),
        (Decimal("3.0"), 3, True),
        (np.int64(3), 3, True),
        (0, 0, True),
        ("3.5", None, False),
        (3.5, None, False),
        (-1, None, False),
        ("-1", None, False),
        (True, None, False),
        (False, None, False),
        (np.bool_(True), None, False),
        (float("inf"), None, False),
        (float("-inf"), None, False),
        ("Infinity", None, False),
        ("NaN", None, False),
        ("invalid", None, False),
    ],
)
def test_integral_count_policy(importer, field, value, expected, valid):
    record = {**valid_record(), field: value}
    original = record.copy()
    normalized = importer.normalize_data(record)
    assert importer.validate_data(normalized) is valid
    if valid:
        assert normalized[field] == expected
        assert type(normalized[field]) is int
    else:
        assert any(field in error for error in importer.validation_errors)
    assert_unchanged(record, original)


def test_neighboring_values_are_preserved(importer, tmp_path):
    records = [
        {
            **valid_record(),
            "total_incidents": "3.0",
            "minor_count": "7",
            "facility": "  synthetic facility  ",
        },
        {
            **valid_record(),
            "total_incidents": "3.5",
            "minor_count": "7",
            "facility": "001",
        },
    ]
    importer.csv_file_path = str(write_csv(tmp_path, records))
    integral, fractional = map(importer.normalize_data, importer.fetch_data())
    assert integral["total_incidents"] == 3
    assert integral["minor_count"] == 7
    assert integral["facility_name"] == "  synthetic facility  "
    assert integral["report_date"] == datetime(2024, 3, 31)
    assert importer.validate_data(integral) is True
    assert fractional["minor_count"] == 7
    assert fractional["facility_name"] == "001"
    assert importer.validate_data(fractional) is False
    assert any("total_incidents" in error for error in importer.validation_errors)


def test_compatibility_import_has_same_missingness(importer):
    canonical = import_module("worldenergydata.hse.importers.bsee_statistics_importer")
    compatibility = import_module(
        "worldenergydata.modules.hse.importers.bsee_statistics_importer"
    )
    assert compatibility.BSEEStatisticsImporter is canonical.BSEEStatisticsImporter
    record = {
        **valid_record(),
        "operator_name": pd.NA,
        "total_incidents": pd.NA,
        "minor_count": "7",
    }
    original = record.copy()
    normalized = importer.normalize_data(record)
    assert normalized["operator"] is None
    assert normalized["total_incidents"] is None
    assert normalized["minor_count"] == 7
    assert importer.validate_data(normalized) is False
    assert "Missing required field: operator" in importer.validation_errors
    assert_unchanged(record, original)
