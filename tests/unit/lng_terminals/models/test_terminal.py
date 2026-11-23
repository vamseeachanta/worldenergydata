"""Tests for LNG terminal model."""

from datetime import datetime

import pytest

from worldenergydata.lng_terminals.constants import (
    Region,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.models.terminal import LNGTerminal


def _make_terminal(**kwargs):
    """Helper to create a minimal valid LNGTerminal."""
    defaults = {
        "terminal_name": "Sabine Pass",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "last_updated": datetime(2024, 6, 15),
    }
    defaults.update(kwargs)
    return LNGTerminal(**defaults)


class TestLNGTerminalBasic:
    def test_minimal(self):
        t = _make_terminal()
        assert t.terminal_name == "Sabine Pass"
        assert t.country == "USA"
        assert t.terminal_type == TerminalType.ONSHORE_EXPORT

    def test_auto_generate_terminal_id(self):
        t = _make_terminal()
        assert t.terminal_id == "sabine-pass-usa"

    def test_explicit_terminal_id_not_overwritten(self):
        t = _make_terminal(terminal_id="custom-id")
        assert t.terminal_id == "custom-id"

    def test_country_uppercase(self):
        t = _make_terminal(country="usa")
        assert t.country == "USA"

    def test_country_stripped(self):
        t = _make_terminal(country="  USA  ")
        assert t.country == "USA"


class TestCountryValidation:
    def test_valid_country(self):
        t = _make_terminal(country="AUS")
        assert t.country == "AUS"

    def test_invalid_country_code(self):
        with pytest.raises(Exception):
            _make_terminal(country="US")

    def test_invalid_country_digits(self):
        with pytest.raises(Exception):
            _make_terminal(country="U1A")


class TestGenerateTerminalId:
    def test_basic(self):
        result = LNGTerminal.generate_terminal_id("Sabine Pass LNG", "USA")
        assert result == "sabine-pass-lng-usa"

    def test_special_chars_removed(self):
        result = LNGTerminal.generate_terminal_id("Donggi-Senoro LNG", "IDN")
        assert result == "donggi-senoro-lng-idn"

    def test_accented_chars_stripped(self):
        result = LNGTerminal.generate_terminal_id("Prelude FLNG", "AUS")
        assert result == "prelude-flng-aus"

    def test_multiple_spaces_collapsed(self):
        result = LNGTerminal.generate_terminal_id("Name  With   Spaces", "USA")
        assert result == "name-with-spaces-usa"


class TestOptionalFields:
    def test_with_coordinates(self):
        t = _make_terminal(latitude=29.75, longitude=-93.86)
        assert t.latitude == 29.75
        assert t.longitude == -93.86

    def test_with_capacity(self):
        t = _make_terminal(capacity_mtpa=30.0)
        assert t.capacity_mtpa == 30.0

    def test_with_region(self):
        t = _make_terminal(region=Region.NORTH_AMERICA)
        assert t.region == Region.NORTH_AMERICA

    def test_defaults_none(self):
        t = _make_terminal()
        assert t.latitude is None
        assert t.longitude is None
        assert t.capacity_mtpa is None
        assert t.hull_design is None
        assert t.pipelines == []
        assert t.sources == []


class TestToFlatDict:
    def test_basic_fields(self):
        t = _make_terminal()
        flat = t.to_flat_dict()
        assert flat["terminal_name"] == "Sabine Pass"
        assert flat["country"] == "USA"
        assert flat["terminal_type"] == "onshore_export"
        assert flat["function"] == "export"
        assert flat["status"] == "operational"

    def test_aliases_joined(self):
        t = _make_terminal(aliases=["SPL", "Sabine Pass LNG"])
        flat = t.to_flat_dict()
        assert flat["aliases"] == "SPL|Sabine Pass LNG"

    def test_aliases_empty(self):
        t = _make_terminal()
        flat = t.to_flat_dict()
        assert flat["aliases"] is None

    def test_pipeline_placeholders(self):
        t = _make_terminal()
        flat = t.to_flat_dict()
        assert "pipeline_1_pipeline_type" in flat
        assert flat["pipeline_1_pipeline_type"] is None

    def test_last_updated_iso(self):
        t = _make_terminal(last_updated=datetime(2024, 6, 15, 12, 0, 0))
        flat = t.to_flat_dict()
        assert "2024-06-15" in flat["last_updated"]
