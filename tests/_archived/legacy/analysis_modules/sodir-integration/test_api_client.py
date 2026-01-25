"""
Tests for SODIR API client with rate limiting, caching, and error handling.

Tests verify:
- HTTP client functionality
- Rate limiting enforcement
- Caching with TTL
- Error handling and retries
- All SODIR endpoint methods
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add the module path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sodir_module.api_client import SodirAPIClient
from sodir_module.cache import SodirCache, CacheEntry
from sodir_module.errors import (
    SodirAPIError, 
    SodirRateLimitError,
    SodirConfigurationError
)


class TestSodirAPIClient:
    """Test SODIR API client basic functionality."""
    
    @pytest.fixture
    def api_client(self):
        """Create API client instance for testing."""
        return SodirAPIClient(
            base_url="https://factmaps.sodir.no/api/rest",
            rate_limit=10
        )
    
    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": [{"id": 1, "name": "test"}]}
        response.text = '{"data": [{"id": 1, "name": "test"}]}'
        response.headers = {"Content-Type": "application/json"}
        return response
    
    def test_api_client_initialization(self):
        """Test API client initializes with correct parameters."""
        client = SodirAPIClient(
            base_url="https://factmaps.sodir.no/api/rest",
            rate_limit=10,
            cache_ttl=86400
        )
        
        assert client.base_url == "https://factmaps.sodir.no/api/rest"
        assert client.rate_limit == 10
        assert client.cache_ttl == 86400
        assert client.min_interval == 0.1  # 1/10 = 0.1 seconds
    
    def test_api_client_removes_trailing_slash(self):
        """Test that API client removes trailing slash from base URL."""
        client = SodirAPIClient(
            base_url="https://factmaps.sodir.no/api/rest/",
            rate_limit=10
        )
        
        assert client.base_url == "https://factmaps.sodir.no/api/rest"
    
    @patch('sodir_module.api_client.requests.get')
    def test_get_request_basic(self, mock_get, api_client, mock_response):
        """Test basic GET request functionality."""
        mock_get.return_value = mock_response
        
        result = api_client.get("/test-endpoint")
        
        assert result == {"data": [{"id": 1, "name": "test"}]}
        mock_get.assert_called_once_with(
            "https://factmaps.sodir.no/api/rest/test-endpoint",
            params=None,
            headers=api_client.headers,
            timeout=api_client.timeout
        )
    
    @patch('sodir_module.api_client.requests.get')
    def test_get_request_with_params(self, mock_get, api_client, mock_response):
        """Test GET request with query parameters."""
        mock_get.return_value = mock_response
        
        params = {"format": "json", "limit": 100}
        result = api_client.get("/test-endpoint", params=params)
        
        assert result == {"data": [{"id": 1, "name": "test"}]}
        mock_get.assert_called_once_with(
            "https://factmaps.sodir.no/api/rest/test-endpoint",
            params=params,
            headers=api_client.headers,
            timeout=api_client.timeout
        )


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.fixture
    def fast_client(self):
        """Create API client with high rate limit for testing."""
        return SodirAPIClient(
            base_url="https://test.api",
            rate_limit=100  # 100 requests per second
        )
    
    @pytest.fixture
    def slow_client(self):
        """Create API client with low rate limit for testing."""
        return SodirAPIClient(
            base_url="https://test.api",
            rate_limit=2  # 2 requests per second
        )
    
    def test_rate_limit_calculation(self):
        """Test rate limit interval calculation."""
        client1 = SodirAPIClient("https://test.api", rate_limit=10)
        assert client1.min_interval == 0.1  # 1/10
        
        client2 = SodirAPIClient("https://test.api", rate_limit=5)
        assert client2.min_interval == 0.2  # 1/5
        
        client3 = SodirAPIClient("https://test.api", rate_limit=0)
        assert client3.min_interval == 0  # No rate limiting
    
    @patch('sodir_module.api_client.requests.get')
    def test_rate_limiting_enforced(self, mock_get, slow_client):
        """Test that rate limiting delays requests appropriately."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        # Make two rapid requests
        start_time = time.time()
        slow_client.get("/test1")
        slow_client.get("/test2")
        elapsed = time.time() - start_time
        
        # With rate_limit=2, min_interval=0.5 seconds
        # Second request should be delayed
        assert elapsed >= 0.4  # Allow some tolerance
        assert mock_get.call_count == 2
    
    @patch('sodir_module.api_client.requests.get')
    def test_no_rate_limiting_when_disabled(self, mock_get):
        """Test that rate limiting can be disabled."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        client = SodirAPIClient("https://test.api", rate_limit=0)
        
        # Make rapid requests
        start_time = time.time()
        for _ in range(5):
            client.get("/test")
        elapsed = time.time() - start_time
        
        # Should complete almost instantly
        assert elapsed < 0.1
        assert mock_get.call_count == 5


class TestCaching:
    """Test caching functionality."""
    
    @pytest.fixture
    def client_with_cache(self):
        """Create API client with caching enabled."""
        client = SodirAPIClient(
            base_url="https://test.api",
            rate_limit=10,
            cache_ttl=3600  # 1 hour
        )
        client.cache_enabled = True
        return client
    
    @patch('sodir_module.api_client.requests.get')
    def test_cache_hit(self, mock_get, client_with_cache):
        """Test that cached responses are returned without API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": ["first"]}
        mock_get.return_value = mock_response
        
        # First call - should hit API
        result1 = client_with_cache.get("/test")
        assert result1 == {"data": ["first"]}
        assert mock_get.call_count == 1
        
        # Second call - should hit cache
        result2 = client_with_cache.get("/test")
        assert result2 == {"data": ["first"]}
        assert mock_get.call_count == 1  # No additional API call
    
    @patch('sodir_module.api_client.requests.get')
    def test_cache_expiration(self, mock_get, client_with_cache):
        """Test that cache entries expire after TTL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": ["first"]}
        mock_get.return_value = mock_response
        
        # Set cache TTL to very short time for testing
        client_with_cache.cache.default_ttl = 0.1  # 100ms
        
        # First call
        result1 = client_with_cache.get("/test")
        assert mock_get.call_count == 1
        
        # Wait for cache to expire
        time.sleep(0.2)
        
        # Second call should hit API again
        mock_response.json.return_value = {"data": ["second"]}
        result2 = client_with_cache.get("/test")
        assert result2 == {"data": ["second"]}
        assert mock_get.call_count == 2
    
    @patch('sodir_module.api_client.requests.get')
    def test_cache_key_includes_params(self, mock_get, client_with_cache):
        """Test that cache keys include query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        # Different parameters should create different cache entries
        client_with_cache.get("/test", params={"page": 1})
        client_with_cache.get("/test", params={"page": 2})
        client_with_cache.get("/test")  # No params
        
        assert mock_get.call_count == 3  # All three should hit API
    
    def test_cache_can_be_cleared(self, client_with_cache):
        """Test that cache can be manually cleared."""
        # Add some cache entries
        client_with_cache.cache.set("key1", {"data": 1})
        client_with_cache.cache.set("key2", {"data": 2})
        
        assert client_with_cache.cache.get("key1") == {"data": 1}
        assert client_with_cache.cache.get("key2") == {"data": 2}
        
        # Clear cache
        client_with_cache.cache.clear()
        
        assert client_with_cache.cache.get("key1") is None
        assert client_with_cache.cache.get("key2") is None


