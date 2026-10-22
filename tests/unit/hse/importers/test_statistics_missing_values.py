"""Synthetic parsing contracts for issue #1599.

Missing tokens are the explicit policy in #1599/#1308, using pandas 2.3:
https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.read_csv.html
https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.isna.html
All numbers below are synthetic place-value examples, not engineering limits.
"""

import csv
import importlib
from datetime import datetime
from unittest.mock import MagicMock

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
TEXT_FIELDS = (
    ("incident_id", "bsee_incident_id"),
    ("report_date", "report_date"),
    ("operator_name", "operator"),
    ("severity", "severity"),
    ("facility", "facility_name"),
    ("field", "field_name"),
)


@pytest.fixture(params=["worldenergydata.hse", "worldenergydata.modules.hse"])
def importer(request):
    module = importlib.import_module(
        request.param + ".importers.bsee_statistics_importer"
    )
    return module.BSEEStatisticsImporter(MagicMock())


def write_csv(importer, tmp_path, rows):
    path = tmp_path / "statistics.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    importer.csv_file_path = str(path)
    return [importer.normalize_data(row) for row in importer.fetch_data()]


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize("missing", ["NA", ""])
def test_csv_missing_counts_and_neighbors(importer, tmp_path, field, missing):
    """NA/blank have no value; 3.0 = 3 + 0/10 and 7 is an integer literal."""
    rows = [{field: missing}, {field: "3.0"}, {field: "7"}]
    result = write_csv(importer, tmp_path, rows)
    assert [row[field] for row in result] == [None, 3, 7]
    assert type(result[1][field]) is int
    assert type(result[2][field]) is int


@pytest.mark.parametrize("source,target", TEXT_FIELDS)
@pytest.mark.parametrize("missing", ["NA", ""])
def test_csv_missing_text(importer, tmp_path, source, target, missing):
    """Every mapped CSV null must be None before field guards run."""
    assert write_csv(importer, tmp_path, [{source: missing}])[0][target] is None


@pytest.mark.parametrize("required", ["operator_name", "report_date"])
@pytest.mark.parametrize("missing", ["NA", ""])
def test_missing_required_field_fails_validation(importer, tmp_path, required, missing):
    row = {"report_date": "2026-01-01", "operator_name": "Synthetic operator"}
    row[required] = missing
    normalized = write_csv(importer, tmp_path, [row])[0]
    assert importer.validate_data(normalized) is False
    assert any(
        "Missing required field" in error for error in importer.validation_errors
    )


@pytest.mark.parametrize("literal", ["N/A", "null", "NaN", "NULL", " NA ", "text"])
def test_other_csv_text_unchanged(importer, tmp_path, literal):
    result = write_csv(importer, tmp_path, [{"operator_name": literal}])
    assert result[0]["operator"] == literal


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize(
    "value,expected",
    [
        ("3.0", 3),
        (" +003.00 ", 3),
        ("-3.0", -3),
        ("9007199254740993.0", 9007199254740993),
        ("3.5", None),
        ("1e3", None),
        ("1e1000000", None),
        ("inf", None),
    ],
)
def test_direct_count_text(importer, field, value, expected):
    """Zero fractions add zero; 9007199254740993 is an exact integer literal.

    Signs negate or preserve the integer; 3.5 has nonzero tenths. Exponents
    and infinity are outside the grammar agreed in PRs #1395 and #1614.
    """
    assert importer.normalize_data({field: value})[field] == expected


@pytest.mark.parametrize("missing", [None, float("nan"), pd.NA, pd.NaT])
def test_direct_scalar_nulls_and_no_mutation(importer, missing):
    raw = {"operator_name": missing, "fatality_count": missing}
    result = importer.normalize_data(raw)
    assert result["operator"] is None
    assert result["fatality_count"] is None
    assert raw["operator_name"] is missing


def test_dictionary_literals_and_nonscalars_preserved(importer):
    """Dictionary callers already supply types; only actual nulls are replaced."""
    values = ["NA", "", ["NA"], {"key": "value"}]
    for value in values:
        assert importer.normalize_data({"operator_name": value})["operator"] == value
    # Synthetic numeric inputs retain legacy types; no range policy is added.
    for value in [3, 3.0, 3.5]:
        result = importer.normalize_data({"total_incidents": value})["total_incidents"]
        assert result is value


def test_identifier_and_date_preserved(importer, tmp_path):
    """Leading zeros identify text; ISO date components identify January first."""
    result = write_csv(
        importer,
        tmp_path,
        [
            {
                "incident_id": "0007",
                "report_date": "2026-01-01",
                "operator_name": "Synthetic operator",
                "total_incidents": "3",
            }
        ],
    )[0]
    assert result["bsee_incident_id"] == "0007"
    assert result["report_date"] == datetime(2026, 1, 1)
    assert importer.validate_data(result) is True


def test_compatibility_route_resolves_to_packaged_class():
    canonical = importlib.import_module(
        "worldenergydata.hse.importers.bsee_statistics_importer"
    )
    compatibility = importlib.import_module(
        "worldenergydata.modules.hse.importers.bsee_statistics_importer"
    )
    assert compatibility.BSEEStatisticsImporter is canonical.BSEEStatisticsImporter
    assert "packages/worldenergydata-bsee" in canonical.__file__


def test_documented_worked_example(importer, tmp_path):
    """Check the documentation's four independent hand-normalized records.

    NA/blank yield None; 3 and 3.0 both give integer 3 by 3 + 0/10 = 3.
    Only the second record lacks its required operator. ISO dates identify
    January first; no engineering coefficients are used.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    document = (root / "docs/hse/import-normalization.md").read_text()
    text = document.split("```csv\n", 1)[1].split("```", 1)[0]
    path = tmp_path / "worked.csv"
    path.write_text(text)
    importer.csv_file_path = str(path)
    results = [importer.normalize_data(row) for row in importer.fetch_data()]
    assert [row["bsee_incident_id"] for row in results] == [
        "sample-a",
        "sample-b",
        "sample-c",
        "sample-d",
    ]
    assert [row["operator"] for row in results] == [
        "Synthetic operator",
        None,
        "Synthetic operator",
        "Synthetic operator",
    ]
    assert [row["fatality_count"] for row in results] == [None, None, 3, 3]
    assert [row["facility_name"] for row in results] == [None, "text", "text", "N/A"]
    assert [importer.validate_data(row) for row in results] == [True, False, True, True]
    for row in results:
        assert row["report_date"] == row["incident_date"] == datetime(2026, 1, 1)
        assert row["field_name"] is None
        assert "severity" not in row
        assert all(
            row[field] is None for field in COUNT_FIELDS if field != "fatality_count"
        )
