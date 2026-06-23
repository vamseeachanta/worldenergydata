# ABOUTME: ERDDAP client for IOOS/GCOOS oceanographic data servers
# ABOUTME: Fetches tabular and gridded scientific datasets via REST API

"""
ERDDAP Client for IOOS/GCOOS Data

Fetches oceanographic data from ERDDAP servers including IOOS national
and regional associations like GCOOS (Gulf of Mexico). Supports dataset
discovery, metadata queries, and data retrieval in multiple formats.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from worldenergydata.metocean.clients.base_client import BaseClient, FetchResult
from worldenergydata.metocean.constants import DataSource


@dataclass
class ERDDAPDataset:
    """
    ERDDAP dataset metadata.

    Represents a dataset available on an ERDDAP server with its
    spatial/temporal coverage and available variables.

    Attributes:
        dataset_id: Unique identifier for the dataset
        title: Human-readable dataset title
        institution: Organization providing the data
        summary: Description of the dataset
        min_lat: Southern boundary of spatial coverage
        max_lat: Northern boundary of spatial coverage
        min_lon: Western boundary of spatial coverage
        max_lon: Eastern boundary of spatial coverage
        min_time: Start of temporal coverage
        max_time: End of temporal coverage
        variables: List of available variable names
    """

    dataset_id: str
    title: Optional[str] = None
    institution: Optional[str] = None
    summary: Optional[str] = None
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None
    min_time: Optional[datetime] = None
    max_time: Optional[datetime] = None
    variables: List[str] = field(default_factory=list)


@dataclass
class ERDDAPObservation:
    """
    ERDDAP observation data point.

    Represents a single observation from an ERDDAP dataset with
    standard oceanographic parameters.

    Attributes:
        dataset_id: Source dataset identifier
        observation_time: Time of observation
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        station_id: Optional station identifier
        wave_height_m: Significant wave height in meters
        wave_period_s: Wave period in seconds
        wave_direction_deg: Wave direction in degrees
        wind_speed_ms: Wind speed in meters per second
        wind_direction_deg: Wind direction in degrees
        sea_surface_temp_c: Sea surface temperature in Celsius
        current_speed_ms: Current speed in meters per second
        current_direction_deg: Current direction in degrees
        salinity_psu: Salinity in PSU
    """

    dataset_id: str
    observation_time: datetime
    latitude: float
    longitude: float
    station_id: Optional[str] = None

    # Wave parameters
    wave_height_m: Optional[float] = None
    wave_period_s: Optional[float] = None
    wave_direction_deg: Optional[float] = None

    # Wind parameters
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None

    # Temperature and other
    sea_surface_temp_c: Optional[float] = None
    current_speed_ms: Optional[float] = None
    current_direction_deg: Optional[float] = None
    salinity_psu: Optional[float] = None


class ERDDAPClient(BaseClient):
    """
    Client for ERDDAP data servers.

    Provides access to oceanographic data from IOOS ERDDAP servers
    and regional associations. Supports dataset discovery, metadata
    queries, and data retrieval for both tabular and gridded datasets.

    Supported servers:
    - IOOS national: https://erddap.ioos.us/erddap
    - GCOOS regional: https://erddap.gcoos.org/erddap (Gulf of Mexico)
    - CoastWatch: https://coastwatch.pfeg.noaa.gov/erddap

    Example usage:
        >>> client = ERDDAPClient(server="ioos")
        >>> datasets = client.search_datasets("wave")
        >>> data = client.fetch_tabledap("some_dataset_id")
    """

    # Common ERDDAP servers
    SERVERS: Dict[str, str] = {
        "ioos": "https://erddap.ioos.us/erddap",
        "gcoos": "https://erddap.gcoos.org/erddap",
        "coastwatch": "https://coastwatch.pfeg.noaa.gov/erddap",
    }

    # Variable name mappings from ERDDAP to standard attribute names
    VARIABLE_MAPPING: Dict[str, str] = {
        "sea_surface_wave_significant_height": "wave_height_m",
        "wave_height": "wave_height_m",
        "significant_wave_height": "wave_height_m",
        "sea_surface_wave_mean_period": "wave_period_s",
        "wave_period": "wave_period_s",
        "dominant_wave_period": "wave_period_s",
        "sea_surface_wave_from_direction": "wave_direction_deg",
        "wave_direction": "wave_direction_deg",
        "sea_surface_temperature": "sea_surface_temp_c",
        "sst": "sea_surface_temp_c",
        "water_temperature": "sea_surface_temp_c",
        "wind_speed": "wind_speed_ms",
        "wind_from_direction": "wind_direction_deg",
        "wind_direction": "wind_direction_deg",
        "sea_water_speed": "current_speed_ms",
        "current_speed": "current_speed_ms",
        "sea_water_direction": "current_direction_deg",
        "current_direction": "current_direction_deg",
        "sea_water_salinity": "salinity_psu",
        "salinity": "salinity_psu",
    }

    def __init__(self, server: str = "ioos") -> None:
        """
        Initialize the ERDDAP client.

        Args:
            server: Server name ('ioos', 'gcoos', 'coastwatch') or full URL
        """
        base_url = self.SERVERS.get(server, server)
        super().__init__(
            source=DataSource.ERDDAP, base_url=base_url, name=f"erddap_{server}_client"
        )
        self.server = server

    def search_datasets(
        self, search_term: str, bbox: Optional[tuple] = None
    ) -> FetchResult[ERDDAPDataset]:
        """
        Search for datasets matching a term.

        Searches dataset titles, summaries, and keywords for the
        given term. Optionally filters by geographic bounding box.

        Args:
            search_term: Text to search for (e.g., "wave", "temperature")
            bbox: Optional bounding box filter (lon_min, lon_max, lat_min, lat_max)

        Returns:
            FetchResult containing matching ERDDAPDataset objects
        """
        url = f"{self.base_url}/search/index.json"
        params = {"searchFor": search_term}

        if bbox:
            lon_min, lon_max, lat_min, lat_max = bbox
            params["minLon"] = str(lon_min)
            params["maxLon"] = str(lon_max)
            params["minLat"] = str(lat_min)
            params["maxLat"] = str(lat_max)

        response = self._get_json(url, params=params)

        datasets = []
        table = response.get("table", {})
        column_names = table.get("columnNames", [])
        rows = table.get("rows", [])

        col_idx = {name: i for i, name in enumerate(column_names)}

        for row in rows:
            try:
                dataset = ERDDAPDataset(
                    dataset_id=self._get_row_value(row, col_idx, "datasetID"),
                    title=self._get_row_value(row, col_idx, "title"),
                    institution=self._get_row_value(row, col_idx, "institution"),
                    summary=self._get_row_value(row, col_idx, "summary"),
                )
                datasets.append(dataset)
            except (IndexError, KeyError) as e:
                self.logger.warning(f"Failed to parse dataset row: {e}")
                continue

        return FetchResult(
            data=datasets,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(datasets),
        )

    def list_datasets(self) -> FetchResult[ERDDAPDataset]:
        """
        List all available datasets on the server.

        Returns:
            FetchResult containing all ERDDAPDataset objects
        """
        url = f"{self.base_url}/info/index.json"
        response = self._get_json(url)

        datasets = []
        table = response.get("table", {})
        column_names = table.get("columnNames", [])
        rows = table.get("rows", [])

        col_idx = {name: i for i, name in enumerate(column_names)}

        for row in rows:
            try:
                dataset = ERDDAPDataset(
                    dataset_id=self._get_row_value(row, col_idx, "Dataset ID"),
                    title=self._get_row_value(row, col_idx, "Title"),
                )
                datasets.append(dataset)
            except (IndexError, KeyError) as e:
                self.logger.warning(f"Failed to parse dataset row: {e}")
                continue

        return FetchResult(
            data=datasets,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(datasets),
        )

    def get_dataset_info(self, dataset_id: str) -> Optional[ERDDAPDataset]:
        """
        Get detailed information for a specific dataset.

        Retrieves full metadata including available variables,
        spatial bounds, and temporal coverage.

        Args:
            dataset_id: Dataset identifier

        Returns:
            ERDDAPDataset with full metadata, or None if not found
        """
        url = f"{self.base_url}/info/{dataset_id}/index.json"

        try:
            response = self._get_json(url)
            table = response.get("table", {})
            rows = table.get("rows", [])

            metadata: Dict[str, Any] = {}
            variables: List[str] = []

            for row in rows:
                if len(row) >= 5:
                    row_type, var_name, attr_name, _, value = row[:5]
                    if row_type == "attribute" and var_name == "NC_GLOBAL":
                        metadata[attr_name] = value
                    elif row_type == "variable":
                        if var_name not in variables:
                            variables.append(var_name)

            return ERDDAPDataset(
                dataset_id=dataset_id,
                title=metadata.get("title"),
                institution=metadata.get("institution"),
                summary=metadata.get("summary"),
                min_lat=self._parse_float(metadata.get("geospatial_lat_min")),
                max_lat=self._parse_float(metadata.get("geospatial_lat_max")),
                min_lon=self._parse_float(metadata.get("geospatial_lon_min")),
                max_lon=self._parse_float(metadata.get("geospatial_lon_max")),
                min_time=self._parse_time(metadata.get("time_coverage_start")),
                max_time=self._parse_time(metadata.get("time_coverage_end")),
                variables=variables,
            )
        except Exception as e:
            self.logger.warning(f"Failed to get dataset info for {dataset_id}: {e}")
            return None

    def fetch_tabledap(
        self,
        dataset_id: str,
        variables: Optional[List[str]] = None,
        constraints: Optional[Dict[str, str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        bbox: Optional[tuple] = None,
    ) -> FetchResult[ERDDAPObservation]:
        """
        Fetch data from a tabledap dataset.

        Retrieves tabular data with optional filtering by variables,
        time range, and geographic bounds.

        Args:
            dataset_id: Dataset identifier
            variables: List of variable names to fetch (default: all)
            constraints: Additional constraints as {variable: ">=value"}
            start_time: Start of time range
            end_time: End of time range
            bbox: Bounding box (lon_min, lon_max, lat_min, lat_max)

        Returns:
            FetchResult containing ERDDAPObservation objects
        """
        var_str = ",".join(variables) if variables else ""
        url = f"{self.base_url}/tabledap/{dataset_id}.json"

        constraint_parts = []
        if start_time:
            constraint_parts.append(
                f"time>={start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )
        if end_time:
            constraint_parts.append(f"time<={end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        if bbox:
            lon_min, lon_max, lat_min, lat_max = bbox
            constraint_parts.append(f"latitude>={lat_min}")
            constraint_parts.append(f"latitude<={lat_max}")
            constraint_parts.append(f"longitude>={lon_min}")
            constraint_parts.append(f"longitude<={lon_max}")

        if constraints:
            for var, constraint in constraints.items():
                constraint_parts.append(f"{var}{constraint}")

        if var_str or constraint_parts:
            query_url = f"{url}?{var_str}"
            if constraint_parts:
                query_url += "&" + "&".join(constraint_parts)
        else:
            query_url = url

        response = self._get_json(query_url)
        observations = self._parse_tabledap_response(dataset_id, response)

        return FetchResult(
            data=observations,
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=len(observations),
        )

    def fetch_griddap(
        self,
        dataset_id: str,
        variables: Optional[List[str]] = None,
        time_range: Optional[tuple] = None,
        lat_range: Optional[tuple] = None,
        lon_range: Optional[tuple] = None,
        depth_range: Optional[tuple] = None,
    ) -> FetchResult[Dict[str, Any]]:
        """
        Fetch data from a griddap dataset.

        Retrieves gridded data with optional subsetting by dimension ranges.

        Args:
            dataset_id: Dataset identifier
            variables: List of variable names to fetch
            time_range: Time range as (start, end) datetime tuple
            lat_range: Latitude range as (min, max) tuple
            lon_range: Longitude range as (min, max) tuple
            depth_range: Depth range as (min, max) tuple

        Returns:
            FetchResult containing raw grid data dictionaries
        """
        url = f"{self.base_url}/griddap/{dataset_id}.json"

        dimension_specs = []
        if time_range:
            start, end = time_range
            dimension_specs.append(
                f"[({start.strftime('%Y-%m-%dT%H:%M:%SZ')}):1:"
                f"({end.strftime('%Y-%m-%dT%H:%M:%SZ')})]"
            )
        if depth_range:
            dimension_specs.append(f"[({depth_range[0]}):1:({depth_range[1]})]")
        if lat_range:
            dimension_specs.append(f"[({lat_range[0]}):1:({lat_range[1]})]")
        if lon_range:
            dimension_specs.append(f"[({lon_range[0]}):1:({lon_range[1]})]")

        dim_str = "".join(dimension_specs)

        if variables:
            var_specs = [f"{var}{dim_str}" for var in variables]
            query_url = f"{url}?{','.join(var_specs)}"
        else:
            query_url = url

        response = self._get_json(query_url)

        return FetchResult(
            data=[response],
            source=self.source,
            fetch_time=datetime.utcnow(),
            records_count=1,
        )

    def _parse_tabledap_response(
        self, dataset_id: str, response: dict
    ) -> List[ERDDAPObservation]:
        """Parse ERDDAP tabledap JSON response into observations."""
        observations = []
        table = response.get("table", {})
        column_names = table.get("columnNames", [])
        rows = table.get("rows", [])

        col_idx = {name: i for i, name in enumerate(column_names)}

        for row in rows:
            try:
                time_val = self._get_row_value(row, col_idx, "time")
                if not time_val:
                    continue

                obs_time = self._parse_time(time_val)
                if not obs_time:
                    continue

                obs = ERDDAPObservation(
                    dataset_id=dataset_id,
                    observation_time=obs_time,
                    latitude=self._get_row_float(row, col_idx, "latitude") or 0.0,
                    longitude=self._get_row_float(row, col_idx, "longitude") or 0.0,
                    station_id=self._get_row_value(row, col_idx, "station_id"),
                )

                # Map ERDDAP variable names to observation attributes
                for erddap_name, obs_attr in self.VARIABLE_MAPPING.items():
                    if erddap_name in col_idx:
                        value = self._get_row_float(row, col_idx, erddap_name)
                        if value is not None:
                            setattr(obs, obs_attr, value)

                observations.append(obs)

            except Exception as e:
                self.logger.warning(f"Failed to parse row: {e}")
                continue

        return observations

    def _get_row_value(
        self, row: List[Any], col_idx: Dict[str, int], column: str
    ) -> Optional[str]:
        """Safely get a string value from a row."""
        if column in col_idx:
            idx = col_idx[column]
            if idx < len(row) and row[idx] is not None:
                return str(row[idx])
        return None

    def _get_row_float(
        self, row: List[Any], col_idx: Dict[str, int], column: str
    ) -> Optional[float]:
        """Safely get a float value from a row."""
        value = self._get_row_value(row, col_idx, column)
        return self._parse_float(value)

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse a value to float, returning None on failure."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_time(self, value: Any) -> Optional[datetime]:
        """Parse a time string to datetime."""
        if value is None:
            return None
        try:
            time_str = str(value)
            # Handle ISO format with or without Z suffix
            time_str = time_str.replace("Z", "+00:00")
            if "+" not in time_str and time_str.count("-") == 2:
                # Add timezone if missing
                time_str += "+00:00"
            return datetime.fromisoformat(time_str)
        except (ValueError, TypeError):
            return None

    # Required abstract method implementations

    def fetch_stations(
        self, bbox: Optional[tuple] = None, active_only: bool = True
    ) -> FetchResult[ERDDAPDataset]:
        """
        Search for buoy/station datasets in the region.

        Args:
            bbox: Optional bounding box (lon_min, lon_max, lat_min, lat_max)
            active_only: If True, only return active datasets (not used)

        Returns:
            FetchResult containing dataset metadata
        """
        return self.search_datasets("buoy", bbox=bbox)

    def fetch_realtime(
        self, station_id: str, parameters: Optional[List[str]] = None
    ) -> FetchResult[ERDDAPObservation]:
        """
        Fetch recent data from a dataset.

        Retrieves the last 24 hours of data from the specified dataset.

        Args:
            station_id: Dataset identifier (used as station_id)
            parameters: Optional list of parameters to fetch

        Returns:
            FetchResult containing recent observations
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        return self.fetch_tabledap(
            station_id, variables=parameters, start_time=start_time, end_time=end_time
        )

    def fetch_historical(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult[ERDDAPObservation]:
        """
        Fetch historical data from a dataset.

        Args:
            station_id: Dataset identifier
            start_date: Start of date range
            end_date: End of date range
            parameters: Optional list of parameters to fetch

        Returns:
            FetchResult containing historical observations
        """
        return self.fetch_tabledap(
            station_id, variables=parameters, start_time=start_date, end_time=end_date
        )
