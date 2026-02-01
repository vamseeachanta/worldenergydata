"""Tests for LNG terminal web collector."""

from worldenergydata.modules.lng_terminals.collectors.web_collector import WebCollector
from worldenergydata.modules.lng_terminals.constants import (
    SourceReliability,
    TerminalType,
)


class TestWebCollectorParsing:
    """Test HTML parsing and extraction logic."""

    def test_extract_hull_from_text(self):
        """Should extract hull dimensions from text."""
        collector = WebCollector()
        html = """
        <html><head><title>Prelude FLNG</title></head>
        <body>
        <h1>Prelude FLNG Facility</h1>
        <p>The vessel has LOA 488 m,
        beam 74 m, and a draft 12 m with depth 30 m.</p>
        </body></html>
        """
        terminals = collector._extract_from_html(html, "https://example.com")
        assert len(terminals) == 1
        t = terminals[0]
        assert t.hull_design is not None
        assert t.hull_design.loa_m == 488.0
        assert t.hull_design.beam_m == 74.0

    def test_extract_process_equipment(self):
        """Should extract train count from text."""
        collector = WebCollector()
        html = """
        <html><head><title>Sabine Pass LNG</title></head>
        <body>
        <h1>Sabine Pass LNG</h1>
        <p>The facility has 6 liquefaction trains using C3MR technology.</p>
        </body></html>
        """
        terminals = collector._extract_from_html(html, "https://example.com")
        assert len(terminals) == 1
        assert terminals[0].process_equipment is not None
        assert terminals[0].process_equipment.number_of_trains == 6

    def test_extract_storage(self):
        """Should extract storage capacity from text."""
        collector = WebCollector()
        html = """
        <html><head><title>Test LNG</title></head>
        <body>
        <h1>Test LNG Terminal</h1>
        <p>Total storage capacity: 540,000 m3 in full containment tanks.</p>
        </body></html>
        """
        terminals = collector._extract_from_html(html, "https://example.com")
        assert len(terminals) == 1
        assert terminals[0].storage is not None
        assert terminals[0].storage.total_capacity_m3 == 540000.0

    def test_extract_capacity(self):
        """Should extract MTPA capacity."""
        collector = WebCollector()
        html = """
        <html><head><title>Big LNG</title></head>
        <body><h1>Big LNG Project</h1>
        <p>Nameplate capacity of 15.6 MTPA.</p></body></html>
        """
        terminals = collector._extract_from_html(html, "https://example.com")
        assert len(terminals) == 1
        assert terminals[0].capacity_mtpa == 15.6

    def test_no_title_returns_empty(self):
        """Should return empty list when no name can be extracted."""
        collector = WebCollector()
        html = "<html><body><p>Some text</p></body></html>"
        result = collector._extract_from_html(html, "https://example.com")
        assert result == []

    def test_fsru_detection(self):
        """Should detect FSRU type from content."""
        collector = WebCollector()
        html = """
        <html><head><title>Test FSRU</title></head>
        <body><h1>Test FSRU Terminal</h1>
        <p>This FSRU has water depth of 15 m.</p></body></html>
        """
        terminals = collector._extract_from_html(html, "https://example.com")
        assert len(terminals) == 1
        assert terminals[0].terminal_type == TerminalType.FSRU

    def test_source_reliability_is_low(self):
        """Web sources should have LOW reliability."""
        collector = WebCollector()
        assert collector.source_reliability == SourceReliability.LOW

    def test_fetch_data_empty_urls(self):
        """Should return empty list when no URLs configured."""
        collector = WebCollector(urls=[])
        data = collector.fetch_data()
        assert data == []

    def test_collect_empty_urls(self):
        """collect() with no URLs returns empty list."""
        collector = WebCollector(urls=[])
        result = collector.collect()
        assert result == []
