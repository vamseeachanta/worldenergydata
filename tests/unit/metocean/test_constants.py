"""Tests for Metocean module constants and enumerations."""

from worldenergydata.metocean.constants import (
    COOPS_BASE_URL,
    DATA_SOURCE_URLS,
    DEFAULT_FETCH_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_DELAY,
    DEFAULT_RETRY_DELAY,
    GOM_BBOX,
    MAX_CONCURRENT_REQUESTS,
    MAX_DEPTH_M,
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_DEPTH_M,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    NDBC_BASE_URL,
    NDBC_COLUMNS,
    NDBC_MISSING_VALUES,
    NDBC_STATION_TYPES,
    PARAMETER_RANGES,
    REGION_BOUNDS,
    RETRYABLE_HTTP_CODES,
    TEST_STATIONS,
    DataSource,
    DataType,
    FetchStatus,
    MetoceanParameter,
    ParameterType,
    QualityFlag,
    SeaState,
    StationType,
)


class TestDataSource:
    def test_ndbc(self):
        assert DataSource.NDBC.value == "ndbc"

    def test_coops(self):
        assert DataSource.COOPS.value == "coops"

    def test_all_are_strings(self):
        for member in DataSource:
            assert isinstance(member.value, str)

    def test_member_count(self):
        assert len(DataSource) >= 10


class TestDataType:
    def test_realtime(self):
        assert DataType.REALTIME.value == "realtime"

    def test_historical(self):
        assert DataType.HISTORICAL.value == "historical"

    def test_forecast(self):
        assert DataType.FORECAST.value == "forecast"


class TestStationType:
    def test_buoy(self):
        assert StationType.BUOY.value == "buoy"

    def test_dart(self):
        assert StationType.DART.value == "dart"

    def test_member_count(self):
        assert len(StationType) >= 15


class TestQualityFlag:
    def test_good(self):
        assert QualityFlag.GOOD.value == "good"

    def test_bad(self):
        assert QualityFlag.BAD.value == "bad"

    def test_missing(self):
        assert QualityFlag.MISSING.value == "missing"


class TestMetoceanParameter:
    def test_wave_height(self):
        assert MetoceanParameter.WAVE_HEIGHT.value == "wave_height_m"

    def test_wind_speed(self):
        assert MetoceanParameter.WIND_SPEED.value == "wind_speed_ms"

    def test_sea_surface_temp(self):
        assert MetoceanParameter.SEA_SURFACE_TEMP.value == "sea_surface_temp_c"


class TestParameterType:
    def test_wave_height(self):
        assert ParameterType.WAVE_HEIGHT.value == "wave_height"

    def test_salinity(self):
        assert ParameterType.SALINITY.value == "salinity"

    def test_member_count(self):
        assert len(ParameterType) >= 20


class TestSeaState:
    def test_calm(self):
        assert SeaState.CALM == 0

    def test_phenomenal(self):
        assert SeaState.PHENOMENAL == 8

    def test_ordering(self):
        assert SeaState.CALM < SeaState.PHENOMENAL


class TestFetchStatus:
    def test_success(self):
        assert FetchStatus.SUCCESS.value == "success"

    def test_failed(self):
        assert FetchStatus.FAILED.value == "failed"

    def test_rate_limited(self):
        assert FetchStatus.RATE_LIMITED.value == "rate_limited"


class TestConstants:
    def test_coordinate_bounds(self):
        assert MIN_LATITUDE == -90.0
        assert MAX_LATITUDE == 90.0
        assert MIN_LONGITUDE == -180.0
        assert MAX_LONGITUDE == 180.0

    def test_depth_bounds(self):
        assert MIN_DEPTH_M == 0.0
        assert MAX_DEPTH_M == 12000.0

    def test_gom_bbox(self):
        assert GOM_BBOX == (-98.0, -88.0, 25.0, 31.0)

    def test_api_base_urls(self):
        assert "ndbc.noaa.gov" in NDBC_BASE_URL
        assert "tidesandcurrents" in COOPS_BASE_URL

    def test_data_source_urls(self):
        assert "NDBC" in DATA_SOURCE_URLS
        assert "COOPS" in DATA_SOURCE_URLS

    def test_parameter_ranges(self):
        assert "wave_height_m" in PARAMETER_RANGES
        assert PARAMETER_RANGES["wave_height_m"]["min"] == 0.0
        assert PARAMETER_RANGES["wave_height_m"]["max"] == 30.0

    def test_ndbc_columns(self):
        assert NDBC_COLUMNS["WVHT"] == "wave_height_m"
        assert NDBC_COLUMNS["WSPD"] == "wind_speed_ms"

    def test_ndbc_missing_values(self):
        assert "MM" in NDBC_MISSING_VALUES
        assert "999" in NDBC_MISSING_VALUES

    def test_ndbc_station_types(self):
        assert NDBC_STATION_TYPES["buoy"] == StationType.BUOY

    def test_region_bounds(self):
        assert "GOM" in REGION_BOUNDS
        gom = REGION_BOUNDS["GOM"]
        assert gom["lat_min"] == 18.0

    def test_test_stations(self):
        assert "NDBC" in TEST_STATIONS
        assert TEST_STATIONS["NDBC"]["primary"] == "42001"

    def test_retryable_codes(self):
        assert 429 in RETRYABLE_HTTP_CODES
        assert 503 in RETRYABLE_HTTP_CODES

    def test_defaults(self):
        assert DEFAULT_FETCH_TIMEOUT == 30
        assert DEFAULT_RATE_LIMIT_DELAY == 1.0
        assert MAX_CONCURRENT_REQUESTS == 5
        assert DEFAULT_MAX_RETRIES == 3
        assert DEFAULT_RETRY_DELAY == 5
