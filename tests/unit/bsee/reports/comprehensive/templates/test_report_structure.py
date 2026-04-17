"""Tests for go-by report structure."""

from datetime import date, datetime

from worldenergydata.bsee.reports.comprehensive.templates.report_structure import (
    GoByReportMapper,
    GoByReportStructure,
    ReportRowData,
    ReportRowType,
)


class TestReportRowType:
    def test_all_14_types(self):
        assert len(ReportRowType) == 14

    def test_values(self):
        assert ReportRowType.HEADER.value == "header"
        assert ReportRowType.PRODUCTION_SUMMARY.value == "production_summary"
        assert ReportRowType.ECONOMICS.value == "economics"
        assert ReportRowType.SPACER.value == "spacer"


class TestReportRowData:
    def test_defaults(self):
        r = ReportRowData(row_number=1, row_type=ReportRowType.HEADER, label="Test")
        assert r.value is None
        assert r.format_type == "text"
        assert r.units is None
        assert r.metadata == {}

    def test_format_value_none(self):
        r = ReportRowData(row_number=1, row_type=ReportRowType.HEADER, label="L")
        assert r.format_value() == "N/A"

    def test_format_value_currency(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.ECONOMICS,
            label="Rev",
            value=1234567.89,
            format_type="currency",
        )
        assert r.format_value() == "$1,234,567.89"

    def test_format_value_percentage(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.ECONOMICS,
            label="M",
            value=85.3,
            format_type="percentage",
        )
        assert r.format_value() == "85.3%"

    def test_format_value_number(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.WELL_DETAILS,
            label="W",
            value=1500,
            format_type="number",
        )
        assert r.format_value() == "1,500"

    def test_format_value_decimal(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.HEADER,
            label="D",
            value=3.14159,
            format_type="decimal",
        )
        assert r.format_value() == "3.14"

    def test_format_value_date_obj(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.FIELD_INFO,
            label="D",
            value=date(2024, 3, 15),
            format_type="date",
        )
        assert r.format_value() == "2024-03-15"

    def test_format_value_date_string(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.FIELD_INFO,
            label="D",
            value="2024-01-01",
            format_type="date",
        )
        assert r.format_value() == "2024-01-01"

    def test_format_value_barrels(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.PRODUCTION_SUMMARY,
            label="Oil",
            value=50000,
            format_type="barrels",
        )
        assert r.format_value() == "50,000 bbl"

    def test_format_value_gas(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.PRODUCTION_SUMMARY,
            label="Gas",
            value=100000,
            format_type="gas",
        )
        assert r.format_value() == "100,000 Mcf"

    def test_format_value_days(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.PRODUCTION_SUMMARY,
            label="Days",
            value=365,
            format_type="days",
        )
        assert r.format_value() == "365 days"

    def test_format_value_text_default(self):
        r = ReportRowData(
            row_number=1,
            row_type=ReportRowType.NOTES,
            label="N",
            value="Active",
            format_type="text",
        )
        assert r.format_value() == "Active"


class TestGoByReportStructure:
    def test_default_14_rows(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test Field",
            entity_type="field",
        )
        assert len(report.rows) == 14

    def test_get_row(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        row = report.get_row(1)
        assert row is not None
        assert row.row_type == ReportRowType.HEADER

    def test_get_row_missing(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        assert report.get_row(999) is None

    def test_get_rows_by_type(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        econ_rows = report.get_rows_by_type(ReportRowType.ECONOMICS)
        assert len(econ_rows) == 4  # Revenue, Costs, Net Income, Margin

    def test_update_row_value(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        report.update_row_value(4, 50000)
        row = report.get_row(4)
        assert row.value == 50000

    def test_populate_from_context(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        ctx = {"total_oil_production": 100000, "total_revenue": 5000000}
        report.populate_from_context(ctx)
        oil_row = report.get_row(4)
        assert oil_row.value == 100000

    def test_get_nested_value(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        ctx = {"a": {"b": {"c": 42}}}
        assert report._get_nested_value(ctx, "a.b.c") == 42

    def test_get_nested_value_missing(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        assert report._get_nested_value({}, "a.b") is None

    def test_to_template_context(self):
        report = GoByReportStructure(
            report_title="Test Report",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        ctx = report.to_template_context()
        assert ctx["report_title"] == "Test Report"
        assert len(ctx["rows"]) == 14
        assert "header_rows" in ctx
        assert "economic_rows" in ctx

    def test_validate_structure_default(self):
        report = GoByReportStructure(
            report_title="Test",
            report_date=date(2024, 1, 1),
            entity_id="E001",
            entity_name="Test",
            entity_type="field",
        )
        result = report.validate_structure()
        assert result["valid"] is True
        assert result["row_count"] == 14

    def test_validate_structure_duplicate_rows(self):
        row1 = ReportRowData(row_number=1, row_type=ReportRowType.HEADER, label="A")
        row2 = ReportRowData(row_number=1, row_type=ReportRowType.HEADER, label="B")
        report = GoByReportStructure.__new__(GoByReportStructure)
        report.report_title = "T"
        report.report_date = date(2024, 1, 1)
        report.entity_id = "E"
        report.entity_name = "N"
        report.entity_type = "field"
        report.rows = [row1, row2]
        result = report.validate_structure()
        assert result["valid"] is False
        assert "Duplicate" in result["errors"][0]


class TestGoByReportMapper:
    def test_create_custom_structure(self):
        row_defs = [
            {"label": "Title", "row_type": "header"},
            {
                "label": "Oil",
                "row_type": "production_summary",
                "format_type": "barrels",
                "value": 1000,
            },
        ]
        entity = {
            "entity_id": "E1",
            "entity_name": "Test",
            "entity_type": "field",
            "report_title": "Custom",
        }
        report = GoByReportMapper.create_custom_structure(row_defs, entity)
        assert len(report.rows) == 2
        assert report.rows[0].row_type == ReportRowType.HEADER
        assert report.rows[1].value == 1000
