"""Tests for LNG terminal quality dashboard."""

import json

import pytest

from worldenergydata.modules.lng_terminals.collectors.seed_collector import (
    SeedCollector,
)
from worldenergydata.modules.lng_terminals.models.terminal import LNGTerminal
from worldenergydata.modules.lng_terminals.reports.quality_dashboard import (
    QualityDashboard,
)


@pytest.fixture
def seed_terminals() -> list[LNGTerminal]:
    collector = SeedCollector()
    return collector.collect()


class TestQualityDashboard:
    """Test quality dashboard report generation."""

    def test_report_structure(self, seed_terminals):
        dashboard = QualityDashboard(seed_terminals)
        report = dashboard.generate_report()
        assert "total_terminals" in report
        assert "scored_terminals" in report
        assert "overall" in report
        assert "required_fields" in report
        assert "optional_fields" in report
        assert "engineering_fields" in report
        assert "source_coverage" in report
        assert "distribution" in report

    def test_overall_scores(self, seed_terminals):
        dashboard = QualityDashboard(seed_terminals)
        report = dashboard.generate_report()
        overall = report["overall"]
        assert 0 <= overall["average"] <= 100
        assert 0 <= overall["min"] <= 100
        assert 0 <= overall["max"] <= 100
        assert overall["min"] <= overall["average"] <= overall["max"]

    def test_required_fields_mostly_complete(self, seed_terminals):
        """Seed data should have required fields at 100% for most records."""
        dashboard = QualityDashboard(seed_terminals)
        report = dashboard.generate_report()
        assert report["required_fields"]["all_complete"] == len(seed_terminals)

    def test_distribution_buckets(self, seed_terminals):
        dashboard = QualityDashboard(seed_terminals)
        report = dashboard.generate_report()
        dist = report["distribution"]
        assert set(dist.keys()) == {"0-20", "20-40", "40-60", "60-80", "80-100"}
        assert sum(dist.values()) == report["scored_terminals"]

    def test_export_json(self, seed_terminals, tmp_path):
        dashboard = QualityDashboard(seed_terminals)
        path = dashboard.export_json(output_path=tmp_path / "quality.json")
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["total_terminals"] == len(seed_terminals)

    def test_empty_terminals(self):
        dashboard = QualityDashboard([])
        report = dashboard.generate_report()
        assert report.get("error") == "No scored terminals"
