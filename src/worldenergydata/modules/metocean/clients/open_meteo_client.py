# ABOUTME: Open-Meteo Marine API client for fetching marine forecast data.
# ABOUTME: Provides coordinate-based marine forecasts with no authentication required.

"""
Open-Meteo Marine API Client

Fetches marine forecast data from Open-Meteo API including:
- Wave height, direction, and period
- Swell parameters (height, direction, period)
- Wind wave parameters
- Ocean current velocity and direction

Open-Meteo provides free marine data without authentication,
supporting forecasts up to 16 days and historical data up to 92 days back.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from worldenergydata.modules.metocean.clients.base_client import BaseClient, FetchResult
from worldenergydata.modules.metocean.constants import DataSource
from worldenergydata.modules.metocean.exceptions import ParsingError

# Open-Meteo base URL without the endpoint path
OPEN_METEO_MARINE_BASE_URL = "https://marine-api.open-meteo.com"


@dataclass
class OpenMeteoForecast:
    """
    Open-Meteo marine forecast data point.

    Represents a single forecast or historical data point from Open-Meteo
    containing wave, swell, wind wave, and ocean current parameters.

    All parameters are optional as data availability varies by location
    and requested variables.

    Attributes:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        forecast_time: UTC timestamp of the forecast/observation
        wave_height_m: Significant wave height in meters
        wave_direction_deg: Wave direction in degrees
        wave_period_s: Wave period in seconds
        swell_wave_height_m: Swell wave height in meters
        swell_wave_direction_deg: Swell wave direction in degrees
        swell_wave_period_s: Swell wave period in seconds
        wind_wave_height_m: Wind wave height in meters
        wind_wave_direction_deg: Wind wave direction in degrees
        wind_wave_period_s: Wind wave period in seconds
        current_speed_ms: Ocean current speed in m/s
        current_direction_deg: Ocean current direction in degrees
        sea_surface_temp_c: Sea surface temperature in Celsius (if available)
    """

    latitude: float
    longitude: float
    forecast_time: datetime

    # Wave parameters
    wave_height_m: Optional[float] = None
    wave_direction_deg: Optional[float] = None
    wave_period_s: Optional[float] = None

    # Swell parameters
    swell_wave_height_m: Optional[float] = None
    swell_wave_direction_deg: Optional[float] = None
    swell_wave_period_s: Optional[float] = None

    # Wind wave parameters
    wind_wave_height_m: Optional[float] = None
    wind_wave_direction_deg: Optional[float] = None
    wind_wave_period_s: Optional[float] = None

    # Ocean current
    current_speed_ms: Optional[float] = None
    current_direction_deg: Optional[float] = None

    # Sea surface temperature
    sea_surface_temp_c: Optional[float] = None


class OpenMeteoClient(BaseClient):
    """
    Client for Open-Meteo Marine API.

    Fetches marine forecast and historical data from Open-Meteo. Unlike
    station-based data sources, Open-Meteo provides data for any ocean
    coordinates.

    Features:
    - Coordinate-based queries (no station IDs required)
    - Forecasts up to 16 days ahead
    - Historical data up to 92 days back
    - No authentication required
    - Free tier with no rate limits (be respectful)

    Example usage:
        with OpenMeteoClient() as client:
            # Get 7-day forecast for Gulf of Mexico
            result = client.fetch_forecast(
                latitude=28.5,
                longitude=-88.5,
                forecast_days=7
            )
            for forecast in result.data[:5]:
                print(f"{forecast.forecast_time}: {forecast.wave_height_m}m waves")

            # Get historical data
            from datetime import datetime, timedelta
            end = datetime.utcnow()
            start = end - timedelta(days=30)
            historical = client.fetch_historical(
                latitude=28.5,
                longitude=-88.5,
                start_date=start,
                end_date=end
            )
    """

    # All available hourly variables from Open-Meteo Marine API
    ALL_HOURLY_VARS = [
        "wave_height",
        "wave_direction",
        "wave_period",
        "wind_wave_height",
        "wind_wave_direction",
        "wind_wave_period",
        "swell_wave_height",
        "swell_wave_direction",
        "swell_wave_period",
        "ocean_current_velocity",
        "ocean_current_direction",
    ]

    # Maximum forecast days supported by API
    MAX_FORECAST_DAYS = 16

    # Maximum past days supported by API
    MAX_PAST_DAYS = 92

    def __init__(self) -> None:
        """Initialize Open-Meteo Marine client."""
        super().__init__(
            source=DataSource.OPEN_METEO,
            base_url=OPEN_METEO_MARINE_BASE_URL,
            name="open_meteo_client",
        )

    def fetch_stations(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        active_only: bool = True,
    ) -> FetchResult[Dict[str, Any]]:
        """
        Open-Meteo uses coordinates, not stations.

        This method returns an empty result. Use fetch_forecast() or
        fetch_historical() with specific coordinates instead.

        Args:
            bbox: Not used - Open-Meteo doesn't have stations
            active_only: Not used

        Returns:
            Empty FetchResult
        """
        self.logger.info(
            "Open-Meteo doesn't have stations. " "Use fetch_forecast(lat, lon) instead."
        )
        return FetchResult(
            data=[],
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=0,
        )

    def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 7,
        variables: Optional[List[str]] = None,
    ) -> FetchResult[OpenMeteoForecast]:
        """
        Fetch marine forecast for coordinates.

        Retrieves hourly marine forecast data for the specified coordinates.
        Data includes wave parameters, swell, wind waves, and ocean currents.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            forecast_days: Number of forecast days (1-16, default 7)
            variables: List of variables to fetch (default: all available)

        Returns:
            FetchResult containing list of OpenMeteoForecast objects

        Example:
            result = client.fetch_forecast(28.5, -88.5, forecast_days=3)
            for forecast in result.data:
                print(f"{forecast.forecast_time}: {forecast.wave_height_m}m")
        """
        vars_to_fetch = variables or self.ALL_HOURLY_VARS

        # Clamp forecast days to API maximum
        forecast_days = min(max(forecast_days, 1), self.MAX_FORECAST_DAYS)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(vars_to_fetch),
            "forecast_days": forecast_days,
            "timezone": "GMT",
        }

        self.logger.debug(
            f"Fetching forecast for ({latitude}, {longitude}), " f"{forecast_days} days"
        )

        try:
            response = self._get_json("/v1/marine", params=params)
        except Exception as e:
            self.logger.error(f"Failed to fetch forecast: {e}")
            return FetchResult(
                data=[],
                source=self.source,
                fetch_time=datetime.utcnow(),
                records_count=0,
                had_errors=True,
                error_messages=[str(e)],
            )

        forecasts = self._parse_response(latitude, longitude, response)

        return FetchResult(
            data=forecasts,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(forecasts),
        )

    def fetch_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        variables: Optional[List[str]] = None,
    ) -> FetchResult[OpenMeteoForecast]:
        """
        Fetch historical marine data for coordinates.

        Retrieves historical hourly data for the specified date range.
        Maximum range is 92 days from current date.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            variables: List of variables to fetch (default: all available)

        Returns:
            FetchResult containing list of OpenMeteoForecast objects

        Example:
            from datetime import datetime, timedelta
            end = datetime.utcnow()
            start = end - timedelta(days=30)
            result = client.fetch_historical(28.5, -88.5, start, end)
        """
        vars_to_fetch = variables or self.ALL_HOURLY_VARS

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(vars_to_fetch),
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "timezone": "GMT",
        }

        self.logger.debug(
            f"Fetching historical data for ({latitude}, {longitude}), "
            f"{start_date.date()} to {end_date.date()}"
        )

        try:
            response = self._get_json("/v1/marine", params=params)
        except Exception as e:
            self.logger.error(f"Failed to fetch historical data: {e}")
            return FetchResult(
                data=[],
                source=self.source,
                fetch_time=datetime.utcnow(),
                records_count=0,
                had_errors=True,
                error_messages=[str(e)],
            )

        forecasts = self._parse_response(latitude, longitude, response)

        return FetchResult(
            data=forecasts,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(forecasts),
        )

    def fetch_realtime(
        self,
        station_id: str,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[OpenMeteoForecast]:
        """
        Open-Meteo uses coordinates, not station IDs.

        For real-time data, use fetch_realtime_coords() instead.

        Args:
            station_id: Not used
            parameters: Not used

        Raises:
            NotImplementedError: Always - use fetch_realtime_coords instead
        """
        raise NotImplementedError(
            "Open-Meteo uses coordinates, not station IDs. "
            "Use fetch_realtime_coords(latitude, longitude) or "
            "fetch_forecast(latitude, longitude, forecast_days=1) instead."
        )

    def fetch_realtime_coords(
        self,
        latitude: float,
        longitude: float,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[OpenMeteoForecast]:
        """
        Fetch current/recent forecast for coordinates.

        Convenience method that fetches a 1-day forecast for the
        specified coordinates.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            parameters: List of variables to fetch (default: all available)

        Returns:
            FetchResult containing forecast data for today

        Example:
            result = client.fetch_realtime_coords(28.5, -88.5)
            current = result.data[0]  # Most recent forecast
            print(f"Current wave height: {current.wave_height_m}m")
        """
        return self.fetch_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_days=1,
            variables=parameters,
        )

    def _parse_response(
        self,
        latitude: float,
        longitude: float,
        response: Dict[str, Any],
    ) -> List[OpenMeteoForecast]:
        """
        Parse Open-Meteo API response into forecast objects.

        The API returns data in this format:
        {
            "latitude": 28.5,
            "longitude": -88.5,
            "hourly": {
                "time": ["2024-01-15T00:00", "2024-01-15T01:00", ...],
                "wave_height": [1.2, 1.3, ...],
                "wave_direction": [180, 185, ...],
                ...
            }
        }

        Args:
            latitude: Query latitude
            longitude: Query longitude
            response: Parsed JSON response from API

        Returns:
            List of OpenMeteoForecast objects

        Raises:
            ParsingError: If response format is invalid
        """
        forecasts: List[OpenMeteoForecast] = []

        hourly = response.get("hourly", {})
        times = hourly.get("time", [])

        if not times:
            self.logger.warning("No time data in response")
            return forecasts

        # Use response coordinates if available (API may adjust to nearest point)
        actual_lat = response.get("latitude", latitude)
        actual_lon = response.get("longitude", longitude)

        num_times = len(times)

        for i, time_str in enumerate(times):
            try:
                # Parse ISO 8601 timestamp
                forecast_time = datetime.fromisoformat(time_str)

                forecast = OpenMeteoForecast(
                    latitude=actual_lat,
                    longitude=actual_lon,
                    forecast_time=forecast_time,
                    wave_height_m=self._get_value(hourly, "wave_height", i, num_times),
                    wave_direction_deg=self._get_value(
                        hourly, "wave_direction", i, num_times
                    ),
                    wave_period_s=self._get_value(hourly, "wave_period", i, num_times),
                    swell_wave_height_m=self._get_value(
                        hourly, "swell_wave_height", i, num_times
                    ),
                    swell_wave_direction_deg=self._get_value(
                        hourly, "swell_wave_direction", i, num_times
                    ),
                    swell_wave_period_s=self._get_value(
                        hourly, "swell_wave_period", i, num_times
                    ),
                    wind_wave_height_m=self._get_value(
                        hourly, "wind_wave_height", i, num_times
                    ),
                    wind_wave_direction_deg=self._get_value(
                        hourly, "wind_wave_direction", i, num_times
                    ),
                    wind_wave_period_s=self._get_value(
                        hourly, "wind_wave_period", i, num_times
                    ),
                    current_speed_ms=self._get_value(
                        hourly, "ocean_current_velocity", i, num_times
                    ),
                    current_direction_deg=self._get_value(
                        hourly, "ocean_current_direction", i, num_times
                    ),
                )

                forecasts.append(forecast)

            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse forecast at index {i}: {e}")
                continue

        return forecasts

    def _get_value(
        self,
        hourly: Dict[str, Any],
        key: str,
        index: int,
        expected_length: int,
    ) -> Optional[float]:
        """
        Safely extract a value from hourly data.

        Handles missing keys and out-of-bounds indices gracefully.

        Args:
            hourly: Hourly data dictionary
            key: Variable key to extract
            index: Time index
            expected_length: Expected length of data arrays

        Returns:
            Float value or None if not available
        """
        values = hourly.get(key)
        if values is None:
            return None

        if not isinstance(values, list):
            return None

        if index >= len(values):
            return None

        value = values[index]

        # Handle null/None values in API response
        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None
