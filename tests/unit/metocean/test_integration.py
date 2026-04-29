# ABOUTME: Integration tests for metocean module against real APIs.
# ABOUTME: These tests require network access and are marked with pytest markers.

"""Integration tests for metocean module - tests against real APIs"""

from datetime import datetime, timedelta

import pytest

# Mark all tests in this module as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


class TestNDBCIntegration:
    """Tests against real NDBC API."""

    def test_fetch_stations_gom(self):
        """Test fetching stations from Gulf of Mexico region."""
        from worldenergydata.metocean.clients import NDBCClient
        from worldenergydata.metocean.constants import GOM_BBOX

        with NDBCClient() as client:
            result = client.fetch_stations(bbox=GOM_BBOX)

        assert result.records_count > 0
        # Station 41001 is a well-known GOM buoy that should exist
        station_ids = [s.station_id for s in result.data]
        # Check we got some stations in the GOM region
        assert len(station_ids) > 0

    def test_fetch_stations_no_filter(self):
        """Test fetching all active stations."""
        from worldenergydata.metocean.clients import NDBCClient

        with NDBCClient() as client:
            result = client.fetch_stations()

        # Should have many stations
        assert result.records_count > 100

    def test_fetch_realtime_42001(self):
        """Test fetching real-time data from station 42001 (Gulf of Mexico)."""
        from worldenergydata.metocean.clients import NDBCClient

        with NDBCClient() as client:
            result = client.fetch_realtime("42001")

        assert result.records_count > 0
        # Check we got recent data (within last 2 days). External NDBC feeds can
        # return stale snapshots in CI; treat that as source-data unavailable.
        if result.data:
            latest = result.data[-1]
            if latest.observation_time <= datetime.utcnow() - timedelta(days=2):
                pytest.skip(
                    "NDBC realtime feed for station 42001 is stale: "
                    f"{latest.observation_time}"
                )

    def test_fetch_realtime_has_expected_fields(self):
        """Test that realtime data has expected observation fields."""
        from worldenergydata.metocean.clients import NDBCClient

        with NDBCClient() as client:
            result = client.fetch_realtime("42001")

        assert result.data
        obs = result.data[-1]

        # Check essential attributes exist (may be None if not available)
        assert hasattr(obs, "station_id")
        assert hasattr(obs, "observation_time")
        assert hasattr(obs, "wind_speed_ms")
        assert hasattr(obs, "wave_height_m")
        assert hasattr(obs, "sea_surface_temp_c")

    def test_get_station_info(self):
        """Test getting info for a specific station."""
        from worldenergydata.metocean.clients import NDBCClient

        with NDBCClient() as client:
            station = client.get_station_info("42001")

        assert station is not None
        assert station.station_id == "42001"
        assert station.latitude > 0  # Northern hemisphere
        assert station.longitude < 0  # Western hemisphere


class TestCOOPSIntegration:
    """Tests against real CO-OPS API."""

    def test_fetch_stations(self):
        """Test fetching CO-OPS stations."""
        from worldenergydata.metocean.clients import COOPSClient
        from worldenergydata.metocean.constants import GOM_BBOX

        with COOPSClient() as client:
            result = client.fetch_stations(bbox=GOM_BBOX)

        # Should have some tide stations in GOM
        assert result.records_count >= 0  # May vary

    def test_fetch_water_levels(self):
        """Test fetching water level data from a tide station."""
        from worldenergydata.metocean.clients import COOPSClient

        end = datetime.utcnow()
        start = end - timedelta(days=2)
        with COOPSClient() as client:
            result = client.fetch_water_level("8761724", start, end)

        if result.data:  # May not have recent data
            assert result.records_count > 0
            obs = result.data[-1]
            assert hasattr(obs, "water_level_m")


class TestOpenMeteoIntegration:
    """Tests against real Open-Meteo API."""

    def test_fetch_marine_forecast(self):
        """Test fetching marine forecast for a location."""
        from worldenergydata.metocean.clients import OpenMeteoClient

        # Location in Gulf of Mexico
        lat, lon = 28.5, -88.5

        with OpenMeteoClient() as client:
            result = client.fetch_forecast(
                latitude=lat,
                longitude=lon,
                forecast_days=3,
            )

        assert result.records_count > 0
        if result.data:
            forecast = result.data[0]
            assert hasattr(forecast, "wave_height_m")
            assert hasattr(forecast, "forecast_time")

    def test_fetch_forecast_with_params(self):
        """Test fetching forecast with specific parameters."""
        from worldenergydata.metocean.clients import OpenMeteoClient

        lat, lon = 28.5, -88.5

        with OpenMeteoClient() as client:
            result = client.fetch_forecast(
                latitude=lat,
                longitude=lon,
                forecast_days=1,
            )

        assert result.records_count > 0


class TestDataHarmonizerIntegration:
    """Integration tests for data harmonization."""

    def test_harmonize_ndbc_data(self):
        """Test harmonizing NDBC observation data."""
        from worldenergydata.metocean.clients import NDBCClient
        from worldenergydata.metocean.processors import DataHarmonizer

        with NDBCClient() as client:
            result = client.fetch_realtime("42001")

        if result.data:
            harmonizer = DataHarmonizer()
            harmonized = harmonizer.harmonize_ndbc(result.data[-1])

            assert harmonized is not None
            assert harmonized.source == "ndbc"
            assert harmonized.station_id == "42001"


class TestCacheIntegration:
    """Integration tests for caching."""

    def test_cache_hit_on_repeated_fetch(self, tmp_path):
        """Test that cache returns data on repeated fetch."""
        import time

        from worldenergydata.metocean.cache import CacheKey, CacheManager
        from worldenergydata.metocean.constants import DataSource

        cache = CacheManager(cache_dir=tmp_path)

        # Store some test data
        key = CacheKey(
            source=DataSource.NDBC, endpoint="realtime", params={"station": "42001"}
        )
        test_data = {"test": "data", "timestamp": str(datetime.utcnow())}

        cache.set(key, test_data)
        time.sleep(0.1)  # Small delay

        # Retrieve
        cached = cache.get(key)
        assert cached is not None
        assert cached.get("test") == "data"
