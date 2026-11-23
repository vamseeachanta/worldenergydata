# ABOUTME: API client for BC Energy Regulator GIS data access
# ABOUTME: Handles ArcGIS REST queries and coordinate transformations for BC data

"""
BCER ArcGIS REST API Client

This module provides a robust HTTP client for interacting with the BC Energy
Regulator (BCER) ArcGIS REST services, including:
- Well location and drilling information
- Facility data (plants, compressors)
- Pipeline network information
- Spatial queries with coordinate transformation

Features:
- Rate limiting (configurable, default 10 requests/second)
- Response caching with TTL
- Automatic retry with exponential backoff
- ArcGIS pagination support
- Coordinate transformation (EPSG:3005 to WGS84)
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import geopandas as gpd
    from shapely.geometry import Point, Polygon, shape  # noqa: F401
except ImportError:
    gpd = None

from worldenergydata.canada.cache import CanadaCache
from worldenergydata.canada.endpoints import BCER_API_DEFAULTS
from worldenergydata.canada.errors import (
    CanadaAPIError,
    CanadaBCERError,
    CanadaDataError,
    CanadaRateLimitError,
    CanadaValidationError,
)

logger = logging.getLogger(__name__)


class BCERClient:
    """
    HTTP client for BCER ArcGIS REST API.

    Features:
    - Rate limiting (configurable requests per second)
    - Response caching with TTL
    - Automatic retry with exponential backoff
    - ArcGIS pagination for large result sets
    - Coordinate transformation support

    Example usage:
        client = BCERClient()

        # Query wells in a bounding box
        wells_gdf = client.query_wells(bbox=(-125, 55, -120, 60))

        # Query facilities by operator
        facilities_gdf = client.query_facilities(where="OPERATOR LIKE '%Shell%'")

        # Query pipelines
        pipelines_gdf = client.query_pipelines()

        # Transform coordinates
        gdf_wgs84 = client.transform_coordinates(gdf, to_crs="EPSG:4326")
    """

    # Base URL for BCER ArcGIS services
    BASE_URL = "https://maps.bcer.gov.bc.ca"
    DATA_BC_URL = "https://data-bc-er.opendata.arcgis.com"

    # ArcGIS Feature Service endpoints
    FEATURE_SERVICES = {
        "wells": "/arcgis/rest/services/BCER_WELLS/FeatureServer/0",
        "facilities": "/arcgis/rest/services/BCER_FACILITIES/FeatureServer/0",
        "pipelines": "/arcgis/rest/services/BCER_PIPELINES/FeatureServer/0",
        "pools": "/arcgis/rest/services/BCER_POOLS/FeatureServer/0",
    }

    # BC Albers projection (native CRS for BCER data)
    BC_ALBERS_EPSG = 3005
    WGS84_EPSG = 4326

    # Default configuration
    DEFAULT_TIMEOUT = 30  # seconds
    DEFAULT_RATE_LIMIT = 10  # requests per second
    DEFAULT_CACHE_TTL = 86400  # 24 hours
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0  # seconds
    DEFAULT_MAX_RECORDS = 1000  # ArcGIS pagination limit

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        base_url: Optional[str] = None,
        rate_limit: Optional[float] = None,
        cache_ttl: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        max_records_per_request: Optional[int] = None,
    ):
        """
        Initialize BCER API client.

        Args:
            config: Optional configuration dictionary (overrides individual params)
            base_url: Optional custom base URL for BCER services
            rate_limit: Maximum requests per second (default 10, set 0 to disable)
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
            max_retries: Maximum number of retry attempts (default 3)
            retry_delay: Base delay between retries in seconds (default 1.0)
            timeout: Request timeout in seconds (default 30)
            headers: Optional custom HTTP headers
            max_records_per_request: Maximum records per ArcGIS request (default 1000)
        """
        # Apply configuration with defaults
        cfg = config or {}
        self.base_url = base_url or cfg.get(
            "base_url", BCER_API_DEFAULTS.get("base_url", self.BASE_URL)
        )
        self.rate_limit = rate_limit or cfg.get(
            "rate_limit", BCER_API_DEFAULTS.get("rate_limit", self.DEFAULT_RATE_LIMIT)
        )
        self.cache_ttl = cache_ttl or cfg.get(
            "cache_ttl", BCER_API_DEFAULTS.get("cache_ttl", self.DEFAULT_CACHE_TTL)
        )
        self.max_retries = max_retries or cfg.get(
            "max_retries",
            BCER_API_DEFAULTS.get("max_retries", self.DEFAULT_MAX_RETRIES),
        )
        self.retry_delay = retry_delay or cfg.get(
            "retry_delay",
            BCER_API_DEFAULTS.get("retry_delay", self.DEFAULT_RETRY_DELAY),
        )
        self.timeout = timeout or cfg.get(
            "timeout", BCER_API_DEFAULTS.get("timeout", self.DEFAULT_TIMEOUT)
        )
        self.max_records = max_records_per_request or cfg.get(
            "max_records_per_request",
            BCER_API_DEFAULTS.get("max_records_per_request", self.DEFAULT_MAX_RECORDS),
        )

        # Calculate rate limiting interval
        self.min_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 0
        self.last_request_time = 0.0

        # Initialize cache
        self.cache = CanadaCache(default_ttl=self.cache_ttl)
        self.cache_enabled = True

        # Setup HTTP headers
        self.headers = self._setup_headers(headers)

        # Setup session with retry strategy
        self.session = self._setup_session() if requests else None

    def _setup_headers(
        self, custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Setup default and custom HTTP headers.

        Args:
            custom_headers: Optional custom headers to add

        Returns:
            Combined headers dictionary
        """
        headers = {
            "User-Agent": "WorldEnergyData BCER Client/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _setup_session(self) -> Optional["requests.Session"]:
        """
        Setup requests session with connection pooling.

        Returns:
            Configured requests Session or None if requests unavailable
        """
        if not requests:
            return None

        session = requests.Session()

        # Configure retry strategy for connection-level retries
        retry_strategy = Retry(
            total=0,  # We handle retries manually for better control
            backoff_factor=0,
            status_forcelist=[],
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _rate_limit(self) -> None:
        """Implement rate limiting with minimum interval between requests."""
        if self.min_interval > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f} seconds")
                time.sleep(sleep_time)
            self.last_request_time = time.time()

    def _generate_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """
        Generate cache key from endpoint and parameters.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Unique cache key string
        """
        if params:
            sorted_params = sorted(params.items())
            param_str = urlencode(sorted_params)
            key_str = f"bcer:{endpoint}?{param_str}"
        else:
            key_str = f"bcer:{endpoint}"

        return hashlib.md5(key_str.encode()).hexdigest()

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> "requests.Response":
        """
        Make actual HTTP request.

        Args:
            method: HTTP method (GET, POST)
            url: Request URL
            params: Query parameters
            data: POST data

        Returns:
            Response object

        Raises:
            CanadaAPIError: If requests library unavailable
        """
        if not requests:
            raise CanadaAPIError(
                "requests library not installed",
                code="CANADA_MISSING_DEPENDENCY",
            )

        logger.debug(f"{method} {url} with params: {params}")

        request_kwargs: Dict[str, Any] = {
            "headers": self.headers,
            "timeout": self.timeout,
        }

        if params:
            request_kwargs["params"] = params
        if data:
            request_kwargs["data"] = data

        if self.session:
            response = self.session.request(method, url, **request_kwargs)
        else:
            response = requests.request(method, url, **request_kwargs)

        return response

    def _execute_with_retry(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> "requests.Response":
        """
        Execute HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Full URL for request
            params: Query parameters
            data: POST data

        Returns:
            Response object

        Raises:
            CanadaAPIError: If request fails after retries
            CanadaRateLimitError: If rate limit is exceeded
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting
                self._rate_limit()

                response = self._make_request(method, url, params, data)

                # Check response status
                if response.status_code == 200:
                    return response

                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(
                        response.headers.get("Retry-After", self.retry_delay * 5)
                    )
                    if attempt < self.max_retries:
                        logger.warning(
                            f"Rate limit exceeded, retrying after {retry_after} seconds"
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        raise CanadaRateLimitError.exceeded(
                            endpoint=url,
                            retry_after=retry_after,
                        )

                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2**attempt)
                        logger.warning(
                            f"Server error {response.status_code}, "
                            f"retrying in {delay} seconds (attempt {attempt + 1}/{self.max_retries})"  # noqa: E501
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise CanadaAPIError.request_failed(
                            endpoint=url,
                            status_code=response.status_code,
                            response_body=response.text,
                        )

                elif response.status_code >= 400:
                    # Client error - don't retry
                    raise CanadaAPIError.request_failed(
                        endpoint=url,
                        status_code=response.status_code,
                        response_body=response.text,
                    )

            except (CanadaAPIError, CanadaRateLimitError):
                raise
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Request failed: {e}, retrying in {delay} seconds "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    continue

        # All retries exhausted
        error_msg = f"Request failed after {self.max_retries + 1} attempts"
        if last_error:
            error_msg += f": {last_error}"
        raise CanadaAPIError(error_msg, endpoint=url, cause=last_error)

    def _build_arcgis_params(
        self,
        where: str = "1=1",
        out_fields: str = "*",
        return_geometry: bool = True,
        geometry: Optional[Dict] = None,
        geometry_type: str = "esriGeometryEnvelope",
        spatial_rel: str = "esriSpatialRelIntersects",
        result_offset: int = 0,
        result_record_count: Optional[int] = None,
        order_by_fields: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Build ArcGIS REST API query parameters.

        Args:
            where: SQL WHERE clause for filtering
            out_fields: Fields to return (* for all)
            return_geometry: Whether to return geometry
            geometry: Spatial geometry for spatial query
            geometry_type: Type of geometry (esriGeometryEnvelope, esriGeometryPolygon)
            spatial_rel: Spatial relationship for query
            result_offset: Pagination offset
            result_record_count: Maximum records to return
            order_by_fields: Fields to order by

        Returns:
            Dictionary of query parameters
        """
        params: Dict[str, str] = {
            "where": where,
            "outFields": out_fields,
            "f": "json",
            "returnGeometry": str(return_geometry).lower(),
            "resultOffset": str(result_offset),
        }

        if result_record_count is not None:
            params["resultRecordCount"] = str(result_record_count)

        if geometry is not None:
            params["geometry"] = json.dumps(geometry)
            params["geometryType"] = geometry_type
            params["spatialRel"] = spatial_rel
            params["inSR"] = str(self.WGS84_EPSG)

        if order_by_fields:
            params["orderByFields"] = order_by_fields

        return params

    def _query_feature_service(
        self,
        service_path: str,
        where: str = "1=1",
        bbox: Optional[Tuple[float, float, float, float]] = None,
        out_fields: str = "*",
        return_geometry: bool = True,
        max_records: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Query an ArcGIS feature service with pagination.

        Args:
            service_path: Path to feature service endpoint
            where: SQL WHERE clause for filtering
            bbox: Bounding box (xmin, ymin, xmax, ymax) in WGS84
            out_fields: Fields to return
            return_geometry: Whether to return geometry
            max_records: Maximum total records (None for all)
            use_cache: Whether to use caching

        Returns:
            List of feature records

        Raises:
            CanadaBCERError: If query fails
        """
        url = urljoin(self.base_url, f"{service_path}/query")

        # Build geometry for spatial query
        geometry = None
        if bbox is not None:
            if len(bbox) != 4:
                raise CanadaValidationError(
                    "Bounding box must have 4 values: (xmin, ymin, xmax, ymax)",
                    code="BCER_INVALID_BBOX",
                )
            geometry = {
                "xmin": bbox[0],
                "ymin": bbox[1],
                "xmax": bbox[2],
                "ymax": bbox[3],
            }

        all_features: List[Dict[str, Any]] = []
        offset = 0
        records_per_request = min(
            self.max_records, max_records if max_records else self.max_records
        )

        while True:
            # Check cache
            cache_key = self._generate_cache_key(
                service_path,
                {"where": where, "bbox": str(bbox), "offset": offset},
            )

            if use_cache and self.cache_enabled:
                cached_data = self.cache.get(cache_key)
                if cached_data is not None:
                    features = cached_data
                    all_features.extend(features)
                    if len(features) < records_per_request:
                        break
                    offset += len(features)
                    if max_records and len(all_features) >= max_records:
                        break
                    continue

            # Build query parameters
            params = self._build_arcgis_params(
                where=where,
                out_fields=out_fields,
                return_geometry=return_geometry,
                geometry=geometry,
                result_offset=offset,
                result_record_count=records_per_request,
            )

            try:
                response = self._execute_with_retry("GET", url, params=params)
                data = response.json()

                # Check for ArcGIS error
                if "error" in data:
                    error_info = data["error"]
                    raise CanadaBCERError.arcgis_error(
                        service_path,
                        f"Code {error_info.get('code')}: {error_info.get('message')}",
                    )

                features = data.get("features", [])

                # Cache results
                if use_cache and self.cache_enabled:
                    self.cache.set(cache_key, features, self.cache_ttl)

                all_features.extend(features)

                # Check if we've received all records
                if len(features) < records_per_request:
                    break

                offset += len(features)

                # Check max records limit
                if max_records and len(all_features) >= max_records:
                    all_features = all_features[:max_records]
                    break

            except (CanadaAPIError, CanadaBCERError):
                raise
            except Exception as e:
                raise CanadaBCERError.arcgis_error(service_path, str(e))

        logger.info(f"Retrieved {len(all_features)} features from {service_path}")
        return all_features

    def _features_to_geodataframe(
        self,
        features: List[Dict[str, Any]],
        crs: str = "EPSG:3005",
    ) -> "gpd.GeoDataFrame":
        """
        Convert ArcGIS features to GeoDataFrame.

        Args:
            features: List of ArcGIS feature dictionaries
            crs: Coordinate reference system of the data

        Returns:
            GeoDataFrame containing the features

        Raises:
            CanadaDataError: If geopandas not available or conversion fails
        """
        if gpd is None:
            raise CanadaDataError(
                "geopandas library required for GeoDataFrame conversion",
                code="BCER_MISSING_DEPENDENCY",
            )

        if not features:
            # Return empty GeoDataFrame
            return gpd.GeoDataFrame(columns=["geometry"], crs=crs)

        try:
            # Extract attributes and geometry
            records = []
            geometries = []

            for feature in features:
                attributes = feature.get("attributes", {})
                geometry_dict = feature.get("geometry", None)

                records.append(attributes)

                if geometry_dict:
                    # Handle point geometry
                    if "x" in geometry_dict and "y" in geometry_dict:
                        geom = Point(geometry_dict["x"], geometry_dict["y"])
                    # Handle ring geometry (polygon)
                    elif "rings" in geometry_dict:
                        rings = geometry_dict["rings"]
                        if rings:
                            geom = Polygon(rings[0])
                        else:
                            geom = None
                    # Handle paths geometry (line)
                    elif "paths" in geometry_dict:
                        from shapely.geometry import LineString, MultiLineString

                        paths = geometry_dict["paths"]
                        if len(paths) == 1:
                            geom = LineString(paths[0])
                        elif len(paths) > 1:
                            geom = MultiLineString(paths)
                        else:
                            geom = None
                    else:
                        geom = None
                else:
                    geom = None

                geometries.append(geom)

            # Create GeoDataFrame
            if pd is None:
                raise CanadaDataError(
                    "pandas library required for GeoDataFrame conversion",
                    code="BCER_MISSING_DEPENDENCY",
                )

            df = pd.DataFrame(records)
            gdf = gpd.GeoDataFrame(df, geometry=geometries, crs=crs)

            return gdf

        except Exception as e:
            raise CanadaDataError.parse_failed(
                "ArcGIS features",
                str(e),
                cause=e,
            )

    def query_wells(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        where: Optional[str] = None,
        out_fields: str = "*",
        max_records: Optional[int] = None,
        use_cache: bool = True,
    ) -> "gpd.GeoDataFrame":
        """
        Query wells from ArcGIS feature service.

        Args:
            bbox: Bounding box (xmin, ymin, xmax, ymax) in WGS84 (EPSG:4326)
            where: SQL WHERE clause for filtering (e.g., "WELL_STATUS = 'Active'")
            out_fields: Fields to return (* for all)
            max_records: Maximum records to return (None for all)
            use_cache: Whether to use cached results

        Returns:
            GeoDataFrame containing well features

        Raises:
            CanadaBCERError: If query fails
        """
        service_path = self.FEATURE_SERVICES["wells"]
        where_clause = where or "1=1"

        logger.info(f"Querying BCER wells - where: {where_clause}, bbox: {bbox}")

        features = self._query_feature_service(
            service_path,
            where=where_clause,
            bbox=bbox,
            out_fields=out_fields,
            return_geometry=True,
            max_records=max_records,
            use_cache=use_cache,
        )

        gdf = self._features_to_geodataframe(
            features, crs=f"EPSG:{self.BC_ALBERS_EPSG}"
        )
        return gdf

    def query_facilities(
        self,
        where: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        out_fields: str = "*",
        max_records: Optional[int] = None,
        use_cache: bool = True,
    ) -> "gpd.GeoDataFrame":
        """
        Query facilities from ArcGIS feature service.

        Args:
            where: SQL WHERE clause for filtering
            bbox: Bounding box (xmin, ymin, xmax, ymax) in WGS84
            out_fields: Fields to return
            max_records: Maximum records to return
            use_cache: Whether to use cached results

        Returns:
            GeoDataFrame containing facility features
        """
        service_path = self.FEATURE_SERVICES["facilities"]
        where_clause = where or "1=1"

        logger.info(f"Querying BCER facilities - where: {where_clause}")

        features = self._query_feature_service(
            service_path,
            where=where_clause,
            bbox=bbox,
            out_fields=out_fields,
            return_geometry=True,
            max_records=max_records,
            use_cache=use_cache,
        )

        gdf = self._features_to_geodataframe(
            features, crs=f"EPSG:{self.BC_ALBERS_EPSG}"
        )
        return gdf

    def query_pipelines(
        self,
        where: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        out_fields: str = "*",
        max_records: Optional[int] = None,
        use_cache: bool = True,
    ) -> "gpd.GeoDataFrame":
        """
        Query pipelines from ArcGIS feature service.

        Args:
            where: SQL WHERE clause for filtering
            bbox: Bounding box (xmin, ymin, xmax, ymax) in WGS84
            out_fields: Fields to return
            max_records: Maximum records to return
            use_cache: Whether to use cached results

        Returns:
            GeoDataFrame containing pipeline features
        """
        service_path = self.FEATURE_SERVICES["pipelines"]
        where_clause = where or "1=1"

        logger.info(f"Querying BCER pipelines - where: {where_clause}")

        features = self._query_feature_service(
            service_path,
            where=where_clause,
            bbox=bbox,
            out_fields=out_fields,
            return_geometry=True,
            max_records=max_records,
            use_cache=use_cache,
        )

        gdf = self._features_to_geodataframe(
            features, crs=f"EPSG:{self.BC_ALBERS_EPSG}"
        )
        return gdf

    def query_pools(
        self,
        where: Optional[str] = None,
        out_fields: str = "*",
        max_records: Optional[int] = None,
        use_cache: bool = True,
    ) -> "gpd.GeoDataFrame":
        """
        Query pools/reservoirs from ArcGIS feature service.

        Args:
            where: SQL WHERE clause for filtering
            out_fields: Fields to return
            max_records: Maximum records to return
            use_cache: Whether to use cached results

        Returns:
            GeoDataFrame containing pool features
        """
        service_path = self.FEATURE_SERVICES["pools"]
        where_clause = where or "1=1"

        logger.info(f"Querying BCER pools - where: {where_clause}")

        features = self._query_feature_service(
            service_path,
            where=where_clause,
            out_fields=out_fields,
            return_geometry=True,
            max_records=max_records,
            use_cache=use_cache,
        )

        gdf = self._features_to_geodataframe(
            features, crs=f"EPSG:{self.BC_ALBERS_EPSG}"
        )
        return gdf

    def transform_coordinates(
        self,
        gdf: "gpd.GeoDataFrame",
        to_crs: str = "EPSG:4326",
    ) -> "gpd.GeoDataFrame":
        """
        Transform GeoDataFrame coordinates to target CRS.

        BCER data is typically in BC Albers (EPSG:3005). This method
        transforms to WGS84 (EPSG:4326) or any other CRS.

        Args:
            gdf: GeoDataFrame to transform
            to_crs: Target coordinate reference system (default WGS84)

        Returns:
            GeoDataFrame with transformed coordinates

        Raises:
            CanadaDataError: If transformation fails
        """
        if gpd is None:
            raise CanadaDataError(
                "geopandas library required for coordinate transformation",
                code="BCER_MISSING_DEPENDENCY",
            )

        if gdf.empty:
            gdf.crs = to_crs
            return gdf

        try:
            if gdf.crs is None:
                # Assume BC Albers if CRS not set
                gdf = gdf.set_crs(f"EPSG:{self.BC_ALBERS_EPSG}")

            transformed = gdf.to_crs(to_crs)
            logger.debug(f"Transformed {len(gdf)} features from {gdf.crs} to {to_crs}")
            return transformed

        except Exception as e:
            raise CanadaDataError.transform_failed(
                "coordinate_transformation",
                str(e),
                cause=e,
            )

    def get_well_by_uwi(
        self,
        uwi: str,
        use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Query specific well by UWI.

        Args:
            uwi: BC UWI (NTS format)
            use_cache: Whether to use cached results

        Returns:
            Dictionary containing well data or None if not found
        """
        # Build WHERE clause for UWI lookup
        where = f"UWI = '{uwi}'"

        gdf = self.query_wells(where=where, max_records=1, use_cache=use_cache)

        if len(gdf) > 0:
            return gdf.iloc[0].to_dict()
        return None

    def get_well_by_wa_num(
        self,
        wa_num: str,
        use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Query specific well by Well Authorization Number.

        Args:
            wa_num: BCER Well Authorization Number
            use_cache: Whether to use cached results

        Returns:
            Dictionary containing well data or None if not found
        """
        # Build WHERE clause for WA number lookup
        where = f"WA_NUM = '{wa_num}'"

        gdf = self.query_wells(where=where, max_records=1, use_cache=use_cache)

        if len(gdf) > 0:
            return gdf.iloc[0].to_dict()
        return None

    def close(self) -> None:
        """Close the client session and clean up resources."""
        if self.session:
            self.session.close()
            self.session = None
        logger.debug("BCER client session closed")

    def __enter__(self) -> "BCERClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats


__all__ = ["BCERClient"]
