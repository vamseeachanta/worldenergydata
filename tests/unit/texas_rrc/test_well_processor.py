"""Tests for Texas RRC well processor module."""

import pandas as pd
import pytest

from worldenergydata.texas_rrc.processors.well_processor import WellProcessor

# ---------------------------------------------------------------------------
# Init and constants
# ---------------------------------------------------------------------------


class TestWellProcessorInit:
    def test_defaults(self):
        proc = WellProcessor()
        assert proc._records_processed == 0
        assert proc._records_invalid == 0
        assert proc.validator is not None

    def test_status_mapping(self):
        assert WellProcessor.STATUS_MAPPING["A"] == "active"
        assert WellProcessor.STATUS_MAPPING["PA"] == "plugged_and_abandoned"

    def test_well_type_mapping(self):
        assert WellProcessor.WELL_TYPE_MAPPING["O"] == "oil"
        assert WellProcessor.WELL_TYPE_MAPPING["HZ"] == "horizontal"


# ---------------------------------------------------------------------------
# _normalize_api_to_14_digit
# ---------------------------------------------------------------------------


class TestNormalizeApi14:
    def test_10_digit(self):
        proc = WellProcessor()
        assert proc._normalize_api_to_14_digit("4200100001") == "42001000010000"

    def test_14_digit(self):
        proc = WellProcessor()
        assert proc._normalize_api_to_14_digit("42001000010100") == "42001000010100"

    def test_none(self):
        proc = WellProcessor()
        assert proc._normalize_api_to_14_digit(None) is None


# ---------------------------------------------------------------------------
# _extract_sidetrack_code / _extract_completion_code
# ---------------------------------------------------------------------------


class TestExtractCodes:
    def test_sidetrack_code(self):
        proc = WellProcessor()
        assert proc._extract_sidetrack_code("42001000010200") == "02"

    def test_sidetrack_none(self):
        proc = WellProcessor()
        assert proc._extract_sidetrack_code(None) is None

    def test_sidetrack_short(self):
        proc = WellProcessor()
        assert proc._extract_sidetrack_code("420010") is None

    def test_completion_code(self):
        proc = WellProcessor()
        assert proc._extract_completion_code("42001000010203") == "03"

    def test_completion_none(self):
        proc = WellProcessor()
        assert proc._extract_completion_code(None) is None

    def test_completion_short(self):
        proc = WellProcessor()
        assert proc._extract_completion_code("4200100001") is None


# ---------------------------------------------------------------------------
# _detect_horizontal_wells
# ---------------------------------------------------------------------------


class TestDetectHorizontalWells:
    def test_by_profile(self):
        proc = WellProcessor()
        df = pd.DataFrame({"wellbore_profile": ["HORIZONTAL", "VERTICAL"]})
        result = proc._detect_horizontal_wells(df)
        assert result.iloc[0] == True
        assert result.iloc[1] == False

    def test_by_well_type(self):
        proc = WellProcessor()
        df = pd.DataFrame({"well_type_code": ["HZ", "O"]})
        result = proc._detect_horizontal_wells(df)
        assert result.iloc[0] == True
        assert result.iloc[1] == False

    def test_no_indicators(self):
        proc = WellProcessor()
        df = pd.DataFrame({"other": [1, 2]})
        result = proc._detect_horizontal_wells(df)
        assert result.sum() == 0


# ---------------------------------------------------------------------------
# _detect_directional_wells
# ---------------------------------------------------------------------------


class TestDetectDirectionalWells:
    def test_by_profile(self):
        proc = WellProcessor()
        df = pd.DataFrame({"wellbore_profile": ["DIRECTIONAL", "VERTICAL"]})
        result = proc._detect_directional_wells(df)
        assert result.iloc[0] == True
        assert result.iloc[1] == False

    def test_by_well_type(self):
        proc = WellProcessor()
        df = pd.DataFrame({"well_type_code": ["DI", "O"]})
        result = proc._detect_directional_wells(df)
        assert result.iloc[0] == True
        assert result.iloc[1] == False


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_iso(self):
        proc = WellProcessor()
        assert proc._parse_date("2023-01-15") == "2023-01-15"

    def test_us_format(self):
        proc = WellProcessor()
        assert proc._parse_date("01/15/2023") == "2023-01-15"

    def test_none(self):
        proc = WellProcessor()
        assert proc._parse_date(None) is None

    def test_empty(self):
        proc = WellProcessor()
        assert proc._parse_date("") is None


# ---------------------------------------------------------------------------
# _process_record (dict-based)
# ---------------------------------------------------------------------------


