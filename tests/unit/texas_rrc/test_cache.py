"""Tests for Texas RRC caching implementation."""

import time

from worldenergydata.texas_rrc.cache import CacheEntry, TexasRRCCache


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time(), ttl=60)
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time() - 120, ttl=60)
        assert entry.is_expired() is True


class TestTexasRRCCache:
    def test_init_defaults(self):
        cache = TexasRRCCache()
        assert cache.default_ttl == 86400

    def test_custom_ttl(self):
        cache = TexasRRCCache(default_ttl=3600)
        assert cache.default_ttl == 3600

    def test_set_and_get(self):
        cache = TexasRRCCache()
        cache.set("key1", {"data": [1, 2, 3]})
        assert cache.get("key1") == {"data": [1, 2, 3]}

    def test_get_missing(self):
        cache = TexasRRCCache()
        assert cache.get("missing") is None

    def test_get_expired(self):
        cache = TexasRRCCache()
        cache.set("key1", "value", ttl=1)
        cache.cache["key1"].timestamp -= 10
        assert cache.get("key1") is None

    def test_get_expired_removes(self):
        cache = TexasRRCCache()
        cache.set("key1", "value", ttl=1)
        cache.cache["key1"].timestamp -= 10
        cache.get("key1")
        assert "key1" not in cache.cache

    def test_set_overwrites(self):
        cache = TexasRRCCache()
        cache.set("k", "v1")
        cache.set("k", "v2")
        assert cache.get("k") == "v2"

    def test_set_custom_ttl(self):
        cache = TexasRRCCache(default_ttl=86400)
        cache.set("k", "v", ttl=100)
        assert cache.cache["k"].ttl == 100

    def test_delete_existing(self):
        cache = TexasRRCCache()
        cache.set("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_delete_missing(self):
        cache = TexasRRCCache()
        assert cache.delete("missing") is False

    def test_clear(self):
        cache = TexasRRCCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.get("k1")  # hit
        cache.clear()
        assert len(cache) == 0
        # clear() resets hits and misses counters
        assert cache._hits == 0
        assert cache._misses == 0

    def test_cleanup_expired(self):
        cache = TexasRRCCache()
        cache.set("fresh", "value", ttl=3600)
        cache.set("old", "value", ttl=1)
        cache.cache["old"].timestamp -= 10
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("fresh") == "value"

    def test_cleanup_expired_none(self):
        cache = TexasRRCCache()
        cache.set("fresh", "value", ttl=3600)
        removed = cache.cleanup_expired()
        assert removed == 0

    def test_stats_initial(self):
        cache = TexasRRCCache()
        stats = cache.stats
        assert stats["entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"

    def test_stats_after_operations(self):
        cache = TexasRRCCache()
        cache.set("k", "v")
        cache.get("k")  # hit
        cache.get("missing")  # miss
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "50.0%"

    def test_len(self):
        cache = TexasRRCCache()
        assert len(cache) == 0
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        assert len(cache) == 2

    def test_contains(self):
        cache = TexasRRCCache()
        cache.set("k", "v")
        assert ("k" in cache) is True
        assert ("missing" in cache) is False

    def test_contains_expired(self):
        cache = TexasRRCCache()
        cache.set("k", "v", ttl=1)
        cache.cache["k"].timestamp -= 10
        assert ("k" in cache) is False
