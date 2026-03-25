"""Tests for FDAS ExcelReportGenerator constants and init."""

import pytest

from worldenergydata.fdas.reports.excel_generator import (
    ExcelReportGenerator,
    ReportGenerationError,
)


# ---------------------------------------------------------------------------
# ReportGenerationError
# ---------------------------------------------------------------------------

class TestReportGenerationError:
    def test_is_exception(self):
        err = ReportGenerationError("generation failed")
        assert isinstance(err, Exception)
        assert "generation failed" in str(err)


# ---------------------------------------------------------------------------
# ExcelReportGenerator constants
# ---------------------------------------------------------------------------

class TestExcelReportGeneratorConstants:
    def test_header_fill(self):
        fill = ExcelReportGenerator.HEADER_FILL
        assert fill.start_color.rgb == "004472C4"

    def test_header_font(self):
        font = ExcelReportGenerator.HEADER_FONT
        assert font.bold is True
        assert font.color.rgb == "00FFFFFF"

    def test_title_font(self):
        font = ExcelReportGenerator.TITLE_FONT
        assert font.bold is True
        assert font.size == 14

    def test_currency_format(self):
        assert "$" in ExcelReportGenerator.CURRENCY_FORMAT

    def test_number_format(self):
        assert ExcelReportGenerator.NUMBER_FORMAT == "#,##0"

    def test_percent_format(self):
        assert "%" in ExcelReportGenerator.PERCENT_FORMAT

    def test_date_format(self):
        assert "yyyy" in ExcelReportGenerator.DATE_FORMAT


# ---------------------------------------------------------------------------
# ExcelReportGenerator init
# ---------------------------------------------------------------------------

class TestExcelReportGeneratorInit:
    def test_output_path(self, tmp_path):
        path = str(tmp_path / "output.xlsx")
        gen = ExcelReportGenerator(path)
        assert str(gen.output_path) == path

    def test_workbook_created(self, tmp_path):
        gen = ExcelReportGenerator(str(tmp_path / "output.xlsx"))
        assert gen.workbook is not None

    def test_default_sheet_removed(self, tmp_path):
        gen = ExcelReportGenerator(str(tmp_path / "output.xlsx"))
        assert "Sheet" not in gen.workbook.sheetnames
