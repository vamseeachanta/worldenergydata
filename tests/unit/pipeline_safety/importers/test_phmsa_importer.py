"""Tests for PHMSA pipeline safety data importer helper functions and constants."""

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from worldenergydata.pipeline_safety.importers.phmsa_importer import (
    FATALITY_COLUMNS,
    FILE_MANIFEST,
    INJURY_COLUMNS,
    LOCATION_COLUMNS,
    LNG_COLUMN_OVERRIDES,
    MID_COLUMN_MAP,
    MID_LOCATION_COLUMNS,
    MODERN_COLUMN_MAP,
    PRE2004_COLUMN_MAP,
    PHMSAImporter,
    _get_col,
    _parse_bool_indicator,
    _parse_datetime,
    _safe_float,
    _safe_int,
    _safe_str,
    _sum_columns,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestPHMSAConstants:
    def test_file_manifest_count(self):
        assert len(FILE_MANIFEST) == 10

    def test_file_manifest_gas_distribution(self):
        gd_files = [f for f in FILE_MANIFEST if f[2] == "gas_distribution"]
        assert len(gd_files) == 3

    def test_file_manifest_pipeline_types(self):
        types = {f[2] for f in FILE_MANIFEST}
        assert types == {"gas_distribution", "gas_transmission", "hazardous_liquid", "lng"}

    def test_modern_column_map_keys(self):
        assert "report_number" in MODERN_COLUMN_MAP
        assert "incident_date" in MODERN_COLUMN_MAP
        assert "narrative" in MODERN_COLUMN_MAP
        assert "latitude" in MODERN_COLUMN_MAP

    def test_lng_column_overrides(self):
        assert "latitude" in LNG_COLUMN_OVERRIDES
        assert "longitude" in LNG_COLUMN_OVERRIDES
        assert "state" in LNG_COLUMN_OVERRIDES

    def test_location_columns_per_type(self):
        assert "gas_distribution" in LOCATION_COLUMNS
        assert "gas_transmission" in LOCATION_COLUMNS
        assert "hazardous_liquid" in LOCATION_COLUMNS
        assert "lng" in LOCATION_COLUMNS

    def test_fatality_columns(self):
        assert len(FATALITY_COLUMNS) == 4
        assert "NUM_EMP_FATALITIES" in FATALITY_COLUMNS

    def test_injury_columns(self):
        assert len(INJURY_COLUMNS) == 4
        assert "NUM_EMP_INJURIES" in INJURY_COLUMNS

    def test_pre2004_column_map(self):
        assert PRE2004_COLUMN_MAP["report_number"] == "RPTID"
        assert PRE2004_COLUMN_MAP["fatalities"] == "FAT"
        assert PRE2004_COLUMN_MAP["injuries"] == "INJ"

    def test_mid_column_map(self):
        assert MID_COLUMN_MAP["report_number"] == "RPTID"
        assert MID_COLUMN_MAP["narrative"] == "NARRATIVE"

    def test_mid_location_columns(self):
        assert MID_LOCATION_COLUMNS["state"] == "ACSTATE"
        assert MID_LOCATION_COLUMNS["city"] == "ACCITY"


# ---------------------------------------------------------------------------
# _safe_int
# ---------------------------------------------------------------------------

class TestSafeInt:
    def test_normal_int(self):
        assert _safe_int(42) == 42

    def test_float(self):
        assert _safe_int(3.7) == 3

    def test_string(self):
        assert _safe_int("10") == 10

    def test_string_float(self):
        assert _safe_int("3.9") == 3

    def test_nan(self):
        assert _safe_int(float("nan")) is None

    def test_pd_na(self):
        assert _safe_int(pd.NA) is None

    def test_non_numeric(self):
        assert _safe_int("abc") is None


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_normal(self):
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_int(self):
        assert _safe_float(42) == 42.0

    def test_string(self):
        assert _safe_float("3.14") == pytest.approx(3.14)

    def test_nan(self):
        assert _safe_float(float("nan")) is None

    def test_pd_na(self):
        assert _safe_float(pd.NA) is None

    def test_non_numeric(self):
        assert _safe_float("abc") is None


# ---------------------------------------------------------------------------
# _safe_str
# ---------------------------------------------------------------------------

class TestSafeStr:
    def test_normal(self):
        assert _safe_str("hello") == "hello"

    def test_strips(self):
        assert _safe_str("  hello  ") == "hello"

    def test_int(self):
        assert _safe_str(42) == "42"

    def test_nan(self):
        assert _safe_str(float("nan")) is None

    def test_pd_na(self):
        assert _safe_str(pd.NA) is None

    def test_empty(self):
        assert _safe_str("  ") is None


# ---------------------------------------------------------------------------
# _parse_bool_indicator
# ---------------------------------------------------------------------------

class TestParseBoolIndicator:
    def test_yes(self):
        assert _parse_bool_indicator("YES") is True

    def test_y(self):
        assert _parse_bool_indicator("Y") is True

    def test_true(self):
        assert _parse_bool_indicator("TRUE") is True

    def test_one(self):
        assert _parse_bool_indicator("1") is True

    def test_no(self):
        assert _parse_bool_indicator("NO") is False

    def test_n(self):
        assert _parse_bool_indicator("N") is False

    def test_false(self):
        assert _parse_bool_indicator("FALSE") is False

    def test_zero(self):
        assert _parse_bool_indicator("0") is False

    def test_case_insensitive(self):
        assert _parse_bool_indicator("yes") is True
        assert _parse_bool_indicator("no") is False

    def test_nan(self):
        assert _parse_bool_indicator(float("nan")) is None

    def test_unknown(self):
        assert _parse_bool_indicator("maybe") is None

    def test_pd_na(self):
        assert _parse_bool_indicator(pd.NA) is None


# ---------------------------------------------------------------------------
# _parse_datetime
# ---------------------------------------------------------------------------

class TestParseDatetime:
    def test_datetime_passthrough(self):
        dt = datetime(2024, 1, 15)
        assert _parse_datetime(dt) == dt

    def test_timestamp(self):
        ts = pd.Timestamp("2024-06-15")
        result = _parse_datetime(ts)
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 6

    def test_string(self):
        result = _parse_datetime("2024-03-20")
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_nan(self):
        assert _parse_datetime(float("nan")) is None

    def test_invalid(self):
        assert _parse_datetime("not-a-date") is None

    def test_pd_na(self):
        assert _parse_datetime(pd.NA) is None


# ---------------------------------------------------------------------------
# _sum_columns
# ---------------------------------------------------------------------------

class TestSumColumns:
    def test_all_present(self):
        row = pd.Series({"A": 1, "B": 2, "C": 3})
        assert _sum_columns(row, ["A", "B", "C"]) == 6

    def test_some_missing(self):
        row = pd.Series({"A": 5, "C": 10})
        assert _sum_columns(row, ["A", "B", "C"]) == 15

    def test_nan_treated_as_zero(self):
        row = pd.Series({"A": 5, "B": float("nan")})
        assert _sum_columns(row, ["A", "B"]) == 5

    def test_empty_columns(self):
        row = pd.Series({"A": 5})
        assert _sum_columns(row, []) == 0


# ---------------------------------------------------------------------------
# _get_col
# ---------------------------------------------------------------------------

class TestGetCol:
    def test_normal(self):
        row = pd.Series({"A": 42})
        assert _get_col(row, "A") == 42

    def test_none_col_name(self):
        row = pd.Series({"A": 42})
        assert pd.isna(_get_col(row, None))

    def test_missing_col(self):
        row = pd.Series({"A": 42})
        assert pd.isna(_get_col(row, "B"))


# ---------------------------------------------------------------------------
# PHMSAImporter init
# ---------------------------------------------------------------------------

class TestPHMSAImporterInit:
    def test_defaults(self, tmp_path):
        imp = PHMSAImporter(db_session=MagicMock(), data_dir=str(tmp_path))
        assert imp.data_dir == tmp_path
        assert imp.pipeline_types is None
        assert imp.imported_count == 0
        assert imp.skipped_count == 0
        assert imp.error_count == 0
        assert imp.validation_errors == []

    def test_filtered_types(self, tmp_path):
        imp = PHMSAImporter(
            db_session=MagicMock(),
            data_dir=str(tmp_path),
            pipeline_types=["lng"],
        )
        assert imp.pipeline_types == ["lng"]


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------

class TestValidate:
    def setup_method(self, tmp_path=None):
        self.imp = PHMSAImporter(db_session=MagicMock(), data_dir="/tmp")

    def test_valid(self):
        data = {
            "report_number": "gas_distribution_12345",
            "incident_date": datetime(2024, 1, 1),
            "operator_name": "Acme Gas",
        }
        assert self.imp._validate(data) is True

    def test_missing_report_number(self):
        data = {
            "report_number": None,
            "incident_date": datetime(2024, 1, 1),
            "operator_name": "Acme",
        }
        assert self.imp._validate(data) is False

    def test_missing_incident_date(self):
        data = {
            "report_number": "test_123",
            "incident_date": None,
            "operator_name": "Acme",
        }
        assert self.imp._validate(data) is False

    def test_missing_operator_name(self):
        data = {
            "report_number": "test_123",
            "incident_date": datetime(2024, 1, 1),
            "operator_name": None,
        }
        assert self.imp._validate(data) is False


# ---------------------------------------------------------------------------
# _normalize_row routing
# ---------------------------------------------------------------------------

class TestNormalizeRow:
    def test_routes_modern(self):
        imp = PHMSAImporter(db_session=MagicMock(), data_dir="/tmp")
        row = pd.Series({
            "REPORT_NUMBER": "20240001",
            "NAME": "Acme Gas",
            "LOCAL_DATETIME": pd.Timestamp("2024-01-15"),
            "SUPPLEMENTAL_NUMBER": "0",
        })
        result = imp._normalize_row(row, "gas_distribution", "2010_present")
        assert result["report_number"] == "gas_distribution_20240001"
        assert result["pipeline_type"] == "gas_distribution"

    def test_routes_mid(self):
        imp = PHMSAImporter(db_session=MagicMock(), data_dir="/tmp")
        row = pd.Series({
            "RPTID": "200500001",
            "NAME": "Test Op",
            "IDATE": pd.Timestamp("2005-06-15"),
            "OPERATOR_ID": "OP123",
        })
        result = imp._normalize_row(row, "gas_distribution", "2004_2009")
        assert result["report_number"] == "gas_distribution_200500001"

    def test_routes_legacy(self):
        imp = PHMSAImporter(db_session=MagicMock(), data_dir="/tmp")
        row = pd.Series({
            "RPTID": "199500001",
            "NAME": "Old Op",
            "IDATE": pd.Timestamp("1995-03-10"),
            "FAT": 0,
            "INJ": 1,
        })
        result = imp._normalize_row(row, "gas_distribution", "pre2004")
        assert result["report_number"] == "gas_distribution_199500001"
        assert result["fatalities"] == 0
        assert result["injuries"] == 1


# ---------------------------------------------------------------------------
# _extract_release_quantity
# ---------------------------------------------------------------------------

class TestExtractReleaseQuantity:
    def setup_method(self):
        self.imp = PHMSAImporter(db_session=MagicMock(), data_dir="/tmp")

    def test_hazardous_liquid(self):
        row = pd.Series({
            "UNINTENTIONAL_RELEASE_BBLS": 100.0,
            "INTENTIONAL_RELEASE_BBLS": 50.0,
        })
        qty, unit = self.imp._extract_release_quantity(row, "hazardous_liquid")
        assert qty == pytest.approx(150.0)
        assert unit == "barrels"

    def test_hazardous_liquid_none(self):
        row = pd.Series({"OTHER": 1})
        qty, unit = self.imp._extract_release_quantity(row, "hazardous_liquid")
        assert qty is None
        assert unit is None

    def test_lng(self):
        row = pd.Series({
            "UNINTENTIONAL_RELEASE": 200.0,
            "INTENTIONAL_RELEASE": 0.0,
        })
        qty, unit = self.imp._extract_release_quantity(row, "lng")
        assert qty == pytest.approx(200.0)
        assert unit == "MCF"

    def test_gas_distribution(self):
        row = pd.Series({"ESTIMATED_GAS_RELEASED": 500.0})
        qty, unit = self.imp._extract_release_quantity(row, "gas_distribution")
        assert qty == pytest.approx(500.0)
        assert unit == "MCF"

    def test_gas_distribution_none(self):
        row = pd.Series({"OTHER": 1})
        qty, unit = self.imp._extract_release_quantity(row, "gas_distribution")
        assert qty is None
        assert unit is None
