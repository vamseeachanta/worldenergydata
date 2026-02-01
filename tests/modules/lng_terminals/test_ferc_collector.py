"""Tests for FERC LNG terminal collector."""

from worldenergydata.modules.lng_terminals.collectors.ferc_collector import (
    FERCCollector,
)
from worldenergydata.modules.lng_terminals.constants import (
    Region,
    TerminalFunction,
    TerminalType,
)
from worldenergydata.modules.lng_terminals.models.terminal import LNGTerminal


class TestFERCCollector:
    """Test FERC collector behavior."""

    def test_fetch_data_returns_empty_without_config(self):
        """Should return empty string when FERC URL not configured."""
        collector = FERCCollector()
        data = collector.fetch_data()
        assert data == ""

    def test_parse_records_empty_input(self):
        """Should return empty list for empty CSV."""
        collector = FERCCollector()
        result = collector.parse_records("")
        assert result == []

    def test_parse_records_valid_csv(self):
        """Should parse valid FERC CSV data."""
        collector = FERCCollector()
        csv_data = (
            "Project Name,Status,Capacity (Bcf/d),Operator,Type,Date Operational\n"
            "Test LNG Terminal,Operating,2.0,Test Corp,Export,2020\n"
            "Another Terminal,Under Construction,1.5,Other Corp,Import,\n"
        )
        terminals = collector.parse_records(csv_data)
        assert len(terminals) == 2
        assert all(isinstance(t, LNGTerminal) for t in terminals)
        assert all(t.country == "USA" for t in terminals)
        assert all(t.region == Region.NORTH_AMERICA for t in terminals)

    def test_parse_export_terminal(self):
        """Export terminals should be typed correctly."""
        collector = FERCCollector()
        csv_data = (
            "Project Name,Status,Capacity (Bcf/d),Operator,Type,Date Operational\n"
            "Sabine Pass,Operating,4.0,Cheniere,Export,2016\n"
        )
        terminals = collector.parse_records(csv_data)
        assert len(terminals) == 1
        t = terminals[0]
        assert t.terminal_type == TerminalType.ONSHORE_EXPORT
        assert t.function == TerminalFunction.EXPORT

    def test_capacity_conversion(self):
        """Bcf/d should be converted to MTPA."""
        collector = FERCCollector()
        csv_data = (
            "Project Name,Status,Capacity (Bcf/d),Operator,Type,Date Operational\n"
            "Test,Operating,1.0,Corp,Export,2020\n"
        )
        terminals = collector.parse_records(csv_data)
        assert terminals[0].capacity_mtpa is not None
        assert 7.0 < terminals[0].capacity_mtpa < 8.0  # ~7.6

    def test_collect_returns_empty_without_url(self):
        """collect() should return empty list when URL not set."""
        collector = FERCCollector()
        terminals = collector.collect()
        assert terminals == []

    def test_all_terminals_have_sources(self):
        """Each parsed terminal should have a source citation."""
        collector = FERCCollector()
        csv_data = (
            "Project Name,Status,Capacity (Bcf/d),Operator,Type,Date Operational\n"
            "Test,Operating,1.0,Corp,Export,2020\n"
        )
        terminals = collector.parse_records(csv_data)
        for t in terminals:
            assert len(t.sources) >= 1
            assert t.sources[0].source_name == "ferc"