class TestErrorHandling:
    """Test error handling and retry logic."""
    
    @pytest.fixture
    def client(self):
        """Create API client for testing."""
        return SodirAPIClient(
            base_url="https://test.api",
            rate_limit=10,
            max_retries=3,
            retry_delay=0.1  # Short delay for testing
        )
    
    @patch('sodir_module.api_client.requests.get')
    def test_retry_on_server_error(self, mock_get, client):
        """Test retry logic for 5xx server errors."""
        # Simulate server error then success
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": []}
        
        mock_get.side_effect = [error_response, error_response, success_response]
        
        result = client.get("/test")
        
        assert result == {"data": []}
        assert mock_get.call_count == 3
    
    @patch('sodir_module.api_client.requests.get')
    def test_retry_on_rate_limit(self, mock_get, client):
        """Test retry logic for rate limit errors."""
        # Simulate rate limit then success
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}
        rate_limit_response.text = "Rate limit exceeded"
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": []}
        
        mock_get.side_effect = [rate_limit_response, success_response]
        
        result = client.get("/test")
        
        assert result == {"data": []}
        assert mock_get.call_count == 2
    
    @patch('sodir_module.api_client.requests.get')
    def test_max_retries_exceeded(self, mock_get, client):
        """Test that retries stop after max attempts."""
        # Always return server error
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        mock_get.return_value = error_response
        
        with pytest.raises(SodirAPIError) as exc_info:
            client.get("/test")
        
        assert exc_info.value.status_code == 500
        assert mock_get.call_count == 4  # Initial + 3 retries
    
    @patch('sodir_module.api_client.requests.get')
    def test_exponential_backoff(self, mock_get, client):
        """Test exponential backoff between retries."""
        # Always return server error
        error_response = Mock()
        error_response.status_code = 503
        error_response.text = "Service Unavailable"
        mock_get.return_value = error_response
        
        client.retry_delay = 0.1  # Base delay
        start_time = time.time()
        
        with pytest.raises(SodirAPIError):
            client.get("/test")
        
        elapsed = time.time() - start_time
        
        # Expected delays: 0.1, 0.2, 0.4 = 0.7 seconds minimum
        assert elapsed >= 0.6  # Allow some tolerance
    
    @patch('sodir_module.api_client.requests.get')
    def test_no_retry_on_client_error(self, mock_get, client):
        """Test that client errors (4xx) don't trigger retries."""
        error_response = Mock()
        error_response.status_code = 400
        error_response.text = "Bad Request"
        mock_get.return_value = error_response
        
        with pytest.raises(SodirAPIError) as exc_info:
            client.get("/test")
        
        assert exc_info.value.status_code == 400
        assert mock_get.call_count == 1  # No retries


