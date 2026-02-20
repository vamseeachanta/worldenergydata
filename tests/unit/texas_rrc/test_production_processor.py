"""Tests for Texas RRC production processor module."""

import pandas as pd
import pytest

from worldenergydata.texas_rrc.processors.production_processor import ProductionProcessor


# ---------------------------------------------------------------------------
# Init and constants
# ---------------------------------------------------------------------------

class TestProductionProcessorInit:
    def test_defaults(self):
        proc = ProductionProcessor()
        assert proc._records_processed == 0
        assert proc._records_invalid == 0
        assert proc.validator is not None

    def test_unit_conversions(self):
        assert ProductionProcessor.UNIT_CONVERSIONS["mcf_to_boe"] == 0.1714


# ---------------------------------------------------------------------------
# _normalize_api_to_14_digit
# ---------------------------------------------------------------------------

class TestNormalizeApi14:
    def test_10_digit(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit("4200100001") == "42001000010000"

    def test_12_digit(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit("420010000101") == "42001000010100"

    def test_14_digit(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit("42001000010100") == "42001000010100"

    def test_long_truncated(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit("420010000101009999") == "42001000010100"

    def test_short_returns_none(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit("4200") is None

    def test_none(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit(None) is None

    def test_nan(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit(float("nan")) is None

    def test_dashes_stripped(self):
        proc = ProductionProcessor()
        assert proc._normalize_api_to_14_digit("42-001-00001") == "42001000010000"


# ---------------------------------------------------------------------------
# _parse_production_date
# ---------------------------------------------------------------------------

class TestParseProductionDate:
    def test_yyyymm(self):
        proc = ProductionProcessor()
        assert proc._parse_production_date("202301") == "2023-01"

    def test_yyyy_mm(self):
        proc = ProductionProcessor()
        assert proc._parse_production_date("2023-01") == "2023-01"

    def test_mm_yyyy(self):
        proc = ProductionProcessor()
        assert proc._parse_production_date("01/2023") == "2023-01"

    def test_full_date(self):
        proc = ProductionProcessor()
        assert proc._parse_production_date("2023-01-15") == "2023-01"

    def test_none(self):
        proc = ProductionProcessor()
        assert proc._parse_production_date(None) is None

    def test_empty(self):
        proc = ProductionProcessor()
        assert proc._parse_production_date("") is None

    def test_unrecognized(self):
        proc = ProductionProcessor()
        result = proc._parse_production_date("not-a-date")
        assert result == "not-a-date"


# ---------------------------------------------------------------------------
# _process_record (dict-based)
# ---------------------------------------------------------------------------

class TestProcessRecord:
    def test_basic(self):
        proc = ProductionProcessor()
        record = {
            "district": "01",
            "oil_production": "100",
            "gas_production": "500",
        }
        result = proc._process_record(record)
        assert result["oil_production"] == 100.0
        assert result["gas_production"] == 500.0
        assert result["boe_total"] == 100.0 + 500.0 * 0.1714

    def test_zero_gas(self):
        proc = ProductionProcessor()
        record = {"oil_production": "100", "gas_production": "0"}
        result = proc._process_record(record)
        assert result["boe_total"] == 100.0

    def test_api_number_added(self):
        proc = ProductionProcessor()
        record = {"api_number": "4200100001"}
        result = proc._process_record(record)
        assert result["api_number_14"] == "42001000010000"

    def test_production_date_parsed(self):
        proc = ProductionProcessor()
        record = {"production_date": "202301"}
        result = proc._process_record(record)
        assert result["production_date"] == "2023-01"

    def test_invalid_numeric(self):
        proc = ProductionProcessor()
        record = {"oil_production": "N/A"}
        result = proc._process_record(record)
        assert result["oil_production"] == 0.0


# ---------------------------------------------------------------------------
# _process_records (list-based)
# ---------------------------------------------------------------------------

class TestProcessRecords:
    def test_basic(self):
        proc = ProductionProcessor()
        records = [
            {"district": "01", "oil_production": "100"},
            {"district": "02", "oil_production": "200"},
        ]
        result = proc._process_records(records, validate=False)
        assert len(result) == 2
        assert proc._records_processed == 2

    def test_validation_filters(self):
        proc = ProductionProcessor()
        records = [{"district": "01", "oil_production": "100"}]
        result = proc._process_records(records, validate=True)
        assert proc._records_processed + proc._records_invalid == len(records)


# ---------------------------------------------------------------------------
# _normalize_columns
# ---------------------------------------------------------------------------

class TestNormalizeColumns:
    def test_standard_columns(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({"DISTRICT_NO": [1], "OIL_BBL": [100]})
        result = proc._normalize_columns(df)
        assert "district" in result.columns
        assert "oil_production" in result.columns

    def test_custom_columns(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({"My Custom Column": [1]})
        result = proc._normalize_columns(df)
        assert "my_custom_column" in result.columns


# ---------------------------------------------------------------------------
# process (DataFrame)
# ---------------------------------------------------------------------------

class TestProcessDataFrame:
    def test_empty_df(self):
        proc = ProductionProcessor()
        df = pd.DataFrame()
        result = proc.process(df)
        assert result.empty

    def test_basic_df(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "DISTRICT_NO": ["01"],
            "OIL_BBL": ["100"],
            "GAS_MCF": ["500"],
        })
        result = proc.process(df, validate=False)
        assert "district" in result.columns
        assert "boe_total" in result.columns
        assert len(result) == 1

    def test_year_month_combined(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "CYCLE_YEAR": [2023],
            "CYCLE_MONTH": [1],
            "OIL_BBL": [100],
        })
        result = proc.process(df, validate=False)
        assert "production_date" in result.columns
        assert result.iloc[0]["production_date"] == "2023-01"


# ---------------------------------------------------------------------------
# aggregate_monthly
# ---------------------------------------------------------------------------

class TestAggregateMonthly:
    def test_basic(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "production_date": ["2023-01", "2023-01", "2023-02"],
            "oil_production": [100.0, 200.0, 150.0],
        })
        result = proc.aggregate_monthly(df)
        assert len(result) == 2
        jan = result[result["production_date"] == "2023-01"]
        assert jan.iloc[0]["oil_production"] == 300.0

    def test_from_list(self):
        proc = ProductionProcessor()
        records = [
            {"production_date": "2023-01", "oil_production": 100.0},
            {"production_date": "2023-01", "oil_production": 200.0},
        ]
        result = proc.aggregate_monthly(records)
        assert len(result) == 1

    def test_empty(self):
        proc = ProductionProcessor()
        result = proc.aggregate_monthly(pd.DataFrame())
        assert result.empty

    def test_no_date_column(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({"oil_production": [100.0]})
        result = proc.aggregate_monthly(df)
        assert len(result) == 1  # Returns unchanged


# ---------------------------------------------------------------------------
# aggregate_annual
# ---------------------------------------------------------------------------

class TestAggregateAnnual:
    def test_basic(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "production_date": ["2023-01", "2023-06", "2024-01"],
            "oil_production": [100.0, 200.0, 150.0],
        })
        result = proc.aggregate_annual(df)
        assert len(result) == 2

    def test_from_list(self):
        proc = ProductionProcessor()
        records = [
            {"production_date": "2023-01", "oil_production": 100.0},
            {"production_date": "2023-06", "oil_production": 200.0},
        ]
        result = proc.aggregate_annual(records)
        assert len(result) == 1

    def test_empty(self):
        proc = ProductionProcessor()
        result = proc.aggregate_annual(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# aggregate_by_district
# ---------------------------------------------------------------------------

class TestAggregateByDistrict:
    def test_basic(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "district": ["01", "01", "02"],
            "oil_production": [100.0, 200.0, 150.0],
        })
        result = proc.aggregate_by_district(df)
        assert len(result) == 2

    def test_with_lease(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "district": ["01", "01"],
            "oil_production": [100.0, 200.0],
            "lease_number": ["L1", "L2"],
        })
        result = proc.aggregate_by_district(df)
        assert "lease_count" in result.columns
        assert result.iloc[0]["lease_count"] == 2

    def test_no_district(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({"oil_production": [100.0]})
        result = proc.aggregate_by_district(df)
        assert len(result) == 1  # Returns unchanged

    def test_from_list(self):
        proc = ProductionProcessor()
        records = [
            {"district": "01", "oil_production": 100.0},
            {"district": "02", "oil_production": 200.0},
        ]
        result = proc.aggregate_by_district(records)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# aggregate_by_lease
# ---------------------------------------------------------------------------

class TestAggregateByLease:
    def test_basic(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "lease_number": ["L1", "L1", "L2"],
            "oil_production": [100.0, 200.0, 150.0],
        })
        result = proc.aggregate_by_lease(df)
        assert len(result) == 2

    def test_with_name_and_district(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "lease_number": ["L1", "L1"],
            "lease_name": ["Ranch A", "Ranch A"],
            "district": ["01", "01"],
            "oil_production": [100.0, 200.0],
        })
        result = proc.aggregate_by_lease(df)
        assert len(result) == 1

    def test_no_lease_column(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({"oil_production": [100.0]})
        result = proc.aggregate_by_lease(df)
        assert len(result) == 1  # Returns unchanged


# ---------------------------------------------------------------------------
# filter_by_date_range
# ---------------------------------------------------------------------------

class TestFilterByDateRange:
    def test_dataframe(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({
            "production_date": ["2023-01", "2023-06", "2024-01"],
            "oil_production": [100.0, 200.0, 150.0],
        })
        result = proc.filter_by_date_range(df, "2023-01", "2023-12")
        assert len(result) == 2

    def test_list(self):
        proc = ProductionProcessor()
        records = [
            {"production_date": "2023-01", "oil_production": 100.0},
            {"production_date": "2024-01", "oil_production": 200.0},
        ]
        result = proc.filter_by_date_range(records, "2023-01", "2023-12")
        assert len(result) == 1

    def test_no_date_column(self):
        proc = ProductionProcessor()
        df = pd.DataFrame({"oil_production": [100.0]})
        result = proc.filter_by_date_range(df, "2023-01", "2023-12")
        assert len(result) == 1  # Unchanged


# ---------------------------------------------------------------------------
# iter_processed
# ---------------------------------------------------------------------------

class TestIterProcessed:
    def test_basic(self):
        proc = ProductionProcessor()
        records = iter([
            {"district": "01", "oil_production": "100"},
        ])
        result = list(proc.iter_processed(records, validate=False))
        assert len(result) == 1
        assert result[0]["oil_production"] == 100.0


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_initial(self):
        proc = ProductionProcessor()
        stats = proc.stats
        assert stats["records_processed"] == 0
        assert stats["records_invalid"] == 0
        assert "validation_stats" in stats
