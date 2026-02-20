"""
ABOUTME: Tests for multi-format export stage (WRK-242).
ABOUTME: Covers ExportManifest, export_report(), all supported formats.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.reporting.export import (
    DEFAULT_FORMATS,
    ExportManifest,
    export_report,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "field": ["Alpha", "Beta", "Gamma"],
            "production_bbl": [10_000, 25_000, 7_500],
            "year": [2020, 2021, 2022],
        }
    )


def _sample_summary() -> dict:
    return {
        "total_production": 42_500,
        "fields_analysed": 3,
        "source": "BSEE",
    }


@dataclass
class FakeResult:
    """Minimal result object with .data and .summary."""

    data: pd.DataFrame
    summary: dict


@dataclass
class FakeResultNoSummary:
    """Result object without a .summary attribute."""

    data: pd.DataFrame


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture()
def simple_result():
    return FakeResult(data=_sample_df(), summary=_sample_summary())


# ---------------------------------------------------------------------------
# ExportManifest dataclass
# ---------------------------------------------------------------------------

class TestExportManifest:
    def test_manifest_fields_exist(self):
        m = ExportManifest(
            output_dir="/tmp/x",
            files={"xlsx": "/tmp/x/report.xlsx"},
            formats_requested=["xlsx"],
            formats_succeeded=["xlsx"],
            formats_failed={},
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert m.output_dir == "/tmp/x"
        assert m.files == {"xlsx": "/tmp/x/report.xlsx"}
        assert m.formats_requested == ["xlsx"]
        assert m.formats_succeeded == ["xlsx"]
        assert m.formats_failed == {}
        assert "2026" in m.timestamp

    def test_manifest_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(ExportManifest)


# ---------------------------------------------------------------------------
# Return type and defaults
# ---------------------------------------------------------------------------

class TestExportReportReturnType:
    def test_returns_export_manifest(self, simple_result, tmp_dir):
        manifest = export_report(simple_result, output_dir=tmp_dir)
        assert isinstance(manifest, ExportManifest)

    def test_default_formats_are_xlsx_and_parquet(self, simple_result, tmp_dir):
        manifest = export_report(simple_result, output_dir=tmp_dir)
        assert set(manifest.formats_requested) == {"xlsx", "parquet"}

    def test_default_formats_constant(self):
        assert "xlsx" in DEFAULT_FORMATS
        assert "parquet" in DEFAULT_FORMATS

    def test_timestamp_is_set(self, simple_result, tmp_dir):
        manifest = export_report(simple_result, output_dir=tmp_dir)
        assert manifest.timestamp
        assert "T" in manifest.timestamp  # ISO-8601

    def test_output_dir_in_manifest(self, simple_result, tmp_dir):
        manifest = export_report(simple_result, output_dir=tmp_dir)
        assert manifest.output_dir == tmp_dir


# ---------------------------------------------------------------------------
# output_dir parameter
# ---------------------------------------------------------------------------

class TestOutputDir:
    def test_custom_output_dir_is_respected(self, simple_result, tmp_dir):
        manifest = export_report(simple_result, output_dir=tmp_dir)
        assert manifest.output_dir == tmp_dir

    def test_nonexistent_output_dir_is_created(self, simple_result, tmp_dir):
        new_dir = str(Path(tmp_dir) / "nested" / "exports")
        manifest = export_report(
            simple_result, formats=["csv"], output_dir=new_dir
        )
        assert Path(new_dir).is_dir()
        assert manifest.output_dir == new_dir


# ---------------------------------------------------------------------------
# filename_prefix parameter
# ---------------------------------------------------------------------------

class TestFilenamePrefix:
    def test_custom_prefix_in_file_paths(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["csv"], output_dir=tmp_dir,
            filename_prefix="myreport"
        )
        assert "myreport" in list(manifest.files.values())[0]

    def test_default_prefix_derived_from_class_name(self, tmp_dir):
        result = FakeResult(data=_sample_df(), summary={})
        manifest = export_report(result, formats=["csv"], output_dir=tmp_dir)
        assert "fakeresult" in list(manifest.files.values())[0]


# ---------------------------------------------------------------------------
# XLSX format
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("openpyxl"),
    reason="openpyxl not installed",
)
class TestXlsxExport:
    def test_xlsx_file_created(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["xlsx"], output_dir=tmp_dir
        )
        assert "xlsx" in manifest.formats_succeeded
        assert Path(manifest.files["xlsx"]).exists()

    def test_xlsx_extension(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["xlsx"], output_dir=tmp_dir
        )
        assert manifest.files["xlsx"].endswith(".xlsx")

    def test_xlsx_readable_back_as_dataframe(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["xlsx"], output_dir=tmp_dir
        )
        df_back = pd.read_excel(manifest.files["xlsx"], sheet_name="data")
        assert list(df_back.columns) == list(simple_result.data.columns)
        assert len(df_back) == len(simple_result.data)

    def test_xlsx_has_summary_sheet(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["xlsx"], output_dir=tmp_dir
        )
        xl = pd.ExcelFile(manifest.files["xlsx"])
        assert "summary" in xl.sheet_names


# ---------------------------------------------------------------------------
# Parquet format
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("pyarrow"),
    reason="pyarrow not installed",
)
class TestParquetExport:
    def test_parquet_file_created(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["parquet"], output_dir=tmp_dir
        )
        assert "parquet" in manifest.formats_succeeded
        assert Path(manifest.files["parquet"]).exists()

    def test_parquet_extension(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["parquet"], output_dir=tmp_dir
        )
        assert manifest.files["parquet"].endswith(".parquet")

    def test_parquet_readable_back_as_dataframe(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["parquet"], output_dir=tmp_dir
        )
        df_back = pd.read_parquet(manifest.files["parquet"])
        assert list(df_back.columns) == list(simple_result.data.columns)
        assert len(df_back) == len(simple_result.data)


# ---------------------------------------------------------------------------
# CSV format
# ---------------------------------------------------------------------------

class TestCsvExport:
    def test_csv_file_created(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["csv"], output_dir=tmp_dir
        )
        assert "csv" in manifest.formats_succeeded
        assert Path(manifest.files["csv"]).exists()

    def test_csv_extension(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["csv"], output_dir=tmp_dir
        )
        assert manifest.files["csv"].endswith(".csv")

    def test_csv_readable_back_as_dataframe(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["csv"], output_dir=tmp_dir
        )
        df_back = pd.read_csv(manifest.files["csv"])
        assert list(df_back.columns) == list(simple_result.data.columns)
        assert len(df_back) == len(simple_result.data)

    def test_csv_maps_correct_key_in_files(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["csv"], output_dir=tmp_dir
        )
        assert "csv" in manifest.files


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------

class TestJsonExport:
    def test_json_file_created(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["json"], output_dir=tmp_dir
        )
        assert "json" in manifest.formats_succeeded
        assert Path(manifest.files["json"]).exists()

    def test_json_extension(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["json"], output_dir=tmp_dir
        )
        assert manifest.files["json"].endswith(".json")

    def test_json_contains_data_and_summary_keys(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["json"], output_dir=tmp_dir
        )
        payload = json.loads(Path(manifest.files["json"]).read_text())
        assert "data" in payload
        assert "summary" in payload

    def test_json_data_is_list_of_records(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["json"], output_dir=tmp_dir
        )
        payload = json.loads(Path(manifest.files["json"]).read_text())
        assert isinstance(payload["data"], list)
        assert len(payload["data"]) == len(simple_result.data)

    def test_json_summary_preserved(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["json"], output_dir=tmp_dir
        )
        payload = json.loads(Path(manifest.files["json"]).read_text())
        assert payload["summary"]["fields_analysed"] == 3


# ---------------------------------------------------------------------------
# PDF / HTML-report format
# ---------------------------------------------------------------------------

class TestPdfHtmlFallback:
    def test_pdf_produces_html_file(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["pdf"], output_dir=tmp_dir
        )
        # manifest key is html_report; file extension is .html
        assert "html_report" in manifest.formats_succeeded
        assert Path(manifest.files["html_report"]).exists()

    def test_pdf_file_has_html_extension(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["pdf"], output_dir=tmp_dir
        )
        assert manifest.files["html_report"].endswith(".html")

    def test_pdf_html_is_valid_html(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["pdf"], output_dir=tmp_dir
        )
        content = Path(manifest.files["html_report"]).read_text()
        assert "<html" in content
        assert "</html>" in content


# ---------------------------------------------------------------------------
# Failure isolation
# ---------------------------------------------------------------------------

class TestFailureIsolation:
    def test_unsupported_format_goes_to_formats_failed(
        self, simple_result, tmp_dir
    ):
        manifest = export_report(
            simple_result, formats=["csv", "unsupported_xyz"], output_dir=tmp_dir
        )
        assert "csv" in manifest.formats_succeeded
        assert "unsupported_xyz" in manifest.formats_failed

    def test_unsupported_format_does_not_block_others(
        self, simple_result, tmp_dir
    ):
        manifest = export_report(
            simple_result,
            formats=["csv", "json", "totally_fake"],
            output_dir=tmp_dir,
        )
        assert "csv" in manifest.formats_succeeded
        assert "json" in manifest.formats_succeeded

    def test_formats_failed_contains_error_message(
        self, simple_result, tmp_dir
    ):
        manifest = export_report(
            simple_result, formats=["bad_format"], output_dir=tmp_dir
        )
        assert "bad_format" in manifest.formats_failed
        assert len(manifest.formats_failed["bad_format"]) > 0

    def test_files_dict_only_contains_succeeded_formats(
        self, simple_result, tmp_dir
    ):
        manifest = export_report(
            simple_result, formats=["csv", "bad_format"], output_dir=tmp_dir
        )
        assert "csv" in manifest.files
        assert "bad_format" not in manifest.files


# ---------------------------------------------------------------------------
# Result objects without .summary
# ---------------------------------------------------------------------------

class TestResultWithoutSummary:
    def test_missing_summary_attribute_does_not_raise(self, tmp_dir):
        result = FakeResultNoSummary(data=_sample_df())
        manifest = export_report(result, formats=["csv"], output_dir=tmp_dir)
        assert "csv" in manifest.formats_succeeded

    def test_empty_dataframe_exports_without_error(self, tmp_dir):
        result = FakeResult(data=pd.DataFrame(), summary={})
        manifest = export_report(result, formats=["csv", "json"], output_dir=tmp_dir)
        assert "csv" in manifest.formats_succeeded
        assert "json" in manifest.formats_succeeded


# ---------------------------------------------------------------------------
# Multi-format batch
# ---------------------------------------------------------------------------

class TestMultiFormatBatch:
    def test_multiple_formats_all_succeed(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["csv", "json"], output_dir=tmp_dir
        )
        assert "csv" in manifest.formats_succeeded
        assert "json" in manifest.formats_succeeded

    def test_files_dict_maps_format_to_real_path(self, simple_result, tmp_dir):
        manifest = export_report(
            simple_result, formats=["csv"], output_dir=tmp_dir
        )
        path = manifest.files["csv"]
        assert Path(path).is_absolute()
        assert Path(path).exists()

    def test_import_from_reporting_package(self):
        from worldenergydata.reporting import ExportManifest, export_report
        assert callable(export_report)
        assert ExportManifest is not None
