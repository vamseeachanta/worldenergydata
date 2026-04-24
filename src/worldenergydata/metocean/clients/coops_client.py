# ABOUTME: NOAA CO-OPS (Center for Operational Oceanographic Products and Services) client.
# ABOUTME: Fetches tide, water level, and current data from NOAA CO-OPS API.

"""
NOAA CO-OPS (Center for Operational Oceanographic Products and Services) Client

Fetches tide, water level, and current data from NOAA CO-OPS API including:
- Water level observations and predictions
- Tide predictions and verified data
- Current speed and direction measurements
- Station metadata from the CO-OPS network

CO-OPS stations provide critical data for coastal and offshore operations,
particularly for tide-sensitive activities and navigation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from worldenergydata.metocean.clients.base_client import BaseClient, FetchResult
from worldenergydata.metocean.constants import (
    COOPS_BASE_URL,
    DataSource,
    StationType,
)
from worldenergydata.metocean.exceptions import DataNotFoundError


@dataclass
class COOPSStation:
    """
    CO-OPS station metadata.

    Represents a tide gauge or current meter in the CO-OPS network
    with its location and available data products.

    Attributes:
        station_id: Unique station identifier (e.g., "8761724")
        name: Human-readable station name
        latitude: Station latitude in decimal degrees
        longitude: Station longitude in decimal degrees
        state: State abbreviation (e.g., "LA" for Louisiana)
        station_type: Type of station (coastal, tide_gauge, current_meter)
        has_water_level: Whether station provides water level data
        has_currents: Whether station provides current data
        has_predictions: Whether tidal predictions are available
        reference_datum: Primary datum for the station (e.g., "MLLW")
        metadata: Additional station metadata
    """

    station_id: str
    name: str
    latitude: float
    longitude: float
    state: Optional[str] = None
    station_type: StationType = StationType.COASTAL
    has_water_level: bool = False
    has_currents: bool = False
    has_predictions: bool = False
    reference_datum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class COOPSWaterLevel:
    """
    CO-OPS water level observation.

    Represents a single water level measurement from a CO-OPS station.
    Water levels are typically referenced to a vertical datum like MLLW.

    Attributes:
        station_id: Station that made the observation
        observation_time: UTC timestamp of the observation
        water_level_m: Water level in meters relative to datum
        sigma: Standard deviation of measurement (meters)
        quality_flag: Quality flag (v=verified, p=preliminary)
        datum: Vertical datum reference (e.g., "MLLW", "MSL")
    """

    station_id: str
    observation_time: datetime
    water_level_m: float
    sigma: Optional[float] = None
    quality_flag: str = "v"
    datum: str = "MLLW"


@dataclass
class COOPSCurrent:
    """
    CO-OPS current observation.

    Represents a single current measurement from a CO-OPS current meter.
    Currents may be measured at multiple depths (bins).

    Attributes:
        station_id: Station that made the observation
        observation_time: UTC timestamp of the observation
        speed_ms: Current speed in meters per second
        direction_deg: Current direction in degrees (direction flow is going)
        bin_depth_m: Depth of measurement bin in meters (if applicable)
        quality_flag: Quality flag for the observation
    """

    station_id: str
    observation_time: datetime
    speed_ms: float
    direction_deg: float
    bin_depth_m: Optional[float] = None
    quality_flag: str = "v"


@dataclass
class COOPSTidePrediction:
    """
    CO-OPS tide prediction.

    Represents a predicted tide height at a specified time.

    Attributes:
        station_id: Station for the prediction
        prediction_time: UTC timestamp for the prediction
        water_level_m: Predicted water level in meters
        tide_type: Type of tide (H=high, L=low, or None for interval)
        datum: Vertical datum reference
    """

    station_id: str
    prediction_time: datetime
    water_level_m: float
    tide_type: Optional[str] = None
    datum: str = "MLLW"


class COOPSClient(BaseClient):
    """
    Client for NOAA CO-OPS tides and currents data.

    Fetches and parses data from the Center for Operational Oceanographic
    Products and Services (CO-OPS) API including:
    - Water level observations and verified data
    - Tide predictions (harmonic-based)
    - Current speed and direction measurements
    - Station metadata and datums

    Example usage:
        with COOPSClient() as client:
            # Get all stations in Gulf of Mexico
            gom_bbox = (-98.0, -80.0, 18.0, 31.0)
            result = client.fetch_stations(bbox=gom_bbox)
            for station in result.data:
                logger.info(f"{station.station_id}: {station.name}")

            # Get water level data for Grand Isle, LA
            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 7)
            data = client.fetch_water_level("8761724", start, end)
            for obs in data.data[:5]:
                logger.info(f"{obs.observation_time}: {obs.water_level_m}m")

            # Get tide predictions
            preds = client.fetch_tide_predictions("8761724", start, end)
    """

    # CO-OPS API endpoints
    DATA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    STATIONS_URL = (
        "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
    )
    STATION_DETAIL_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}.json"  # noqa: E501

    # Valid products for the API
    PRODUCTS = {
        "water_level": "Preliminary/verified water levels",
        "hourly_height": "Hourly height data",
        "predictions": "Tide predictions",
        "currents": "Current speed and direction",
        "currents_predictions": "Current predictions",
        "daily_mean": "Daily mean water levels",
        "monthly_mean": "Monthly mean water levels",
        "high_low": "High/low tide data",
    }

    # Valid datums for water level data
    DATUMS = ["MLLW", "MSL", "NAVD", "MHHW", "MHW", "MTL", "MLW", "STND"]

    def __init__(self) -> None:
        """Initialize CO-OPS client with base URL."""
        super().__init__(
            source=DataSource.COOPS,
            base_url=COOPS_BASE_URL,
            name="coops_client",
        )

    def fetch_stations(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        active_only: bool = True,
    ) -> FetchResult[COOPSStation]:
        """
        Fetch list of CO-OPS stations.

        Retrieves station metadata from the CO-OPS MDAPI. Optionally filters
        by bounding box and active status.

        Args:
            bbox: Optional bounding box (lon_min, lon_max, lat_min, lat_max)
                  to filter stations by location
            active_only: Only return active stations (default True)

        Returns:
            FetchResult containing list of COOPSStation objects

        Example:
            # Get Gulf of Mexico stations
            gom_bbox = (-98.0, -80.0, 18.0, 31.0)
            result = client.fetch_stations(bbox=gom_bbox)
        """
        response = self._get_json(self.STATIONS_URL)

        stations: List[COOPSStation] = []
        errors: List[str] = []

        station_list = response.get("stations", [])
        if not station_list:
            self.logger.warning("No stations found in CO-OPS response")

        for station_data in station_list:
            try:
                station = self._parse_station(station_data)

                # Apply bbox filter if provided
                if bbox is not None:
                    lon_min, lon_max, lat_min, lat_max = bbox
                    if not (
                        lon_min <= station.longitude <= lon_max
                        and lat_min <= station.latitude <= lat_max
                    ):
                        continue

                stations.append(station)

            except (KeyError, ValueError, TypeError) as e:
                station_id = station_data.get("id", "unknown")
                error_msg = f"Failed to parse station {station_id}: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
                continue

        return FetchResult(
            data=stations,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(stations),
            had_errors=len(errors) > 0,
            error_messages=errors,
        )

    def _parse_station(self, data: Dict[str, Any]) -> COOPSStation:
        """
        Parse station data from API response.

        Args:
            data: Station data dictionary from API

        Returns:
            COOPSStation object

        Raises:
            KeyError: If required fields are missing
            ValueError: If coordinate parsing fails
        """
        station_id = str(data["id"])
        name = data.get("name", station_id)

        lat = data.get("lat")
        lng = data.get("lng")
        if lat is None or lng is None:
            raise ValueError(f"Station {station_id} missing coordinates")

        latitude = float(lat)
        longitude = float(lng)

        # Determine station type based on available sensors
        sensors = data.get("sensors", {}) or {}
        has_water_level = (
            any(s.get("sensor") == "A1" for s in sensors.get("sensors", []))
            if isinstance(sensors.get("sensors"), list)
            else False
        )
        has_currents = (
            any(
                "current" in str(s.get("sensor", "")).lower()
                for s in sensors.get("sensors", [])
            )
            if isinstance(sensors.get("sensors"), list)
            else False
        )

        # Determine station type
        station_type = StationType.COASTAL
        if has_currents:
            station_type = StationType.CURRENT_METER
        elif has_water_level:
            station_type = StationType.TIDE_GAUGE

        # Check for tide predictions availability
        has_predictions = data.get("tidal", False)

        # Build metadata
        metadata: Dict[str, Any] = {}
        for key in ["observedst", "timezone", "timezonecorr", "affiliations"]:
            if data.get(key):
                metadata[key] = data[key]

        return COOPSStation(
            station_id=station_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            state=data.get("state"),
            station_type=station_type,
            has_water_level=has_water_level or data.get("tidal", False),
            has_currents=has_currents,
            has_predictions=has_predictions,
            reference_datum=data.get("reference_datum"),
            metadata=metadata,
        )

    def fetch_water_level(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        datum: str = "MLLW",
        verified: bool = True,
    ) -> FetchResult[COOPSWaterLevel]:
        """
        Fetch water level data for a station.

        Retrieves observed water level data from CO-OPS. Data is available
        in verified (quality controlled) or preliminary form.

        Args:
            station_id: CO-OPS station identifier (e.g., "8761724")
            start_date: Start of date range
            end_date: End of date range
            datum: Vertical datum (MLLW, MSL, NAVD, etc.)
            verified: If True, request verified data; else preliminary

        Returns:
            FetchResult containing list of COOPSWaterLevel objects

        Example:
            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 7)
            result = client.fetch_water_level("8761724", start, end)
        """
        if datum not in self.DATUMS:
            self.logger.warning(
                f"Unknown datum '{datum}', using MLLW. Valid: {self.DATUMS}"
            )
            datum = "MLLW"

        params = {
            "station": station_id,
            "product": "water_level",
            "begin_date": start_date.strftime("%Y%m%d %H:%M"),
            "end_date": end_date.strftime("%Y%m%d %H:%M"),
            "datum": datum,
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
            "application": "WorldEnergyData",
        }

        response = self._get_json(self.DATA_URL, params=params)

        # Check for API errors
        if "error" in response:
            error_msg = response["error"].get("message", "Unknown error")
            raise DataNotFoundError(
                source=self.source.value,
                message=f"CO-OPS API error: {error_msg}",
            )

        observations: List[COOPSWaterLevel] = []
        errors: List[str] = []

        for record in response.get("data", []):
            try:
                obs = self._parse_water_level(station_id, record, datum)
                observations.append(obs)
            except (KeyError, ValueError) as e:
                errors.append(f"Failed to parse record: {str(e)}")
                continue

        return FetchResult(
            data=observations,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(observations),
            had_errors=len(errors) > 0,
            error_messages=errors,
        )

    def _parse_water_level(
        self,
        station_id: str,
        record: Dict[str, Any],
        datum: str,
    ) -> COOPSWaterLevel:
        """
        Parse a single water level record.

        CO-OPS returns timestamps in format "2024-01-15 12:00".

        Args:
            station_id: Station identifier
            record: Data record from API response
            datum: Datum used for the request

        Returns:
            COOPSWaterLevel object
        """
        # Parse timestamp (format: "2024-01-15 12:00")
        time_str = record["t"]
        obs_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")

        # Parse water level value
        value_str = record.get("v")
        if value_str is None or value_str == "":
            raise ValueError("Missing water level value")
        water_level = float(value_str)

        # Parse optional sigma (standard deviation)
        sigma = None
        if record.get("s"):
            try:
                sigma = float(record["s"])
            except (ValueError, TypeError):
                pass

        # Quality flag (f field)
        quality_flag = record.get("f", "v")

        return COOPSWaterLevel(
            station_id=station_id,
            observation_time=obs_time,
            water_level_m=water_level,
            sigma=sigma,
            quality_flag=quality_flag,
            datum=datum,
        )

    def fetch_currents(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        bin_num: Optional[int] = None,
    ) -> FetchResult[COOPSCurrent]:
        """
        Fetch current data for a station.

        Retrieves current speed and direction observations. Some stations
        have multiple depth bins for current measurements.

        Args:
            station_id: CO-OPS station identifier
            start_date: Start of date range
            end_date: End of date range
            bin_num: Optional bin number for multi-bin stations

        Returns:
            FetchResult containing list of COOPSCurrent objects
        """
        params = {
            "station": station_id,
            "product": "currents",
            "begin_date": start_date.strftime("%Y%m%d %H:%M"),
            "end_date": end_date.strftime("%Y%m%d %H:%M"),
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
            "application": "WorldEnergyData",
        }

        if bin_num is not None:
            params["bin"] = str(bin_num)

        response = self._get_json(self.DATA_URL, params=params)

        # Check for API errors
        if "error" in response:
            error_msg = response["error"].get("message", "Unknown error")
            raise DataNotFoundError(
                source=self.source.value,
                message=f"CO-OPS API error: {error_msg}",
            )

        currents: List[COOPSCurrent] = []
        errors: List[str] = []

        for record in response.get("data", []):
            try:
                current = self._parse_current(station_id, record)
                currents.append(current)
            except (KeyError, ValueError) as e:
                errors.append(f"Failed to parse current record: {str(e)}")
                continue

        return FetchResult(
            data=currents,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(currents),
            had_errors=len(errors) > 0,
            error_messages=errors,
        )

    def _parse_current(
        self,
        station_id: str,
        record: Dict[str, Any],
    ) -> COOPSCurrent:
        """
        Parse a single current record.

        Args:
            station_id: Station identifier
            record: Data record from API response

        Returns:
            COOPSCurrent object
        """
        # Parse timestamp
        time_str = record["t"]
        obs_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")

        # Parse speed (s field for currents)
        speed_str = record.get("s")
        if speed_str is None or speed_str == "":
            raise ValueError("Missing current speed value")
        speed = float(speed_str)

        # Parse direction (d field)
        direction_str = record.get("d")
        if direction_str is None or direction_str == "":
            raise ValueError("Missing current direction value")
        direction = float(direction_str)

        # Parse optional bin depth
        bin_depth = None
        if record.get("b"):
            try:
                bin_depth = float(record["b"])
            except (ValueError, TypeError):
                pass

        return COOPSCurrent(
            station_id=station_id,
            observation_time=obs_time,
            speed_ms=speed,
            direction_deg=direction,
            bin_depth_m=bin_depth,
            quality_flag=record.get("f", "v"),
        )

    def fetch_tide_predictions(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        datum: str = "MLLW",
        interval: str = "hilo",
    ) -> FetchResult[COOPSTidePrediction]:
        """
        Fetch tide predictions for a station.

        Retrieves harmonic tide predictions. Can be high/low only
        or at regular intervals.

        Args:
            station_id: CO-OPS station identifier
            start_date: Start of date range
            end_date: End of date range
            datum: Vertical datum (MLLW, MSL, etc.)
            interval: "hilo" for high/low only, or minutes (6, 10, 15, etc.)

        Returns:
            FetchResult containing list of COOPSTidePrediction objects
        """
        params = {
            "station": station_id,
            "product": "predictions",
            "begin_date": start_date.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
            "datum": datum,
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
            "application": "WorldEnergyData",
            "interval": interval,
        }

        response = self._get_json(self.DATA_URL, params=params)

        # Check for API errors
        if "error" in response:
            error_msg = response["error"].get("message", "Unknown error")
            raise DataNotFoundError(
                source=self.source.value,
                message=f"CO-OPS API error: {error_msg}",
            )

        predictions: List[COOPSTidePrediction] = []
        errors: List[str] = []

        for record in response.get("predictions", []):
            try:
                pred = self._parse_prediction(station_id, record, datum)
                predictions.append(pred)
            except (KeyError, ValueError) as e:
                errors.append(f"Failed to parse prediction: {str(e)}")
                continue

        return FetchResult(
            data=predictions,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(predictions),
            had_errors=len(errors) > 0,
            error_messages=errors,
        )

    def _parse_prediction(
        self,
        station_id: str,
        record: Dict[str, Any],
        datum: str,
    ) -> COOPSTidePrediction:
        """
        Parse a single tide prediction record.

        Args:
            station_id: Station identifier
            record: Prediction record from API response
            datum: Datum used for the request

        Returns:
            COOPSTidePrediction object
        """
        # Parse timestamp
        time_str = record["t"]
        pred_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")

        # Parse water level
        value_str = record.get("v")
        if value_str is None or value_str == "":
            raise ValueError("Missing prediction value")
        water_level = float(value_str)

        # Parse tide type (H=high, L=low) if present
        tide_type = record.get("type")

        return COOPSTidePrediction(
            station_id=station_id,
            prediction_time=pred_time,
            water_level_m=water_level,
            tide_type=tide_type,
            datum=datum,
        )

    def fetch_realtime(
        self,
        station_id: str,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[COOPSWaterLevel]:
        """
        Fetch real-time (recent 48 hours) water level data.

        Convenience method implementing the BaseClient abstract method.
        Returns the last 48 hours of water level observations.

        Args:
            station_id: CO-OPS station identifier
            parameters: Optional parameters (not used, for interface compat)

        Returns:
            FetchResult containing recent water level observations
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=48)
        return self.fetch_water_level(station_id, start_date, end_date)

    def fetch_historical(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[COOPSWaterLevel]:
        """
        Fetch historical water level data.

        Convenience method implementing the BaseClient abstract method.
        For long date ranges, data is fetched in chunks to avoid API limits.

        Args:
            station_id: CO-OPS station identifier
            start_date: Start of date range
            end_date: End of date range
            parameters: Optional parameters (not used, for interface compat)

        Returns:
            FetchResult containing historical water level observations
        """
        # CO-OPS limits requests to ~31 days, so chunk if needed
        max_days = 31
        total_days = (end_date - start_date).days

        if total_days <= max_days:
            return self.fetch_water_level(station_id, start_date, end_date)

        # Fetch in chunks
        all_observations: List[COOPSWaterLevel] = []
        errors: List[str] = []
        chunk_start = start_date

        while chunk_start < end_date:
            chunk_end = min(chunk_start + timedelta(days=max_days), end_date)

            try:
                result = self.fetch_water_level(station_id, chunk_start, chunk_end)
                all_observations.extend(result.data)
                if result.had_errors:
                    errors.extend(result.error_messages)
            except Exception as e:
                error_msg = (
                    f"Failed to fetch {chunk_start.date()} to {chunk_end.date()}: {e}"
                )
                errors.append(error_msg)
                self.logger.warning(error_msg)

            chunk_start = chunk_end

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

    def get_station_info(self, station_id: str) -> Optional[COOPSStation]:
        """
        Get detailed info for a single station.

        Fetches detailed metadata for a specific station using the
        station detail endpoint.

        Args:
            station_id: CO-OPS station identifier

        Returns:
            COOPSStation object or None if not found
        """
        url = self.STATION_DETAIL_URL.format(station_id=station_id)
        try:
            response = self._get_json(url)
            stations = response.get("stations", [])
            if stations:
                return self._parse_station(stations[0])
        except Exception as e:
            self.logger.warning(f"Failed to fetch station {station_id}: {e}")

        return None

    def fetch_datums(
        self,
        station_id: str,
    ) -> Dict[str, float]:
        """
        Fetch available datums and their elevations for a station.

        CO-OPS provides datum conversion information that can be used
        to convert water levels between different reference datums.

        Args:
            station_id: CO-OPS station identifier

        Returns:
            Dictionary mapping datum names to elevations in meters
        """
        url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}/datums.json"  # noqa: E501

        response = self._get_json(url)

        datums: Dict[str, float] = {}
        for datum_data in response.get("datums", []):
            name = datum_data.get("name")
            value = datum_data.get("value")
            if name and value is not None:
                try:
                    datums[name] = float(value)
                except (ValueError, TypeError):
                    pass

        return datums
