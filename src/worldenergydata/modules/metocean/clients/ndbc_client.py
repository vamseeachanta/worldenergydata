# ABOUTME: NOAA NDBC (National Data Buoy Center) client for fetching buoy data.
# ABOUTME: Parses NDBC text and XML formats for stations, real-time, and historical data.

"""
NOAA NDBC (National Data Buoy Center) Client

Fetches buoy data from NDBC including:
- Station metadata from XML listings
- Real-time meteorological data (last 45 days)
- Spectral wave data
- Historical data archives

NDBC uses text file formats (not JSON), requiring custom parsing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from worldenergydata.modules.metocean.clients.base_client import BaseClient, FetchResult
from worldenergydata.modules.metocean.constants import (
    NDBC_BASE_URL,
    NDBC_MISSING_VALUES,
    NDBC_STATION_TYPES,
    DataSource,
    StationType,
)
from worldenergydata.modules.metocean.exceptions import ParsingError


@dataclass
class NDBCStation:
    """
    NDBC station metadata.

    Represents a buoy or station in the NDBC network with its
    location and characteristics.

    Attributes:
        station_id: Unique station identifier (e.g., "41001")
        name: Human-readable station name
        latitude: Station latitude in decimal degrees
        longitude: Station longitude in decimal degrees
        water_depth_m: Water depth at station in meters (if known)
        station_type: Type of station (buoy, CMAN, DART, etc.)
        owner: Organization that owns/operates the station
        is_active: Whether the station is currently reporting
        metadata: Additional station metadata
    """

    station_id: str
    name: str
    latitude: float
    longitude: float
    water_depth_m: Optional[float] = None
    station_type: StationType = StationType.BUOY
    owner: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NDBCObservation:
    """
    NDBC observation data point.

    Represents a single observation from an NDBC station containing
    all available meteorological and oceanographic parameters.

    All parameters are optional as not all stations report all values.

    Attributes:
        station_id: Station that made the observation
        observation_time: UTC timestamp of the observation
        wind_speed_ms: Wind speed in m/s
        wind_direction_deg: Wind direction in degrees (from)
        wind_gust_ms: Wind gust speed in m/s
        wave_height_m: Significant wave height in meters
        dominant_wave_period_s: Dominant wave period in seconds
        average_wave_period_s: Average wave period in seconds
        wave_direction_deg: Mean wave direction in degrees
        sea_surface_temp_c: Sea surface temperature in Celsius
        air_temp_c: Air temperature in Celsius
        dew_point_c: Dew point temperature in Celsius
        pressure_hpa: Barometric pressure in hPa
        pressure_tendency_hpa: 3-hour pressure tendency in hPa
        visibility_nm: Visibility in nautical miles
        water_level_ft: Water level in feet (tide stations)
    """

    station_id: str
    observation_time: datetime
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_gust_ms: Optional[float] = None
    wave_height_m: Optional[float] = None
    dominant_wave_period_s: Optional[float] = None
    average_wave_period_s: Optional[float] = None
    wave_direction_deg: Optional[float] = None
    sea_surface_temp_c: Optional[float] = None
    air_temp_c: Optional[float] = None
    dew_point_c: Optional[float] = None
    pressure_hpa: Optional[float] = None
    pressure_tendency_hpa: Optional[float] = None
    visibility_nm: Optional[float] = None
    water_level_ft: Optional[float] = None


class NDBCClient(BaseClient):
    """
    Client for NOAA NDBC buoy data.

    Fetches and parses data from the National Data Buoy Center including:
    - Station listings and metadata from XML
    - Real-time observations (last 45 days) from text files
    - Historical data archives

    Example usage:
        with NDBCClient() as client:
            # Get all active stations
            result = client.fetch_stations()
            for station in result.data:
                print(f"{station.station_id}: {station.name}")

            # Get real-time data for a specific buoy
            data = client.fetch_realtime("41001")
            for obs in data.data[:5]:
                print(f"{obs.observation_time}: {obs.wave_height_m}m waves")
    """

    def __init__(self) -> None:
        """Initialize NDBC client with base URL."""
        super().__init__(
            source=DataSource.NDBC,
            base_url=NDBC_BASE_URL,
            name="ndbc_client",
        )

    def fetch_stations(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        active_only: bool = True,
    ) -> FetchResult[NDBCStation]:
        """
        Fetch list of NDBC stations.

        Retrieves station metadata from the NDBC active stations XML feed.
        Optionally filters by bounding box and active status.

        Args:
            bbox: Optional bounding box (lon_min, lon_max, lat_min, lat_max)
                  to filter stations by location
            active_only: Only return active stations (default True)

        Returns:
            FetchResult containing list of NDBCStation objects

        Example:
            # Get Gulf of Mexico stations
            gom_bbox = (-98.0, -80.0, 18.0, 31.0)
            result = client.fetch_stations(bbox=gom_bbox)
        """
        url = "/activestations.xml"
        response = self._get(url)

        try:
            soup = BeautifulSoup(response.text, "xml")
        except Exception as e:
            raise ParsingError(
                source=self.source.value,
                reason=f"Failed to parse stations XML: {str(e)}",
            )

        stations: List[NDBCStation] = []
        errors: List[str] = []

        for station_elem in soup.find_all("station"):
            try:
                station = self._parse_station_element(station_elem)

                # Apply bbox filter if provided
                if bbox is not None:
                    lon_min, lon_max, lat_min, lat_max = bbox
                    if not (
                        lon_min <= station.longitude <= lon_max
                        and lat_min <= station.latitude <= lat_max
                    ):
                        continue

                # Apply active filter if provided
                if active_only and not station.is_active:
                    continue

                stations.append(station)

            except Exception as e:
                station_id = station_elem.get("id", "unknown")
                errors.append(f"Failed to parse station {station_id}: {str(e)}")
                self.logger.warning(f"Failed to parse station {station_id}: {e}")
                continue

        return FetchResult(
            data=stations,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(stations),
            had_errors=len(errors) > 0,
            error_messages=errors,
        )

    def _parse_station_element(self, elem: Any) -> NDBCStation:
        """
        Parse a station XML element into NDBCStation.

        Args:
            elem: BeautifulSoup station element

        Returns:
            NDBCStation object

        Raises:
            ValueError: If required attributes are missing
        """
        station_id = elem.get("id")
        if not station_id:
            raise ValueError("Station element missing id attribute")

        lat_str = elem.get("lat")
        lon_str = elem.get("lon")
        if not lat_str or not lon_str:
            raise ValueError(f"Station {station_id} missing lat/lon")

        latitude = float(lat_str)
        longitude = float(lon_str)
        name = elem.get("name", station_id)
        owner = elem.get("owner")

        # Parse station type from 'type' attribute
        type_str = elem.get("type", "buoy").lower()
        station_type = NDBC_STATION_TYPES.get(type_str, StationType.OTHER)

        # Parse water depth if available
        water_depth = None
        elev = elem.get("elev")
        if elev:
            try:
                water_depth = abs(float(elev))
            except ValueError:
                pass

        # Collect additional metadata
        metadata: Dict[str, Any] = {}
        for attr in ["pgm", "met", "currents", "waterquality", "dart"]:
            if elem.get(attr):
                metadata[attr] = elem.get(attr)

        return NDBCStation(
            station_id=station_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            water_depth_m=water_depth,
            station_type=station_type,
            owner=owner,
            is_active=True,  # Only active stations appear in activestations.xml
            metadata=metadata,
        )

    def fetch_realtime(
        self,
        station_id: str,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[NDBCObservation]:
        """
        Fetch real-time data for a station.

        NDBC provides 45 days of recent data in text format. The standard
        meteorological file includes wind, wave, temperature, and pressure.

        Data format example:
        #YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
        #yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
        2024 01 15 12 00 180  5.0  6.0   1.2   8.0   5.5 170  1015.0  22.5  24.0  18.0   MM   MM    MM

        Args:
            station_id: NDBC station identifier (e.g., "41001")
            parameters: Optional list of parameters to include (not implemented)

        Returns:
            FetchResult containing list of NDBCObservation objects
        """
        url = f"/data/realtime2/{station_id}.txt"
        text = self._get_text(url)

        observations = self._parse_realtime_data(station_id, text)

        return FetchResult(
            data=observations,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(observations),
        )

    def _parse_realtime_data(
        self,
        station_id: str,
        text: str,
    ) -> List[NDBCObservation]:
        """
        Parse NDBC text format real-time data.

        Handles the standard NDBC text format with header rows starting
        with '#' and data rows with space-separated values. Missing values
        are indicated by 'MM' or various '999'/'9999' patterns.

        Args:
            station_id: Station identifier for the observations
            text: Raw text content from NDBC data file

        Returns:
            List of NDBCObservation objects
        """
        observations: List[NDBCObservation] = []
        lines = text.strip().split("\n")

        # Skip header lines (start with #)
        data_lines = [line for line in lines if not line.startswith("#")]

        for line in data_lines:
            parts = line.split()
            if len(parts) < 5:
                continue

            try:
                obs = self._parse_observation_line(station_id, parts)
                if obs is not None:
                    observations.append(obs)
            except (ValueError, IndexError) as e:
                self.logger.warning(
                    f"Failed to parse line for {station_id}: {line[:50]}... ({e})"
                )
                continue

        return observations

    def _parse_observation_line(
        self,
        station_id: str,
        parts: List[str],
    ) -> Optional[NDBCObservation]:
        """
        Parse a single observation line into NDBCObservation.

        Column positions in standard NDBC format:
        0: Year, 1: Month, 2: Day, 3: Hour, 4: Minute
        5: WDIR, 6: WSPD, 7: GST, 8: WVHT, 9: DPD, 10: APD
        11: MWD, 12: PRES, 13: ATMP, 14: WTMP, 15: DEWP
        16: VIS, 17: PTDY, 18: TIDE

        Args:
            station_id: Station identifier
            parts: Space-split line parts

        Returns:
            NDBCObservation or None if parsing fails
        """
        # Parse datetime (first 5 columns)
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = int(parts[3])
        minute = int(parts[4])

        # Handle 2-digit year
        if year < 100:
            year = 2000 + year if year < 50 else 1900 + year

        obs_time = datetime(year, month, day, hour, minute)

        return NDBCObservation(
            station_id=station_id,
            observation_time=obs_time,
            wind_direction_deg=self._parse_value(parts, 5),
            wind_speed_ms=self._parse_value(parts, 6),
            wind_gust_ms=self._parse_value(parts, 7),
            wave_height_m=self._parse_value(parts, 8),
            dominant_wave_period_s=self._parse_value(parts, 9),
            average_wave_period_s=self._parse_value(parts, 10),
            wave_direction_deg=self._parse_value(parts, 11),
            pressure_hpa=self._parse_value(parts, 12),
            air_temp_c=self._parse_value(parts, 13),
            sea_surface_temp_c=self._parse_value(parts, 14),
            dew_point_c=self._parse_value(parts, 15),
            visibility_nm=self._parse_value(parts, 16),
            pressure_tendency_hpa=self._parse_value(parts, 17),
            water_level_ft=self._parse_value(parts, 18),
        )

    def _parse_value(
        self,
        parts: List[str],
        index: int,
    ) -> Optional[float]:
        """
        Parse a value from the data line, handling missing values.

        NDBC uses various indicators for missing data:
        - 'MM' for missing measurements
        - '999', '9999', '99.0', '99.00' for invalid values

        Args:
            parts: Line parts split by whitespace
            index: Column index to parse

        Returns:
            Float value or None if missing/invalid
        """
        if index >= len(parts):
            return None

        val = parts[index]

        # Check for missing value indicators
        if val in NDBC_MISSING_VALUES:
            return None

        try:
            return float(val)
        except ValueError:
            return None

    def fetch_historical(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[NDBCObservation]:
        """
        Fetch historical data from NDBC archives.

        Historical data is available as yearly compressed files. This method
        fetches data for each year in the requested range and combines them.

        Note: Historical data may not be available for all years/stations.

        Args:
            station_id: NDBC station identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            parameters: Optional list of parameters (not implemented)

        Returns:
            FetchResult containing historical observations
        """
        all_observations: List[NDBCObservation] = []
        errors: List[str] = []

        # Fetch data for each year in range
        for year in range(start_date.year, end_date.year + 1):
            try:
                year_obs = self._fetch_historical_year(station_id, year)
                # Filter to requested date range
                filtered = [
                    obs
                    for obs in year_obs
                    if start_date <= obs.observation_time <= end_date
                ]
                all_observations.extend(filtered)
            except Exception as e:
                error_msg = f"Failed to fetch {year} data: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(
                    f"Historical fetch error for {station_id}: {error_msg}"
                )

        # Sort by time
        all_observations.sort(key=lambda x: x.observation_time)

        return FetchResult(
            data=all_observations,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(all_observations),
            had_errors=len(errors) > 0,
            error_messages=errors,
        )

    def _fetch_historical_year(
        self,
        station_id: str,
        year: int,
    ) -> List[NDBCObservation]:
        """
        Fetch historical data for a specific year.

        NDBC historical files are available at:
        /view_text_file.php?filename={station}h{year}.txt.gz&dir=data/historical/stdmet/

        Args:
            station_id: Station identifier
            year: Year to fetch

        Returns:
            List of observations for that year
        """
        url = (
            f"/view_text_file.php?"
            f"filename={station_id}h{year}.txt.gz"
            f"&dir=data/historical/stdmet/"
        )
        text = self._get_text(url)
        return self._parse_realtime_data(station_id, text)

    def get_station_info(self, station_id: str) -> Optional[NDBCStation]:
        """
        Get detailed info for a single station.

        Fetches the station list and returns metadata for the specified
        station if found.

        Args:
            station_id: NDBC station identifier

        Returns:
            NDBCStation object or None if not found
        """
        result = self.fetch_stations(active_only=False)
        for station in result.data:
            if station.station_id.upper() == station_id.upper():
                return station
        return None

    def fetch_spectral(
        self,
        station_id: str,
    ) -> FetchResult[Dict[str, Any]]:
        """
        Fetch spectral wave data for a station.

        NDBC provides detailed spectral wave data including energy
        distribution across frequencies and directions.

        Args:
            station_id: NDBC station identifier

        Returns:
            FetchResult containing spectral data dictionaries
        """
        url = f"/data/realtime2/{station_id}.spec"
        text = self._get_text(url)

        # Parse spectral data (simplified - returns raw parsed data)
        spectral_data = self._parse_spectral_data(station_id, text)

        return FetchResult(
            data=spectral_data,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(spectral_data),
        )

    def _parse_spectral_data(
        self,
        station_id: str,
        text: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse NDBC spectral wave data.

        Spectral data includes frequency-dependent wave energy
        and directional information.

        Args:
            station_id: Station identifier
            text: Raw spectral data text

        Returns:
            List of spectral data dictionaries
        """
        records: List[Dict[str, Any]] = []
        lines = text.strip().split("\n")

        # Skip header lines
        data_lines = [line for line in lines if not line.startswith("#")]

        for line in data_lines:
            parts = line.split()
            if len(parts) < 6:
                continue

            try:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                hour = int(parts[3])
                minute = int(parts[4])

                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year

                obs_time = datetime(year, month, day, hour, minute)

                record = {
                    "station_id": station_id,
                    "observation_time": obs_time,
                    "raw_data": parts[5:],  # Remaining spectral values
                }
                records.append(record)

            except (ValueError, IndexError) as e:
                self.logger.warning(f"Failed to parse spectral line: {e}")
                continue

        return records
