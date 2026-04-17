"""Tests for LNG terminals constants."""

from worldenergydata.lng_terminals.constants import (
    MAX_PIPELINES_PER_TERMINAL,
    RETRYABLE_HTTP_CODES,
    PipelineType,
    RefreshMode,
    Region,
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)


class TestTerminalType:
    def test_all_members(self):
        expected = {
            "ONSHORE_IMPORT",
            "ONSHORE_EXPORT",
            "FSRU",
            "FLNG",
            "ONSHORE_LIQUEFACTION",
        }
        assert {m.name for m in TerminalType} == expected

    def test_string_enum(self):
        assert isinstance(TerminalType.FSRU, str)
        assert TerminalType.FSRU == "fsru"


class TestTerminalFunction:
    def test_all_members(self):
        expected = {"IMPORT", "EXPORT", "BIDIRECTIONAL"}
        assert {m.name for m in TerminalFunction} == expected


class TestTerminalStatus:
    def test_all_members(self):
        expected = {
            "OPERATIONAL",
            "UNDER_CONSTRUCTION",
            "PLANNED",
            "PROPOSED",
            "DECOMMISSIONED",
            "MOTHBALLED",
        }
        assert {m.name for m in TerminalStatus} == expected


class TestPipelineType:
    def test_all_members(self):
        expected = {
            "FEED_GAS",
            "LNG_TRANSFER",
            "LNG_LOADING",
            "BOIL_OFF_GAS",
            "SEND_OUT",
            "PROCESS",
            "CONDENSATE",
        }
        assert {m.name for m in PipelineType} == expected


class TestSourceReliability:
    def test_all_members(self):
        expected = {"HIGH", "MEDIUM", "LOW"}
        assert {m.name for m in SourceReliability} == expected


class TestRegion:
    def test_all_members(self):
        expected = {
            "NORTH_AMERICA",
            "SOUTH_AMERICA",
            "EUROPE",
            "MIDDLE_EAST",
            "AFRICA",
            "ASIA_PACIFIC",
            "OCEANIA",
        }
        assert {m.name for m in Region} == expected

    def test_display_names(self):
        assert Region.NORTH_AMERICA.value == "North America"
        assert Region.MIDDLE_EAST.value == "Middle East"


class TestRefreshMode:
    def test_all_members(self):
        expected = {"FULL", "INCREMENTAL", "CACHE_FIRST", "FORCE_CACHE"}
        assert {m.name for m in RefreshMode} == expected

    def test_values(self):
        assert RefreshMode.FULL.value == "full"
        assert RefreshMode.CACHE_FIRST.value == "cache_first"


class TestScalarConstants:
    def test_retryable_http_codes(self):
        assert RETRYABLE_HTTP_CODES == {500, 502, 503, 504}
        assert 200 not in RETRYABLE_HTTP_CODES

    def test_max_pipelines(self):
        assert MAX_PIPELINES_PER_TERMINAL == 8
