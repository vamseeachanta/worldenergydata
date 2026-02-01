"""Tests for LNG terminal analysis modules."""

import pytest

from worldenergydata.modules.lng_terminals.analysis.capacity_analysis import (
    CapacityAnalysis,
)
from worldenergydata.modules.lng_terminals.analysis.timeline_analysis import (
    TimelineAnalysis,
)
from worldenergydata.modules.lng_terminals.collectors.seed_collector import (
    SeedCollector,
)
from worldenergydata.modules.lng_terminals.models.terminal import LNGTerminal


@pytest.fixture
def seed_terminals() -> list[LNGTerminal]:
    collector = SeedCollector()
    return collector.collect()


class TestCapacityAnalysis:
    """Test capacity analysis."""

    def test_summary_keys(self, seed_terminals):
        analysis = CapacityAnalysis(seed_terminals)
        summary = analysis.summary()
        assert "total_terminals" in summary
        assert "total_capacity_mtpa" in summary
        assert "by_region" in summary
        assert "by_country" in summary
        assert "by_type" in summary
        assert "by_status" in summary
        assert "top_countries" in summary

    def test_total_capacity_positive(self, seed_terminals):
        analysis = CapacityAnalysis(seed_terminals)
        summary = analysis.summary()
        assert summary["total_capacity_mtpa"] > 0

    def test_total_terminals_matches(self, seed_terminals):
        analysis = CapacityAnalysis(seed_terminals)
        summary = analysis.summary()
        assert summary["total_terminals"] == len(seed_terminals)

    def test_by_region_has_entries(self, seed_terminals):
        analysis = CapacityAnalysis(seed_terminals)
        regions = analysis.by_region()
        assert len(regions) >= 4  # At least 4 regions

    def test_by_country_has_entries(self, seed_terminals):
        analysis = CapacityAnalysis(seed_terminals)
        countries = analysis.by_country()
        assert len(countries) >= 15

    def test_top_countries_ordered(self, seed_terminals):
        analysis = CapacityAnalysis(seed_terminals)
        top = analysis.top_countries(n=5)
        assert len(top) == 5
        # Should be sorted descending by capacity
        for i in range(len(top) - 1):
            assert top[i]["capacity_mtpa"] >= top[i + 1]["capacity_mtpa"]

    def test_by_type_includes_export_import(self, seed_terminals):
        analysis = CapacityAnalysis(seed_terminals)
        types = analysis.by_type()
        assert "onshore_export" in types
        assert "onshore_import" in types

    def test_empty_terminals(self):
        analysis = CapacityAnalysis([])
        summary = analysis.summary()
        assert summary["total_terminals"] == 0
        assert summary["total_capacity_mtpa"] == 0.0


class TestTimelineAnalysis:
    """Test timeline analysis."""

    def test_summary_keys(self, seed_terminals):
        analysis = TimelineAnalysis(seed_terminals)
        summary = analysis.summary()
        assert "commissioning_by_decade" in summary
        assert "under_construction" in summary
        assert "planned_capacity" in summary
        assert "commissioning_by_year" in summary

    def test_by_decade_has_entries(self, seed_terminals):
        analysis = TimelineAnalysis(seed_terminals)
        decades = analysis.by_decade()
        assert len(decades) >= 2  # At least 2 decades

    def test_under_construction_list(self, seed_terminals):
        analysis = TimelineAnalysis(seed_terminals)
        uc = analysis.under_construction()
        assert isinstance(uc, list)
        # Seed data should have some under-construction terminals
        assert len(uc) >= 1
        for item in uc:
            assert "terminal_name" in item
            assert "country" in item

    def test_planned_capacity_structure(self, seed_terminals):
        analysis = TimelineAnalysis(seed_terminals)
        planned = analysis.planned_capacity()
        assert "count" in planned
        assert "total_capacity_mtpa" in planned
        assert "by_status" in planned

    def test_empty_terminals(self):
        analysis = TimelineAnalysis([])
        summary = analysis.summary()
        assert summary["under_construction"] == []
