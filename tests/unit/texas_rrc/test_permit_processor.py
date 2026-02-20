"""Tests for Texas RRC permit processor module."""

import pandas as pd
import pytest

from worldenergydata.texas_rrc.processors.permit_processor import PermitProcessor


# ---------------------------------------------------------------------------
# Init and constants
# ---------------------------------------------------------------------------

class TestPermitProcessorInit:
    def test_defaults(self):
        proc = PermitProcessor()
        assert proc._records_processed == 0
        assert proc._records_invalid == 0
        assert proc.validator is not None

    def test_permit_type_mapping(self):
        assert PermitProcessor.PERMIT_TYPE_MAPPING["01"] == "new_drill"
        assert PermitProcessor.PERMIT_TYPE_MAPPING["N"] == "new_drill"

    def test_permit_status_mapping(self):
        assert PermitProcessor.PERMIT_STATUS_MAPPING["A"] == "approved"
        assert PermitProcessor.PERMIT_STATUS_MAPPING["AP"] == "approved"


# ---------------------------------------------------------------------------
# _normalize_api_to_14_digit
# ---------------------------------------------------------------------------

class TestNormalizeApi14:
    def test_10_digit(self):
        proc = PermitProcessor()
        assert proc._normalize_api_to_14_digit("4200100001") == "42001000010000"

    def test_14_digit(self):
        proc = PermitProcessor()
        assert proc._normalize_api_to_14_digit("42001000010100") == "42001000010100"

    def test_none(self):
        proc = PermitProcessor()
        assert proc._normalize_api_to_14_digit(None) is None

    def test_with_special_chars(self):
        proc = PermitProcessor()
        result = proc._normalize_api_to_14_digit("42-001-00001-AB")
        # Non-numeric chars stripped, only digits remain
        assert result == "42001000010000"


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_iso(self):
        proc = PermitProcessor()
        assert proc._parse_date("2023-01-15") == "2023-01-15"

    def test_us_format(self):
        proc = PermitProcessor()
        assert proc._parse_date("01/15/2023") == "2023-01-15"

    def test_compact(self):
        proc = PermitProcessor()
        assert proc._parse_date("20230115") == "2023-01-15"

    def test_none(self):
        proc = PermitProcessor()
        assert proc._parse_date(None) is None

    def test_empty(self):
        proc = PermitProcessor()
        assert proc._parse_date("") is None

    def test_unrecognized(self):
        proc = PermitProcessor()
        result = proc._parse_date("not-a-date")
        assert result == "not-a-date"


# ---------------------------------------------------------------------------
# _calculate_permit_age
# ---------------------------------------------------------------------------

class TestCalculatePermitAge:
    def test_basic(self):
        proc = PermitProcessor()
        age = proc._calculate_permit_age("2020-01-01")
        assert isinstance(age, int)
        assert age > 1000

    def test_none(self):
        proc = PermitProcessor()
        assert proc._calculate_permit_age(None) is None

    def test_invalid(self):
        proc = PermitProcessor()
        assert proc._calculate_permit_age("not-a-date") is None


# ---------------------------------------------------------------------------
# _detect_horizontal_wells
# ---------------------------------------------------------------------------

class TestDetectHorizontalWells:
    def test_by_profile(self):
        proc = PermitProcessor()
        df = pd.DataFrame({"wellbore_profile": ["HORIZONTAL", "VERTICAL"]})
        result = proc._detect_horizontal_wells(df)
        assert result.iloc[0] == True
        assert result.iloc[1] == False

    def test_by_length(self):
        proc = PermitProcessor()
        df = pd.DataFrame({"horizontal_length": ["5000", "0"]})
        result = proc._detect_horizontal_wells(df)
        assert result.iloc[0] == True
        assert result.iloc[1] == False

    def test_no_indicators(self):
        proc = PermitProcessor()
        df = pd.DataFrame({"other": ["a", "b"]})
        result = proc._detect_horizontal_wells(df)
        assert result.sum() == 0


