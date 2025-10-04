"""
Base Scraper for Marine Safety Module

Abstract base class for all web scrapers with common functionality.
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from worldenergydata.modules.marine_safety.config import get_config
from worldenergydata.modules.marine_safety.constants import DataSource, RETRYABLE_HTTP_CODES
from worldenergydata.modules.marine_safety.exceptions import (
    HTTPError,
    TimeoutError,
    RateLimitError,
    ParsingError,
    ScraperError
)
from worldenergydata.modules.marine_safety.utils.logger import get_logger


class BaseScraper(ABC):
    """
    Abstract base class for all web scrapers.

    Provides common functionality for HTTP requests, rate limiting,
    error handling, and retry logic.
    """

    def __init__(
        self,
        source: DataSource,
        base_url: str,
        name: Optional[str] = None
    ) -> None:
        """
        Initialize the base scraper.

        Args:
            source: Data source identifier
            base_url: Base URL for the data source
            name: Optional custom name for the scraper
        """
        self.source = source
        self.base_url = base_url
        self.name = name or f"{source.value}_scraper"
        self.config = get_config().scraper
        self.logger = get_logger(self.name)

        # HTTP client configuration
        self.client = httpx.Client(
            timeout=self.config.request_timeout,
            headers={"User-Agent": self.config.user_agent},
            follow_redirects=True
        )

        # Rate limiting
        self._last_request_time: Optional[float] = None
        self._request_count = 0

    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
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
        **kwargs: Any
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.

        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments for httpx

        Returns:
            httpx.Response: HTTP response

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
                self.logger.debug(f"Request {method} {full_url} (attempt {retries + 1})")

                response = self.client.request(method, full_url, **kwargs)
                response.raise_for_status()

                self._request_count += 1
                return response

            except httpx.TimeoutException as e:
                if retries >= self.config.max_retries:
                    raise TimeoutError(
                        url=full_url,
                        timeout=self.config.request_timeout
                    )
                retries += 1
                time.sleep(self.config.retry_delay * retries)

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                # Handle rate limiting
                if status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    if retries >= self.config.max_retries:
                        raise RateLimitError(
                            source=self.source.value,
                            retry_after=retry_after
                        )
                    self.logger.warning(
                        f"Rate limited, waiting {retry_after}s before retry"
                    )
                    time.sleep(retry_after)
                    retries += 1
                    continue

                # Retry on server errors
                if status_code in RETRYABLE_HTTP_CODES and retries < self.config.max_retries:
                    retries += 1
                    time.sleep(self.config.retry_delay * retries)
                    continue

                # Don't retry client errors
                raise HTTPError(url=full_url, status_code=status_code)

            except httpx.RequestError as e:
                if retries >= self.config.max_retries:
                    raise HTTPError(
                        url=full_url,
                        status_code=0,
                        message=f"Request failed: {str(e)}"
                    )
                retries += 1
                time.sleep(self.config.retry_delay * retries)

        raise HTTPError(
            url=full_url,
            status_code=0,
            message="Max retries exceeded"
        )

    def _parse_html(self, content: str) -> BeautifulSoup:
        """
        Parse HTML content.

        Args:
            content: HTML content string

        Returns:
            BeautifulSoup: Parsed HTML
        """
        try:
            return BeautifulSoup(content, "html.parser")
        except Exception as e:
            raise ParsingError(
                source=self.source.value,
                reason=f"Failed to parse HTML: {str(e)}"
            )

    def _extract_text(
        self,
        element: Any,
        selector: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Safely extract text from HTML element.

        Args:
            element: BeautifulSoup element
            selector: CSS selector
            default: Default value if not found

        Returns:
            Extracted text or default value
        """
        try:
            found = element.select_one(selector)
            if found:
                return found.get_text(strip=True)
            return default
        except Exception as e:
            self.logger.warning(f"Failed to extract text with selector '{selector}': {e}")
            return default

    def _extract_attribute(
        self,
        element: Any,
        selector: str,
        attribute: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Safely extract attribute from HTML element.

        Args:
            element: BeautifulSoup element
            selector: CSS selector
            attribute: Attribute name
            default: Default value if not found

        Returns:
            Extracted attribute or default value
        """
        try:
            found = element.select_one(selector)
            if found and found.has_attr(attribute):
                return found[attribute]
            return default
        except Exception as e:
            self.logger.warning(
                f"Failed to extract attribute '{attribute}' with selector '{selector}': {e}"
            )
            return default

    @abstractmethod
    def scrape(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape data from the source.

        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            List of dictionaries containing scraped data
        """
        pass

    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate scraped data.

        Args:
            data: Dictionary containing scraped data

        Returns:
            True if data is valid
        """
        pass

    def close(self) -> None:
        """Close HTTP client and clean up resources"""
        self.client.close()
        self.logger.info(
            f"Scraper closed. Total requests made: {self._request_count}"
        )

    def __enter__(self) -> "BaseScraper":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()
