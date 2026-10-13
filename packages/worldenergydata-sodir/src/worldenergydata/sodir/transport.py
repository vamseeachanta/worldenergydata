"""
SODIR API client with rate limiting and caching.

This module provides a robust HTTP client for interacting with the SODIR REST API,
including rate limiting, caching, retry logic, and error handling.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, Mapping, Optional, Protocol
from urllib.parse import urlencode

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    requests_available = True
except ImportError:
    # For testing without requests installed
    requests_available = False

from .cache import SodirCache
from .errors import SodirAPIError, SodirRateLimitError

logger = logging.getLogger(__name__)


class ResponseLike(Protocol):
    """Response fields used by the legacy retry loop."""

    @property
    def status_code(self) -> int: ...

    @property
    def headers(self) -> Mapping[str, str]: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Dict[str, Any]: ...


class SodirTransport:
    """
    HTTP client for SODIR API interactions.

    Features:
    - Rate limiting (configurable requests per second)
    - Response caching with TTL
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Support for all SODIR data endpoints
    """

    feature_observations: list[Dict[str, Any]]

    def __init__(
        self,
        base_url: str,
        rate_limit: int = 10,
        cache_ttl: int = 86400,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize SODIR API client.

        Args:
            base_url: Base URL for SODIR API
            rate_limit: Maximum requests per second (0 to disable)
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            timeout: Request timeout in seconds
            headers: Optional custom HTTP headers
        """
        self.base_url = base_url.rstrip("/")
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        # Calculate rate limiting interval
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self.last_request_time = 0.0

        # Initialize cache
        self.cache = SodirCache(default_ttl=cache_ttl)
        self.cache_enabled = True

        # Setup HTTP headers
        self.headers = self._setup_headers(headers)

        # Setup session with retry strategy if requests is available
        self.session = self._setup_session() if requests_available else None

    def _setup_headers(
        self, custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Supply the entity client's HTTP header contract."""
        raise NotImplementedError

    def _setup_session(self) -> Optional[requests.Session]:
        """
        Setup requests session with retry strategy.

        Returns:
            Configured requests Session
        """
        if not requests_available:
            return None

        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=0,  # We handle retries manually for better control
            backoff_factor=0,
            status_forcelist=[],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make GET request to SODIR API with rate limiting and caching.

        Args:
            endpoint: API endpoint (e.g., '/api/rest/1001')
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            SodirAPIError: If request fails after retries
            SodirRateLimitError: If rate limit is exceeded
        """
        # Generate cache key
        cache_key = self._generate_cache_key(endpoint, params)

        # Check cache first
        if self.cache_enabled:
            cached_data: Dict[str, Any] | None = self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for {endpoint}")
                return cached_data

        # Apply rate limiting
        self._rate_limit()

        # Build full URL
        url = f"{self.base_url}{endpoint}"

        # Execute request with retry logic
        response_data = self._execute_request_with_retry(url, params)

        # Cache successful response
        if self.cache_enabled and response_data:
            self.cache.set(cache_key, response_data, self.cache_ttl)

        return response_data

    def _generate_cache_key(self, endpoint: str, params: Optional[Dict]) -> str:
        """
        Generate cache key from endpoint and parameters.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Unique cache key string
        """
        if params:
            # Sort parameters for consistent cache keys
            sorted_params = sorted(params.items())
            param_str = urlencode(sorted_params)
            key_str = f"{endpoint}?{param_str}"
        else:
            key_str = endpoint

        # This digest identifies cache entries; it is not a security primitive.
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

    def _rate_limit(self) -> None:
        """Implement rate limiting with minimum interval between requests."""
        if self.min_interval > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f} seconds")
                time.sleep(sleep_time)
            self.last_request_time = time.time()

    def _execute_request_with_retry(
        self, url: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with retry logic.

        Args:
            url: Full URL for request
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            SodirAPIError: If request fails after retries
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._make_request(url, params)

                # Check response status
                if response.status_code == 200:
                    data: Dict[str, Any] = response.json()
                    return data

                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(
                        response.headers.get("Retry-After", self.retry_delay)
                    )
                    if attempt < self.max_retries:
                        logger.warning(
                            f"Rate limit exceeded, retrying after {retry_after} seconds"
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        raise SodirRateLimitError(
                            "Rate limit exceeded", retry_after=retry_after
                        )

                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2**attempt)
                        logger.warning(
                            f"Server error {response.status_code}, "
                            f"retrying in {delay} seconds "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise SodirAPIError(
                            f"Server error: {response.text}",
                            status_code=response.status_code,
                        )

                elif response.status_code >= 400:
                    # Client error - don't retry
                    raise SodirAPIError(
                        f"Client error: {response.text}",
                        status_code=response.status_code,
                    )

            except Exception as e:
                # Handle both requests exceptions and other errors
                if requests_available and isinstance(
                    e, requests.exceptions.RequestException
                ):
                    request_error: Exception = e
                else:
                    request_error = e
                last_error = request_error
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Request failed: {request_error}, retrying in {delay} seconds "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    continue

        # All retries exhausted
        error_msg = f"Request failed after {self.max_retries + 1} attempts"
        if last_error:
            error_msg += f": {last_error}"
        raise SodirAPIError(error_msg)

    def _make_request(self, url: str, params: Optional[Dict] = None) -> ResponseLike:
        """
        Make actual HTTP request.

        Args:
            url: Request URL
            params: Query parameters

        Returns:
            Response object
        """
        if not requests_available:
            # For testing without requests library
            class MockResponse:
                status_code = 200
                headers: Dict[str, str] = {}
                text = '{"data": []}'

                def json(self) -> Dict[str, Any]:
                    return {"data": []}

            return MockResponse()

        # Add format=json to params if not present
        if params is None:
            params = {}
        if "format" not in params:
            params["format"] = "json"

        logger.debug(f"GET {url} with params: {params}")

        if self.session:
            response = self.session.get(
                url, params=params, headers=self.headers, timeout=self.timeout
            )
        else:
            response = requests.get(
                url, params=params, headers=self.headers, timeout=self.timeout
            )

        return response
