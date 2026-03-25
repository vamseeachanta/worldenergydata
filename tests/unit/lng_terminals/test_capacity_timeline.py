"""Tests for LNG terminals capacity and timeline analysis modules."""

from datetime import datetime, timezone

import pytest

from worldenergydata.lng_terminals.analysis.capacity_analysis import CapacityAnalysis
from worldenergydata.lng_terminals.analysis.timeline_analysis import TimelineAnalysis
from worldenergydata.lng_terminals.constants import (
    Region,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.models.terminal import LNGTerminal


def _make_terminal(**overrides):
    defaults = dict(
        terminal_name="Test Terminal",
        country="USA",
        terminal_type=TerminalType.ONSHORE_IMPORT,
        function=TerminalFunction.IMPORT,
        status=TerminalStatus.OPERATIONAL,
        capacity_mtpa=10.0,
        year_commissioned=2020,
        region=Region.NORTH_AMERICA,
        operator="TestOp",
        last_updated=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return LNGTerminal(**defaults)


# ---------------------------------------------------------------------------
# CapacityAnalysis
# ---------------------------------------------------------------------------

class TestCapacityAnalysisTotal:
    def test_total_capacity(self):
        terminals = [_make_terminal(capacity_mtpa=10.0), _make_terminal(capacity_mtpa=20.0)]
        ca = CapacityAnalysis(terminals)
        assert ca._total_capacity() == 30.0

    def test_total_capacity_with_none(self):
        terminals = [_make_terminal(capacity_mtpa=10.0), _make_terminal(capacity_mtpa=None)]
        ca = CapacityAnalysis(terminals)
        assert ca._total_capacity() == 10.0

    def test_empty_list(self):
        ca = CapacityAnalysis([])
        assert ca._total_capacity() == 0.0


class TestCapacityByRegion:
    def test_single_region(self):
        terminals = [
            _make_terminal(region=Region.NORTH_AMERICA, capacity_mtpa=10.0),
            _make_terminal(region=Region.NORTH_AMERICA, capacity_mtpa=5.0),
        ]
        result = CapacityAnalysis(terminals).by_region()
        assert "North America" in result
        assert result["North America"]["count"] == 2
        assert result["North America"]["capacity_mtpa"] == 15.0

    def test_multiple_regions(self):
        terminals = [
            _make_terminal(region=Region.NORTH_AMERICA),
            _make_terminal(region=Region.ASIA_PACIFIC),
        ]
        result = CapacityAnalysis(terminals).by_region()
        assert len(result) == 2

    def test_operational_count(self):
        terminals = [
            _make_terminal(status=TerminalStatus.OPERATIONAL, region=Region.NORTH_AMERICA),
            _make_terminal(status=TerminalStatus.PLANNED, region=Region.NORTH_AMERICA),
        ]
        result = CapacityAnalysis(terminals).by_region()
        assert result["North America"]["operational"] == 1


class TestCapacityByCountry:
    def test_basic(self):
        terminals = [
            _make_terminal(country="USA", capacity_mtpa=10.0),
            _make_terminal(country="USA", capacity_mtpa=5.0),
            _make_terminal(country="QAT", capacity_mtpa=20.0),
        ]
        result = CapacityAnalysis(terminals).by_country()
        assert result["USA"]["count"] == 2
        assert result["USA"]["capacity_mtpa"] == 15.0
        assert result["QAT"]["count"] == 1


class TestCapacityByType:
    def test_basic(self):
        terminals = [
            _make_terminal(terminal_type=TerminalType.ONSHORE_IMPORT),
            _make_terminal(terminal_type=TerminalType.FSRU),
        ]
        result = CapacityAnalysis(terminals).by_type()
        assert len(result) == 2


class TestCapacityByStatus:
    def test_basic(self):
        terminals = [
            _make_terminal(status=TerminalStatus.OPERATIONAL),
            _make_terminal(status=TerminalStatus.OPERATIONAL),
            _make_terminal(status=TerminalStatus.PLANNED),
        ]
        result = CapacityAnalysis(terminals).by_status()
        assert result["operational"]["count"] == 2
        assert result["planned"]["count"] == 1


class TestTopCountries:
    def test_basic(self):
        terminals = [
            _make_terminal(country="USA", capacity_mtpa=100.0),
            _make_terminal(country="QAT", capacity_mtpa=80.0),
            _make_terminal(country="AUS", capacity_mtpa=50.0),
        ]
        result = CapacityAnalysis(terminals).top_countries(n=2)
        assert len(result) == 2
        assert result[0]["country"] == "USA"
        assert result[1]["country"] == "QAT"


class TestCapacitySummary:
    def test_summary_keys(self):
        terminals = [_make_terminal()]
        result = CapacityAnalysis(terminals).summary()
        assert "total_terminals" in result
        assert "total_capacity_mtpa" in result
        assert "by_region" in result
        assert "by_country" in result
        assert "by_type" in result
        assert "by_status" in result
        assert "top_countries" in result


# ---------------------------------------------------------------------------
# TimelineAnalysis
# ---------------------------------------------------------------------------

class TestTimelineByDecade:
    def test_basic(self):
        terminals = [
            _make_terminal(year_commissioned=1995, capacity_mtpa=5.0),
            _make_terminal(year_commissioned=2005, capacity_mtpa=10.0),
            _make_terminal(year_commissioned=2015, capacity_mtpa=20.0),
        ]
        result = TimelineAnalysis(terminals).by_decade()
        assert "1990s" in result
        assert "2000s" in result
        assert "2010s" in result
        assert result["2010s"]["capacity_mtpa"] == 20.0

    def test_no_year(self):
        terminals = [_make_terminal(year_commissioned=None)]
        result = TimelineAnalysis(terminals).by_decade()
        assert len(result) == 0


class TestTimelineByYear:
    def test_basic(self):
        terminals = [
            _make_terminal(year_commissioned=2020, terminal_name="A"),
            _make_terminal(year_commissioned=2020, terminal_name="B"),
            _make_terminal(year_commissioned=2021, terminal_name="C"),
        ]
        result = TimelineAnalysis(terminals).by_year()
        assert result[2020]["count"] == 2
        assert "A" in result[2020]["names"]
        assert result[2021]["count"] == 1


class TestUnderConstruction:
    def test_basic(self):
        terminals = [
            _make_terminal(status=TerminalStatus.UNDER_CONSTRUCTION, terminal_name="UC1"),
            _make_terminal(status=TerminalStatus.OPERATIONAL, terminal_name="OP1"),
        ]
        result = TimelineAnalysis(terminals).under_construction()
        assert len(result) == 1
        assert result[0]["terminal_name"] == "UC1"

    def test_empty(self):
        terminals = [_make_terminal(status=TerminalStatus.OPERATIONAL)]
        result = TimelineAnalysis(terminals).under_construction()
        assert len(result) == 0


class TestPlannedCapacity:
    def test_basic(self):
        terminals = [
            _make_terminal(status=TerminalStatus.PLANNED, capacity_mtpa=15.0),
            _make_terminal(status=TerminalStatus.UNDER_CONSTRUCTION, capacity_mtpa=10.0),
            _make_terminal(status=TerminalStatus.OPERATIONAL, capacity_mtpa=20.0),
        ]
        result = TimelineAnalysis(terminals).planned_capacity()
        assert result["count"] == 2
        assert result["total_capacity_mtpa"] == 25.0
        assert result["by_status"]["planned"] == 15.0
        assert result["by_status"]["under_construction"] == 10.0


class TestTimelineSummary:
    def test_summary_keys(self):
        terminals = [_make_terminal()]
        result = TimelineAnalysis(terminals).summary()
        assert "commissioning_by_decade" in result
        assert "under_construction" in result
        assert "planned_capacity" in result
        assert "commissioning_by_year" in result