# ---------------------------------------------------------------------------
# _process_record (dict-based)
# ---------------------------------------------------------------------------

class TestProcessRecord:
    def test_permit_type_mapped(self):
        proc = PermitProcessor()
        result = proc._process_record({"permit_type": "01"})
        assert result["permit_type"] == "new_drill"
        assert result["permit_type_code"] == "01"

    def test_permit_status_mapped(self):
        proc = PermitProcessor()
        result = proc._process_record({"permit_status": "A"})
        assert result["permit_status"] == "approved"
        assert result["permit_status_code"] == "A"

    def test_well_purpose_mapped(self):
        proc = PermitProcessor()
        result = proc._process_record({"well_purpose": "O"})
        assert result["well_purpose"] == "oil"

    def test_dates_parsed(self):
        proc = PermitProcessor()
        result = proc._process_record({"approved_date": "01/15/2023"})
        assert result["approved_date"] == "2023-01-15"
        assert result["permit_age_days"] is not None

    def test_api_number(self):
        proc = PermitProcessor()
        result = proc._process_record({"api_number": "4200100001"})
        assert result["api_number_14"] == "42001000010000"

    def test_coordinates(self):
        proc = PermitProcessor()
        result = proc._process_record({"latitude": "31.5", "longitude": "-97.2"})
        assert result["latitude"] == 31.5
        assert result["longitude"] == -97.2
        assert "coordinates_valid" in result

    def test_positive_longitude_corrected(self):
        proc = PermitProcessor()
        result = proc._process_record({"latitude": "31.5", "longitude": "97.2"})
        assert result["longitude"] == -97.2

    def test_total_depth(self):
        proc = PermitProcessor()
        result = proc._process_record({"total_depth": "15000"})
        assert result["total_depth"] == 15000.0

    def test_horizontal_length(self):
        proc = PermitProcessor()
        result = proc._process_record({"horizontal_length": "5000"})
        assert result["horizontal_length"] == 5000.0
        assert result["is_horizontal"] is True

    def test_no_horizontal_length(self):
        proc = PermitProcessor()
        result = proc._process_record({"wellbore_profile": "VERTICAL"})
        assert result["is_horizontal"] is False

    def test_field_key(self):
        proc = PermitProcessor()
        result = proc._process_record({"district": "01", "field_number": "12345"})
        assert "field_key" in result

    def test_lease_key(self):
        proc = PermitProcessor()
        result = proc._process_record({"district": "01", "lease_number": "99999"})
        assert "lease_key" in result


# ---------------------------------------------------------------------------
# _process_records
# ---------------------------------------------------------------------------

class TestProcessRecords:
    def test_basic(self):
        proc = PermitProcessor()
        records = [
            {"permit_type": "01", "district": "01"},
            {"permit_type": "02", "district": "02"},
        ]
        result = proc._process_records(records, validate=False)
        assert len(result) == 2
        assert proc._records_processed == 2


# ---------------------------------------------------------------------------
# filter_by_permit_type
# ---------------------------------------------------------------------------

class TestFilterByPermitType:
    def test_dataframe(self):
        proc = PermitProcessor()
        df = pd.DataFrame({
            "permit_type": ["new_drill", "recompletion", "new_drill"],
        })
        result = proc.filter_by_permit_type(df, ["new_drill"])
        assert len(result) == 2

    def test_list(self):
        proc = PermitProcessor()
        records = [
            {"permit_type": "new_drill"},
            {"permit_type": "recompletion"},
        ]
        result = proc.filter_by_permit_type(records, ["new_drill"])
        assert len(result) == 1

    def test_no_column(self):
        proc = PermitProcessor()
        df = pd.DataFrame({"other": [1, 2]})
        result = proc.filter_by_permit_type(df, ["new_drill"])
        assert len(result) == 2  # Unchanged


# ---------------------------------------------------------------------------
# filter_by_status
# ---------------------------------------------------------------------------

