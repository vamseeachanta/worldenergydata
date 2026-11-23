"""Tests for report_builder GoByReportBuilder pure-logic methods."""

import pytest

from worldenergydata.bsee.reports.comprehensive.report_builder import (
    GoByReportBuilder,
)

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestGoByReportBuilderInit:
    def test_defaults(self):
        builder = GoByReportBuilder()
        assert builder.report_data is None
        assert builder.aggregator is not None

    def test_goby_row_structure(self):
        assert len(GoByReportBuilder.GOBY_ROW_STRUCTURE) == 14
        assert "Field Name" in GoByReportBuilder.GOBY_ROW_STRUCTURE
        assert "Net Income ($)" in GoByReportBuilder.GOBY_ROW_STRUCTURE


# ---------------------------------------------------------------------------
# _build_metadata
# ---------------------------------------------------------------------------


class TestBuildMetadata:
    def test_basic(self):
        builder = GoByReportBuilder()
        meta = builder._build_metadata("block", "MC807")
        assert meta["report_type"] == "block"
        assert meta["entity"] == "MC807"
        assert meta["data_source"] == "BSEE"
        assert meta["report_format"] == "Go-By Standard 14-Row"
        assert meta["version"] == "1.0"
        assert "generated_date" in meta
        assert "generated_time" in meta


# ---------------------------------------------------------------------------
# _build_summary_section
# ---------------------------------------------------------------------------


class TestBuildSummarySection:
    def test_no_data(self):
        builder = GoByReportBuilder()
        builder.report_data = None
        result = builder._build_summary_section()
        assert result == {}

    def test_with_summary(self):
        builder = GoByReportBuilder()
        builder.report_data = {
            "summary": {
                "entity_count": 5,
                "total_oil_bbls": 100000,
                "total_gas_mcf": 500000,
                "total_water_bbls": 30000,
                "total_boe": 183333,
                "total_gross_revenue": 8000000,
                "total_costs": 3000000,
                "total_net_income": 5000000,
                "profit_margin": 62.5,
            }
        }
        result = builder._build_summary_section()
        assert result["total_entities"] == 5
        assert "100,000" in result["total_oil_production"]
        assert "$8,000,000" in result["gross_revenue"]
        assert "62.5%" in result["profit_margin"]

    def test_empty_summary(self):
        builder = GoByReportBuilder()
        builder.report_data = {"summary": {}}
        result = builder._build_summary_section()
        assert result["total_entities"] == 0


# ---------------------------------------------------------------------------
# _create_well_row
# ---------------------------------------------------------------------------


class TestCreateWellRow:
    def test_full_data(self):
        builder = GoByReportBuilder()
        field = {"field_name": "Anchor"}
        lease = {"lease_number": "G09868"}
        well = {
            "well_name": "Well-A1",
            "api_number": "608174001",
            "water_depth_ft": 5183,
            "total_depth_ft": 25000,
            "spud_date": "2024-01-15",
            "status": "Producing",
            "oil_production_bbls": 50000.5,
            "gas_production_mcf": 200000.3,
            "water_production_bbls": 10000.7,
            "gross_revenue": 4000000.123,
            "operating_cost": 1500000.456,
            "net_income": 2500000.789,
        }
        row = builder._create_well_row(field, lease, well)
        assert len(row) == 14
        assert row[0] == "Anchor"
        assert row[1] == "G09868"
        assert row[2] == "Well-A1"
        assert row[4] == 5183
        assert row[7] == "Producing"

    def test_no_field(self):
        builder = GoByReportBuilder()
        lease = {"lease_number": "G09868"}
        well = {"well_name": "W1"}
        row = builder._create_well_row(None, lease, well)
        assert row[0] == "N/A"
        assert row[1] == "G09868"

    def test_missing_values(self):
        builder = GoByReportBuilder()
        row = builder._create_well_row({"field_name": "F"}, {}, {})
        assert row[2] == "N/A"
        assert row[7] == "Unknown"
        assert row[8] == 0


# ---------------------------------------------------------------------------
# _build_detail_rows
# ---------------------------------------------------------------------------


class TestBuildDetailRows:
    def test_no_data(self):
        builder = GoByReportBuilder()
        builder.report_data = None
        assert builder._build_detail_rows("block") == []

    def test_lease_report(self):
        builder = GoByReportBuilder()
        builder.report_data = {
            "data": {
                "G09868": {
                    "wells": [
                        {"well_name": "W1", "status": "Active"},
                        {"well_name": "W2", "status": "Idle"},
                    ]
                }
            }
        }
        rows = builder._build_detail_rows("lease")
        assert len(rows) == 2
        assert rows[0][2] == "W1"

    def test_field_report(self):
        builder = GoByReportBuilder()
        builder.report_data = {
            "data": {
                "Anchor": {
                    "leases": [
                        {
                            "lease_number": "G001",
                            "wells": [{"well_name": "W1"}],
                        }
                    ]
                }
            }
        }
        rows = builder._build_detail_rows("field")
        assert len(rows) == 1

    def test_block_report(self):
        builder = GoByReportBuilder()
        builder.report_data = {
            "data": {
                "MC807": {
                    "fields": [
                        {
                            "field_name": "Anchor",
                            "leases": [
                                {
                                    "lease_number": "G001",
                                    "wells": [{"well_name": "W1"}],
                                }
                            ],
                        }
                    ]
                }
            }
        }
        rows = builder._build_detail_rows("block")
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# _build_aggregation_section
# ---------------------------------------------------------------------------


