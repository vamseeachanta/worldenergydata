"""
SODIR API client with rate limiting and caching.

This module provides a robust HTTP client for interacting with the SODIR REST API,
including rate limiting, caching, retry logic, and error handling.
"""

import logging
import time
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlencode

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    # For testing without requests installed
    requests = None

from .cache import SodirCache
from .errors import SodirAPIError, SodirRateLimitError

logger = logging.getLogger(__name__)


class SodirAPIClient:
    """
    HTTP client for SODIR API interactions.
    
    Features:
    - Rate limiting (configurable requests per second)
    - Response caching with TTL
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Support for all SODIR data endpoints
    """
    
    def __init__(
        self,
        base_url: str,
        rate_limit: int = 10,
        cache_ttl: int = 86400,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
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
        self.base_url = base_url.rstrip('/')
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Calculate rate limiting interval
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self.last_request_time = 0
        
        # Initialize cache
        self.cache = SodirCache(default_ttl=cache_ttl)
        self.cache_enabled = True
        
        # Setup HTTP headers
        self.headers = self._setup_headers(headers)
        
        # Setup session with retry strategy if requests is available
        self.session = self._setup_session() if requests else None
    
    def _setup_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Setup default and custom HTTP headers.
        
        Args:
            custom_headers: Optional custom headers to add
        
        Returns:
            Combined headers dictionary
        """
        headers = {
            "User-Agent": "WorldEnergyData SODIR Client/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json"
        }
        
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    def _setup_session(self):
        """
        Setup requests session with retry strategy.
        
        Returns:
            Configured requests Session
        """
        if not requests:
            return None
            
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=0,  # We handle retries manually for better control
            backoff_factor=0,
            status_forcelist=[]
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
            cached_data = self.cache.get(cache_key)
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
        
        # Create hash for shorter cache keys
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _rate_limit(self):
        """Implement rate limiting with minimum interval between requests."""
        if self.min_interval > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f} seconds")
                time.sleep(sleep_time)
            self.last_request_time = time.time()
    
    def _execute_request_with_retry(
        self, 
        url: str, 
        params: Optional[Dict] = None
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
                    return response.json()
                
                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get("Retry-After", self.retry_delay))
                    if attempt < self.max_retries:
                        logger.warning(f"Rate limit exceeded, retrying after {retry_after} seconds")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise SodirRateLimitError(
                            "Rate limit exceeded",
                            retry_after=retry_after
                        )
                
                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Server error {response.status_code}, "
                            f"retrying in {delay} seconds (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise SodirAPIError(
                            f"Server error: {response.text}",
                            status_code=response.status_code
                        )
                
                elif response.status_code >= 400:
                    # Client error - don't retry
                    raise SodirAPIError(
                        f"Client error: {response.text}",
                        status_code=response.status_code
                    )
                
            except Exception as e:
                # Handle both requests exceptions and other errors
                if requests and isinstance(e, requests.exceptions.RequestException):
                    request_error = e
                else:
                    request_error = e
                last_error = request_error
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
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
    
    def _make_request(self, url: str, params: Optional[Dict] = None):
        """
        Make actual HTTP request.
        
        Args:
            url: Request URL
            params: Query parameters
        
        Returns:
            Response object
        """
        if not requests:
            # For testing without requests library
            class MockResponse:
                status_code = 200
                headers = {}
                text = '{"data": []}'
                def json(self):
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
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
        else:
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
        
        return response
    
    # SODIR-specific endpoint methods
    
    def get_blocks(self, **kwargs) -> List[Dict]:
        """
        Get block data from SODIR API.
        
        Endpoint: /api/rest/1001 - Norwegian Continental Shelf blocks
        
        Args:
            **kwargs: Query parameters such as:
                - startdate: Filter by start date (YYYY-MM-DD)
                - enddate: Filter by end date (YYYY-MM-DD)
        
        Returns:
            List of block data dictionaries
        """
        response = self.get("/1001", params=kwargs)
        return response.get("data", []) if response else []
    
    def get_wellbores(self, **kwargs) -> List[Dict]:
        """
        Get wellbore data from SODIR API.
        
        Endpoint: /api/rest/5000 - Wellbore drilling and completion
        
        Args:
            **kwargs: Query parameters such as:
                - wellboreStatus: Filter by status (DRILLING, COMPLETED, ABANDONED)
                - npdidBlock: Filter by block ID
        
        Returns:
            List of wellbore data dictionaries
        """
        response = self.get("/5000", params=kwargs)
        return response.get("data", []) if response else []
    
    def get_fields(self, **kwargs) -> List[Dict]:
        """
        Get field data from SODIR API.
        
        Endpoint: /api/rest/7100 - Field information and reserves
        
        Args:
            **kwargs: Query parameters such as:
                - fieldStatus: Filter by status
                - operator: Filter by operator company
        
        Returns:
            List of field data dictionaries
        """
        response = self.get("/7100", params=kwargs)
        return response.get("data", []) if response else []
    
    def get_discoveries(self, **kwargs) -> List[Dict]:
        """
        Get discovery data from SODIR API.
        
        Endpoint: /api/rest/7000 - Discovery information
        
        Args:
            **kwargs: Query parameters such as:
                - discoveryYear: Filter by discovery year
                - hydrocarbon: Filter by type (OIL, GAS, OIL/GAS)
        
        Returns:
            List of discovery data dictionaries
        """
        response = self.get("/7000", params=kwargs)
        return response.get("data", []) if response else []
    
    def get_surveys(self, **kwargs) -> List[Dict]:
        """
        Get survey data from SODIR API.
        
        Endpoint: /api/rest/4000 - Seismic surveys
        
        Args:
            **kwargs: Query parameters such as:
                - surveyType: Type of survey (2D_SEISMIC, 3D_SEISMIC)
                - acquisitionYear: Filter by year
        
        Returns:
            List of survey data dictionaries
        """
        response = self.get("/4000", params=kwargs)
        return response.get("data", []) if response else []