class TestSODIREndpoints:
    """Test SODIR-specific endpoint methods."""
    
    @pytest.fixture
    def client(self):
        """Create API client for testing."""
        return SodirAPIClient(
            base_url="https://factmaps.sodir.no/api/rest",
            rate_limit=10
        )
    
    @patch('sodir_module.api_client.requests.get')
    def test_get_blocks(self, mock_get, client):
        """Test blocks endpoint method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"npdidBlock": "1", "blockName": "30/11"}]
        }
        mock_get.return_value = mock_response
        
        result = client.get_blocks(startdate="2020-01-01")
        
        assert result == [{"npdidBlock": "1", "blockName": "30/11"}]
        mock_get.assert_called_with(
            "https://factmaps.sodir.no/api/rest/1001",
            params={"startdate": "2020-01-01", "format": "json"},
            headers=client.headers,
            timeout=client.timeout
        )
    
    @patch('sodir_module.api_client.requests.get')
    def test_get_wellbores(self, mock_get, client):
        """Test wellbores endpoint method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"npdidWellbore": "123", "wellboreName": "Test Well"}]
        }
        mock_get.return_value = mock_response
        
        result = client.get_wellbores(wellboreStatus="COMPLETED")
        
        assert result == [{"npdidWellbore": "123", "wellboreName": "Test Well"}]
        mock_get.assert_called_with(
            "https://factmaps.sodir.no/api/rest/5000",
            params={"wellboreStatus": "COMPLETED", "format": "json"},
            headers=client.headers,
            timeout=client.timeout
        )
    
    @patch('sodir_module.api_client.requests.get')
    def test_get_fields(self, mock_get, client):
        """Test fields endpoint method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"npdidField": "456", "fieldName": "Johan Sverdrup"}]
        }
        mock_get.return_value = mock_response
        
        result = client.get_fields(fieldStatus="PRODUCING")
        
        assert result == [{"npdidField": "456", "fieldName": "Johan Sverdrup"}]
        mock_get.assert_called_with(
            "https://factmaps.sodir.no/api/rest/7100",
            params={"fieldStatus": "PRODUCING", "format": "json"},
            headers=client.headers,
            timeout=client.timeout
        )
    
    @patch('sodir_module.api_client.requests.get')
    def test_get_discoveries(self, mock_get, client):
        """Test discoveries endpoint method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"npdidDiscovery": "789", "discoveryName": "Test Discovery"}]
        }
        mock_get.return_value = mock_response
        
        result = client.get_discoveries(discoveryYear=2020)
        
        assert result == [{"npdidDiscovery": "789", "discoveryName": "Test Discovery"}]
        mock_get.assert_called_with(
            "https://factmaps.sodir.no/api/rest/7000",
            params={"discoveryYear": 2020, "format": "json"},
            headers=client.headers,
            timeout=client.timeout
        )
    
    @patch('sodir_module.api_client.requests.get')
    def test_get_surveys(self, mock_get, client):
        """Test surveys endpoint method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"npdidSurvey": "999", "surveyName": "Test Survey"}]
        }
        mock_get.return_value = mock_response
        
        result = client.get_surveys(surveyType="3D_SEISMIC")
        
        assert result == [{"npdidSurvey": "999", "surveyName": "Test Survey"}]
        mock_get.assert_called_with(
            "https://factmaps.sodir.no/api/rest/4000",
            params={"surveyType": "3D_SEISMIC", "format": "json"},
            headers=client.headers,
            timeout=client.timeout
        )


class TestRequestHeaders:
    """Test HTTP request headers configuration."""
    
    def test_default_headers(self):
        """Test default headers are set correctly."""
        client = SodirAPIClient("https://test.api", rate_limit=10)
        
        assert "User-Agent" in client.headers
        assert "WorldEnergyData" in client.headers["User-Agent"]
        assert client.headers["Accept"] == "application/json"
        assert client.headers["Accept-Encoding"] == "gzip, deflate"
    
    def test_custom_headers(self):
        """Test custom headers can be added."""
        client = SodirAPIClient(
            base_url="https://test.api",
            rate_limit=10,
            headers={"X-Custom-Header": "test-value"}
        )
        
        assert client.headers["X-Custom-Header"] == "test-value"
        assert "User-Agent" in client.headers  # Default still present
    
    @patch('sodir_module.api_client.requests.get')
    def test_headers_sent_with_request(self, mock_get):
        """Test headers are included in requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        client = SodirAPIClient("https://test.api", rate_limit=10)
        client.get("/test")
        
        # Verify headers were passed to requests.get
        call_args = mock_get.call_args
        assert call_args[1]["headers"] == client.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])