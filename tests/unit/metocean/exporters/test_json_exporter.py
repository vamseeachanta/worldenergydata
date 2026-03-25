"""Tests for metocean JSON exporter."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from worldenergydata.metocean.constants import DataSource, QualityFlag
from worldenergydata.metocean.exceptions import ExportError
from worldenergydata.metocean.exporters.json_exporter import JSONExporter
from worldenergydata.metocean.processors.data_harmonizer import HarmonizedObservation


def _make_obs(
    time=None,
    station_id="STN001",
    source=DataSource.NDBC,
    wave_height=2.5,
    wind_speed=10.0,
    quality=QualityFlag.GOOD,
    lat=None,
    lon=None,
    **kwargs,
):
    return HarmonizedObservation(
        source=source,
        observation_time=time or datetime(2024, 6, 15, 12, 0),
        station_id=station_id,
        wave_height_m=wave_height,
        wind_speed_ms=wind_speed,
        quality_flag=quality,
        latitude=lat,
        longitude=lon,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestJSONExporterInit:
    def test_defaults(self):
        e = JSONExporter()
        assert e.pretty is True
        assert e.include_metadata is True

    def test_custom(self):
        e = JSONExporter(pretty=False, include_metadata=False)
        assert e.pretty is False
        assert e.include_metadata is False


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestJSONExporterExport:
    def test_empty_raises(self, tmp_path):
        e = JSONExporter()
        with pytest.raises(ExportError, match="No observations"):
            e.export([], tmp_path / "out.json")

    def test_basic_export(self, tmp_path):
        e = JSONExporter()
        obs = [_make_obs()]
        out = tmp_path / "out.json"
        count = e.export(obs, out)
        assert count == 1
        data = json.loads(out.read_text())
        assert data["count"] == 1
        assert len(data["records"]) == 1
        assert "metadata" in data

    def test_without_metadata(self, tmp_path):
        e = JSONExporter(include_metadata=False)
        obs = [_make_obs()]
        out = tmp_path / "out.json"
        e.export(obs, out)
        data = json.loads(out.read_text())
        assert "metadata" not in data

    def test_date_filtering(self, tmp_path):
        e = JSONExporter()
        obs = [
            _make_obs(time=datetime(2024, 1, 1)),
            _make_obs(time=datetime(2024, 6, 1)),
            _make_obs(time=datetime(2024, 12, 1)),
        ]
        out = tmp_path / "out.json"
        count = e.export(
            obs, out,
            start_date=datetime(2024, 3, 1),
            end_date=datetime(2024, 9, 30),
        )
        assert count == 1

    def test_no_match_raises(self, tmp_path):
        e = JSONExporter()
        obs = [_make_obs(time=datetime(2024, 1, 1))]
        with pytest.raises(ExportError, match="date range"):
            e.export(obs, tmp_path / "out.json", start_date=datetime(2025, 1, 1))

    def test_not_pretty(self, tmp_path):
        e = JSONExporter(pretty=False)
        obs = [_make_obs()]
        out = tmp_path / "out.json"
        e.export(obs, out)
        content = out.read_text()
        # Not pretty means no indentation (single line)
        assert "\n" not in content.strip() or "  " not in content

    def test_creates_parent_dirs(self, tmp_path):
        e = JSONExporter()
        obs = [_make_obs()]
        out = tmp_path / "deep" / "nested" / "out.json"
        e.export(obs, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# Export GeoJSON
# ---------------------------------------------------------------------------

class TestJSONExporterGeoJSON:
    def test_no_coordinates_raises(self, tmp_path):
        e = JSONExporter()
        obs = [_make_obs()]  # No lat/lon
        with pytest.raises(ExportError, match="coordinates"):
            e.export_geojson(obs, tmp_path / "out.geojson")

    def test_basic_geojson(self, tmp_path):
        e = JSONExporter()
        obs = [_make_obs(lat=28.5, lon=-88.5)]
        out = tmp_path / "out.geojson"
        count = e.export_geojson(obs, out)
        assert count == 1
        data = json.loads(out.read_text())
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        feature = data["features"][0]
        assert feature["geometry"]["type"] == "Point"
        assert feature["geometry"]["coordinates"] == [-88.5, 28.5]

    def test_filters_no_coordinates(self, tmp_path):
        e = JSONExporter()
        obs = [
            _make_obs(lat=28.5, lon=-88.5, station_id="HAS_COORDS"),
            _make_obs(station_id="NO_COORDS"),
        ]
        out = tmp_path / "out.geojson"
        count = e.export_geojson(obs, out)
        assert count == 1

    def test_geojson_properties(self, tmp_path):
        e = JSONExporter()
        obs = [_make_obs(lat=28.5, lon=-88.5)]
        out = tmp_path / "out.geojson"
        e.export_geojson(obs, out)
        data = json.loads(out.read_text())
        assert "properties" in data  # metadata
        assert data["properties"]["feature_count"] == 1

    def test_geojson_without_metadata(self, tmp_path):
        e = JSONExporter(include_metadata=False)
        obs = [_make_obs(lat=28.5, lon=-88.5)]
        out = tmp_path / "out.geojson"
        e.export_geojson(obs, out)
        data = json.loads(out.read_text())
        assert "properties" not in data


# ---------------------------------------------------------------------------
# Export by station
# ---------------------------------------------------------------------------

class TestJSONExporterByStation:
    def test_empty_raises(self, tmp_path):
        e = JSONExporter()
        with pytest.raises(ExportError, match="No observations"):
            e.export_by_station([], tmp_path / "out.json")

    def test_basic(self, tmp_path):
        e = JSONExporter()
        obs = [
            _make_obs(station_id="A"),
            _make_obs(station_id="A"),
            _make_obs(station_id="B"),
        ]
        out = tmp_path / "out.json"
        count = e.export_by_station(obs, out)
        assert count == 2  # 2 stations
        data = json.loads(out.read_text())
        assert data["station_count"] == 2
        assert data["total_observations"] == 3
        assert len(data["stations"]["A"]) == 2

    def test_unknown_station(self, tmp_path):
        e = JSONExporter()
        obs = [_make_obs(station_id=None)]
        out = tmp_path / "out.json"
        count = e.export_by_station(obs, out)
        data = json.loads(out.read_text())
        assert "unknown" in data["stations"]

    def test_with_metadata(self, tmp_path):
        e = JSONExporter(include_metadata=True)
        obs = [_make_obs()]
        out = tmp_path / "out.json"
        e.export_by_station(obs, out)
        data = json.loads(out.read_text())
        assert "metadata" in data
        assert "exported_at" in data["metadata"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestJSONExporterHelpers:
    def test_filter_by_date_no_filters(self):
        e = JSONExporter()
        obs = [_make_obs()]
        result = e._filter_by_date(obs, None, None)
        assert len(result) == 1

    def test_build_metadata(self):
        e = JSONExporter()
        obs = [_make_obs(station_id="STN001")]
        meta = e._build_metadata(obs, None, None)
        assert meta["station_count"] == 1
        assert "exported_at" in meta

    def test_json_serializer_datetime(self):
        e = JSONExporter()
        dt = datetime(2024, 6, 15, 12, 0)
        assert e._json_serializer(dt) == dt.isoformat()

    def test_json_serializer_enum(self):
        e = JSONExporter()
        assert e._json_serializer(DataSource.NDBC) == DataSource.NDBC.value

    def test_json_serializer_unsupported_raises(self):
        e = JSONExporter()
        with pytest.raises(TypeError):
            e._json_serializer(set())

    def test_geojson_feature_structure(self):
        e = JSONExporter()
        obs = _make_obs(lat=28.5, lon=-88.5)
        feature = e._observation_to_geojson_feature(obs)
        assert feature["type"] == "Feature"
        assert feature["geometry"]["coordinates"] == [-88.5, 28.5]
        assert feature["properties"]["station_id"] == "STN001"
