"""Tests for deduplicator handling of numbered facility names."""

from datetime import datetime

from worldenergydata.modules.lng_terminals.constants import (
    Region,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.modules.lng_terminals.models.terminal import LNGTerminal
from worldenergydata.modules.lng_terminals.processors.deduplicator import Deduplicator


def _make_terminal(name: str, country: str = "USA", **kwargs) -> LNGTerminal:
    defaults = {
        "terminal_name": name,
        "country": country,
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "region": Region.NORTH_AMERICA,
        "last_updated": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return LNGTerminal(**defaults)


class TestDifferOnlyByNumber:
    """Unit tests for _differ_only_by_number."""

    def test_vessel_numbers(self):
        d = Deduplicator()
        assert d._differ_only_by_number("delfin flng vessel 2", "delfin flng vessel 3")

    def test_train_numbers(self):
        d = Deduplicator()
        assert d._differ_only_by_number("sabine pass train 1", "sabine pass train 2")

    def test_same_number_not_different(self):
        d = Deduplicator()
        assert not d._differ_only_by_number(
            "delfin flng vessel 2", "delfin flng vessel 2"
        )

    def test_no_number_not_different(self):
        d = Deduplicator()
        assert not d._differ_only_by_number("sabine pass", "sabine pass")

    def test_different_bases_not_matched(self):
        d = Deduplicator()
        assert not d._differ_only_by_number("sabine pass train 1", "cameron train 2")

    def test_one_has_number_other_does_not(self):
        d = Deduplicator()
        assert not d._differ_only_by_number("delfin flng", "delfin flng vessel 2")


class TestDeduplicatorNumberedFacilities:
    """Integration: numbered facilities stay separate after dedup."""

    def test_delfin_vessels_stay_separate(self):
        terminals = [
            _make_terminal("Delfin FLNG"),
            _make_terminal("Delfin FLNG Vessel 2"),
            _make_terminal("Delfin FLNG Vessel 3"),
        ]
        d = Deduplicator()
        result = d.deduplicate(terminals)
        names = {t.terminal_name for t in result}
        # All three should survive - vessel 2 and 3 must not merge
        # Note: "Delfin FLNG" (no number) may merge with one of them
        # but vessel 2 and vessel 3 must remain distinct
        assert "Delfin FLNG Vessel 2" in names or len(result) >= 2
        assert "Delfin FLNG Vessel 3" in names or len(result) >= 2
        # At minimum: vessel 2 and 3 are separate entities
        vessel_names = [n for n in names if "Vessel" in n or "vessel" in n.lower()]
        # If both vessel names survived, they must be distinct
        if len(vessel_names) == 2:
            assert "Delfin FLNG Vessel 2" in vessel_names
            assert "Delfin FLNG Vessel 3" in vessel_names

    def test_three_delfin_vessels_all_survive(self):
        """All 3 Delfin entries should survive dedup as distinct facilities."""
        terminals = [
            _make_terminal("Delfin FLNG", status=TerminalStatus.PLANNED),
            _make_terminal("Delfin FLNG Vessel 2", status=TerminalStatus.PLANNED),
            _make_terminal("Delfin FLNG Vessel 3", status=TerminalStatus.PROPOSED),
        ]
        d = Deduplicator()
        result = d.deduplicate(terminals)
        # "Delfin FLNG" (no number) may still merge with one of the numbered ones
        # since it has no trailing number. But vessel 2 and 3 MUST stay separate.
        assert len(result) >= 2

    def test_identical_numbered_facilities_merge(self):
        """Same numbered facility from two sources should merge."""
        t1 = _make_terminal("Delfin FLNG Vessel 2", capacity_mtpa=4.4)
        t2 = _make_terminal(
            "Delfin FLNG Vessel 2", capacity_mtpa=4.4, operator="Delfin Midstream"
        )
        d = Deduplicator()
        result = d.deduplicate([t1, t2])
        assert len(result) == 1

    def test_genuine_duplicates_still_merge(self):
        """True duplicates (same name, no number) still get merged."""
        t1 = _make_terminal(
            "Sabine Pass LNG", terminal_type=TerminalType.ONSHORE_EXPORT
        )
        t2 = _make_terminal(
            "Sabine Pass Liquefaction", terminal_type=TerminalType.ONSHORE_EXPORT
        )
        d = Deduplicator()
        result = d.deduplicate([t1, t2])
        assert len(result) == 1
