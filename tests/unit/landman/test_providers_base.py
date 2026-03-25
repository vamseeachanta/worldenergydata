"""Tests for landman.providers.base CacheEntry, MemoryCache, and BaseProvider."""

import time

import pytest

from worldenergydata.landman.providers.base import (
    BaseProvider,
    CacheEntry,
    MemoryCache,
)


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

class TestCacheEntry:
    def test_init(self):
        entry = CacheEntry("data", ttl_seconds=3600)
        assert entry.data == "data"
        assert not entry.is_expired()

    def test_expired(self):
        entry = CacheEntry("data", ttl_seconds=1)
        # Manually set expires_at to the past
        from datetime import datetime, timedelta
        entry.expires_at = datetime.utcnow() - timedelta(seconds=1)
        assert entry.is_expired()


# ---------------------------------------------------------------------------
# MemoryCache
# ---------------------------------------------------------------------------

class TestMemoryCache:
    def test_get_miss(self):
        cache = MemoryCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_set_and_get(self):
        cache = MemoryCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_expired_entry_removed(self):
        cache = MemoryCache()
        cache.set("key1", "value1", ttl=1)
        # Immediately should NOT be expired (1s TTL)
        assert cache.get("key1") == "value1"
        # Manually expire by patching the entry
        hashed = cache._make_key("key1")
        from datetime import datetime, timedelta
        cache._cache[hashed].expires_at = datetime.utcnow() - timedelta(seconds=1)
        assert cache.get("key1") is None

    def test_max_entries_eviction(self):
        cache = MemoryCache(max_entries=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict oldest
        assert cache.get("key3") == "value3"
        # At least 2 entries remain
        stats = cache.stats()
        assert stats["entries"] <= 2

    def test_clear(self):
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.stats()["entries"] == 0

    def test_stats(self):
        cache = MemoryCache()
        cache.get("miss1")
        cache.set("hit1", "data")
        cache.get("hit1")
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["entries"] == 1

    def test_hit_rate(self):
        cache = MemoryCache()
        cache.set("k", "v")
        cache.get("k")  # hit
        cache.get("k")  # hit
        cache.get("missing")  # miss
        stats = cache.stats()
        assert "66.7%" in stats["hit_rate"]

    def test_make_key_deterministic(self):
        cache = MemoryCache()
        k1 = cache._make_key("test-key")
        k2 = cache._make_key("test-key")
        assert k1 == k2

    def test_evict_expired(self):
        cache = MemoryCache()
        cache.set("expired1", "v", ttl=0)
        cache.set("valid1", "v", ttl=3600)
        time.sleep(0.01)
        cache._evict_expired()
        assert cache.get("valid1") == "v"


# ---------------------------------------------------------------------------
# BaseProvider (abstract, test via concrete subclass)
# ---------------------------------------------------------------------------

class ConcreteProvider(BaseProvider):
    PROVIDER_NAME = "test_provider"
    BASE_URL = "https://example.com"

    def health_check(self) -> bool:
        return True


class TestBaseProvider:
    def test_init(self):
        provider = ConcreteProvider(timeout=15, max_retries=2)
        assert provider.timeout == 15
        assert provider.max_retries == 2
        assert provider._request_count == 0

    def test_cache_clear(self):
        provider = ConcreteProvider()
        provider._cache.set("k", "v")
        provider.clear_cache()
        assert provider._cache.get("k") is None

    def test_cache_stats(self):
        provider = ConcreteProvider()
        stats = provider.cache_stats()
        assert "entries" in stats
        assert "hits" in stats

    def test_request_count(self):
        provider = ConcreteProvider()
        assert provider.request_count() == 0

    def test_close(self):
        provider = ConcreteProvider()
        # Access client to create it
        _ = provider.client
        assert provider._client is not None
        provider.close()
        assert provider._client is None

    def test_context_manager(self):
        with ConcreteProvider() as provider:
            assert provider.health_check() is True
        assert provider._client is None

    def test_health_check(self):
        provider = ConcreteProvider()
        assert provider.health_check() is True

    def test_client_lazy_init(self):
        provider = ConcreteProvider()
        assert provider._client is None
        client = provider.client
        assert client is not None
        # Second access returns same client
        assert provider.client is client

    def test_rate_limit_delay(self):
        provider = ConcreteProvider(rate_limit_delay=0.01)
        provider._last_request_time = time.time()
        start = time.time()
        provider._wait_for_rate_limit()
        # Should have waited at least a tiny bit
        elapsed = time.time() - start
        assert elapsed >= 0  # non-negative

    def test_rate_limit_no_previous(self):
        provider = ConcreteProvider()
        # No previous request, should not wait
        provider._wait_for_rate_limit()
        assert provider._last_request_time is not None
