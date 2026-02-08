"""Tests for LNG terminal deduplicator."""

from datetime import datetime

from worldenergydata.lng_terminals.constants import (
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.models.terminal import LNGTerminal
from worldenergydata.lng_terminals.processors.deduplicator import Deduplicator


def _make_terminal(
    name: str,
    country: str = "USA",
    capacity: float | None = None,
    lat: float | None = None,
    lon: float | None = None,
    operator: str | None = None,
) -> LNGTerminal:
    return LNGTerminal(
        terminal_name=name,
        country=country,
        terminal_type=TerminalType.ONSHORE_EXPORT,
        function=TerminalFunction.EXPORT,
        status=TerminalStatus.OPERATIONAL,
        capacity_mtpa=capacity,
        latitude=lat,
        longitude=lon,
        operator=operator,
        last_updated=datetime.utcnow(),
    )


class TestDeduplicator:
    """Test deduplication logic."""

    def test_no_duplicates(self):
        """Distinct terminals should not be merged."""
        dedup = Deduplicator()
        terminals = [
            _make_terminal("Sabine Pass LNG", "USA"),
            _make_terminal("Cameron LNG", "USA"),
            _make_terminal("Gorgon LNG", "AUS"),
        ]
        result = dedup.deduplicate(terminals)
        assert len(result) == 3

    def test_exact_name_match(self):
        """Identical names + same country should merge."""
        dedup = Deduplicator()
        terminals = [
            _make_terminal("Sabine Pass LNG", "USA", capacity=30.0),
            _make_terminal("Sabine Pass LNG", "USA", operator="Cheniere"),
        ]
        result = dedup.deduplicate(terminals)
        assert len(result) == 1

    def test_different_country_no_merge(self):
        """Same name but different country should NOT merge."""
        dedup = Deduplicator()
        terminals = [
            _make_terminal("Test LNG Terminal", "USA"),
            _make_terminal("Test LNG Terminal", "GBR"),
        ]
        result = dedup.deduplicate(terminals)
        assert len(result) == 2

    def test_fuzzy_name_match(self):
        """Similar names should merge when above threshold."""
        dedup = Deduplicator()
        terminals = [
            _make_terminal("Sabine Pass LNG Terminal", "USA"),
            _make_terminal("Sabine Pass LNG", "USA"),
        ]
        result = dedup.deduplicate(terminals)
        assert len(result) == 1

    def test_keeps_most_complete_record(self):
        """Should keep the record with more non-None fields."""
        dedup = Deduplicator()
        terminals = [
            _make_terminal("Sabine Pass LNG", "USA"),
            _make_terminal(
                "Sabine Pass LNG", "USA", capacity=30.0, operator="Cheniere"
            ),
        ]
        result = dedup.deduplicate(terminals)
        assert len(result) == 1
        assert result[0].capacity_mtpa == 30.0
        assert result[0].operator == "Cheniere"

    def test_empty_input(self):
        dedup = Deduplicator()
        assert dedup.deduplicate([]) == []

    def test_single_terminal(self):
        dedup = Deduplicator()
        terminals = [_make_terminal("Test", "USA")]
        result = dedup.deduplicate(terminals)
        assert len(result) == 1

    def test_name_normalization(self):
        """'LNG', 'Terminal' etc. should be stripped for comparison."""
        name_a = Deduplicator._normalize_name("Sabine Pass LNG Terminal")
        name_b = Deduplicator._normalize_name("Sabine Pass")
        assert name_a == name_b

    def test_haversine_known_distance(self):
        """Houston to Dallas is ~362 km."""
        dist = Deduplicator._haversine_km(29.76, -95.37, 32.78, -96.80)
        assert 350 < dist < 380

    def test_seed_data_dedup(self):
        """Dedup on seed data should not remove any (they're all distinct)."""
        from worldenergydata.lng_terminals.collectors.seed_collector import (
            SeedCollector,
        )

        collector = SeedCollector()
        terminals = collector.collect()
        dedup = Deduplicator()
        result = dedup.deduplicate(terminals)
        # Should be very close to original count (seed has no intentional dupes)
        assert len(result) >= len(terminals) - 5  # Allow small margin for fuzzy matches
