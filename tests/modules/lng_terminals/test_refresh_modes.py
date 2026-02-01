"""Tests for BaseCollector refresh modes and JSON cache layer.

Validates that the four RefreshMode options (FULL, INCREMENTAL,
CACHE_FIRST, FORCE_CACHE) behave correctly with respect to
fetching fresh data vs. returning cached results, and that the
cache round-trip (write -> read) preserves terminal data.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import pytest

from worldenergydata.modules.lng_terminals.collectors.base_collector import (
    BaseCollector,
)
from worldenergydata.modules.lng_terminals.config import CacheConfig, LNGTerminalsConfig
from worldenergydata.modules.lng_terminals.constants import (
    RefreshMode,
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.modules.lng_terminals.exceptions import LNGCollectionError
from worldenergydata.modules.lng_terminals.models.terminal import LNGTerminal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_terminal(
    name: str = "Test Terminal",
    country: str = "USA",
    terminal_type: TerminalType = TerminalType.ONSHORE_IMPORT,
    function: TerminalFunction = TerminalFunction.IMPORT,
    status: TerminalStatus = TerminalStatus.OPERATIONAL,
    capacity_mtpa: float | None = 5.0,
    operator: str | None = "TestCorp",
    last_updated: datetime | None = None,
) -> LNGTerminal:
    """Build a minimal LNGTerminal with sane defaults."""
    return LNGTerminal(
        terminal_name=name,
        country=country,
        terminal_type=terminal_type,
        function=function,
        status=status,
        capacity_mtpa=capacity_mtpa,
        operator=operator,
        last_updated=last_updated or datetime.utcnow(),
    )


class StubCollector(BaseCollector):
    """Concrete BaseCollector subclass for testing.

    Accepts pre-built LNGTerminal objects; ``fetch_data`` returns them
    directly and ``parse_records`` passes them through unchanged.
    ``fetch_count`` tracks how many times ``fetch_data`` was invoked so
    tests can verify whether the cache path was taken.
    """

    source_name = "test_stub"
    source_reliability = SourceReliability.MEDIUM

    def __init__(
        self,
        terminals: list[LNGTerminal] | None = None,
        refresh_mode: RefreshMode | None = None,
    ) -> None:
        super().__init__(source_name="test_stub", refresh_mode=refresh_mode)
        self._terminals = terminals or []
        self.fetch_count: int = 0

    def fetch_data(self) -> Any:
        self.fetch_count += 1
        return self._terminals

    def parse_records(self, raw_data: Any) -> list[LNGTerminal]:
        return raw_data  # Already LNGTerminal objects


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_config(tmp_path):
    """Reset the singleton config before every test.

    Points the cache directory at the pytest ``tmp_path`` so that each
    test gets an isolated, empty cache on the real filesystem.
    """
    import worldenergydata.modules.lng_terminals.config as config_module

    config_module._config = LNGTerminalsConfig(
        cache=CacheConfig(
            enabled=True,
            cache_dir=str(tmp_path),
            default_refresh_mode="cache_first",
            max_age_seconds=86400,
        ),
    )
    yield
    config_module._config = None


@pytest.fixture()
def sample_terminals() -> list[LNGTerminal]:
    """A small list of real LNGTerminal objects for cache tests."""
    return [
        _make_terminal(name="Alpha LNG", country="USA", capacity_mtpa=10.0),
        _make_terminal(
            name="Beta FSRU",
            country="GBR",
            terminal_type=TerminalType.FSRU,
            function=TerminalFunction.IMPORT,
            capacity_mtpa=3.5,
            operator="BetaEnergy",
        ),
    ]


# ---------------------------------------------------------------------------
# 1. Concrete collector sanity
# ---------------------------------------------------------------------------


class TestConcreteCollector:
    """Verify the StubCollector test helper works end-to-end."""

    def test_concrete_collector_can_collect(self, sample_terminals):
        """Basic collect() cycle returns the same terminals fed in."""
        collector = StubCollector(terminals=sample_terminals)
        result = collector.collect(refresh_mode=RefreshMode.FULL)

        assert len(result) == len(sample_terminals)
        assert all(isinstance(t, LNGTerminal) for t in result)
        assert collector.fetch_count == 1


# ---------------------------------------------------------------------------
# 2. FULL mode
# ---------------------------------------------------------------------------


class TestRefreshModeFull:
    """FULL mode always re-fetches, ignoring any existing cache."""

    def test_full_mode_fetches_fresh_data(self, sample_terminals, tmp_path):
        """Even with a warm cache, FULL mode calls fetch_data."""
        # Warm the cache with a first collection
        first = StubCollector(terminals=sample_terminals, refresh_mode=RefreshMode.FULL)
        first.collect()
        first.close()

        # Collect again in FULL mode
        second = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        result = second.collect()
        second.close()

        assert second.fetch_count == 1
        assert len(result) == len(sample_terminals)

    def test_full_mode_writes_cache(self, sample_terminals, tmp_path):
        """After FULL collection the cache and meta files exist on disk."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()
        collector.close()

        assert collector._cache_path.exists()
        assert collector._cache_meta_path.exists()

        cached_data = json.loads(collector._cache_path.read_text(encoding="utf-8"))
        assert len(cached_data) == len(sample_terminals)


