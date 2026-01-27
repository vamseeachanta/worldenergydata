# ABOUTME: Tests for metocean constants and enumerations.
# ABOUTME: Validates enum values, geographic bounds, and parameter ranges.

"""Tests for metocean constants"""

import pytest


class TestDataSourceEnum:
    """Tests for DataSource enumeration."""

    def test_data_source_values(self):
        """Test DataSource enum values."""
        from worldenergydata.modules.metocean.constants import DataSource

        assert DataSource.NDBC.value == "ndbc"
        assert DataSource.COOPS.value == "coops"
        assert DataSource.OPEN_METEO.value == "open_meteo"
        assert DataSource.ERDDAP.value == "erddap"
        assert DataSource.CMEMS.value == "cmems"

    def test_data_source_membership(self):
        """Test DataSource enum membership."""
        from worldenergydata.modules.metocean.constants import DataSource

        assert "ndbc" in [ds.value for ds in DataSource]
        assert "coops" in [ds.value for ds in DataSource]


class TestDataTypeEnum:
    """Tests for DataType enumeration."""

    def test_data_type_values(self):
        """Test DataType enum values."""
        from worldenergydata.modules.metocean.constants import DataType

        assert DataType.REALTIME.value == "realtime"
        assert DataType.HISTORICAL.value == "historical"
        assert DataType.FORECAST.value == "forecast"


class TestStationTypeEnum:
    """Tests for StationType enumeration."""

    def test_station_type_values(self):
        """Test StationType enum values."""
        from worldenergydata.modules.metocean.constants import StationType

        assert StationType.BUOY.value == "buoy"
        assert StationType.COASTAL.value == "coastal"
        assert StationType.PLATFORM.value == "platform"
        assert StationType.CMAN.value == "cman"
        assert StationType.DART.value == "dart"
        assert StationType.TIDE_GAUGE.value == "tide_gauge"


class TestQualityFlagEnum:
    """Tests for QualityFlag enumeration."""

    def test_quality_flag_values(self):
        """Test QualityFlag enum values."""
        from worldenergydata.modules.metocean.constants import QualityFlag

        assert QualityFlag.GOOD.value == "good"
        assert QualityFlag.SUSPECT.value == "suspect"
        assert QualityFlag.BAD.value == "bad"
        assert QualityFlag.MISSING.value == "missing"


class TestMetoceanParameterEnum:
    """Tests for MetoceanParameter enumeration."""

    def test_parameter_values(self):
        """Test MetoceanParameter enum values."""
        from worldenergydata.modules.metocean.constants import MetoceanParameter

        assert MetoceanParameter.WAVE_HEIGHT.value == "wave_height_m"
        assert MetoceanParameter.WIND_SPEED.value == "wind_speed_ms"
        assert MetoceanParameter.SEA_SURFACE_TEMP.value == "sea_surface_temp_c"
        assert MetoceanParameter.WATER_LEVEL.value == "water_level_m"


class TestSeaStateEnum:
    """Tests for SeaState enumeration (Douglas scale)."""

    def test_sea_state_values(self):
        """Test SeaState enum values."""
        from worldenergydata.modules.metocean.constants import SeaState

        assert SeaState.CALM == 0
        assert SeaState.SLIGHT == 2
        assert SeaState.MODERATE == 3
        assert SeaState.ROUGH == 4
        assert SeaState.PHENOMENAL == 8


class TestGeographicBounds:
    """Tests for geographic bounding boxes."""

    def test_gom_bbox(self):
        """Test Gulf of Mexico bounding box."""
        from worldenergydata.modules.metocean.constants import GOM_BBOX

        lon_min, lon_max, lat_min, lat_max = GOM_BBOX

        assert lon_min == -98.0
        assert lon_max == -88.0
        assert lat_min == 25.0
        assert lat_max == 31.0

    def test_gom_bbox_contains_valid_region(self):
        """Test that GOM bbox contains expected region."""
        from worldenergydata.modules.metocean.constants import GOM_BBOX

        lon_min, lon_max, lat_min, lat_max = GOM_BBOX

        # Check that longitude range is west of Prime Meridian (negative)
        assert lon_min < 0
        assert lon_max < 0
        assert lon_min < lon_max

        # Check latitude is in northern hemisphere
        assert lat_min > 0
        assert lat_max > 0
        assert lat_min < lat_max

    def test_region_bounds_keys(self):
        """Test that all expected regions are defined."""
        from worldenergydata.modules.metocean.constants import REGION_BOUNDS

        expected_regions = [
            "GOM",
            "ATLANTIC",
            "PACIFIC",
            "ALASKA",
            "CARIBBEAN",
            "NORTH_SEA",
        ]

        for region in expected_regions:
            assert region in REGION_BOUNDS
            assert "lat_min" in REGION_BOUNDS[region]
            assert "lat_max" in REGION_BOUNDS[region]
            assert "lon_min" in REGION_BOUNDS[region]
            assert "lon_max" in REGION_BOUNDS[region]


