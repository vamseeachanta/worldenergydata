# ABOUTME: MET Norway (Norwegian Meteorological Institute) client for ocean and weather forecasts
# ABOUTME: Fetches wave, current, SST, wind, and atmospheric data from MET Norway's free API

"""
MET Norway (Norwegian Meteorological Institute) Client

Fetches ocean and weather forecast data from MET Norway's free API.
Good coverage for North Atlantic, Arctic, and Nordic seas.

API Documentation: https://api.met.no/
No authentication required (but User-Agent header required).
Rate limit: ~20 requests/second
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from worldenergydata.metocean.clients.base_client import BaseClient, FetchResult
from worldenergydata.metocean.constants import MET_NORWAY_BASE_URL, DataSource


@dataclass
class MetNorwayForecast:
    """
    MET Norway forecast data point.

    Contains ocean and weather parameters for a specific time and location.
    Ocean parameters include waves, currents, and sea surface temperature.
    Weather parameters include wind, pressure, temperature, and humidity.

    Attributes:
        latitude: Latitude of forecast point
        longitude: Longitude of forecast point
        forecast_time: Time of forecast
        updated_at: When the forecast was last updated
        wave_height_m: Significant wave height in meters
        wave_direction_deg: Wave direction in degrees (from)
        wave_period_s: Mean wave period in seconds
        sea_surface_temp_c: Sea surface temperature in Celsius
        current_speed_ms: Current speed in m/s
        current_direction_deg: Current direction in degrees (to)
        wind_speed_ms: Wind speed in m/s
        wind_direction_deg: Wind direction in degrees (from)
        wind_gust_ms: Wind gust speed in m/s
        air_temp_c: Air temperature in Celsius
        pressure_hpa: Sea level pressure in hPa
        humidity_percent: Relative humidity as percentage
        cloud_cover_percent: Cloud cover as percentage
    """

    latitude: float
    longitude: float
    forecast_time: datetime
    updated_at: Optional[datetime] = None

    # Ocean parameters
    wave_height_m: Optional[float] = None
    wave_direction_deg: Optional[float] = None
    wave_period_s: Optional[float] = None
    sea_surface_temp_c: Optional[float] = None
    current_speed_ms: Optional[float] = None
    current_direction_deg: Optional[float] = None

    # Weather parameters
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_gust_ms: Optional[float] = None
    air_temp_c: Optional[float] = None
    pressure_hpa: Optional[float] = None
    humidity_percent: Optional[float] = None
    cloud_cover_percent: Optional[float] = None


class MetNorwayClient(BaseClient):
    """
    Client for MET Norway weather and ocean forecast API.

    MET Norway provides free access to weather and ocean forecast data.
    Good coverage for North Atlantic, Arctic, and Nordic seas.

    Features:
        - Ocean forecasts (waves, currents, SST)
        - Weather forecasts (wind, temp, pressure)
        - No authentication required
        - Good Arctic/North Atlantic coverage

    Note: Requires User-Agent header with contact information per
    MET Norway Terms of Service.

    Example:
        >>> client = MetNorwayClient()
        >>> result = client.fetch_ocean_forecast(60.0, 5.0)  # Bergen, Norway
        >>> for forecast in result.data:
        ...     print(f"{forecast.forecast_time}: {forecast.wave_height_m}m waves")
    """

    OCEAN_ENDPOINT = "/oceanforecast/2.0/complete"
    WEATHER_ENDPOINT = "/locationforecast/2.0/complete"

    def __init__(self) -> None:
        """Initialize MET Norway client with required headers."""
        super().__init__(
            source=DataSource.MET_NORWAY,
            base_url=MET_NORWAY_BASE_URL,
            name="met_norway_client",
        )
        # MET Norway requires User-Agent with contact info per Terms of Service
        self.client.headers["User-Agent"] = (
            "WorldEnergyData/1.0 (https://github.com/worldenergydata)"
        )

    def fetch_ocean_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> FetchResult[MetNorwayForecast]:
        """
        Fetch ocean forecast for coordinates.

        Returns forecast data including wave height, period, direction,
        sea surface temperature, and ocean currents.

        Args:
            latitude: Latitude (-90 to 90)
            longitude: Longitude (-180 to 180)

        Returns:
            FetchResult containing list of MetNorwayForecast objects

        Raises:
            HTTPError: If API request fails
            ParsingError: If response parsing fails
        """
        self._validate_coordinates(latitude, longitude)

        url = f"{self.base_url}{self.OCEAN_ENDPOINT}"
        params = {"lat": latitude, "lon": longitude}

        self.logger.info(f"Fetching ocean forecast for ({latitude}, {longitude})")
        response = self._get_json(url, params=params)

        forecasts = self._parse_ocean_response(latitude, longitude, response)

        return FetchResult(
            data=forecasts,
            source=self.source,
            fetch_time=datetime.now(timezone.utc),
            records_count=len(forecasts),
        )

    def fetch_weather_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> FetchResult[MetNorwayForecast]:
        """
        Fetch weather forecast for coordinates.

        Returns forecast data including wind speed, direction, gusts,
        air temperature, pressure, humidity, and cloud cover.

        Args:
            latitude: Latitude (-90 to 90)
            longitude: Longitude (-180 to 180)

        Returns:
            FetchResult containing list of MetNorwayForecast objects

        Raises:
            HTTPError: If API request fails
            ParsingError: If response parsing fails
        """
        self._validate_coordinates(latitude, longitude)

        url = f"{self.base_url}{self.WEATHER_ENDPOINT}"
        params = {"lat": latitude, "lon": longitude}

        self.logger.info(f"Fetching weather forecast for ({latitude}, {longitude})")
        response = self._get_json(url, params=params)

        forecasts = self._parse_weather_response(latitude, longitude, response)

        return FetchResult(
            data=forecasts,
            source=self.source,
            fetch_time=datetime.now(timezone.utc),
            records_count=len(forecasts),
        )

    def fetch_combined_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> FetchResult[MetNorwayForecast]:
        """
        Fetch both ocean and weather forecasts and merge them.

        Returns combined forecasts with all available parameters from
        both endpoints merged by forecast time.

        Args:
            latitude: Latitude (-90 to 90)
            longitude: Longitude (-180 to 180)

        Returns:
            FetchResult containing combined forecast data

        Raises:
            HTTPError: If API request fails
            ParsingError: If response parsing fails
        """
        self.logger.info(f"Fetching combined forecast for ({latitude}, {longitude})")

        ocean_result = self.fetch_ocean_forecast(latitude, longitude)
        weather_result = self.fetch_weather_forecast(latitude, longitude)

        # Merge forecasts by time
        combined = self._merge_forecasts(ocean_result.data, weather_result.data)

        # Combine any errors from both fetches
        error_messages = ocean_result.error_messages + weather_result.error_messages
        had_errors = ocean_result.had_errors or weather_result.had_errors

        return FetchResult(
            data=combined,
            source=self.source,
            fetch_time=datetime.now(timezone.utc),
            records_count=len(combined),
            had_errors=had_errors,
            error_messages=error_messages,
        )

    def _validate_coordinates(self, latitude: float, longitude: float) -> None:
        """
        Validate coordinate ranges.

        Args:
            latitude: Latitude to validate
            longitude: Longitude to validate

        Raises:
            ValueError: If coordinates are out of valid range
        """
        if not -90.0 <= latitude <= 90.0:
            raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
        if not -180.0 <= longitude <= 180.0:
            raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

    def _parse_timestamp(self, time_str: str) -> datetime:
        """
        Parse ISO 8601 timestamp from MET Norway API.

        Args:
            time_str: ISO format timestamp string

        Returns:
            Parsed datetime object with timezone info
        """
        # Handle both "Z" and explicit timezone formats
        if time_str.endswith("Z"):
            time_str = time_str[:-1] + "+00:00"
        return datetime.fromisoformat(time_str)

    def _parse_ocean_response(
        self,
        latitude: float,
        longitude: float,
        response: Dict[str, Any],
    ) -> List[MetNorwayForecast]:
        """
        Parse MET Norway ocean forecast GeoJSON response.

        Args:
            latitude: Request latitude
            longitude: Request longitude
            response: API response dictionary

        Returns:
            List of MetNorwayForecast objects with ocean parameters
        """
        forecasts = []

        properties = response.get("properties", {})
        timeseries = properties.get("timeseries", [])

        # Extract update time from metadata
        meta = properties.get("meta", {})
        updated_at_str = meta.get("updated_at")
        updated_at = None
        if updated_at_str:
            updated_at = self._parse_timestamp(updated_at_str)

        for entry in timeseries:
            time_str = entry.get("time")
            if not time_str:
                continue

            forecast_time = self._parse_timestamp(time_str)
            data = entry.get("data", {}).get("instant", {}).get("details", {})

            forecasts.append(
                MetNorwayForecast(
                    latitude=latitude,
                    longitude=longitude,
                    forecast_time=forecast_time,
                    updated_at=updated_at,
                    wave_height_m=data.get("sea_surface_wave_significant_height"),
                    wave_direction_deg=data.get("sea_surface_wave_from_direction"),
                    wave_period_s=data.get("sea_surface_wave_mean_period"),
                    sea_surface_temp_c=data.get("sea_water_temperature"),
                    current_speed_ms=data.get("sea_water_speed"),
                    current_direction_deg=data.get("sea_water_to_direction"),
                )
            )

        self.logger.debug(f"Parsed {len(forecasts)} ocean forecast entries")
        return forecasts

    def _parse_weather_response(
        self,
        latitude: float,
        longitude: float,
        response: Dict[str, Any],
    ) -> List[MetNorwayForecast]:
        """
        Parse MET Norway weather forecast GeoJSON response.

        Args:
            latitude: Request latitude
            longitude: Request longitude
            response: API response dictionary

        Returns:
            List of MetNorwayForecast objects with weather parameters
        """
        forecasts = []

        properties = response.get("properties", {})
        timeseries = properties.get("timeseries", [])

        # Extract update time from metadata
        meta = properties.get("meta", {})
        updated_at_str = meta.get("updated_at")
        updated_at = None
        if updated_at_str:
            updated_at = self._parse_timestamp(updated_at_str)

        for entry in timeseries:
            time_str = entry.get("time")
            if not time_str:
                continue

            forecast_time = self._parse_timestamp(time_str)
            data = entry.get("data", {}).get("instant", {}).get("details", {})

            forecasts.append(
                MetNorwayForecast(
                    latitude=latitude,
                    longitude=longitude,
                    forecast_time=forecast_time,
                    updated_at=updated_at,
                    wind_speed_ms=data.get("wind_speed"),
                    wind_direction_deg=data.get("wind_from_direction"),
                    wind_gust_ms=data.get("wind_speed_of_gust"),
                    air_temp_c=data.get("air_temperature"),
                    pressure_hpa=data.get("air_pressure_at_sea_level"),
                    humidity_percent=data.get("relative_humidity"),
                    cloud_cover_percent=data.get("cloud_area_fraction"),
                )
            )

        self.logger.debug(f"Parsed {len(forecasts)} weather forecast entries")
        return forecasts

    def _merge_forecasts(
        self,
        ocean: List[MetNorwayForecast],
        weather: List[MetNorwayForecast],
    ) -> List[MetNorwayForecast]:
        """
        Merge ocean and weather forecasts by forecast time.

        Weather parameters are merged into ocean forecast records where
        timestamps match. Ocean forecasts without matching weather data
        are preserved with only ocean parameters.

        Args:
            ocean: List of ocean forecasts
            weather: List of weather forecasts

        Returns:
            List of merged forecasts with both ocean and weather data
        """
        # Create lookup by forecast time
        weather_by_time: Dict[datetime, MetNorwayForecast] = {
            f.forecast_time: f for f in weather
        }

        merged = []
        for ocean_fc in ocean:
            weather_fc = weather_by_time.get(ocean_fc.forecast_time)
            if weather_fc:
                # Merge weather data into ocean forecast
                ocean_fc.wind_speed_ms = weather_fc.wind_speed_ms
                ocean_fc.wind_direction_deg = weather_fc.wind_direction_deg
                ocean_fc.wind_gust_ms = weather_fc.wind_gust_ms
                ocean_fc.air_temp_c = weather_fc.air_temp_c
                ocean_fc.pressure_hpa = weather_fc.pressure_hpa
                ocean_fc.humidity_percent = weather_fc.humidity_percent
                ocean_fc.cloud_cover_percent = weather_fc.cloud_cover_percent
            merged.append(ocean_fc)

        self.logger.debug(
            f"Merged {len(merged)} forecasts "
            f"({len(ocean)} ocean, {len(weather)} weather)"
        )
        return merged

    # Required abstract methods from BaseClient

    def fetch_stations(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        active_only: bool = True,
    ) -> FetchResult[Any]:
        """
        Fetch available stations.

        MET Norway uses coordinate-based queries rather than stations.
        This method returns an empty result.

        Args:
            bbox: Optional bounding box (ignored)
            active_only: Only active stations (ignored)

        Returns:
            Empty FetchResult
        """
        self.logger.info("MET Norway uses coordinate queries, not stations")
        return FetchResult(
            data=[],
            source=self.source,
            fetch_time=datetime.now(timezone.utc),
            records_count=0,
        )

    def fetch_realtime(
        self,
        station_id: str,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[Any]:
        """
        Fetch real-time data for a station.

        MET Norway uses coordinate-based queries. Use fetch_ocean_forecast()
        or fetch_weather_forecast() with latitude/longitude instead.

        Args:
            station_id: Station identifier (not used)
            parameters: Optional parameters (not used)

        Raises:
            NotImplementedError: Always, as MET Norway uses coordinate queries
        """
        raise NotImplementedError(
            "Use fetch_ocean_forecast(lat, lon) or "
            "fetch_weather_forecast(lat, lon) for MET Norway"
        )

    def fetch_realtime_coords(
        self,
        latitude: float,
        longitude: float,
    ) -> FetchResult[MetNorwayForecast]:
        """
        Fetch current forecast for coordinates.

        Convenience method that returns combined ocean and weather forecast
        for the specified location.

        Args:
            latitude: Latitude (-90 to 90)
            longitude: Longitude (-180 to 180)

        Returns:
            FetchResult containing combined forecast data
        """
        return self.fetch_combined_forecast(latitude, longitude)

    def fetch_historical(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[Any]:
        """
        Fetch historical data for a station.

        MET Norway only provides forecast data, not historical observations.
        For historical data, use NDBC or other observation-based sources.

        Args:
            station_id: Station identifier
            start_date: Start of date range
            end_date: End of date range
            parameters: Optional parameters to fetch

        Raises:
            NotImplementedError: Always, as MET Norway only provides forecasts
        """
        raise NotImplementedError(
            "MET Norway only provides forecast data. "
            "For historical data, use NDBC or CO-OPS clients."
        )
