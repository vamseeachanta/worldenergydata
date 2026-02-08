"""Tests for LNG terminal seed collector."""

from worldenergydata.lng_terminals.collectors.seed_collector import (
    _SEED_TERMINALS,
    SeedCollector,
)
from worldenergydata.lng_terminals.constants import TerminalStatus, TerminalType
from worldenergydata.lng_terminals.models.terminal import LNGTerminal


class TestSeedData:
    """Validate the seed dataset itself."""

    def test_seed_data_has_minimum_count(self):
        """Should have at least 80 terminal records."""
        assert len(_SEED_TERMINALS) >= 80

    def test_all_seed_records_have_required_fields(self):
        """Every seed record must have name, country, type, function, status."""
        required_keys = {
            "terminal_name",
            "country",
            "terminal_type",
            "function",
            "status",
        }
        for i, record in enumerate(_SEED_TERMINALS):
            missing = required_keys - set(record.keys())
            assert (
                not missing
            ), f"Record {i} ({record.get('terminal_name', '?')}) missing: {missing}"

    def test_seed_countries_are_valid_alpha3(self):
        """All country codes should be exactly 3 uppercase letters."""
        import re

        for record in _SEED_TERMINALS:
            code = record["country"]
            assert re.fullmatch(
                r"[A-Z]{3}", code
            ), f"Invalid country code: {code} for {record['terminal_name']}"

    def test_seed_types_are_valid_enums(self):
        """terminal_type values should be valid TerminalType members."""
        for record in _SEED_TERMINALS:
            assert isinstance(
                record["terminal_type"], TerminalType
            ), f"Invalid type for {record['terminal_name']}: {record['terminal_type']}"

    def test_seed_has_diverse_countries(self):
        """Should cover at least 15 different countries."""
        countries = {r["country"] for r in _SEED_TERMINALS}
        assert len(countries) >= 15, f"Only {len(countries)} countries in seed data"

    def test_seed_has_diverse_types(self):
        """Should include FSRU, FLNG, and onshore terminals."""
        types = {r["terminal_type"] for r in _SEED_TERMINALS}
        assert TerminalType.FSRU in types
        assert TerminalType.FLNG in types
        assert TerminalType.ONSHORE_EXPORT in types
        assert TerminalType.ONSHORE_IMPORT in types

    def test_seed_has_mixed_statuses(self):
        """Should include both operational and under-construction terminals."""
        statuses = {r["status"] for r in _SEED_TERMINALS}
        assert TerminalStatus.OPERATIONAL in statuses
        assert TerminalStatus.UNDER_CONSTRUCTION in statuses


class TestSeedCollector:
    """Test the SeedCollector class."""

    def test_collect_returns_terminals(self):
        """collect() should return a non-empty list of LNGTerminal."""
        collector = SeedCollector()
        terminals = collector.collect()
        assert len(terminals) >= 80
        assert all(isinstance(t, LNGTerminal) for t in terminals)

    def test_fetch_data_returns_seed_list(self):
        """fetch_data() should return the seed data list."""
        collector = SeedCollector()
        data = collector.fetch_data()
        assert isinstance(data, list)
        assert len(data) == len(_SEED_TERMINALS)

    def test_terminals_have_auto_generated_ids(self):
        """Each terminal should get an auto-generated terminal_id."""
        collector = SeedCollector()
        terminals = collector.collect()
        for t in terminals:
            assert t.terminal_id, f"Missing ID for {t.terminal_name}"
            assert t.country.lower() in t.terminal_id

    def test_terminals_have_source_citations(self):
        """Each terminal should have at least one source citation."""
        collector = SeedCollector()
        terminals = collector.collect()
        for t in terminals:
            assert len(t.sources) >= 1, f"No sources for {t.terminal_name}"

    def test_sabine_pass_in_dataset(self):
        """Sabine Pass should be in the collected data with correct attributes."""
        collector = SeedCollector()
        terminals = collector.collect()
        sabine = [t for t in terminals if "sabine" in t.terminal_name.lower()]
        assert len(sabine) >= 1
        sp = sabine[0]
        assert sp.country == "USA"
        assert sp.terminal_type == TerminalType.ONSHORE_EXPORT
        assert sp.status == TerminalStatus.OPERATIONAL
