"""End-to-end pipeline integration tests (WRK-116 Phase 5d).

Validates the full pipeline: synthetic data -> enrichment -> analysis
-> insights -> report generation.  Uses shared fixtures from conftest.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.comprehensive_analyzer import (
    ComprehensiveActivityAnalyzer,
)
from worldenergydata.bsee.analysis.intervention.drilling_report import (
    DrillingAnalysisReport,
)
from worldenergydata.bsee.analysis.intervention.enrichment_engine import (
    ActivityEnrichmentEngine,
)
from worldenergydata.bsee.analysis.intervention.insight_generator import (
    InsightGenerator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_pipeline(
    war_df: pd.DataFrame,
    fleet_df: pd.DataFrame,
    borehole_df: pd.DataFrame,
    paleowells_era_map: dict[str, str],
) -> tuple[pd.DataFrame, dict, dict]:
    """Run enrichment -> analysis -> insights and return all three."""
    engine = ActivityEnrichmentEngine(war_df, fleet_df, borehole_df, paleowells_era_map)
    enriched = engine.enrich()
    analyzer = ComprehensiveActivityAnalyzer(enriched)
    results = analyzer.analyze()
    insights = InsightGenerator(results).generate()
    return enriched, results, insights


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """End-to-end pipeline integration tests."""

    def test_full_pipeline_enrichment_to_analysis(
        self, war_df, fleet_df, borehole_df, paleowells_era_map,
    ):
        """Enrichment -> analysis produces dict with 7 keys."""
        engine = ActivityEnrichmentEngine(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        enriched = engine.enrich()
        analyzer = ComprehensiveActivityAnalyzer(enriched)
        results = analyzer.analyze()
        assert set(results.keys()) == {
            "drilling_efficiency",
            "well_depth",
            "geological_era",
            "cross_activity",
            "well_lifecycle",
            "operator_portfolio",
            "duration_benchmarking",
        }

    def test_full_pipeline_analysis_to_insights(
        self, war_df, fleet_df, borehole_df, paleowells_era_map,
    ):
        """Analysis -> insights produces dict with 5 keys."""
        _, _, insights = _run_pipeline(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        assert set(insights.keys()) == {
            "key_findings",
            "market_trends",
            "competitive_intelligence",
            "opportunity_areas",
            "risk_factors",
        }

    def test_full_pipeline_report_generation(
        self, war_df, fleet_df, borehole_df, paleowells_era_map, tmp_path,
    ):
        """Full pipeline produces valid HTML report."""
        enriched, results, insights = _run_pipeline(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        report = DrillingAnalysisReport.from_enriched(enriched, results, insights)
        out = str(tmp_path / "test_report.html")
        path = report.generate(out)
        content = Path(path).read_text()
        assert Path(path).exists()
        assert "Actual Drilling Duration" in content
        assert "Well Depth Analysis" in content
        assert "Key Insights" in content

    def test_report_backward_compat(self, war_df, fleet_df, tmp_path):
        """Old constructor still works without enriched data."""
        report = DrillingAnalysisReport(war_df, fleet_df)
        path = report.generate(str(tmp_path / "legacy.html"))
        content = Path(path).read_text()
        assert Path(path).exists()
        assert "Actual Drilling Duration" not in content
        assert "Key Insights" not in content

    def test_enriched_report_has_extra_sections(
        self, war_df, fleet_df, borehole_df, paleowells_era_map, tmp_path,
    ):
        """Enhanced report includes new sections not in legacy."""
        enriched, results, insights = _run_pipeline(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        legacy = DrillingAnalysisReport(war_df, fleet_df)
        legacy_path = str(tmp_path / "legacy.html")
        legacy.generate(legacy_path)
        legacy_html = Path(legacy_path).read_text()

        enhanced = DrillingAnalysisReport.from_enriched(enriched, results, insights)
        enhanced_path = str(tmp_path / "enhanced.html")
        enhanced.generate(enhanced_path)
        enhanced_html = Path(enhanced_path).read_text()

        legacy_sections = legacy_html.count('<div class="section"')
        enhanced_sections = enhanced_html.count('<div class="section"')
        assert enhanced_sections == legacy_sections + 3

    def test_insights_all_strings(
        self, war_df, fleet_df, borehole_df, paleowells_era_map,
    ):
        """Every insight value is a list of strings."""
        _, _, insights = _run_pipeline(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        for key, items in insights.items():
            assert isinstance(items, list), f"{key} should be a list"
            for item in items:
                assert isinstance(item, str), (
                    f"Item in {key} should be str, got {type(item)}"
                )

    def test_analysis_drilling_efficiency_uses_actual_days(
        self, war_df, fleet_df, borehole_df, paleowells_era_map,
    ):
        """Verify drilling days come from borehole SPUD/TD, not WAR x 7."""
        enriched, results, _ = _run_pipeline(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        eff = results["drilling_efficiency"]
        mean_days = eff["mean_drilling_days"]
        # Borehole fixture has SPUD->TD durations of 70, 64, 45, 66, 47, 73,
        # 76, 188 days.  The WAR x 7 estimate would produce 7-21 for the
        # conftest data (1-3 records per well).  Actual durations are all > 40,
        # so the mean must exceed 30 to confirm real borehole data is used.
        assert mean_days > 30, (
            f"Expected actual drilling days (>30), got {mean_days} -- "
            "this looks like WAR x 7 estimate instead of SPUD->TD"
        )
