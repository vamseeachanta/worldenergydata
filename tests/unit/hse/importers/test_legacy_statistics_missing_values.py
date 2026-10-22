"""Physical legacy-source regressions for #1308; bypass only the import redirect.

Expected missing tokens follow #1308 and pandas 2.3 read_csv/isna:
https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.read_csv.html
https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.isna.html
"""

import importlib.util
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


@pytest.fixture
def importer():
    root = Path(__file__).resolve().parents[4]
    path = (
        root / "src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py"
    )
    spec = importlib.util.spec_from_file_location("physical_legacy_statistics", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BSEEStatisticsImporter(MagicMock())


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize("missing", ["NA", ""])
def test_legacy_csv_missing_counts(importer, tmp_path, field, missing):
    """Missing means None; 3.0 = 3 + 0/10 and 7 is a literal integer."""
    path = tmp_path / "statistics.csv"
    path.write_text(f"{field},operator_name\n{missing},NA\n3.0,\n7,text\n")
    importer.csv_file_path = str(path)
    results = [importer.normalize_data(row) for row in importer.fetch_data()]
    assert [row[field] for row in results] == [None, 3, 7]
    assert [row["operator"] for row in results] == [None, None, "text"]
    assert type(results[1][field]) is int
    assert type(results[2][field]) is int


@pytest.mark.parametrize("field", COUNT_FIELDS)
@pytest.mark.parametrize(
    "text,expected",
    [
        ("+003.0", 3),
        ("-3.0", -3),
        ("9007199254740993.0", 9007199254740993),
        ("3.5", None),
        ("1e3", None),
        ("1e1000000", None),
    ],
)
def test_legacy_exact_counts_and_exponent_rejection(importer, field, text, expected):
    """Signed zero fractions preserve integers; nonzero fractions/exponents reject.

    Place values give +003 = 3 and -3 = -(3). The large integer is the
    literal 9007199254740993, without any floating-point intermediate.
    """
    assert importer.normalize_data({field: text})[field] == expected


@pytest.mark.parametrize("missing", [float("nan"), pd.NA, pd.NaT, None])
def test_legacy_scalar_nulls(importer, missing):
    raw = {"operator_name": missing, "fatality_count": missing}
    result = importer.normalize_data(raw)
    assert result["operator"] is None
    assert result["fatality_count"] is None
    assert raw["operator_name"] is missing


def test_legacy_preserves_other_text_and_identifiers(importer, tmp_path):
    path = tmp_path / "statistics.csv"
    path.write_text("incident_id,operator_name,facility,field\n0007,N/A,null,NaN\n")
    importer.csv_file_path = str(path)
    result = importer.normalize_data(importer.fetch_data()[0])
    assert result["bsee_incident_id"] == "0007"
    assert result["operator"] == "N/A"
    assert result["facility_name"] == "null"
    assert result["field_name"] == "NaN"
    value = ["NA"]
    assert importer.normalize_data({"operator_name": value})["operator"] is value