# ---------------------------------------------------------------------------
# 3. CACHE_FIRST mode
# ---------------------------------------------------------------------------


class TestRefreshModeCacheFirst:
    """CACHE_FIRST returns cached data when valid, otherwise fetches."""

    def test_cache_first_fetches_when_no_cache(self, sample_terminals):
        """Without any cache, CACHE_FIRST falls through to fetch_data."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.CACHE_FIRST
        )
        result = collector.collect()
        collector.close()

        assert collector.fetch_count == 1
        assert len(result) == len(sample_terminals)

    def test_cache_first_returns_cached_data(self, sample_terminals):
        """With a warm cache, CACHE_FIRST returns cached data without fetching."""
        # Populate cache via FULL
        writer = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        writer.collect()
        writer.close()

        # Now CACHE_FIRST should hit cache
        reader = StubCollector(terminals=[], refresh_mode=RefreshMode.CACHE_FIRST)
        result = reader.collect()
        reader.close()

        assert reader.fetch_count == 0
        assert len(result) == len(sample_terminals)

    def test_cache_first_fetches_when_cache_expired(self, sample_terminals, tmp_path):
        """Expired cache causes CACHE_FIRST to fall through to fetch_data."""
        # Write cache manually with an old timestamp
        writer = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        writer.collect()
        writer.close()

        # Backdate the meta to 2 days ago (max_age is 86400s = 1 day)
        old_time = datetime.utcnow() - timedelta(days=2)
        meta = {
            "source_name": "test_stub",
            "collected_at": old_time.isoformat(),
            "record_count": len(sample_terminals),
        }
        writer._cache_meta_path.write_text(json.dumps(meta), encoding="utf-8")

        reader = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.CACHE_FIRST
        )
        result = reader.collect()
        reader.close()

        assert reader.fetch_count == 1
        assert len(result) == len(sample_terminals)


# ---------------------------------------------------------------------------
# 4. FORCE_CACHE mode
# ---------------------------------------------------------------------------


class TestRefreshModeForceCache:
    """FORCE_CACHE never fetches; it either returns cache or raises."""

    def test_force_cache_returns_cached_data(self, sample_terminals):
        """With a warm cache, FORCE_CACHE returns the cached terminals."""
        writer = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        writer.collect()
        writer.close()

        reader = StubCollector(terminals=[], refresh_mode=RefreshMode.FORCE_CACHE)
        result = reader.collect()
        reader.close()

        assert reader.fetch_count == 0
        assert len(result) == len(sample_terminals)

    def test_force_cache_raises_when_no_cache(self):
        """Without any cache, FORCE_CACHE raises LNGCollectionError."""
        collector = StubCollector(terminals=[], refresh_mode=RefreshMode.FORCE_CACHE)
        with pytest.raises(LNGCollectionError) as exc_info:
            collector.collect()
        collector.close()

        assert "FORCE_CACHE" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5. INCREMENTAL mode
# ---------------------------------------------------------------------------


class TestRefreshModeIncremental:
    """INCREMENTAL currently behaves identically to FULL."""

    def test_incremental_fetches_fresh(self, sample_terminals):
        """INCREMENTAL calls fetch_data even when a cache exists."""
        # Warm the cache
        writer = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        writer.collect()
        writer.close()

        reader = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.INCREMENTAL
        )
        result = reader.collect()
        reader.close()

        assert reader.fetch_count == 1
        assert len(result) == len(sample_terminals)


# ---------------------------------------------------------------------------
# 6. Cache round-trip
# ---------------------------------------------------------------------------


class TestCacheRoundTrip:
    """Verify data survives serialization to JSON and back."""

    def test_cache_write_read_roundtrip(self, sample_terminals):
        """Terminals written to cache can be loaded back as LNGTerminal objects."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()

        loaded = collector._load_from_cache()
        collector.close()

        assert len(loaded) == len(sample_terminals)
        assert all(isinstance(t, LNGTerminal) for t in loaded)

    def test_cache_preserves_terminal_fields(self):
        """Specific field values survive the JSON round-trip."""
        now = datetime(2025, 6, 15, 12, 0, 0)
        terminal = _make_terminal(
            name="Precise Terminal",
            country="NOR",
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.UNDER_CONSTRUCTION,
            capacity_mtpa=22.5,
            operator="PreciseCorp",
            last_updated=now,
        )
        collector = StubCollector(terminals=[terminal], refresh_mode=RefreshMode.FULL)
        collector.collect()

        loaded = collector._load_from_cache()
        collector.close()

        assert len(loaded) == 1
        t = loaded[0]
        assert t.terminal_name == "Precise Terminal"
        assert t.country == "NOR"
        assert t.terminal_type == TerminalType.ONSHORE_EXPORT
        assert t.function == TerminalFunction.EXPORT
        assert t.status == TerminalStatus.UNDER_CONSTRUCTION
        assert t.capacity_mtpa == 22.5
        assert t.operator == "PreciseCorp"

    def test_cache_disabled_skips_write(self, sample_terminals, tmp_path):
        """When config.cache.enabled is False, no cache files are created."""
        import worldenergydata.modules.lng_terminals.config as config_module

        config_module._config = LNGTerminalsConfig(
            cache=CacheConfig(
                enabled=False,
                cache_dir=str(tmp_path),
                max_age_seconds=86400,
            ),
        )

        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()
        collector.close()

        assert not collector._cache_path.exists()
        assert not collector._cache_meta_path.exists()


