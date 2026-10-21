"""Exercise the physical legacy file, rather than its redirected replacement.

Missing-token expectations follow issue #1308. pandas 2.3 ``read_csv`` documents
explicit ``na_values``, ``keep_default_na`` and string dtype semantics:
https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.read_csv.html
Scalar missingness follows pandas 2.3 ``isna``:
https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.isna.html
These are parsing examples; no engineering coefficients or limits apply.
"""

import csv
import importlib.util
from datetime import datetime
from pathlib import Path
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
    ("report_date", "incident_date"),
    ("operator_name", "operator"),
    ("severity", "severity"),
    ("facility", "facility_name"),
    ("field", "field_name"),
)


@pytest.fixture
def importer():
    """Load the changed source explicitly; retain its real base-class dependency."""
    root = Path(__file__).resolve().parents[4]
    source = (
        root / "src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py"
    )
    spec = importlib.util.spec_from_file_location(
        "legacy_statistics_under_test", source
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == source
    return module.BSEEStatisticsImporter(MagicMock())


def write_csv(tmp_path, rows):
    """Write literal inputs independently of pandas' own CSV formatting."""
    csv_path = tmp_path / "statistics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(csv_path)


@pytest.mark.parametrize("token", ["NA", ""])
@pytest.mark.parametrize("field", COUNT_FIELDS)
def test_csv_missing_counts_and_integer_neighbors(importer, tmp_path, field, token):
    """Hand calculation: decimal '0' = 0 and '1' = 1; missing is not zero.

    The integer literals are synthetic parsing inputs, not measured counts.
    A missing row between them must not promote either result to float.
    """
    importer.csv_file_path = write_csv(
        tmp_path,
        [
            {"incident_id": "first", field: "0"},
            {"incident_id": "missing", field: token},
            {"incident_id": "last", field: "1"},
        ],
    )
    first, missing, last = map(importer.normalize_data, importer.fetch_data())

    assert missing[field] is None
    assert first[field] == 0
    assert type(first[field]) is int
    assert last[field] == 1
    assert type(last[field]) is int


@pytest.mark.parametrize("token", ["NA", ""])
@pytest.mark.parametrize("source,target", TEXT_FIELDS)
def test_csv_missing_text_and_dates(importer, tmp_path, source, target, token):
    """Issue #1308's missing token maps to None, including required fields."""
    importer.csv_file_path = write_csv(tmp_path, [{"other": "keep-row", source: token}])
    (raw,) = importer.fetch_data()

    assert importer.normalize_data(raw)[target] is None


@pytest.mark.parametrize("token", ["NA", ""])
@pytest.mark.parametrize(
    "field", ["incident_id", "report_date", "operator_name", "severity"]
)
def test_csv_missing_required_field_is_rejected(importer, tmp_path, field, token):
    """The real base validator requires each of these fields, not a NaN sentinel."""
    row = {
        "incident_id": "synthetic-record",
        "report_date": "2024-01-01",
        "operator_name": "synthetic-operator",
        "severity": "minor",
    }
    row[field] = token
    importer.csv_file_path = write_csv(tmp_path, [row])
    (raw,) = importer.fetch_data()

    assert importer.validate_data(importer.normalize_data(raw)) is False
    assert any(
        "Missing required field:" in error for error in importer.validation_errors
    )


@pytest.mark.parametrize("missing", [float("nan"), pd.NA, pd.NaT, None])
def test_normalize_missing_scalars_without_mutating_input(importer, missing):
    """pandas' documented scalar nulls become None before any field guard."""
    raw = {field: missing for field in COUNT_FIELDS}
    raw.update({source: missing for source, _ in TEXT_FIELDS})

    normalized = importer.normalize_data(raw)

    for field in COUNT_FIELDS:
        assert normalized[field] is None
    for _, target in TEXT_FIELDS:
        assert normalized[target] is None
    assert all(value is missing for value in raw.values())


@pytest.mark.parametrize("token", ["NULL", "N/A", "NaN", "None", "null"])
def test_csv_preserves_text_outside_explicit_missing_tokens(importer, tmp_path, token):
    """Only the explicit token list defines missing CSV cells (pandas read_csv)."""
    importer.csv_file_path = write_csv(
        tmp_path, [{"incident_id": "leading-zero", "operator_name": token}]
    )
    (raw,) = importer.fetch_data()

    assert importer.normalize_data(raw)["operator"] == token


def test_csv_preserves_identifier_and_parses_date(importer, tmp_path):
    """Hand interpretation: '001' is an identifier; ISO date labels a calendar day."""
    importer.csv_file_path = write_csv(
        tmp_path, [{"incident_id": "001", "report_date": "2024-01-01"}]
    )
    (raw,) = importer.fetch_data()
    normalized = importer.normalize_data(raw)

    assert normalized["bsee_incident_id"] == "001"
    assert normalized["incident_date"] == datetime.fromisoformat("2024-01-01")


@pytest.mark.parametrize("contents", ["", "incident_id,report_date\n"])
def test_empty_csv_returns_no_records(importer, tmp_path, contents):
    """Zero data rows implies an empty record list, independently of field types."""
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text(contents, encoding="utf-8")
    importer.csv_file_path = str(csv_path)

    assert importer.fetch_data() == []


def test_fetch_requires_csv_path(importer):
    """An absent locator cannot identify an input file."""
    with pytest.raises(ValueError, match="csv_file_path not provided"):
        importer.fetch_data()


def test_fetch_requires_existing_file(importer, tmp_path):
    """A locator with no file must fail before parsing."""
    importer.csv_file_path = str(tmp_path / "absent.csv")
    with pytest.raises(FileNotFoundError):
        importer.fetch_data()


def test_malformed_csv_raises_parse_error(importer, tmp_path):
    """An unclosed quoted field has no CSV record interpretation."""
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text('incident_id,report_date\n"unclosed', encoding="utf-8")
    importer.csv_file_path = str(csv_path)

    with pytest.raises(ValueError, match="Failed to parse CSV file:"):
        importer.fetch_data()


@pytest.mark.parametrize("field", COUNT_FIELDS)
def test_invalid_integer_text_remains_none(importer, field):
    """The nonnumeric word cannot denote an integer; the legacy result is None."""
    assert importer.normalize_data({field: "invalid"})[field] is None


@pytest.mark.parametrize("token", ["NA", ""])
@pytest.mark.parametrize("field", COUNT_FIELDS)
def test_csv_integral_decimal_counts_and_missing_rows(importer, tmp_path, field, token):
    """Decimal '1.0' = 1 and '2.0' = 2, including beside missing CSV cells."""
    importer.csv_file_path = write_csv(
        tmp_path, [{field: "1.0"}, {field: token}, {field: "2.0"}]
    )
    first, missing, last = map(importer.normalize_data, importer.fetch_data())

    assert first[field] == 1
    assert type(first[field]) is int
    assert missing[field] is None
    assert last[field] == 2
    assert type(last[field]) is int


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize(
    "text,expected",
    [("0.0", 0), (" +001.00 ", 1), ("9007199254740993.0", 9007199254740993)],
)
def test_integral_decimal_count_text_is_exact(importer, field, text, expected):
    """Integral decimals retain their value, including beyond float precision."""
    actual = importer.normalize_data({field: text})[field]

    assert actual == expected
    assert type(actual) is int


@pytest.mark.parametrize("field", COUNT_FIELDS)
def test_negative_counts_preserve_legacy_sign_behavior(importer, field):
    """Legacy parsing preserves signs; count-range validation is separate work."""
    assert importer.normalize_data({field: "-1.0"})[field] == -1


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize("text", ["1e2", "1e1000000", "1E+10000000", "0e9999999"])
def test_exponents_rejected_before_integer_conversion(
    importer, monkeypatch, field, text
):
    """Exponent text is invalid and must never reach costly integer expansion."""

    def forbidden_conversion(value):
        pytest.fail("Exponent text reached integer conversion")

    monkeypatch.setitem(
        importer.normalize_data.__globals__, "int", forbidden_conversion
    )
    assert importer.normalize_data({field: text})[field] is None


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize(
    "text",
    ["1.5", "1.0000000000000000000000000001", "NaN", "sNaN", "Infinity", "-Infinity"],
)
def test_fractional_and_nonfinite_count_text_remains_none(importer, field, text):
    """Fractions and nonfinite text cannot denote integer counts; never round."""
    assert importer.normalize_data({field: text})[field] is None


@pytest.mark.parametrize("value", [[], [None], ["first", "second"]])
@pytest.mark.parametrize("field", ["unused", "operator_name"])
def test_direct_dictionary_lists_are_preserved(importer, field, value):
    """Only scalar nulls become None; unrelated list keys remain ignorable."""
    raw = {field: value, "incident_id": "synthetic-record"}

    normalized = importer.normalize_data(raw)

    assert normalized["bsee_incident_id"] == "synthetic-record"
    if field == "unused":
        assert field not in normalized
    else:
        assert normalized["operator"] is value
    assert raw[field] is value
