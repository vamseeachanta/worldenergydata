# ABOUTME: Base client for metocean data sources with HTTP handling
# ABOUTME: Provides rate limiting, retry logic, and error handling for all API clients

"""
Base Client for Metocean Data Sources

Abstract base class providing common HTTP functionality with rate limiting,
retry logic, and error handling for all metocean API clients.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from urllib.parse import urljoin

import httpx

from worldenergydata.modules.metocean.config import get_config
from worldenergydata.modules.metocean.constants import RETRYABLE_HTTP_CODES, DataSource
from worldenergydata.modules.metocean.exceptions import (
    HTTPError,
    ParsingError,
    RateLimitError,
    TimeoutError,
)

T = TypeVar("T")


@dataclass
class FetchResult(Generic[T]):
    """
    Result container for fetch operations.

    Encapsulates the results of a data fetch operation including
    metadata about the fetch and any errors encountered.

    Attributes:
        data: List of fetched data items
        source: Data source identifier
        fetch_time: Timestamp of the fetch operation
        records_count: Number of records fetched
        had_errors: Whether any errors occurred during fetch
        error_messages: List of error messages if any
    """

    data: List[T]
    source: DataSource
    fetch_time: datetime
    records_count: int
    had_errors: bool = False
    error_messages: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Ensure error_messages is initialized as list."""
        if self.error_messages is None:
            self.error_messages = []


class BaseClient(ABC):
    """
    Abstract base class for all metocean API clients.

    Provides common functionality for HTTP requests, rate limiting,
    error handling, and retry logic. Subclasses implement source-specific
    data fetching methods.

    Attributes:
        source: Data source identifier
        base_url: Base URL for API requests
        name: Client name for logging
        config: API configuration from MetoceanConfig
        logger: Logger instance for this client
        client: HTTP client instance
    """

    def __init__(
        self, source: DataSource, base_url: str, name: Optional[str] = None
    ) -> None:
        """
        Initialize the base client.

        Args:
            source: Data source identifier
            base_url: Base URL for the data source
            name: Optional custom name for the client
        """
        self.source = source
        self.base_url = base_url
        self.name = name or f"{source.value}_client"
        self.config = get_config().api
        self.logger = logging.getLogger(f"metocean.{self.name}")

        # HTTP client configuration
        self.client = httpx.Client(
            timeout=self.config.request_timeout,
            headers={"User-Agent": self.config.user_agent},
            follow_redirects=True,
        )

        # Rate limiting state
        self._last_request_time: Optional[float] = None
        self._request_count = 0

    def _wait_for_rate_limit(self) -> None:
        """
        Enforce rate limiting between requests.

        Ensures minimum delay between consecutive requests to avoid
        overwhelming the data source or triggering rate limits.
        """
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.config.rate_limit_delay:
                wait_time = self.config.rate_limit_delay - elapsed
                self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
        self._last_request_time = time.time()

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.

        Handles rate limiting, retryable errors, and exponential backoff.
        All requests go through this method for consistent error handling.

        Args:
            url: URL to request (relative to base_url)
            method: HTTP method (GET, POST, etc.)
            params: Optional query parameters
            **kwargs: Additional arguments for httpx

        Returns:
            httpx.Response: HTTP response object

        Raises:
            HTTPError: If request fails after retries
            TimeoutError: If request times out
            RateLimitError: If rate limited by server
        """
        self._wait_for_rate_limit()

        full_url = urljoin(self.base_url, url)
        retries = 0

        while retries <= self.config.max_retries:
            try:
                self.logger.debug(
                    f"Request {method} {full_url} (attempt {retries + 1})"
                )

                response = self.client.request(
                    method, full_url, params=params, **kwargs
                )
                response.raise_for_status()

                self._request_count += 1
                return response

            except httpx.TimeoutException:
                if retries >= self.config.max_retries:
                    raise TimeoutError(
                        url=full_url, timeout=self.config.request_timeout
                    )
                retries += 1
                wait_time = self.config.retry_delay * retries
                self.logger.warning(f"Request timeout, retrying in {wait_time}s")
                time.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                # Handle rate limiting (429)
                if status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    if retries >= self.config.max_retries:
                        raise RateLimitError(
                            source=self.source.value, retry_after=retry_after
                        )
                    self.logger.warning(
                        f"Rate limited, waiting {retry_after}s before retry"
                    )
                    time.sleep(retry_after)
                    retries += 1
                    continue

                # Retry on server errors
                if (
                    status_code in RETRYABLE_HTTP_CODES
                    and retries < self.config.max_retries
                ):
                    retries += 1
                    wait_time = self.config.retry_delay * retries
                    self.logger.warning(
                        f"Server error {status_code}, " f"retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue

                # Don't retry client errors (4xx except 429, 408)
                raise HTTPError(url=full_url, status_code=status_code)

            except httpx.RequestError as e:
                if retries >= self.config.max_retries:
                    raise HTTPError(
                        url=full_url, status_code=0, message=f"Request failed: {str(e)}"
                    )
                retries += 1
                wait_time = self.config.retry_delay * retries
                self.logger.warning(f"Request error: {e}, retrying in {wait_time}s")
                time.sleep(wait_time)

        raise HTTPError(url=full_url, status_code=0, message="Max retries exceeded")

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """
        Convenience method for GET requests.

        Args:
            url: URL to request (relative to base_url)
            params: Optional query parameters

        Returns:
            httpx.Response: HTTP response object
        """
        return self._make_request(url, "GET", params=params)

    def _get_json(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GET request returning parsed JSON.

        Args:
            url: URL to request (relative to base_url)
            params: Optional query parameters

        Returns:
            Dict containing parsed JSON response

        Raises:
            ParsingError: If JSON parsing fails
        """
        response = self._get(url, params)
        try:
            return response.json()
        except Exception as e:
            raise ParsingError(
                source=self.source.value, reason=f"Failed to parse JSON: {str(e)}"
            )

    def _get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        GET request returning text content.

        Args:
            url: URL to request (relative to base_url)
            params: Optional query parameters

        Returns:
            str: Response text content
        """
        response = self._get(url, params)
        return response.text

    @abstractmethod
    def fetch_stations(
        self, bbox: Optional[tuple] = None, active_only: bool = True
    ) -> FetchResult:
        """
        Fetch available stations/buoys from the source.

        Args:
            bbox: Optional bounding box (lon_min, lon_max, lat_min, lat_max)
            active_only: If True, only return active stations

        Returns:
            FetchResult containing station metadata
        """
        pass

    @abstractmethod
    def fetch_realtime(
        self, station_id: str, parameters: Optional[List[str]] = None
    ) -> FetchResult:
        """
        Fetch real-time data for a station.

        Args:
            station_id: Station identifier
            parameters: Optional list of parameters to fetch

        Returns:
            FetchResult containing real-time observations
        """
        pass

    @abstractmethod
    def fetch_historical(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
        parameters: Optional[List[str]] = None,
    ) -> FetchResult:
        """
        Fetch historical data for a station.

        Args:
            station_id: Station identifier
            start_date: Start of date range
            end_date: End of date range
            parameters: Optional list of parameters to fetch

        Returns:
            FetchResult containing historical observations
        """
        pass

    def close(self) -> None:
        """Close HTTP client and clean up resources."""
        self.client.close()
        self.logger.info(f"Client closed. Total requests made: {self._request_count}")

    def __enter__(self) -> "BaseClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