# ---------------------------------------------------------------------------
# 7. Cache expiration
# ---------------------------------------------------------------------------


class TestCacheExpiration:
    """Verify TTL-based cache invalidation."""

    def test_cache_expired_returns_none(self, sample_terminals):
        """_read_cache returns None when the cache exceeds max_age_seconds."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()

        # Backdate meta beyond the 86400s TTL
        old_time = datetime.utcnow() - timedelta(seconds=86401)
        meta = {
            "source_name": "test_stub",
            "collected_at": old_time.isoformat(),
            "record_count": len(sample_terminals),
        }
        collector._cache_meta_path.write_text(json.dumps(meta), encoding="utf-8")

        result = collector._read_cache()
        collector.close()

        assert result is None

    def test_cache_within_ttl_returns_data(self, sample_terminals):
        """_read_cache returns data when cache age is within max_age_seconds."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()

        # Meta timestamp is fresh (just written), so should be valid
        result = collector._read_cache()
        collector.close()

        assert result is not None
        assert len(result) == len(sample_terminals)


# ---------------------------------------------------------------------------
# 8. Cache metadata
# ---------------------------------------------------------------------------


class TestCacheMetadata:
    """Verify the last_collected_at property and meta file behaviour."""

    def test_last_collected_at_returns_datetime(self, sample_terminals):
        """After a successful write, last_collected_at returns a datetime."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        before = datetime.utcnow()
        collector.collect()
        after = datetime.utcnow()

        ts = collector.last_collected_at
        collector.close()

        assert isinstance(ts, datetime)
        assert before <= ts <= after

    def test_last_collected_at_none_when_no_cache(self):
        """Without a meta file, last_collected_at returns None."""
        collector = StubCollector(terminals=[], refresh_mode=RefreshMode.FULL)
        assert collector.last_collected_at is None
        collector.close()


# ---------------------------------------------------------------------------
# 9. Cache corruption
# ---------------------------------------------------------------------------


class TestCacheCorruption:
    """Verify graceful handling of corrupt or incomplete cache files."""

    def test_corrupt_cache_returns_none(self, sample_terminals, tmp_path):
        """Invalid JSON in the cache file causes _read_cache to return None."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()

        # Corrupt the cache data file
        collector._cache_path.write_text("NOT VALID JSON {{{", encoding="utf-8")

        result = collector._read_cache()
        collector.close()

        assert result is None

    def test_corrupt_meta_returns_none(self, sample_terminals, tmp_path):
        """Invalid JSON in the meta file causes _read_cache to return None."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()

        # Corrupt the meta file
        collector._cache_meta_path.write_text("BROKEN META", encoding="utf-8")

        result = collector._read_cache()
        collector.close()

        assert result is None

    def test_missing_meta_file_returns_none(self, sample_terminals, tmp_path):
        """Cache data file present but meta file missing -> _read_cache returns None."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FULL
        )
        collector.collect()

        # Remove only the meta file
        collector._cache_meta_path.unlink()

        result = collector._read_cache()
        collector.close()

        assert result is None


