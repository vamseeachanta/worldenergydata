# ABOUTME: Texas RRC API client with rate limiting, caching, and retry logic
# ABOUTME: Provides methods for downloading PDQ data, wellbore data, and drilling permits

"""
Texas RRC API Client

This module provides a robust HTTP client for interacting with the Texas Railroad
Commission (RRC) data services, including:
- Production Data Query (PDQ) CSV downloads
- Wellbore data retrieval
- Drilling permit downloads
- Well lookups by API number

Features:
- Rate limiting (configurable, default 2 requests/second)
- Response caching with TTL
- Automatic retry with exponential backoff
- Support for large file downloads with progress tracking
"""

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urljoin

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

from .cache import FileDownloadCache, TexasRRCCache
from .errors import TexasRRCAPIError, TexasRRCRateLimitError, TexasRRCValidationError

logger = logging.getLogger(__name__)


class TexasRRCClient:
    """
    HTTP client for Texas RRC data services.

    Features:
    - Rate limiting (configurable requests per second)
    - Response caching with TTL
    - Automatic retry with exponential backoff
    - Large file download support
    - Session management for connection pooling

    Example usage:
        client = TexasRRCClient()

        # Download PDQ production data
        pdq_path = client.download_pdq_dump(output_dir=Path("./data"))

        # Query well by API number
        well_data = client.get_well_by_api("42-123-45678")

        # Download drilling permits
        permits_path = client.download_drilling_permits(
            output_dir=Path("./data"),
            date_range=("2024-01-01", "2024-12-31")
        )
    """

    # Base URLs for Texas RRC services
    BASE_URL = "https://mft.rrc.texas.gov"
    PDQ_URL = "https://webapps2.rrc.texas.gov/EWA"
    PUBLIC_DATA_URL = "https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/"  # noqa: E501

    # PDQ download endpoints
    PDQ_ENDPOINTS = {
        "og_production": "/EWA/ewaMain.do?action=ogprodDownloadAction",
        "og_completion": "/EWA/ewaMain.do?action=ogComplDownloadAction",
        "og_well": "/EWA/ewaMain.do?action=ogWellDownloadAction",
        "drilling_permits": "/EWA/ewaMain.do?action=drillPermitDownloadAction",
    }

    # Default configuration
    DEFAULT_TIMEOUT = 60
    DEFAULT_RATE_LIMIT = 2  # requests per second
    DEFAULT_CACHE_TTL = 86400  # 24 hours
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0

    def __init__(
        self,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        timeout: int = DEFAULT_TIMEOUT,
        headers: Optional[Dict[str, str]] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize Texas RRC API client.

        Args:
            rate_limit: Maximum requests per second (default 2, set 0 to disable)
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
            max_retries: Maximum number of retry attempts (default 3)
            retry_delay: Base delay between retries in seconds (default 1.0)
            timeout: Request timeout in seconds (default 60)
            headers: Optional custom HTTP headers
            cache_dir: Optional directory for file cache
        """
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        # Calculate rate limiting interval
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self.last_request_time = 0.0

        # Initialize caches
        self.cache = TexasRRCCache(default_ttl=cache_ttl)
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
            "User-Agent": "WorldEnergyData TexasRRC Client/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
            key_str = f"{endpoint}?{param_str}"
        else:
            key_str = endpoint

        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

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
            TexasRRCAPIError: If requests library unavailable
        """
        if not requests:
            raise TexasRRCAPIError(
                "requests library not installed",
                code="TEXAS_RRC_MISSING_DEPENDENCY",
            )

        logger.debug(f"{method} {url} with params: {params}")

        request_kwargs = {
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
            TexasRRCAPIError: If request fails after retries
            TexasRRCRateLimitError: If rate limit is exceeded
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
                        raise TexasRRCRateLimitError.exceeded(
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
                        raise TexasRRCAPIError.request_failed(
                            endpoint=url,
                            status_code=response.status_code,
                            response_body=response.text,
                        )

                elif response.status_code >= 400:
                    # Client error - don't retry
                    raise TexasRRCAPIError.request_failed(
                        endpoint=url,
                        status_code=response.status_code,
                        response_body=response.text,
                    )

            except TexasRRCAPIError:
                raise
            except TexasRRCRateLimitError:
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
        raise TexasRRCAPIError(error_msg, endpoint=url, cause=last_error)

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
            TexasRRCAPIError: If request fails after retries
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
            TexasRRCAPIError: If download fails
        """
        # Check file cache
        if use_cache:
            cached_path = self.file_cache.get_cached_file(url)
            if cached_path and cached_path.exists():
                # Check if cache is still valid (within TTL)
                if self.file_cache.is_cached(url, max_age=self.cache_ttl):
                    logger.info(f"Using cached file: {cached_path}")
                    # Copy to output path if different
                    if cached_path != output_path:
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
            raise TexasRRCAPIError.download_failed(
                file_type="file",
                reason=str(e),
                cause=e,
            )

    def download_pdq_dump(
        self,
        output_dir: Optional[Path] = None,
        data_type: str = "og_production",
        use_cache: bool = True,
    ) -> Path:
        """
        Download Production Data Query (PDQ) CSV dump.

        The PDQ system provides downloadable CSV files containing
        oil and gas production data for Texas wells.

        Args:
            output_dir: Directory to save downloaded file
            data_type: Type of data to download:
                - "og_production": Oil & gas production data
                - "og_completion": Well completion data
                - "og_well": Well header data
                - "drilling_permits": Drilling permit data
            use_cache: Whether to use cached files if available

        Returns:
            Path to downloaded CSV file

        Raises:
            TexasRRCAPIError: If download fails
            TexasRRCValidationError: If invalid data_type
        """
        if data_type not in self.PDQ_ENDPOINTS:
            valid_types = ", ".join(self.PDQ_ENDPOINTS.keys())
            raise TexasRRCValidationError(
                message=f"Invalid PDQ data type: {data_type}. Valid types: {valid_types}",
                code="TEXAS_RRC_INVALID_DATA_TYPE",
                context={
                    "data_type": data_type,
                    "valid_types": list(self.PDQ_ENDPOINTS.keys()),
                },
            )

        output_dir = output_dir or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        endpoint = self.PDQ_ENDPOINTS[data_type]
        url = urljoin(self.PDQ_URL, endpoint)

        # Generate filename with timestamp
        timestamp = time.strftime("%Y%m%d")
        filename = f"texas_rrc_{data_type}_{timestamp}.csv"
        output_path = output_dir / filename

        logger.info(f"Downloading Texas RRC {data_type} data to {output_path}")

        return self.download_file(url, output_path, use_cache=use_cache)

    def download_wellbore_data(
        self,
        output_dir: Optional[Path] = None,
        district: Optional[int] = None,
        county: Optional[str] = None,
        use_cache: bool = True,
    ) -> Path:
        """
        Download wellbore query data.

        Downloads well data from the Texas RRC EWA system, optionally
        filtered by district or county.

        Args:
            output_dir: Directory to save downloaded file
            district: RRC district number (1-10, or None for all)
            county: County name filter
            use_cache: Whether to use cached files if available

        Returns:
            Path to downloaded file

        Raises:
            TexasRRCAPIError: If download fails
        """
        output_dir = output_dir or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build query parameters
        params: Dict[str, Any] = {}
        if district is not None:
            if not 1 <= district <= 10:
                raise TexasRRCValidationError(
                    message=f"Invalid district number: {district}. Must be 1-10.",
                    code="TEXAS_RRC_INVALID_DISTRICT",
                    context={"district": district},
                )
            params["district"] = str(district)
        if county:
            params["county"] = county.upper()

        url = urljoin(self.PDQ_URL, self.PDQ_ENDPOINTS["og_well"])

        # Generate filename
        timestamp = time.strftime("%Y%m%d")
        suffix = ""
        if district:
            suffix += f"_d{district}"
        if county:
            suffix += f"_{county.lower()}"
        filename = f"texas_rrc_wellbore{suffix}_{timestamp}.csv"
        output_path = output_dir / filename

        logger.info(f"Downloading Texas RRC wellbore data to {output_path}")

        return self.download_file(url, output_path, params=params, use_cache=use_cache)

    def download_drilling_permits(
        self,
        output_dir: Optional[Path] = None,
        date_range: Optional[tuple[str, str]] = None,
        permit_type: Optional[str] = None,
        use_cache: bool = True,
    ) -> Path:
        """
        Download drilling permit files.

        Downloads drilling permit data from the Texas RRC, optionally
        filtered by date range and permit type.

        Args:
            output_dir: Directory to save downloaded file
            date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format
            permit_type: Type of permit to filter (e.g., "new", "amended")
            use_cache: Whether to use cached files if available

        Returns:
            Path to downloaded file

        Raises:
            TexasRRCAPIError: If download fails
        """
        output_dir = output_dir or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        params: Dict[str, Any] = {}
        if date_range:
            start_date, end_date = date_range
            params["startDate"] = start_date
            params["endDate"] = end_date
        if permit_type:
            params["permitType"] = permit_type

        url = urljoin(self.PDQ_URL, self.PDQ_ENDPOINTS["drilling_permits"])

        # Generate filename
        timestamp = time.strftime("%Y%m%d")
        suffix = ""
        if date_range:
            suffix = f"_{date_range[0]}_{date_range[1]}"
        filename = f"texas_rrc_drilling_permits{suffix}_{timestamp}.csv"
        output_path = output_dir / filename

        logger.info(f"Downloading Texas RRC drilling permits to {output_path}")

        return self.download_file(url, output_path, params=params, use_cache=use_cache)

    def get_well_by_api(
        self,
        api_number: str,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Query specific well by API number.

        The API number format for Texas is: 42-XXX-XXXXX or 42XXXXXXXX
        where 42 is the Texas state code.

        Args:
            api_number: Well API number (with or without dashes)
            use_cache: Whether to use cached responses

        Returns:
            Dictionary containing well data

        Raises:
            TexasRRCAPIError: If query fails
            TexasRRCValidationError: If invalid API number format
        """
        # Normalize and validate API number
        normalized_api = self._validate_api_number(api_number)

        cache_key = f"well_api_{normalized_api}"

        # Check cache first
        if use_cache and self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for well {normalized_api}")
                return cached_data

        # Query the well data
        url = f"{self.PDQ_URL}/EWA/ewaMain.do"
        params = {
            "action": "ogWellByApiAction",
            "apiNo": normalized_api,
        }

        try:
            response = self._execute_with_retry("GET", url, params=params)
            content = response.text

            # Parse the HTML response to extract well data
            well_data = self._parse_well_response(content, normalized_api)

            # Cache the result
            if use_cache and self.cache_enabled:
                self.cache.set(cache_key, well_data, self.cache_ttl)

            return well_data

        except Exception as e:
            raise TexasRRCAPIError(
                message=f"Failed to query well {api_number}",
                endpoint=url,
                context={"api_number": api_number},
                cause=e,
            )

    def _validate_api_number(self, api_number: str) -> str:
        """
        Validate and normalize Texas API number.

        Texas API numbers are 10 digits: 42-XXX-XXXXX
        State code (42) + County code (3 digits) + Well number (5 digits)

        Args:
            api_number: API number to validate

        Returns:
            Normalized API number (digits only)

        Raises:
            TexasRRCValidationError: If invalid format
        """
        # Remove dashes and spaces
        normalized = re.sub(r"[-\s]", "", api_number)

        # Check length
        if len(normalized) != 10:
            raise TexasRRCValidationError.invalid_api_number(
                api_number,
                f"Expected 10 digits, got {len(normalized)}",
            )

        # Check all digits
        if not normalized.isdigit():
            raise TexasRRCValidationError.invalid_api_number(
                api_number,
                "API number must contain only digits",
            )

        # Check Texas state code
        if not normalized.startswith("42"):
            raise TexasRRCValidationError.invalid_api_number(
                api_number,
                "Texas API numbers must start with state code 42",
            )

        return normalized

    def _parse_well_response(
        self, html_content: str, api_number: str
    ) -> Dict[str, Any]:
        """
        Parse HTML response from well query.

        This is a simplified parser that extracts key well information
        from the RRC's HTML response format.

        Args:
            html_content: HTML response content
            api_number: API number for reference

        Returns:
            Dictionary with parsed well data
        """
        # Basic structure for well data
        well_data: Dict[str, Any] = {
            "api_number": api_number,
            "state_code": "42",
            "county_code": api_number[2:5],
            "well_number": api_number[5:],
            "raw_response_available": True,
        }

        # Simple pattern matching for common fields
        patterns = {
            "lease_name": r"Lease\s*Name[:\s]*([^<\n]+)",
            "operator_name": r"Operator[:\s]*([^<\n]+)",
            "well_type": r"Well\s*Type[:\s]*([^<\n]+)",
            "status": r"Well\s*Status[:\s]*([^<\n]+)",
            "district": r"District[:\s]*(\d+)",
            "field_name": r"Field[:\s]*([^<\n]+)",
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                well_data[field] = match.group(1).strip()

        return well_data

    def close(self) -> None:
        """Close the client session and clean up resources."""
        if self.session:
            self.session.close()
            self.session = None
        logger.debug("Texas RRC client session closed")

    def __enter__(self) -> "TexasRRCClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats


__all__ = ["TexasRRCClient"]
