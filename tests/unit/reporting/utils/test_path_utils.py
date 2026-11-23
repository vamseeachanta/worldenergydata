"""Tests for reporting path utilities."""

from pathlib import Path

import pytest

from worldenergydata.reporting.utils.path_utils import (
    get_data_path,
    get_project_root,
    get_report_path,
    relative_path_from_report,
)


class TestGetProjectRoot:
    def test_returns_path(self):
        root = get_project_root()
        assert isinstance(root, Path)

    def test_is_absolute(self):
        root = get_project_root()
        assert root.is_absolute()


class TestGetDataPath:
    def test_processed_default(self):
        path = get_data_path("test.csv")
        assert str(path).endswith("data/processed/test.csv")

    def test_raw(self):
        path = get_data_path("test.csv", "raw")
        assert str(path).endswith("data/raw/test.csv")

    def test_results(self):
        path = get_data_path("test.csv", "results")
        assert str(path).endswith("data/results/test.csv")

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="data_type must be one of"):
            get_data_path("test.csv", "invalid")

    def test_returns_absolute_path(self):
        path = get_data_path("test.csv")
        assert path.is_absolute()


class TestGetReportPath:
    def test_no_subfolder(self):
        path = get_report_path("report.html")
        assert str(path).endswith("reports/report.html")

    def test_with_subfolder(self):
        path = get_report_path("report.html", "monthly")
        assert str(path).endswith("reports/monthly/report.html")


class TestRelativePathFromReport:
    def test_relative_inputs(self):
        result = relative_path_from_report(
            "data/processed/data.csv",
            "reports/analysis.html",
        )
        assert isinstance(result, str)

    def test_absolute_inputs(self):
        data = Path("/tmp/project/data/processed/data.csv")
        report = Path("/tmp/project/reports/analysis.html")
        result = relative_path_from_report(data, report)
        assert isinstance(result, str)