# ---------------------------------------------------------------------------
# 10. Default refresh mode
# ---------------------------------------------------------------------------


class TestDefaultRefreshMode:
    """Verify refresh mode resolution from config vs. explicit parameter."""

    def test_default_from_config(self):
        """Without explicit mode, the collector uses config.cache.default_refresh_mode."""
        collector = StubCollector(terminals=[], refresh_mode=None)
        assert collector.refresh_mode == RefreshMode.CACHE_FIRST
        collector.close()

    def test_explicit_mode_overrides_config(self):
        """An explicit refresh_mode takes precedence over the config default."""
        collector = StubCollector(terminals=[], refresh_mode=RefreshMode.FORCE_CACHE)
        assert collector.refresh_mode == RefreshMode.FORCE_CACHE
        collector.close()

    def test_config_default_full(self, tmp_path):
        """Changing config default to 'full' is respected by the collector."""
        import worldenergydata.modules.lng_terminals.config as config_module

        config_module._config = LNGTerminalsConfig(
            cache=CacheConfig(
                enabled=True,
                cache_dir=str(tmp_path),
                default_refresh_mode="full",
                max_age_seconds=86400,
            ),
        )

        collector = StubCollector(terminals=[], refresh_mode=None)
        assert collector.refresh_mode == RefreshMode.FULL
        collector.close()

    def test_collect_override_mode(self, sample_terminals):
        """Passing refresh_mode to collect() overrides the instance mode."""
        collector = StubCollector(
            terminals=sample_terminals, refresh_mode=RefreshMode.FORCE_CACHE
        )
        # Instance mode is FORCE_CACHE, but collect with FULL should fetch
        result = collector.collect(refresh_mode=RefreshMode.FULL)
        collector.close()

        assert collector.fetch_count == 1
        assert len(result) == len(sample_terminals)
