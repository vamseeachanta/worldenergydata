"""Tests for LNG terminal enricher."""

from datetime import datetime

from worldenergydata.lng_terminals.constants import (
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.models.terminal import LNGTerminal
from worldenergydata.lng_terminals.processors.enricher import (
    SOURCE_PRIORITY,
    Enricher,
)


def _make_terminal(
    name: str,
    country: str = "USA",
    capacity: float | None = None,
    operator: str | None = None,
    terminal_id: str | None = None,
) -> LNGTerminal:
    t = LNGTerminal(
        terminal_name=name,
        country=country,
        terminal_type=TerminalType.ONSHORE_EXPORT,
        function=TerminalFunction.EXPORT,
        status=TerminalStatus.OPERATIONAL,
        capacity_mtpa=capacity,
        operator=operator,
        last_updated=datetime.utcnow(),
    )
    if terminal_id:
        t.terminal_id = terminal_id
    return t


class TestEnricher:
    """Test enrichment logic."""

    def test_enrich_adds_new_records(self):
        """Records not in base should be appended."""
        enricher = Enricher()
        base = [_make_terminal("Sabine Pass LNG", "USA")]
        additional = [_make_terminal("Cameron LNG", "USA")]
        result = enricher.enrich(base, additional, source_name="ferc")
        assert len(result) == 2

    def test_enrich_fills_missing_fields(self):
        """Should fill None fields from additional source."""
        enricher = Enricher()
        base = [_make_terminal("Sabine Pass LNG", "USA")]
        additional = [
            _make_terminal("Sabine Pass LNG", "USA", capacity=30.0, operator="Cheniere")
        ]
        # Make IDs match
        additional[0].terminal_id = base[0].terminal_id
        result = enricher.enrich(base, additional, source_name="ferc")
        assert len(result) == 1
        assert result[0].capacity_mtpa == 30.0

    def test_higher_priority_overwrites(self):
        """Higher-priority source should overwrite existing values."""
        enricher = Enricher()
        base = [_make_terminal("Test LNG", "USA", operator="Old Corp")]
        additional = [_make_terminal("Test LNG", "USA", operator="New Corp")]
        additional[0].terminal_id = base[0].terminal_id
        result = enricher.enrich(base, additional, source_name="ferc")
        assert len(result) == 1
        # FERC (50) > seed (10), so new value wins
        assert result[0].operator == "New Corp"

    def test_source_priority_order(self):
        """Verify source priority ordering."""
        assert SOURCE_PRIORITY["ferc"] > SOURCE_PRIORITY["gie"]
        assert SOURCE_PRIORITY["gie"] > SOURCE_PRIORITY["giignl"]
        assert SOURCE_PRIORITY["giignl"] > SOURCE_PRIORITY["seed_dataset"]

    def test_empty_base(self):
        enricher = Enricher()
        additional = [_make_terminal("Test", "USA")]
        result = enricher.enrich([], additional, source_name="ferc")
        assert len(result) == 1

    def test_empty_additional(self):
        enricher = Enricher()
        base = [_make_terminal("Test", "USA")]
        result = enricher.enrich(base, [], source_name="ferc")
        assert len(result) == 1
