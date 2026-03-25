"""Tests for Metocean module validators."""

from datetime import datetime, timedelta

import pytest

from worldenergydata.metocean.constants import DataSource
from worldenergydata.metocean.exceptions import InvalidDataError, ValidationError
from worldenergydata.metocean.utils.validators import (
    validate_bbox,
    validate_coordinates,
    validate_datetime_range,
    validate_parameters,
    validate_positive_number,
    validate_station_id,
)


class TestValidateCoordinates:
    def test_valid(self):
        lat, lon = validate_coordinates(29.0, -90.0)
        assert lat == 29.0
        assert lon == -90.0

    def test_boundary_values(self):
        lat, lon = validate_coordinates(90.0, 180.0)
        assert lat == 90.0
        assert lon == 180.0

    def test_negative_boundary(self):
        lat, lon = validate_coordinates(-90.0, -180.0)
        assert lat == -90.0
        assert lon == -180.0

    def test_none_not_allowed(self):
        with pytest.raises(ValidationError):
            validate_coordinates(None, -90.0)

    def test_none_allowed(self):
        lat, lon = validate_coordinates(None, None, allow_none=True)
        assert lat is None
        assert lon is None

    def test_lat_too_high(self):
        with pytest.raises(InvalidDataError):
            validate_coordinates(91.0, -90.0)

    def test_lat_too_low(self):
        with pytest.raises(InvalidDataError):
            validate_coordinates(-91.0, -90.0)

    def test_lon_too_high(self):
        with pytest.raises(InvalidDataError):
            validate_coordinates(29.0, 181.0)

    def test_lon_too_low(self):
        with pytest.raises(InvalidDataError):
            validate_coordinates(29.0, -181.0)

    def test_returns_float(self):
        lat, lon = validate_coordinates(29, -90)
        assert isinstance(lat, float)
        assert isinstance(lon, float)


class TestValidateBbox:
    def test_valid(self):
        result = validate_bbox((-98.0, -88.0, 25.0, 31.0))
        assert result == (-98.0, -88.0, 25.0, 31.0)

    def test_wrong_length(self):
        with pytest.raises(ValidationError):
            validate_bbox((1.0, 2.0, 3.0))

    def test_lat_min_greater_than_max(self):
        with pytest.raises(InvalidDataError):
            validate_bbox((-98.0, -88.0, 31.0, 25.0))

    def test_invalid_lat_out_of_range(self):
        with pytest.raises(InvalidDataError):
            validate_bbox((-98.0, -88.0, -91.0, 31.0))

    def test_invalid_lon_out_of_range(self):
        with pytest.raises(InvalidDataError):
            validate_bbox((-200.0, -88.0, 25.0, 31.0))


class TestValidateDatetimeRange:
    def test_valid_range(self):
        start = datetime(2020, 1, 1)
        end = datetime(2020, 12, 31)
        s, e = validate_datetime_range(start, end)
        assert s == start
        assert e == end

    def test_start_after_end(self):
        start = datetime(2021, 1, 1)
        end = datetime(2020, 1, 1)
        with pytest.raises(InvalidDataError):
            validate_datetime_range(start, end)

    def test_max_range_exceeded(self):
        start = datetime(2020, 1, 1)
        end = datetime(2020, 12, 31)
        with pytest.raises(InvalidDataError):
            validate_datetime_range(start, end, max_range_days=30)

    def test_max_range_ok(self):
        start = datetime(2020, 1, 1)
        end = datetime(2020, 1, 15)
        s, e = validate_datetime_range(start, end, max_range_days=30)
        assert s == start

    def test_future_allowed_by_default(self):
        future = datetime.utcnow() + timedelta(days=30)
        s, e = validate_datetime_range(datetime.utcnow(), future)
        assert e == future

    def test_future_not_allowed_clips_end(self):
        start = datetime(2020, 1, 1)
        future = datetime.utcnow() + timedelta(days=30)
        s, e = validate_datetime_range(
            start, future, allow_future=False
        )
        assert e <= datetime.utcnow() + timedelta(seconds=5)

    def test_future_start_not_allowed(self):
        future_start = datetime.utcnow() + timedelta(days=30)
        future_end = future_start + timedelta(days=10)
        with pytest.raises(InvalidDataError):
            validate_datetime_range(
                future_start, future_end, allow_future=False
            )


class TestValidateStationId:
    def test_valid_generic(self):
        result = validate_station_id("42001")
        assert result == "42001"

    def test_strips_and_uppercases(self):
        result = validate_station_id("  abc  ")
        assert result == "ABC"

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            validate_station_id("")

    def test_ndbc_valid(self):
        result = validate_station_id("42001", source=DataSource.NDBC)
        assert result == "42001"

    def test_ndbc_valid_alpha(self):
        result = validate_station_id("BURL1", source=DataSource.NDBC)
        assert result == "BURL1"

    def test_ndbc_too_short(self):
        with pytest.raises(InvalidDataError):
            validate_station_id("AB", source=DataSource.NDBC)

    def test_ndbc_too_long(self):
        with pytest.raises(InvalidDataError):
            validate_station_id("ABCDEFGH", source=DataSource.NDBC)

    def test_coops_valid(self):
        result = validate_station_id("8761724", source=DataSource.COOPS)
        assert result == "8761724"

    def test_coops_invalid_alpha(self):
        with pytest.raises(InvalidDataError):
            validate_station_id("ABCDEFG", source=DataSource.COOPS)

    def test_coops_wrong_length(self):
        with pytest.raises(InvalidDataError):
            validate_station_id("123456", source=DataSource.COOPS)


class TestValidateParameters:
    def test_valid(self):
        result = validate_parameters(["wave_height", "wind_speed"])
        assert result == ["wave_height", "wind_speed"]

    def test_lowercases(self):
        result = validate_parameters(["WAVE_HEIGHT"])
        assert result == ["wave_height"]

    def test_strips(self):
        result = validate_parameters(["  wind_speed  "])
        assert result == ["wind_speed"]

    def test_empty_list_rejected(self):
        with pytest.raises(ValidationError):
            validate_parameters([])

    def test_allowed_filter(self):
        result = validate_parameters(
            ["wave_height"], allowed=["wave_height", "wind_speed"]
        )
        assert result == ["wave_height"]

    def test_not_in_allowed(self):
        with pytest.raises(InvalidDataError):
            validate_parameters(
                ["temperature"], allowed=["wave_height", "wind_speed"]
            )


class TestValidatePositiveNumber:
    def test_valid_positive(self):
        result = validate_positive_number(5.0, "depth")
        assert result == 5.0

    def test_zero_not_allowed_by_default(self):
        with pytest.raises(InvalidDataError):
            validate_positive_number(0, "depth")

    def test_zero_allowed(self):
        result = validate_positive_number(0, "depth", allow_zero=True)
        assert result == 0.0

    def test_negative_not_allowed(self):
        with pytest.raises(InvalidDataError):
            validate_positive_number(-1, "depth")

    def test_negative_not_allowed_with_zero(self):
        with pytest.raises(InvalidDataError):
            validate_positive_number(-1, "depth", allow_zero=True)

    def test_string_number(self):
        result = validate_positive_number("5.5", "depth")
        assert result == 5.5

    def test_non_numeric_rejected(self):
        with pytest.raises(InvalidDataError):
            validate_positive_number("abc", "depth")

    def test_none_rejected(self):
        with pytest.raises(InvalidDataError):
            validate_positive_number(None, "depth")