class TestBuildAggregationSection:
    def test_no_data(self):
        builder = GoByReportBuilder()
        builder.report_data = None
        assert builder._build_aggregation_section("block") == {}

    def test_block_aggregation(self):
        builder = GoByReportBuilder()
        builder.report_data = {
            "data": {
                "MC807": {
                    "fields": [
                        {
                            "field_name": "Anchor",
                            "oil_production_bbls": 50000,
                            "gas_production_mcf": 200000,
                            "gross_revenue": 4000000,
                            "total_wells": 5,
                            "total_leases": 2,
                        }
                    ]
                }
            }
        }
        agg = builder._build_aggregation_section("block")
        assert "by_field" in agg
        assert "Anchor" in agg["by_field"]
        assert agg["by_field"]["Anchor"]["oil_bbls"] == 50000

    def test_lease_aggregation(self):
        builder = GoByReportBuilder()
        builder.report_data = {
            "data": {
                "G09868": {
                    "wells": [
                        {"status": "active"},
                        {"status": "inactive"},
                        {"status": "abandoned"},
                        {"status": "other_status"},
                    ]
                }
            }
        }
        agg = builder._build_aggregation_section("lease")
        assert "by_status" in agg
        assert agg["by_status"]["active"] == 1
        assert agg["by_status"]["inactive"] == 2  # 1 actual + 1 unknown
        assert agg["by_status"]["abandoned"] == 1


# ---------------------------------------------------------------------------
# _prepare_chart_data
# ---------------------------------------------------------------------------


class TestPrepareChartData:
    def test_no_data(self):
        builder = GoByReportBuilder()
        builder.report_data = None
        assert builder._prepare_chart_data() == {}

    def test_with_summary(self):
        builder = GoByReportBuilder()
        builder.report_data = {
            "summary": {
                "total_oil_bbls": 100000,
                "total_gas_mcf": 600000,
                "total_costs": 3000000,
                "total_net_income": 5000000,
            }
        }
        charts = builder._prepare_chart_data()
        assert "production_pie" in charts
        assert "revenue_breakdown" in charts
        assert charts["production_pie"]["values"][0] == 100000
        # Gas converted to BOE: 600000/6 = 100000
        assert charts["production_pie"]["values"][1] == 100000


# ---------------------------------------------------------------------------
# _validate_report_data
# ---------------------------------------------------------------------------


class TestValidateReportData:
    def test_complete_report(self):
        builder = GoByReportBuilder()
        report = {
            "metadata": {},
            "summary": {},
            "detail_rows": [],
            "aggregations": {},
        }
        # Should not raise
        builder._validate_report_data(report)

    def test_missing_sections_warns(self):
        builder = GoByReportBuilder()
        # Should not raise, just log warnings
        builder._validate_report_data({})

    def test_row_length_mismatch(self):
        builder = GoByReportBuilder()
        report = {
            "metadata": {},
            "summary": {},
            "detail_rows": [[1, 2, 3]],
            "aggregations": {},
        }
        # Should not raise, just log warning about row length
        builder._validate_report_data(report)


# ---------------------------------------------------------------------------
# _apply_goby_formatting
# ---------------------------------------------------------------------------


class TestApplyGobyFormatting:
    def test_formats_production_volumes(self):
        builder = GoByReportBuilder()
        report = {
            "detail_rows": [
                [
                    "F",
                    "L",
                    "W",
                    "API",
                    5000,
                    20000,
                    "2024-01-01",
                    "Active",
                    50000.7,
                    200000.3,
                    10000.9,  # production columns
                    4000000.123,
                    1500000.456,
                    2500000.789,  # financial columns
                ]
            ]
        }
        result = builder._apply_goby_formatting(report)
        row = result["detail_rows"][0]
        # Production volumes should be integers
        assert isinstance(row[8], int)
        assert isinstance(row[9], int)
        assert isinstance(row[10], int)
        # Financial values should be rounded to 2 decimals
        assert row[11] == 4000000.12
        assert row[12] == 1500000.46
        assert row[13] == 2500000.79

    def test_empty_rows(self):
        builder = GoByReportBuilder()
        report = {"detail_rows": []}
        result = builder._apply_goby_formatting(report)
        assert result["detail_rows"] == []
