# ABOUTME: API client for Alberta Energy Regulator and Petrinex data access
# ABOUTME: Handles CSV downloads, API queries, and rate limiting for Alberta data

"""
AER/Petrinex API Client

This module provides a robust HTTP client for interacting with Alberta Energy
Regulator (AER) and Petrinex data services, including:
- Well infrastructure data downloads
- Production volumetric data (Petrinex)
- Facility and license information
- Rate limiting and retry logic
- Response caching with TTL

Features:
- Rate limiting (configurable, default 5 requests/second)
- Response caching with TTL
- Automatic retry with exponential backoff
- Support for large CSV file downloads
"""

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

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

from worldenergydata.canada.cache import CanadaCache, FileDownloadCache
from worldenergydata.canada.endpoints import (
    AER_API_DEFAULTS,
)
from worldenergydata.canada.errors import (
    CanadaAERError,
    CanadaAPIError,
    CanadaRateLimitError,
    CanadaValidationError,
)

logger = logging.getLogger(__name__)


class AERClient:
    """
    HTTP client for AER and Petrinex data services.

    Features:
    - Rate limiting (configurable requests per second)
    - Response caching with TTL
    - Automatic retry with exponential backoff
    - Large file download support
    - Session management for connection pooling

    Example usage:
        client = AERClient()

        # Download well infrastructure data
        wells_df = client.download_well_infrastructure()

        # Query production data
        production_df = client.download_volumetrics(year=2024)

        # Lookup specific well by UWI
        well_data = client.query_well_by_uwi("100/06-12-078-06W6/00")
    """

    # Base URLs for AER and Petrinex services
    AER_BASE_URL = "https://www.aer.ca"
    PETRINEX_BASE_URL = "https://www.petrinex.gov.ab.ca"
    PETRINEX_PUBLIC_DATA_URL = "https://www.petrinex.gov.ab.ca/publicdata"

    # Known Petrinex public data CSV endpoints
    PETRINEX_CSV_ENDPOINTS = {
        "well_infrastructure": "/PublicData/WellInfrastructure",
        "volumetric_oil": "/PublicData/OilVolumetricData",
        "volumetric_gas": "/PublicData/GasVolumetricData",
        "volumetric_water": "/PublicData/WaterVolumetricData",
        "facility_licence": "/PublicData/FacilityLicence",
        "facility_volumetric": "/PublicData/FacilityVolumetricData",
    }

    # Default configuration
    DEFAULT_TIMEOUT = 120  # seconds
    DEFAULT_RATE_LIMIT = 5  # requests per second
    DEFAULT_CACHE_TTL = 86400  # 24 hours
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2.0  # seconds

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        rate_limit: Optional[float] = None,
        cache_ttl: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize AER API client.

        Args:
            config: Optional configuration dictionary (overrides individual params)
            rate_limit: Maximum requests per second (default 5, set 0 to disable)
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
            max_retries: Maximum number of retry attempts (default 3)
            retry_delay: Base delay between retries in seconds (default 2.0)
            timeout: Request timeout in seconds (default 120)
            headers: Optional custom HTTP headers
            cache_dir: Optional directory for file cache
        """
        # Apply configuration with defaults
        cfg = config or {}
        self.rate_limit = rate_limit or cfg.get(
            "rate_limit", AER_API_DEFAULTS.get("rate_limit", self.DEFAULT_RATE_LIMIT)
        )
        self.cache_ttl = cache_ttl or cfg.get(
            "cache_ttl", AER_API_DEFAULTS.get("cache_ttl", self.DEFAULT_CACHE_TTL)
        )
        self.max_retries = max_retries or cfg.get(
            "max_retries", AER_API_DEFAULTS.get("max_retries", self.DEFAULT_MAX_RETRIES)
        )
        self.retry_delay = retry_delay or cfg.get(
            "retry_delay",
            AER_API_DEFAULTS.get("retry_delay", self.DEFAULT_RETRY_DELAY),
        )
        self.timeout = timeout or cfg.get(
            "timeout", AER_API_DEFAULTS.get("timeout", self.DEFAULT_TIMEOUT)
        )

        # Calculate rate limiting interval
        self.min_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 0
        self.last_request_time = 0.0

        # Initialize caches
        self.cache = CanadaCache(default_ttl=self.cache_ttl)
        self.file_cache = FileDownloadCache(cache_dir=cache_dir)
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
            "User-Agent": "WorldEnergyData AER Client/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/csv;q=0.8,*/*;q=0.7",  # noqa: E501
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
            key_str = f"aer:{endpoint}?{param_str}"
        else:
            key_str = f"aer:{endpoint}"

        return hashlib.md5(key_str.encode()).hexdigest()

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        stream: bool = False,
    ) -> "requests.Response":
        """
        Make actual HTTP request.

        Args:
            method: HTTP method (GET, POST)
            url: Request URL
            params: Query parameters
            data: POST data
            stream: Whether to stream response

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
            "stream": stream,
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
        stream: bool = False,
    ) -> "requests.Response":
        """
        Execute HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Full URL for request
            params: Query parameters
            data: POST data
            stream: Whether to stream response

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

                response = self._make_request(method, url, params, data, stream)

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

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> bytes:
        """
        Make GET request with rate limiting and optional caching.

        Args:
            url: Full URL for request
            params: Query parameters
            use_cache: Whether to use caching

        Returns:
            Response content as bytes

        Raises:
            CanadaAPIError: If request fails after retries
        """
        cache_key = self._generate_cache_key(url, params)

        # Check cache first
        if use_cache and self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for {url}")
                return cached_data

        # Execute request
        response = self._execute_with_retry("GET", url, params=params)
        content = response.content

        # Cache successful response
        if use_cache and self.cache_enabled:
            self.cache.set(cache_key, content, self.cache_ttl)

        return content

    def download_file(
        self,
        url: str,
        output_path: Path,
        params: Optional[Dict] = None,
        chunk_size: int = 8192,
        use_cache: bool = True,
    ) -> Path:
        """
        Download file with streaming and progress tracking.

        Args:
            url: URL to download from
            output_path: Path to save file
            params: Optional query parameters
            chunk_size: Download chunk size in bytes
            use_cache: Whether to check file cache first

        Returns:
            Path to downloaded file

        Raises:
            CanadaAERError: If download fails
        """
        # Check file cache
        if use_cache:
            cached_path = self.file_cache.get_cached_file(url)
            if cached_path and cached_path.exists():
                if self.file_cache.is_cached(url, max_age=self.cache_ttl):
                    logger.info(f"Using cached file: {cached_path}")
                    # Copy to output path if different
                    if cached_path != output_path:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_bytes(cached_path.read_bytes())
                    return output_path

        # Execute streaming download
        self._rate_limit()

        try:
            response = self._make_request("GET", url, params=params, stream=True)
            response.raise_for_status()

            # Get content length if available
            total_size = int(response.headers.get("content-length", 0))

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            downloaded = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")

            logger.info(f"Downloaded {downloaded} bytes to {output_path}")

            # Update file cache
            if use_cache:
                self.file_cache.save_to_cache(
                    url,
                    output_path.read_bytes(),
                    suffix=output_path.suffix,
                )

            return output_path

        except Exception as e:
            raise CanadaAERError(
                f"Failed to download file from {url}: {e}",
                code="AER_DOWNLOAD_FAILED",
                cause=e,
            )

    def download_well_infrastructure(
        self,
        output_dir: Optional[Path] = None,
        use_cache: bool = True,
    ) -> "pd.DataFrame":
        """
        Download well infrastructure data from Petrinex.

        Downloads the well infrastructure CSV file containing well header
        information including UWI, location, operator, and status.

        Args:
            output_dir: Optional directory to save downloaded file
            use_cache: Whether to use cached files if available

        Returns:
            DataFrame containing well infrastructure data

        Raises:
            CanadaAERError: If download or parsing fails
        """
        if pd is None:
            raise CanadaAERError(
                "pandas library required for well infrastructure download",
                code="AER_MISSING_DEPENDENCY",
            )

        url = f"{self.PETRINEX_PUBLIC_DATA_URL}{self.PETRINEX_CSV_ENDPOINTS['well_infrastructure']}"

        output_dir = output_dir or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d")
        filename = f"aer_well_infrastructure_{timestamp}.csv"
        output_path = output_dir / filename

        logger.info(f"Downloading AER well infrastructure data to {output_path}")

        try:
            self.download_file(url, output_path, use_cache=use_cache)

            # Parse CSV
            df = pd.read_csv(output_path, encoding="utf-8-sig", low_memory=False)
            logger.info(f"Loaded {len(df)} well infrastructure records")
            return df

        except Exception as e:
            raise CanadaAERError.data_unavailable(
                "well infrastructure",
                str(e),
            )

    def download_volumetrics(
        self,
        year: Optional[int] = None,
        product_type: str = "oil",
        output_dir: Optional[Path] = None,
        use_cache: bool = True,
    ) -> "pd.DataFrame":
        """
        Download production volumetric data from Petrinex.

        Downloads monthly production volumetric data (oil, gas, or water)
        for Alberta wells.

        Args:
            year: Optional year filter (None for all available)
            product_type: Type of volumetric data ("oil", "gas", "water")
            output_dir: Optional directory to save downloaded file
            use_cache: Whether to use cached files if available

        Returns:
            DataFrame containing volumetric production data

        Raises:
            CanadaAERError: If download or parsing fails
            CanadaValidationError: If invalid product_type
        """
        if pd is None:
            raise CanadaAERError(
                "pandas library required for volumetrics download",
                code="AER_MISSING_DEPENDENCY",
            )

        valid_types = ["oil", "gas", "water"]
        if product_type.lower() not in valid_types:
            raise CanadaValidationError(
                f"Invalid product_type: {product_type}. Valid types: {valid_types}",
                code="AER_INVALID_PRODUCT_TYPE",
            )

        endpoint_key = f"volumetric_{product_type.lower()}"
        url = f"{self.PETRINEX_PUBLIC_DATA_URL}{self.PETRINEX_CSV_ENDPOINTS[endpoint_key]}"

        output_dir = output_dir or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d")
        year_suffix = f"_{year}" if year else ""
        filename = f"aer_volumetric_{product_type}{year_suffix}_{timestamp}.csv"
        output_path = output_dir / filename

        logger.info(f"Downloading AER {product_type} volumetric data to {output_path}")

        try:
            self.download_file(url, output_path, use_cache=use_cache)

            # Parse CSV
            df = pd.read_csv(output_path, encoding="utf-8-sig", low_memory=False)

            # Filter by year if specified
            if year is not None:
                date_cols = [
                    c for c in df.columns if "date" in c.lower() or "month" in c.lower()
                ]
                if date_cols:
                    # Attempt to filter by year
                    date_col = date_cols[0]
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df[df[date_col].dt.year == year]

            logger.info(f"Loaded {len(df)} {product_type} volumetric records")
            return df

        except Exception as e:
            raise CanadaAERError.data_unavailable(
                f"{product_type} volumetrics",
                str(e),
            )

    def download_facility_licence(
        self,
        output_dir: Optional[Path] = None,
        use_cache: bool = True,
    ) -> "pd.DataFrame":
        """
        Download facility licence data from Petrinex.

        Downloads facility licence information including facility IDs,
        types, operators, and status.

        Args:
            output_dir: Optional directory to save downloaded file
            use_cache: Whether to use cached files if available

        Returns:
            DataFrame containing facility licence data

        Raises:
            CanadaAERError: If download or parsing fails
        """
        if pd is None:
            raise CanadaAERError(
                "pandas library required for facility licence download",
                code="AER_MISSING_DEPENDENCY",
            )

        url = f"{self.PETRINEX_PUBLIC_DATA_URL}{self.PETRINEX_CSV_ENDPOINTS['facility_licence']}"

        output_dir = output_dir or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d")
        filename = f"aer_facility_licence_{timestamp}.csv"
        output_path = output_dir / filename

        logger.info(f"Downloading AER facility licence data to {output_path}")

        try:
            self.download_file(url, output_path, use_cache=use_cache)

            # Parse CSV
            df = pd.read_csv(output_path, encoding="utf-8-sig", low_memory=False)
            logger.info(f"Loaded {len(df)} facility licence records")
            return df

        except Exception as e:
            raise CanadaAERError.data_unavailable(
                "facility licence",
                str(e),
            )

    def query_well_by_uwi(
        self,
        uwi: str,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Query specific well by UWI.

        Searches cached well infrastructure data for a specific UWI.
        Falls back to API query if data not cached.

        Alberta UWI format: LE/LSD-SEC-TWP-RGE-MER/EVENT
        Example: 100/06-12-078-06W6/00

        Args:
            uwi: Well UWI (DLS format)
            use_cache: Whether to use cached data

        Returns:
            Dictionary containing well data

        Raises:
            CanadaAERError: If well not found
            CanadaValidationError: If UWI format invalid
        """
        # Validate UWI format
        normalized_uwi = self._validate_uwi(uwi)

        cache_key = f"aer_well_{normalized_uwi}"

        # Check cache
        if use_cache and self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        logger.info(f"Querying AER well data for UWI: {normalized_uwi}")

        # Try to find in well infrastructure data
        try:
            df = self.download_well_infrastructure(use_cache=True)

            # Search for UWI in common column names
            uwi_cols = [
                c
                for c in df.columns
                if "uwi" in c.lower() or "unique" in c.lower() and "well" in c.lower()
            ]

            if uwi_cols:
                uwi_col = uwi_cols[0]
                # Normalize UWIs in dataframe for comparison
                mask = (
                    df[uwi_col]
                    .astype(str)
                    .str.replace(r"[\s-]", "", regex=True)
                    .str.upper()
                    == normalized_uwi.replace("-", "").replace("/", "").upper()
                )

                matches = df[mask]
                if len(matches) > 0:
                    well_data = matches.iloc[0].to_dict()

                    # Cache result
                    if use_cache and self.cache_enabled:
                        self.cache.set(cache_key, well_data, self.cache_ttl)

                    return well_data

        except Exception as e:
            logger.warning(f"Error searching well infrastructure: {e}")

        raise CanadaAERError.license_not_found(uwi)

    def _validate_uwi(self, uwi: str) -> str:
        """
        Validate and normalize Alberta UWI.

        Alberta UWIs follow DLS (Dominion Land Survey) format:
        LE/LSD-SEC-TWP-RGE-MER/EVENT
        Example: 100/06-12-078-06W6/00

        Args:
            uwi: UWI to validate

        Returns:
            Normalized UWI string

        Raises:
            CanadaValidationError: If invalid format
        """
        # Remove extra whitespace
        normalized = uwi.strip()

        # Basic format check - Alberta UWI should contain numbers and separators
        if not re.match(r"^[\d/\-WwEe]+$", normalized.replace(" ", "")):
            raise CanadaValidationError(
                f"Invalid Alberta UWI format: {uwi}",
                code="AER_INVALID_UWI",
                context={"uwi": uwi},
            )

        return normalized

    def search_wells(
        self,
        field_name: Optional[str] = None,
        operator: Optional[str] = None,
        well_status: Optional[str] = None,
        limit: int = 100,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for wells with filters.

        Args:
            field_name: Filter by field name (partial match)
            operator: Filter by operator name (partial match)
            well_status: Filter by well status
            limit: Maximum records to return
            use_cache: Whether to use cached data

        Returns:
            List of matching well records
        """
        logger.info(
            f"Searching AER wells - field: {field_name}, operator: {operator}, "
            f"status: {well_status}, limit: {limit}"
        )

        try:
            df = self.download_well_infrastructure(use_cache=use_cache)

            # Apply filters
            mask = pd.Series([True] * len(df))

            if field_name:
                field_cols = [c for c in df.columns if "field" in c.lower()]
                if field_cols:
                    mask &= (
                        df[field_cols[0]]
                        .astype(str)
                        .str.contains(field_name, case=False, na=False)
                    )

            if operator:
                op_cols = [
                    c
                    for c in df.columns
                    if "operator" in c.lower() or "licensee" in c.lower()
                ]
                if op_cols:
                    mask &= (
                        df[op_cols[0]]
                        .astype(str)
                        .str.contains(operator, case=False, na=False)
                    )

            if well_status:
                status_cols = [c for c in df.columns if "status" in c.lower()]
                if status_cols:
                    mask &= (
                        df[status_cols[0]].astype(str).str.upper()
                        == well_status.upper()
                    )

            filtered = df[mask].head(limit)
            return filtered.to_dict("records")

        except Exception as e:
            logger.error(f"Error searching wells: {e}")
            return []

    def close(self) -> None:
        """Close the client session and clean up resources."""
        if self.session:
            self.session.close()
            self.session = None
        logger.debug("AER client session closed")

    def __enter__(self) -> "AERClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats


__all__ = ["AERClient"]
