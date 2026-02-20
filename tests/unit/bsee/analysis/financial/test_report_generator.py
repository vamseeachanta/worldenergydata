"""Tests for BSEE financial report generator formatters and helpers."""

import math

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.financial.report_generator import (
    ExcelFormatter,
    ReportGenerator,
    format_currency,
    format_number,
    format_percentage,
)


# ---------------------------------------------------------------------------
# format_currency
# ---------------------------------------------------------------------------

class TestFormatCurrency:
    def test_positive(self):
        assert format_currency(1500) == "$1,500"

    def test_negative(self):
        assert format_currency(-1500) == "-$1,500"

    def test_zero(self):
        assert format_currency(0) == "$0"

    def test_float(self):
        assert format_currency(1234.56) == "$1,235"

    def test_large(self):
        assert format_currency(1000000) == "$1,000,000"

    def test_nan(self):
        assert format_currency(float("nan")) == ""


# ---------------------------------------------------------------------------
# format_number
# ---------------------------------------------------------------------------

class TestFormatNumber:
    def test_normal(self):
        assert format_number(1234) == "1,234"

    def test_zero(self):
        assert format_number(0) == "0"

    def test_float(self):
        assert format_number(1234.6) == "1,235"

    def test_large(self):
        assert format_number(1000000) == "1,000,000"

    def test_nan(self):
        assert format_number(float("nan")) == ""


# ---------------------------------------------------------------------------
# format_percentage
# ---------------------------------------------------------------------------

class TestFormatPercentage:
    def test_half(self):
        assert format_percentage(0.5) == "50.00%"

    def test_zero(self):
        assert format_percentage(0) == "0.00%"

    def test_one(self):
        assert format_percentage(1.0) == "100.00%"

    def test_small(self):
        assert format_percentage(0.123) == "12.30%"

    def test_nan(self):
        assert format_percentage(float("nan")) == ""


# ---------------------------------------------------------------------------
# ExcelFormatter
# ---------------------------------------------------------------------------

class TestExcelFormatter:
    def test_init_creates_styles(self):
        formatter = ExcelFormatter()
        assert "header" in formatter.styles
        assert "title" in formatter.styles
        assert "currency" in formatter.styles
        assert "percentage" in formatter.styles
        assert "number" in formatter.styles
        assert "date" in formatter.styles


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------

class TestReportGenerator:
    def test_init(self):
        gen = ReportGenerator()
        assert gen.formatter is not None
        assert gen.workbook is None

    def test_truncate_sheet_name_short(self):
        gen = ReportGenerator()
        assert gen._truncate_sheet_name("ShortName") == "ShortName"

    def test_truncate_sheet_name_long(self):
        gen = ReportGenerator()
        long_name = "A" * 50
        result = gen._truncate_sheet_name(long_name)
        assert len(result) == 31

    def test_truncate_sheet_name_exact(self):
        gen = ReportGenerator()
        name = "A" * 31
        assert gen._truncate_sheet_name(name) == name

    def test_format_executive_summary_data(self):
        gen = ReportGenerator()
        dev_data = {
            "Dev A": {
                "metrics": {
                    "total_oil_bbls": 1000,
                    "total_capex_facilities": 500,
                    "total_capex_drill": 200,
                    "total_capex_comp": 100,
                    "npv": 50000,
                    "mirr_annual": 0.15,
                },
            },
        }
        result = gen._format_executive_summary_data(dev_data)
        assert len(result) == 1
        assert result[0]["Project Name"] == "Dev A"
        assert result[0]["TOTAL OIL BBL"] == 1000
        assert result[0]["DnC Total USD"] == 300
        assert result[0]["NPV10 afterTax"] == 50000

    def test_format_executive_summary_missing_metrics(self):
        gen = ReportGenerator()
        dev_data = {"Dev B": {"metrics": {}}}
        result = gen._format_executive_summary_data(dev_data)
        assert result[0]["TOTAL OIL BBL"] == 0
        assert result[0]["DnC Total USD"] == 0

    def test_format_project_summary_data_subsea(self):
        gen = ReportGenerator()
        dev_data = {
            "Dev A": {
                "development_type": "subsea",
                "producer_count": 14,
                "first_oil": "2025-01",
                "metrics": {
                    "total_oil_bbls": 5000,
                    "host_usd": 100,
                    "surf_usd": 50,
                    "pump_usd": 25,
                    "total_capex_facilities": 175,
                    "total_capex_drill": 200,
                    "total_capex_comp": 100,
                    "total_opex": 80,
                },
            },
        }
        result = gen._format_project_summary_data(dev_data)
        assert len(result) == 1
        row = result[0]
        assert row["Producer Wells Used"] == 14
        assert row["Injector Wells"] == 2  # 14 // 7
        assert row["Pumps Count (8/prod)"] == 1  # 14 // 8
        assert row["DEV SYSTEM USED"] == "subsea"

    def test_format_project_summary_data_dry_tree(self):
        gen = ReportGenerator()
        dev_data = {
            "Dev B": {
                "development_type": "dry_tree",
                "producer_count": 5,
                "metrics": {},
            },
        }
        result = gen._format_project_summary_data(dev_data)
        row = result[0]
        assert row["DEV SYSTEM USED"] == "dry"
        assert row["Facilities SURF USD"] == 0
        assert row["ECON PATH USED"] == "dry: MODU->DRY at FO"

    def test_format_project_summary_few_producers(self):
        gen = ReportGenerator()
        dev_data = {
            "Dev C": {
                "development_type": "subsea",
                "producer_count": 3,
                "metrics": {},
            },
        }
        result = gen._format_project_summary_data(dev_data)
        row = result[0]
        assert row["Injector Wells"] == 0  # 3 < 7
        assert row["Pumps Count (8/prod)"] == 0  # 3 < 8
