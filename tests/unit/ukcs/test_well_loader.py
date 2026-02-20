"""Tests for UKCS well completions and test data loader."""

import pandas as pd
import pytest

from worldenergydata.ukcs.wells.well_loader import UKCSWellLoader


MOCK_WELL_DATA = {
    "WellName": ["14/19-F1", "14/19-F2", "16/26-B1", "9/23-A1", "21/30-G1"],
    "FieldName": ["FORTIES", "FORTIES", "BUZZARD", "MARINER", "CLAIR RIDGE"],
    "CompletionDate": ["2001-06", "2003-09", "2007-01", "2018-05", "2017-10"],
    "Status": ["PRODUCER", "PRODUCER", "PRODUCER", "PRODUCER", "INJECTOR"],
    "WaterDepth_m": [128.0, 128.0, 108.0, 98.0, 140.0],
    "TestRate_bopd": [12000.0, 9500.0, 24000.0, 8000.0, 11000.0],
}


def make_mock_well_df():
    return pd.DataFrame(MOCK_WELL_DATA)


class TestUKCSWellLoaderLoad:
    @pytest.fixture
    def loader(self):
        return UKCSWellLoader()

    def test_load_returns_dataframe(self, loader):
        raw = make_mock_well_df()
        result = loader.load(raw)
        assert isinstance(result, pd.DataFrame)

    def test_load_output_columns(self, loader):
        raw = make_mock_well_df()
        result = loader.load(raw)
        assert "well_name" in result.columns
        assert "field" in result.columns
        assert "status" in result.columns

    def test_load_normalises_field_to_upper(self, loader):
        raw = make_mock_well_df()
        result = loader.load(raw)
        assert result["field"].str.isupper().all()

    def test_load_normalises_status_to_upper(self, loader):
        raw = make_mock_well_df()
        result = loader.load(raw)
        assert result["status"].str.isupper().all()

    def test_load_preserves_all_rows(self, loader):
        raw = make_mock_well_df()
        result = loader.load(raw)
        assert len(result) == len(raw)

    def test_load_empty_returns_empty(self, loader):
        empty = pd.DataFrame(
            columns=["WellName", "FieldName", "CompletionDate",
                     "Status", "WaterDepth_m", "TestRate_bopd"]
        )
        result = loader.load(empty)
        assert result.empty


class TestUKCSWellLoaderFilter:
    @pytest.fixture
    def loader(self):
        return UKCSWellLoader()

    def test_filter_by_field(self, loader):
        raw = make_mock_well_df()
        df = loader.load(raw)
        result = loader.filter_field(df, "FORTIES")
        assert all(result["field"] == "FORTIES")
        assert len(result) == 2

    def test_filter_by_status_producer(self, loader):
        raw = make_mock_well_df()
        df = loader.load(raw)
        producers = loader.filter_status(df, "PRODUCER")
        assert all(producers["status"] == "PRODUCER")
        assert len(producers) == 4

    def test_filter_by_status_injector(self, loader):
        raw = make_mock_well_df()
        df = loader.load(raw)
        injectors = loader.filter_status(df, "INJECTOR")
        assert len(injectors) == 1


class TestUKCSWellLoaderSummary:
    @pytest.fixture
    def loader(self):
        return UKCSWellLoader()

    def test_field_summary_returns_dict(self, loader):
        raw = make_mock_well_df()
        df = loader.load(raw)
        summary = loader.field_summary(df, "FORTIES")
        assert isinstance(summary, dict)

    def test_field_summary_well_count(self, loader):
        raw = make_mock_well_df()
        df = loader.load(raw)
        summary = loader.field_summary(df, "FORTIES")
        assert summary["well_count"] == 2

    def test_field_summary_missing_field(self, loader):
        raw = make_mock_well_df()
        df = loader.load(raw)
        summary = loader.field_summary(df, "NONEXISTENT")
        assert summary["well_count"] == 0

    def test_field_summary_avg_test_rate(self, loader):
        raw = make_mock_well_df()
        df = loader.load(raw)
        summary = loader.field_summary(df, "FORTIES")
        assert "avg_test_rate_bopd" in summary
        assert summary["avg_test_rate_bopd"] == pytest.approx(10750.0, rel=1e-3)
