"""Tests for SODIR cache implementation."""

import time

from worldenergydata.sodir.cache import CacheEntry, SodirCache


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_not_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time(), ttl=3600)
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time() - 100, ttl=50)
        assert entry.is_expired() is True

    def test_just_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time() - 2, ttl=1)
        assert entry.is_expired() is True


class TestSodirCache:
    """Tests for SodirCache."""

    def setup_method(self):
        self.cache = SodirCache(default_ttl=3600)

    def test_set_and_get(self):
        self.cache.set("key1", {"data": "value"})
        result = self.cache.get("key1")
        assert result == {"data": "value"}

    def test_get_missing_key(self):
        result = self.cache.get("nonexistent")
        assert result is None

    def test_get_expired_key(self):
        # Manually create an expired entry (ttl=0 is falsy so cache uses default)
        from worldenergydata.sodir.cache import CacheEntry
        self.cache.cache["key1"] = CacheEntry(
            data="value", timestamp=time.time() - 100, ttl=50
        )
        result = self.cache.get("key1")
        assert result is None

    def test_set_with_custom_ttl(self):
        self.cache.set("key1", "value", ttl=7200)
        assert "key1" in self.cache.cache
        assert self.cache.cache["key1"].ttl == 7200

    def test_set_overwrites_existing(self):
        self.cache.set("key1", "old")
        self.cache.set("key1", "new")
        assert self.cache.get("key1") == "new"

    def test_clear(self):
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is None

    def test_default_ttl(self):
        cache = SodirCache(default_ttl=1800)
        assert cache.default_ttl == 1800

    def test_cache_stores_various_types(self):
        self.cache.set("str", "hello")
        self.cache.set("list", [1, 2, 3])
        self.cache.set("dict", {"a": 1})
        assert self.cache.get("str") == "hello"
        assert self.cache.get("list") == [1, 2, 3]
        assert self.cache.get("dict") == {"a": 1}

    def test_expired_entry_removed_on_get(self):
        from worldenergydata.sodir.cache import CacheEntry
        self.cache.cache["key1"] = CacheEntry(
            data="value", timestamp=time.time() - 100, ttl=50
        )
        self.cache.get("key1")
        assert "key1" not in self.cache.cache
