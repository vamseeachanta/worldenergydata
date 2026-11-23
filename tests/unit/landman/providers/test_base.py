"""Tests for landman base provider utilities (CacheEntry, MemoryCache)."""

import time
from datetime import timedelta

from worldenergydata.landman.providers.base import CacheEntry, MemoryCache


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(data="hello", ttl_seconds=3600)
        assert entry.is_expired() is False
        assert entry.data == "hello"

    def test_expired(self):
        entry = CacheEntry(data="old", ttl_seconds=0)
        # Force expiration by manipulating expires_at
        entry.expires_at = entry.created_at - timedelta(seconds=1)
        assert entry.is_expired() is True

    def test_created_at_set(self):
        entry = CacheEntry(data=42)
        assert entry.created_at is not None


class TestMemoryCache:
    def test_set_and_get(self):
        cache = MemoryCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_get_expired(self):
        cache = MemoryCache(default_ttl=0)
        cache.set("key1", "value1")
        # Manually expire
        for entry in cache._cache.values():
            entry.expires_at = entry.created_at - timedelta(seconds=1)
        assert cache.get("key1") is None

    def test_clear(self):
        cache = MemoryCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_max_entries_eviction(self):
        cache = MemoryCache(max_entries=2)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        # One of the earlier entries should be evicted
        assert cache.get("k3") == "v3"
        assert len(cache._cache) <= 2

    def test_stats(self):
        cache = MemoryCache()
        cache.set("k1", "v1")
        cache.get("k1")  # hit
        cache.get("missing")  # miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["entries"] == 1
        assert "hit_rate" in stats

    def test_stats_zero_requests(self):
        cache = MemoryCache()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"

    def test_key_hashing(self):
        cache = MemoryCache()
        cache.set("same-key", "first")
        cache.set("same-key", "second")
        assert cache.get("same-key") == "second"

    def test_different_keys_independent(self):
        cache = MemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
