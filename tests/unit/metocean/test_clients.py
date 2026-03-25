# ABOUTME: Tests for metocean API clients.
# ABOUTME: Unit tests with mocked responses for NDBC, CO-OPS, and Open-Meteo clients.

"""Tests for metocean clients"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.metocean.clients import (
    COOPSClient,
    NDBCClient,
    NDBCObservation,
    NDBCStation,
    OpenMeteoClient,
)
from worldenergydata.metocean.constants import DataSource, StationType


class TestNDBCClient:
    """Tests for NDBCClient class."""

    def test_client_initialization(self):
        """Test NDBC client initializes correctly."""
        client = NDBCClient()
        assert client.source == DataSource.NDBC
        assert "ndbc" in client.base_url.lower()

    def test_parse_realtime_data(self):
        """Test parsing of NDBC text format."""
        client = NDBCClient()

        sample_data = """#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
2024 01 15 12 00 180  5.0  6.0   1.2   8.0   5.5 170  1015.0  22.5  24.0  18.0   MM   MM    MM"""

        observations = client._parse_realtime_data("41001", sample_data)
        assert len(observations) == 1

        obs = observations[0]
        assert obs.station_id == "41001"
        assert obs.wind_speed_ms == 5.0
        assert obs.wind_gust_ms == 6.0
        assert obs.wave_height_m == 1.2
        assert obs.dominant_wave_period_s == 8.0
        assert obs.average_wave_period_s == 5.5
        assert obs.pressure_hpa == 1015.0
        assert obs.air_temp_c == 22.5
        assert obs.sea_surface_temp_c == 24.0
        assert obs.wind_direction_deg == 180
        assert obs.wave_direction_deg == 170

    def test_parse_realtime_data_with_missing(self):
        """Test parsing handles missing values correctly."""
        client = NDBCClient()

        sample_data = """#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
2024 01 15 12 00 180  5.0  MM    MM   MM    MM  MM  1015.0  MM    24.0   MM   MM   MM    MM"""

        observations = client._parse_realtime_data("41001", sample_data)
        assert len(observations) == 1

        obs = observations[0]
        assert obs.wind_speed_ms == 5.0
        assert obs.wind_gust_ms is None
        assert obs.wave_height_m is None
        assert obs.sea_surface_temp_c == 24.0

    def test_parse_realtime_data_empty(self):
        """Test parsing empty data returns empty list."""
        client = NDBCClient()
        observations = client._parse_realtime_data("41001", "")
        assert observations == []

    def test_parse_realtime_data_header_only(self):
        """Test parsing data with only headers returns empty list."""
        client = NDBCClient()

        sample_data = """#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft"""

        observations = client._parse_realtime_data("41001", sample_data)
        assert observations == []

    def test_parse_value_missing_values(self):
        """Test _parse_value handles missing value indicators."""
        client = NDBCClient()

        # Test various missing value indicators
        assert client._parse_value(["MM"], 0) is None
        assert client._parse_value(["999"], 0) is None
        assert client._parse_value(["9999"], 0) is None
        assert client._parse_value(["99.0"], 0) is None

        # Test valid value
        assert client._parse_value(["10.5"], 0) == 10.5

        # Test out of range index
        assert client._parse_value(["10.5"], 5) is None


class TestNDBCStation:
    """Tests for NDBCStation dataclass."""

    def test_station_creation(self):
        """Test NDBCStation can be created with minimal data."""
        station = NDBCStation(
            station_id="41001",
            name="Test Buoy",
            latitude=28.5,
            longitude=-88.5,
        )

        assert station.station_id == "41001"
        assert station.name == "Test Buoy"
        assert station.latitude == 28.5
        assert station.longitude == -88.5
        assert station.station_type == StationType.BUOY
        assert station.is_active is True

    def test_station_creation_full(self):
        """Test NDBCStation with all fields."""
        station = NDBCStation(
            station_id="41001",
            name="Test Buoy",
            latitude=28.5,
            longitude=-88.5,
            water_depth_m=100.0,
            station_type=StationType.CMAN,
            owner="NDBC",
            is_active=False,
            metadata={"program": "NDBC"},
        )

        assert station.water_depth_m == 100.0
        assert station.station_type == StationType.CMAN
        assert station.owner == "NDBC"
        assert station.is_active is False
        assert station.metadata == {"program": "NDBC"}


class TestNDBCObservation:
    """Tests for NDBCObservation dataclass."""

    def test_observation_creation_minimal(self):
        """Test NDBCObservation with minimal data."""
        obs = NDBCObservation(
            station_id="41001",
            observation_time=datetime(2024, 1, 15, 12, 0),
        )

        assert obs.station_id == "41001"
        assert obs.observation_time == datetime(2024, 1, 15, 12, 0)
        assert obs.wind_speed_ms is None
        assert obs.wave_height_m is None

    def test_observation_creation_full(self):
        """Test NDBCObservation with all fields."""
        obs = NDBCObservation(
            station_id="41001",
            observation_time=datetime(2024, 1, 15, 12, 0),
            wind_speed_ms=5.0,
            wind_direction_deg=180,
            wind_gust_ms=6.0,
            wave_height_m=1.2,
            dominant_wave_period_s=8.0,
            average_wave_period_s=5.5,
            wave_direction_deg=170,
            sea_surface_temp_c=24.0,
            air_temp_c=22.5,
            dew_point_c=18.0,
            pressure_hpa=1015.0,
            pressure_tendency_hpa=-0.5,
            visibility_nm=10.0,
            water_level_ft=2.5,
        )

        assert obs.wind_speed_ms == 5.0
        assert obs.wave_height_m == 1.2
        assert obs.sea_surface_temp_c == 24.0


class TestOpenMeteoClient:
    """Tests for OpenMeteoClient class."""

    def test_client_initialization(self):
        """Test Open-Meteo client initializes correctly."""
        client = OpenMeteoClient()
        assert client.source == DataSource.OPEN_METEO
        assert "open-meteo" in client.base_url.lower()


class TestCOOPSClient:
    """Tests for COOPSClient class."""

    def test_client_initialization(self):
        """Test CO-OPS client initializes correctly."""
        client = COOPSClient()
        assert client.source == DataSource.COOPS
        assert "tidesandcurrents" in client.base_url.lower()


class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_fetch_result_creation(self):
        """Test FetchResult can be created."""
        from worldenergydata.metocean.clients import FetchResult

        result = FetchResult(
            data=[{"test": "data"}],
            source=DataSource.NDBC,
            fetch_time=datetime.utcnow(),
            records_count=1,
        )

        assert len(result.data) == 1
        assert result.source == DataSource.NDBC
        assert result.records_count == 1
        assert result.had_errors is False
        assert result.error_messages == []

    def test_fetch_result_with_errors(self):
        """Test FetchResult with errors."""
        from worldenergydata.metocean.clients import FetchResult

        result = FetchResult(
            data=[],
            source=DataSource.NDBC,
            fetch_time=datetime.utcnow(),
            records_count=0,
            had_errors=True,
            error_messages=["Error 1", "Error 2"],
        )

        assert result.had_errors is True
        assert len(result.error_messages) == 2