class TestProcessRecord:
    def test_well_status_mapped(self):
        proc = WellProcessor()
        result = proc._process_record({"well_status": "A"})
        assert result["well_status"] == "active"
        assert result["well_status_code"] == "A"

    def test_well_type_mapped(self):
        proc = WellProcessor()
        result = proc._process_record({"well_type": "O"})
        assert result["well_type"] == "oil"
        assert result["well_type_code"] == "O"

    def test_api_number(self):
        proc = WellProcessor()
        result = proc._process_record({"api_number": "4200100001"})
        assert result["api_number_14"] == "42001000010000"
        assert result["sidetrack_code"] == "00"
        assert result["completion_code"] == "00"
        assert result["is_sidetrack"] is False

    def test_sidetrack(self):
        proc = WellProcessor()
        result = proc._process_record({"api_number": "420010000102"})
        assert result["sidetrack_code"] == "02"
        assert result["is_sidetrack"] is True

    def test_coordinates(self):
        proc = WellProcessor()
        result = proc._process_record({"latitude": "31.5", "longitude": "-97.2"})
        assert result["latitude"] == 31.5
        assert result["longitude"] == -97.2

    def test_positive_longitude_corrected(self):
        proc = WellProcessor()
        result = proc._process_record({"latitude": "31.5", "longitude": "97.2"})
        assert result["longitude"] == -97.2

    def test_invalid_coordinates(self):
        proc = WellProcessor()
        result = proc._process_record({"latitude": "abc", "longitude": "def"})
        assert result["coordinates_valid"] is False

    def test_total_depth(self):
        proc = WellProcessor()
        result = proc._process_record({"total_depth": "15000"})
        assert result["total_depth"] == 15000.0

    def test_dates_parsed(self):
        proc = WellProcessor()
        result = proc._process_record({"spud_date": "01/15/2023"})
        assert result["spud_date"] == "2023-01-15"


# ---------------------------------------------------------------------------
# _process_records
# ---------------------------------------------------------------------------


class TestProcessRecords:
    def test_basic(self):
        proc = WellProcessor()
        records = [
            {"well_status": "A", "district": "01"},
            {"well_status": "P", "district": "02"},
        ]
        result = proc._process_records(records, validate=False)
        assert len(result) == 2
        assert proc._records_processed == 2


# ---------------------------------------------------------------------------
# filter_by_status
# ---------------------------------------------------------------------------


class TestFilterByStatus:
    def test_dataframe(self):
        proc = WellProcessor()
        df = pd.DataFrame(
            {
                "well_status": ["active", "plugged", "active"],
            }
        )
        result = proc.filter_by_status(df, ["active"])
        assert len(result) == 2

    def test_list(self):
        proc = WellProcessor()
        records = [
            {"well_status": "active"},
            {"well_status": "plugged"},
        ]
        result = proc.filter_by_status(records, ["active"])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# filter_by_well_type
# ---------------------------------------------------------------------------


class TestFilterByWellType:
    def test_dataframe(self):
        proc = WellProcessor()
        df = pd.DataFrame(
            {
                "well_type": ["oil", "gas", "oil"],
            }
        )
        result = proc.filter_by_well_type(df, ["oil"])
        assert len(result) == 2

    def test_list(self):
        proc = WellProcessor()
        records = [
            {"well_type": "oil"},
            {"well_type": "gas"},
        ]
        result = proc.filter_by_well_type(records, ["oil"])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# filter_sidetracks
# ---------------------------------------------------------------------------


class TestFilterSidetracks:
    def test_originals_only_df(self):
        proc = WellProcessor()
        df = pd.DataFrame({"is_sidetrack": [True, False, True]})
        result = proc.filter_sidetracks(df, include_original=True)
        assert len(result) == 1

    def test_sidetracks_only_df(self):
        proc = WellProcessor()
        df = pd.DataFrame({"is_sidetrack": [True, False, True]})
        result = proc.filter_sidetracks(df, include_original=False)
        assert len(result) == 2

    def test_list_originals(self):
        proc = WellProcessor()
        records = [
            {"is_sidetrack": True},
            {"is_sidetrack": False},
        ]
        result = proc.filter_sidetracks(records, include_original=True)
        assert len(result) == 1

    def test_list_sidetracks(self):
        proc = WellProcessor()
        records = [
            {"is_sidetrack": True},
            {"is_sidetrack": False},
        ]
        result = proc.filter_sidetracks(records, include_original=False)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# summarize_by_district
# ---------------------------------------------------------------------------


class TestSummarizeByDistrict:
    def test_basic(self):
        proc = WellProcessor()
        df = pd.DataFrame(
            {
                "district": ["01", "01", "02"],
                "well_status": ["active", "plugged", "active"],
                "is_horizontal": [True, False, True],
                "is_sidetrack": [False, False, True],
                "total_depth": [10000.0, 8000.0, 12000.0],
            }
        )
        result = proc.summarize_by_district(df)
        assert len(result) == 2
        assert "total_wells" in result.columns

    def test_empty(self):
        proc = WellProcessor()
        result = proc.summarize_by_district(pd.DataFrame())
        assert result.empty

    def test_from_list(self):
        proc = WellProcessor()
        records = [
            {
                "district": "01",
                "well_status": "active",
                "is_horizontal": True,
                "is_sidetrack": False,
                "total_depth": 10000.0,
            },
        ]
        result = proc.summarize_by_district(records)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_initial(self):
        proc = WellProcessor()
        stats = proc.stats
        assert stats["records_processed"] == 0
        assert stats["records_invalid"] == 0
