"""Tests for the base collector."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.vessel_fleet.collectors.base import BaseCollector


class ConcreteCollector(BaseCollector):
    """Concrete implementation for testing the ABC."""

    def collect(self):
        return self.get("https://example.com/fleet")


class TestBaseCollectorInit:
    """Constructor and default configuration."""

    def test_default_rate_limit(self):
        c = ConcreteCollector(name="test")
        assert c.rate_limit == 1.0

    def test_custom_rate_limit(self):
        c = ConcreteCollector(name="test", rate_limit=0.5)
        assert c.rate_limit == 0.5

    def test_default_max_retries(self):
        c = ConcreteCollector(name="test")
        assert c.max_retries == 3

    def test_default_timeout(self):
        c = ConcreteCollector(name="test")
        assert c.timeout == 30

    def test_name_stored(self):
        c = ConcreteCollector(name="transocean")
        assert c.name == "transocean"

    def test_user_agent_set(self):
        c = ConcreteCollector(name="test")
        assert "worldenergydata" in c.session.headers["User-Agent"]


class TestRateLimiting:
    """Rate limiting between requests."""

    def test_rate_limit_enforced(self):
        c = ConcreteCollector(name="test", rate_limit=10.0)
        c._last_request_time = time.monotonic()
        start = time.monotonic()
        c._apply_rate_limit()
        elapsed = time.monotonic() - start
        # With rate_limit=10, min_interval is 0.1s
        # Should have waited at least ~0.05s (allowing some tolerance)
        assert elapsed >= 0.05

    def test_no_wait_when_enough_time_passed(self):
        c = ConcreteCollector(name="test", rate_limit=10.0)
        c._last_request_time = time.monotonic() - 1.0  # 1 second ago
        start = time.monotonic()
        c._apply_rate_limit()
        elapsed = time.monotonic() - start
        assert elapsed < 0.05


class TestCaching:
    """Response caching behaviour."""

    def test_cache_stores_and_retrieves(self):
        c = ConcreteCollector(name="test")
        c._set_cache("key1", "value1")
        assert c._get_cache("key1") == "value1"

    def test_cache_miss_returns_none(self):
        c = ConcreteCollector(name="test")
        assert c._get_cache("nonexistent") is None

    def test_cache_ttl_expiry(self):
        c = ConcreteCollector(name="test", cache_ttl=0.0)
        c._set_cache("key1", "value1")
        # TTL is 0, should be expired immediately
        time.sleep(0.01)
        assert c._get_cache("key1") is None

    def test_cache_disabled(self):
        c = ConcreteCollector(name="test", cache_enabled=False)
        c._set_cache("key1", "value1")
        assert c._get_cache("key1") is None


class TestRetry:
    """Retry logic with exponential backoff."""

    @patch("worldenergydata.vessel_fleet.collectors.base.requests")
    def test_retries_on_failure(self, mock_requests):
        mock_session = MagicMock()
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = Exception("Server error")
        mock_response_ok = MagicMock()
        mock_response_ok.raise_for_status.return_value = None
        mock_response_ok.text = "success"
        mock_response_ok.status_code = 200
        mock_session.get.side_effect = [mock_response_fail, mock_response_ok]
        mock_requests.Session.return_value = mock_session

        c = ConcreteCollector(name="test", max_retries=2, retry_base_delay=0.01)
        result = c.get("https://example.com")
        assert result.text == "success"
        assert mock_session.get.call_count == 2

    @patch("worldenergydata.vessel_fleet.collectors.base.requests")
    def test_raises_after_max_retries(self, mock_requests):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_session.get.return_value = mock_response
        mock_requests.Session.return_value = mock_session

        c = ConcreteCollector(name="test", max_retries=2, retry_base_delay=0.01)
        with pytest.raises(Exception, match="Server error"):
            c.get("https://example.com")
        assert mock_session.get.call_count == 2
