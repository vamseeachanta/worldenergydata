"""Tests for report export base classes."""

from datetime import datetime
from pathlib import Path

from worldenergydata.bsee.reports.comprehensive.exporters.base import (
    ExportConfig,
    ExportFormat,
    ExportResult,
    ReportExporter,
)


class TestExportFormat:
    def test_values(self):
        assert ExportFormat.EXCEL.value == "excel"
        assert ExportFormat.PDF.value == "pdf"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.POWERPOINT.value == "powerpoint"

    def test_count(self):
        assert len(ExportFormat) == 5


class TestExportConfig:
    def test_basic(self):
        cfg = ExportConfig(format=ExportFormat.EXCEL, output_path=Path("/tmp/report.xlsx"))
        assert cfg.format == ExportFormat.EXCEL
        assert cfg.output_path == Path("/tmp/report.xlsx")
        assert cfg.template_name is None
        assert cfg.include_charts is True
        assert cfg.include_raw_data is False
        assert cfg.compression is False
        assert cfg.page_size == "A4"
        assert cfg.orientation == "portrait"
        assert cfg.excel_options == {}
        assert cfg.pdf_options == {}

    def test_string_path_converted(self):
        cfg = ExportConfig(format=ExportFormat.JSON, output_path="/tmp/data.json")
        assert isinstance(cfg.output_path, Path)
        assert cfg.output_path == Path("/tmp/data.json")

    def test_custom_options(self):
        cfg = ExportConfig(
            format=ExportFormat.PDF,
            output_path=Path("/tmp/report.pdf"),
            page_size="Letter",
            orientation="landscape",
            include_charts=False,
            compression=True,
        )
        assert cfg.page_size == "Letter"
        assert cfg.orientation == "landscape"
        assert cfg.include_charts is False
        assert cfg.compression is True


class TestExportResult:
    def test_success(self):
        r = ExportResult(success=True, file_path=Path("/tmp/report.xlsx"), file_size=1024)
        assert r.success is True
        assert r.file_path == Path("/tmp/report.xlsx")
        assert r.file_size == 1024
        assert r.warnings == []
        assert r.errors == []

    def test_failure(self):
        r = ExportResult(success=False, message="No data available")
        assert r.success is False
        assert r.message == "No data available"

    def test_add_warning(self):
        r = ExportResult(success=True)
        r.add_warning("Missing charts")
        assert r.warnings == ["Missing charts"]
        assert r.success is True  # Warnings don't change success

    def test_add_error(self):
        r = ExportResult(success=True)
        r.add_error("Write failed")
        assert r.errors == ["Write failed"]
        assert r.success is False  # Errors set success to False

    def test_get_summary_success(self):
        r = ExportResult(
            success=True,
            file_path=Path("/tmp/report.xlsx"),
            file_size=2048,
            export_time=1.5,
        )
        summary = r.get_summary()
        assert "successful" in summary.lower()
        assert "/tmp/report.xlsx" in summary
        assert "2,048 bytes" in summary
        assert "1.50s" in summary

    def test_get_summary_failure(self):
        r = ExportResult(success=False, message="Disk full")
        r.add_error("Write error")
        summary = r.get_summary()
        assert "failed" in summary.lower()
        assert "Disk full" in summary
        assert "Write error" in summary

    def test_get_summary_with_warnings(self):
        r = ExportResult(success=True, file_path=Path("/tmp/r.xlsx"))
        r.add_warning("Large file")
        summary = r.get_summary()
        assert "Large file" in summary


class ConcreteExporter(ReportExporter):
    """Concrete implementation for testing."""

    def __init__(self):
        super().__init__()
        self.supported_format = ExportFormat.JSON

    def export(self, data, config):
        return ExportResult(success=True)

    def validate_data(self, data):
        return bool(data)

    def get_supported_features(self):
        return ["charts", "raw_data"]


class TestReportExporter:
    def test_init(self):
        exp = ConcreteExporter()
        assert exp.supported_format == ExportFormat.JSON
        assert exp.max_file_size == 100 * 1024 * 1024

    def test_prepare_output_directory(self, tmp_path):
        exp = ConcreteExporter()
        output = tmp_path / "subdir" / "report.json"
        result = exp.prepare_output_directory(output)
        assert result is True
        assert output.parent.exists()

    def test_check_file_size_within_limit(self, tmp_path):
        exp = ConcreteExporter()
        f = tmp_path / "small.json"
        f.write_text("{}")
        assert exp.check_file_size_limit(f) is True

    def test_check_file_size_nonexistent(self, tmp_path):
        exp = ConcreteExporter()
        f = tmp_path / "missing.json"
        assert exp.check_file_size_limit(f) is True

    def test_format_timestamp_now(self):
        exp = ConcreteExporter()
        ts = exp.format_timestamp()
        assert len(ts) == 15  # YYYYMMDD_HHMMSS
        assert "_" in ts

    def test_format_timestamp_specific(self):
        exp = ConcreteExporter()
        dt = datetime(2024, 6, 15, 10, 30, 45)
        ts = exp.format_timestamp(dt)
        assert ts == "20240615_103045"

    def test_sanitize_filename(self):
        exp = ConcreteExporter()
        assert exp.sanitize_filename("report.xlsx") == "report.xlsx"
        assert exp.sanitize_filename('file<>:"/\\|?*.xlsx') == "file_________.xlsx"

    def test_sanitize_filename_long(self):
        exp = ConcreteExporter()
        long_name = "a" * 250 + ".json"
        result = exp.sanitize_filename(long_name)
        assert len(result) <= 200 + 8  # 195 + "..." + ".json"

    def test_get_file_extension_json(self):
        exp = ConcreteExporter()
        assert exp.get_file_extension() == ".json"

    def test_get_file_extension_no_format(self):
        exp = ConcreteExporter()
        exp.supported_format = None
        assert exp.get_file_extension() == ""

    def test_add_metadata(self):
        exp = ConcreteExporter()
        data = {"key": "value"}
        result = exp.add_metadata(data)
        assert "metadata" in result
        assert "export_timestamp" in result["metadata"]
        assert result["metadata"]["export_format"] == "json"
        assert result["metadata"]["exporter_version"] == "1.0.0"

    def test_add_metadata_existing(self):
        exp = ConcreteExporter()
        data = {"metadata": {"existing": True}}
        result = exp.add_metadata(data)
        assert result["metadata"]["existing"] is True
        assert "export_timestamp" in result["metadata"]

    def test_validate_data(self):
        exp = ConcreteExporter()
        assert exp.validate_data({"some": "data"}) is True
        assert exp.validate_data({}) is False

    def test_get_supported_features(self):
        exp = ConcreteExporter()
        assert exp.get_supported_features() == ["charts", "raw_data"]