class TestFilterByStatus:
    def test_dataframe(self):
        proc = PermitProcessor()
        df = pd.DataFrame({
            "permit_status": ["approved", "pending", "approved"],
        })
        result = proc.filter_by_status(df, ["approved"])
        assert len(result) == 2

    def test_list(self):
        proc = PermitProcessor()
        records = [
            {"permit_status": "approved"},
            {"permit_status": "pending"},
        ]
        result = proc.filter_by_status(records, ["approved"])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# filter_by_date_range
# ---------------------------------------------------------------------------

class TestFilterByDateRange:
    def test_dataframe(self):
        proc = PermitProcessor()
        df = pd.DataFrame({
            "approved_date": ["2023-01-15", "2023-06-15", "2024-01-15"],
        })
        result = proc.filter_by_date_range(df, "2023-01-01", "2023-12-31")
        assert len(result) == 2

    def test_list(self):
        proc = PermitProcessor()
        records = [
            {"approved_date": "2023-01-15"},
            {"approved_date": "2024-01-15"},
        ]
        result = proc.filter_by_date_range(records, "2023-01-01", "2023-12-31")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# filter_horizontal_wells
# ---------------------------------------------------------------------------

class TestFilterHorizontalWells:
    def test_horizontal_only_df(self):
        proc = PermitProcessor()
        df = pd.DataFrame({
            "is_horizontal": [True, False, True],
        })
        result = proc.filter_horizontal_wells(df, horizontal_only=True)
        assert len(result) == 2

    def test_exclude_horizontal_df(self):
        proc = PermitProcessor()
        df = pd.DataFrame({"is_horizontal": [True, False, True]})
        result = proc.filter_horizontal_wells(df, horizontal_only=False)
        assert len(result) == 1

    def test_list_horizontal_only(self):
        proc = PermitProcessor()
        records = [
            {"is_horizontal": True},
            {"is_horizontal": False},
        ]
        result = proc.filter_horizontal_wells(records, horizontal_only=True)
        assert len(result) == 1

    def test_list_exclude(self):
        proc = PermitProcessor()
        records = [
            {"is_horizontal": True},
            {"is_horizontal": False},
        ]
        result = proc.filter_horizontal_wells(records, horizontal_only=False)
        assert len(result) == 1

    def test_no_column(self):
        proc = PermitProcessor()
        df = pd.DataFrame({"other": [1, 2]})
        result = proc.filter_horizontal_wells(df)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# summarize_by_district
# ---------------------------------------------------------------------------

class TestSummarizeByDistrict:
    def test_basic(self):
        proc = PermitProcessor()
        df = pd.DataFrame({
            "district": ["01", "01", "02"],
            "permit_type": ["new_drill", "recompletion", "new_drill"],
            "permit_status": ["approved", "pending", "approved"],
            "is_horizontal": [True, False, True],
            "total_depth": [10000.0, 8000.0, 12000.0],
        })
        result = proc.summarize_by_district(df)
        assert len(result) == 2
        assert "total_permits" in result.columns

    def test_empty(self):
        proc = PermitProcessor()
        result = proc.summarize_by_district(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# summarize_by_operator
# ---------------------------------------------------------------------------

class TestSummarizeByOperator:
    def test_basic(self):
        proc = PermitProcessor()
        df = pd.DataFrame({
            "operator_name": ["Exxon", "Exxon", "Chevron"],
            "permit_type": ["new_drill", "recompletion", "new_drill"],
            "permit_status": ["approved", "pending", "approved"],
            "is_horizontal": [True, False, True],
            "district": ["01", "01", "02"],
        })
        result = proc.summarize_by_operator(df)
        assert len(result) == 2
        assert "district_count" in result.columns

    def test_empty(self):
        proc = PermitProcessor()
        result = proc.summarize_by_operator(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_initial(self):
        proc = PermitProcessor()
        stats = proc.stats
        assert stats["records_processed"] == 0
        assert stats["records_invalid"] == 0
