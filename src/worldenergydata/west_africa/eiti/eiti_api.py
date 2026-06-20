"""
EITI Data Explorer API client.

Provides access to the EITI Data Explorer JSON API at https://data.eiti.org/
with country, year, and company filtering, in-memory caching, and retry logic.

EITI data has an 18-24 month publication lag relative to the reporting year.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    requests = None
    RequestException = Exception

logger = logging.getLogger(__name__)

EITI_BASE_URL = "https://data.eiti.org"

# Countries with structured EITI data (full or pilot compliance)
_SUPPORTED_COUNTRIES = [
    "Nigeria",
    "Angola",
    "Ghana",
    "Mozambique",
    "Tanzania",
    "Liberia",
    "Cameroon",
    "Côte d'Ivoire",
    "Kazakhstan",
    "Azerbaijan",
    "Iraq",
]


class EitiApiError(Exception):
    """Raised when the EITI API returns an error or is unreachable."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class EitiApiClient:
    """
    JSON API client for the EITI Data Explorer.

    Supports country/year/company filtering for production and payment data.
    In-memory caching prevents duplicate network requests within a session.
    """

    def __init__(
        self,
        base_url: str = EITI_BASE_URL,
        timeout: int = 30,
        cache_enabled: bool = True,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self.max_retries = max_retries
        self.supported_countries: List[str] = list(_SUPPORTED_COUNTRIES)
        self._cache: Dict[str, Any] = {}

    def _cache_key(self, endpoint: str, params: Optional[Dict]) -> str:
        raw = endpoint + json.dumps(params or {}, sort_keys=True)
        return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """
        Make GET request to EITI API with caching and retry.

        Args:
            endpoint: API endpoint path (e.g. '/api/v1/countries').
            params: Optional query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            EitiApiError: On HTTP error or network failure after retries.
        """
        cache_key = self._cache_key(endpoint, params)
        if self.cache_enabled and cache_key in self._cache:
            logger.debug("EITI cache hit for %s", endpoint)
            return self._cache[cache_key]

        if requests is None:
            raise EitiApiError("requests library not installed")

        url = f"{self.base_url}{endpoint}"
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    if self.cache_enabled:
                        self._cache[cache_key] = data
                    return data

                if resp.status_code >= 500:
                    raise EitiApiError(
                        f"EITI server error {resp.status_code}: {resp.text}",
                        status_code=resp.status_code,
                    )

                raise EitiApiError(
                    f"EITI API error {resp.status_code}: {resp.text}",
                    status_code=resp.status_code,
                )

            except EitiApiError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "EITI request attempt %d/%d failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )

        raise EitiApiError(
            "EITI API unreachable after retries"
            + (f": {last_error}" if last_error else "")
        )

    def get_countries(self) -> List[Dict[str, Any]]:
        """
        Retrieve list of EITI member countries.

        Returns:
            List of country dicts with id, name, and iso2 keys.
        """
        data = self._get("/api/v1/countries")
        if isinstance(data, list):
            return data
        return data.get("data", []) if isinstance(data, dict) else []

    def get_production_data(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        company: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve production volume data with optional filters.

        Args:
            country: Country name filter (e.g. 'Nigeria').
            year: Reporting year filter.
            company: Company name filter.

        Returns:
            List of production record dicts.
        """
        params: Dict[str, Any] = {}
        if country:
            params["country"] = country
        if year:
            params["year"] = year
        if company:
            params["company"] = company

        data = self._get("/api/v1/production", params=params)
        if isinstance(data, list):
            return data
        return data.get("data", []) if isinstance(data, dict) else []

    def get_payment_data(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        company: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve government revenue and company payment data.

        Args:
            country: Country name filter (e.g. 'Nigeria').
            year: Reporting year filter.
            company: Company name filter.

        Returns:
            List of payment record dicts.
        """
        params: Dict[str, Any] = {}
        if country:
            params["country"] = country
        if year:
            params["year"] = year
        if company:
            params["company"] = company

        data = self._get("/api/v1/payments", params=params)
        if isinstance(data, list):
            return data
        return data.get("data", []) if isinstance(data, dict) else []