class TestParameterRanges:
    """Tests for parameter validation ranges."""

    def test_parameter_ranges_exist(self):
        """Test that parameter ranges are defined."""
        from worldenergydata.modules.metocean.constants import PARAMETER_RANGES

        assert "wave_height_m" in PARAMETER_RANGES
        assert "wind_speed_ms" in PARAMETER_RANGES
        assert "sea_surface_temp_c" in PARAMETER_RANGES

    def test_parameter_ranges_have_min_max(self):
        """Test that parameter ranges have min and max."""
        from worldenergydata.modules.metocean.constants import PARAMETER_RANGES

        for param, ranges in PARAMETER_RANGES.items():
            assert "min" in ranges, f"Missing min for {param}"
            assert "max" in ranges, f"Missing max for {param}"
            assert ranges["min"] <= ranges["max"], f"Invalid range for {param}"

    def test_wave_height_range(self):
        """Test wave height reasonable range."""
        from worldenergydata.modules.metocean.constants import PARAMETER_RANGES

        ranges = PARAMETER_RANGES["wave_height_m"]
        assert ranges["min"] == 0.0  # Waves can't be negative
        assert ranges["max"] >= 20.0  # Should allow for large storm waves

    def test_pressure_range(self):
        """Test atmospheric pressure reasonable range."""
        from worldenergydata.modules.metocean.constants import PARAMETER_RANGES

        ranges = PARAMETER_RANGES["pressure_hpa"]
        # Should include extreme values (record lows in hurricanes, highs)
        assert ranges["min"] < 900  # Hurricane Patricia was ~872 hPa
        assert ranges["max"] > 1050  # High pressure systems


class TestNDBCConstants:
    """Tests for NDBC-specific constants."""

    def test_ndbc_missing_values(self):
        """Test NDBC missing value indicators."""
        from worldenergydata.modules.metocean.constants import NDBC_MISSING_VALUES

        assert "MM" in NDBC_MISSING_VALUES
        assert "999" in NDBC_MISSING_VALUES
        assert "9999" in NDBC_MISSING_VALUES

    def test_ndbc_columns_mapping(self):
        """Test NDBC column name mapping."""
        from worldenergydata.modules.metocean.constants import NDBC_COLUMNS

        assert NDBC_COLUMNS["WDIR"] == "wind_direction_deg"
        assert NDBC_COLUMNS["WSPD"] == "wind_speed_ms"
        assert NDBC_COLUMNS["WVHT"] == "wave_height_m"
        assert NDBC_COLUMNS["ATMP"] == "air_temp_c"
        assert NDBC_COLUMNS["WTMP"] == "sea_surface_temp_c"

    def test_ndbc_station_types_mapping(self):
        """Test NDBC station type mapping."""
        from worldenergydata.modules.metocean.constants import (
            NDBC_STATION_TYPES,
            StationType,
        )

        assert NDBC_STATION_TYPES["buoy"] == StationType.BUOY
        assert NDBC_STATION_TYPES["cman"] == StationType.CMAN
        assert NDBC_STATION_TYPES["dart"] == StationType.DART


class TestAPIConstants:
    """Tests for API-related constants."""

    def test_base_urls_defined(self):
        """Test that base URLs are defined."""
        from worldenergydata.modules.metocean.constants import (
            COOPS_BASE_URL,
            NDBC_BASE_URL,
            OPEN_METEO_BASE_URL,
        )

        assert "ndbc.noaa.gov" in NDBC_BASE_URL
        assert "tidesandcurrents" in COOPS_BASE_URL
        assert "open-meteo.com" in OPEN_METEO_BASE_URL

    def test_retryable_http_codes(self):
        """Test retryable HTTP status codes."""
        from worldenergydata.modules.metocean.constants import RETRYABLE_HTTP_CODES

        # Server errors should be retryable
        assert 500 in RETRYABLE_HTTP_CODES
        assert 502 in RETRYABLE_HTTP_CODES
        assert 503 in RETRYABLE_HTTP_CODES
        assert 504 in RETRYABLE_HTTP_CODES

        # Rate limiting should be retryable
        assert 429 in RETRYABLE_HTTP_CODES

        # Client errors should not be retryable (except 429)
        assert 400 not in RETRYABLE_HTTP_CODES
        assert 404 not in RETRYABLE_HTTP_CODES


class TestDefaultValues:
    """Tests for default values."""

    def test_default_fetch_timeout(self):
        """Test default fetch timeout."""
        from worldenergydata.modules.metocean.constants import DEFAULT_FETCH_TIMEOUT

        assert DEFAULT_FETCH_TIMEOUT == 30

    def test_default_max_retries(self):
        """Test default max retries."""
        from worldenergydata.modules.metocean.constants import DEFAULT_MAX_RETRIES

        assert DEFAULT_MAX_RETRIES == 3

    def test_max_concurrent_requests(self):
        """Test max concurrent requests."""
        from worldenergydata.modules.metocean.constants import MAX_CONCURRENT_REQUESTS

        assert MAX_CONCURRENT_REQUESTS == 5

    def test_coordinate_bounds(self):
        """Test coordinate validation bounds."""
        from worldenergydata.modules.metocean.constants import (
            MAX_LATITUDE,
            MAX_LONGITUDE,
            MIN_LATITUDE,
            MIN_LONGITUDE,
        )

        assert MIN_LATITUDE == -90.0
        assert MAX_LATITUDE == 90.0
        assert MIN_LONGITUDE == -180.0
        assert MAX_LONGITUDE == 180.0
