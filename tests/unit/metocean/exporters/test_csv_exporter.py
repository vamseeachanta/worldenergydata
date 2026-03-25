"""Tests for metocean CSV exporter."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from worldenergydata.metocean.constants import DataSource, QualityFlag
from worldenergydata.metocean.exceptions import ExportError
from worldenergydata.metocean.exporters.csv_exporter import CSVExporter
from worldenergydata.metocean.processors.data_harmonizer import HarmonizedObservation


def _make_obs(
    time=None,
    station_id="STN001",
    source=DataSource.NDBC,
    wave_height=2.5,
    wind_speed=10.0,
    quality=QualityFlag.GOOD,
    **kwargs,
):
    return HarmonizedObservation(
        source=source,
        observation_time=time or datetime(2024, 6, 15, 12, 0),
        station_id=station_id,
        wave_height_m=wave_height,
        wind_speed_ms=wind_speed,
        quality_flag=quality,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestCSVExporterInit:
    def test_defaults(self):
        e = CSVExporter()
        assert e.include_quality is True
        assert e.date_format == "%Y-%m-%d %H:%M:%S"
        assert "observation_time" in e.columns

    def test_custom_columns(self):
        e = CSVExporter(columns=["wave_height_m", "wind_speed_ms"])
        assert e.columns == ["wave_height_m", "wind_speed_ms"]

    def test_include_quality_false(self):
        e = CSVExporter(include_quality=False)
        assert e.include_quality is False


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestCSVExporterExport:
    def test_empty_raises(self, tmp_path):
        e = CSVExporter()
        with pytest.raises(ExportError, match="No observations"):
            e.export([], tmp_path / "out.csv")

    def test_basic_export(self, tmp_path):
        e = CSVExporter()
        obs = [_make_obs()]
        out = tmp_path / "out.csv"
        count = e.export(obs, out)
        assert count == 1
        assert out.exists()
        content = out.read_text()
        assert "observation_time" in content
        assert "quality_flag" in content

    def test_without_quality(self, tmp_path):
        e = CSVExporter(include_quality=False)
        obs = [_make_obs()]
        out = tmp_path / "out.csv"
        e.export(obs, out)
        content = out.read_text()
        assert "quality_flag" not in content

    def test_date_filtering(self, tmp_path):
        e = CSVExporter()
        obs = [
            _make_obs(time=datetime(2024, 1, 1, 12, 0)),
            _make_obs(time=datetime(2024, 6, 1, 12, 0)),
            _make_obs(time=datetime(2024, 12, 1, 12, 0)),
        ]
        out = tmp_path / "out.csv"
        count = e.export(
            obs, out,
            start_date=datetime(2024, 3, 1),
            end_date=datetime(2024, 9, 30),
        )
        assert count == 1

    def test_date_filter_no_match_raises(self, tmp_path):
        e = CSVExporter()
        obs = [_make_obs(time=datetime(2024, 1, 1, 12, 0))]
        with pytest.raises(ExportError, match="date range"):
            e.export(obs, tmp_path / "out.csv", start_date=datetime(2025, 1, 1))

    def test_multiple_observations(self, tmp_path):
        e = CSVExporter()
        obs = [_make_obs(station_id=f"STN{i}") for i in range(5)]
        count = e.export(obs, tmp_path / "out.csv")
        assert count == 5

    def test_creates_parent_dirs(self, tmp_path):
        e = CSVExporter()
        obs = [_make_obs()]
        out = tmp_path / "deep" / "nested" / "out.csv"
        e.export(obs, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# Export summary
# ---------------------------------------------------------------------------

class TestCSVExporterSummary:
    def test_empty_raises(self, tmp_path):
        e = CSVExporter()
        with pytest.raises(ExportError):
            e.export_summary([], tmp_path / "summary.csv")

    def test_invalid_group_by_raises(self, tmp_path):
        e = CSVExporter()
        obs = [_make_obs()]
        with pytest.raises(ExportError, match="Invalid group_by"):
            e.export_summary(obs, tmp_path / "summary.csv", group_by="invalid")

    def test_group_by_day(self, tmp_path):
        e = CSVExporter()
        obs = [
            _make_obs(time=datetime(2024, 6, 15, 10, 0)),
            _make_obs(time=datetime(2024, 6, 15, 14, 0), wave_height=3.0),
            _make_obs(time=datetime(2024, 6, 16, 10, 0), wave_height=1.5),
        ]
        out = tmp_path / "summary.csv"
        count = e.export_summary(obs, out, group_by="day")
        assert count == 2  # 2 days

    def test_group_by_station(self, tmp_path):
        e = CSVExporter()
        obs = [
            _make_obs(station_id="A"),
            _make_obs(station_id="A"),
            _make_obs(station_id="B"),
        ]
        out = tmp_path / "summary.csv"
        count = e.export_summary(obs, out, group_by="station")
        assert count == 2  # 2 stations

    def test_group_by_hour(self, tmp_path):
        e = CSVExporter()
        obs = [
            _make_obs(time=datetime(2024, 6, 15, 10, 0)),
            _make_obs(time=datetime(2024, 6, 15, 10, 30)),
            _make_obs(time=datetime(2024, 6, 15, 11, 0)),
        ]
        out = tmp_path / "summary.csv"
        count = e.export_summary(obs, out, group_by="hour")
        assert count == 2  # 2 hours


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestCSVExporterHelpers:
    def test_filter_by_date_no_filters(self):
        e = CSVExporter()
        obs = [_make_obs()]
        result = e._filter_by_date(obs, None, None)
        assert len(result) == 1

    def test_observation_to_row(self):
        e = CSVExporter()
        obs = _make_obs()
        row = e._observation_to_row(obs, ["station_id", "wave_height_m"])
        assert row["station_id"] == "STN001"
        assert row["wave_height_m"] == 2.5

    def test_observation_to_row_datetime_formatted(self):
        e = CSVExporter(date_format="%Y-%m-%d")
        obs = _make_obs(time=datetime(2024, 6, 15, 12, 0))
        row = e._observation_to_row(obs, ["observation_time"])
        assert row["observation_time"] == "2024-06-15"
