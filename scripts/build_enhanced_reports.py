#!/usr/bin/env python3
"""Build enhanced GOM analysis reports (WRK-116).

Master pipeline: DATA -> ENRICHMENT -> ANALYSIS -> INSIGHTS -> REPORTS.

Usage:
    PYTHONPATH=src python scripts/build_enhanced_reports.py [--output-dir DIR] [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

logger = logging.getLogger(__name__)


def load_data(data_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None, dict | None]:
    """Load WAR, fleet, borehole, and paleowells data.

    Returns (war_df, fleet_df, borehole_df_or_None, era_map_or_None).
    """
    from worldenergydata.bsee.data.loaders.rig_fleet.war_acquirer import WARDataAcquirer
    from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
    from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor

    # WAR data
    acquirer = WARDataAcquirer(BSEEWebScraper(), MemoryProcessor())
    war_df = acquirer.acquire_war_dataframe()
    if war_df is None:
        logger.error("Could not load WAR data")
        sys.exit(1)
    logger.info("WAR: %d records", len(war_df))

    # Fleet data (prefer pre-built .bin, fall back to building from WAR)
    fleet_path = data_root / ".local" / "rig_fleet" / "rig_fleet_full.bin"
    if fleet_path.exists():
        with open(fleet_path, "rb") as f:
            fleet_df = pickle.load(f)  # nosec B301
        logger.info("Fleet (cached): %d rigs", len(fleet_df))
    else:
        from worldenergydata.bsee.data.loaders.rig_fleet.rig_fleet_loader import RigFleetLoader
        loader = RigFleetLoader()
        fleet_df = loader.build_fleet_from_war(war_df)
        logger.info("Fleet (built): %d rigs", len(fleet_df))

    # Borehole data (optional)
    borehole_df = None
    try:
        from worldenergydata.bsee.data.loaders.well.borehole_acquirer import BoreholeDataAcquirer
        acq = BoreholeDataAcquirer()
        borehole_df = acq.acquire_borehole_dataframe()
        if borehole_df is not None:
            logger.info("Borehole: %d wells", len(borehole_df))
    except Exception as exc:
        logger.warning("Borehole data not available: %s", exc)

    # Paleowells era map (optional)
    era_map = None
    paleowells_csv = data_root / "paleowells" / "Paleowells.csv"
    if paleowells_csv.exists():
        try:
            from worldenergydata.bsee.paleowells.era_classifier import GeologicalEraClassifier
            classifier = GeologicalEraClassifier(paleowells_csv=paleowells_csv)
            era_map = classifier.get_well_eras()
            logger.info("Paleowells: %d wells with era data", len(era_map))
        except Exception as exc:
            logger.warning("Paleowells data not available: %s", exc)

    return war_df, fleet_df, borehole_df, era_map


def run_pipeline(
    war_df: pd.DataFrame,
    fleet_df: pd.DataFrame,
    borehole_df: pd.DataFrame | None,
    era_map: dict | None,
) -> tuple[pd.DataFrame, dict, dict]:
    """Run enrichment -> analysis -> insights pipeline.

    Returns (enriched_df, analysis_results, insights).
    """
    from worldenergydata.bsee.analysis.intervention.enrichment_engine import ActivityEnrichmentEngine
    from worldenergydata.bsee.analysis.intervention.comprehensive_analyzer import ComprehensiveActivityAnalyzer
    from worldenergydata.bsee.analysis.intervention.insight_generator import InsightGenerator

    engine = ActivityEnrichmentEngine(war_df, fleet_df, borehole_df, era_map)
    enriched_df = engine.enrich()
    stats = engine.get_join_stats()
    logger.info(
        "Enrichment: %d rows, fleet=%.0f%%, borehole=%.0f%%, era=%.0f%%",
        stats["total_war_records"],
        stats["fleet_match_rate"] * 100,
        stats["borehole_match_rate"] * 100,
        stats["era_match_rate"] * 100,
    )

    analyzer = ComprehensiveActivityAnalyzer(enriched_df)
    analysis_results = analyzer.analyze()
    logger.info("Analysis: 7 modules completed")

    gen = InsightGenerator(analysis_results)
    insights = gen.generate()
    logger.info(
        "Insights: %d findings, %d trends, %d risks",
        len(insights.get("key_findings", [])),
        len(insights.get("market_trends", [])),
        len(insights.get("risk_factors", [])),
    )

    return enriched_df, analysis_results, insights


def generate_reports(
    war_df: pd.DataFrame,
    fleet_df: pd.DataFrame,
    insights: dict,
    output_dir: Path,
) -> list[str]:
    """Generate all reports and return list of output paths."""
    from worldenergydata.bsee.analysis.intervention.drilling_report import DrillingAnalysisReport
    from worldenergydata.bsee.analysis.intervention.dashboard import InterventionDashboard
    from worldenergydata.bsee.analysis.intervention.intervention_detail_report import InterventionDetailReport

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    # Drilling analysis report
    report = DrillingAnalysisReport(war_df, fleet_df)
    path = report.generate(str(output_dir / "drilling_analysis.html"))
    generated.append(path)
    logger.info("Generated: %s", path)

    # Intervention dashboard (with optional insights)
    dashboard = InterventionDashboard(war_df, fleet_df, insights=insights)
    path = dashboard.generate(str(output_dir / "intervention_dashboard.html"))
    generated.append(path)
    logger.info("Generated: %s", path)

    # Intervention detail report
    detail = InterventionDetailReport(war_df, fleet_df)
    path = detail.generate(str(output_dir / "intervention_by_service.html"))
    generated.append(path)
    logger.info("Generated: %s", path)

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Build enhanced GOM analysis reports")
    parser.add_argument(
        "--output-dir",
        default="reports/bsee/intervention",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without generating reports",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    data_root = Path("data/modules/bsee")
    war_df, fleet_df, borehole_df, era_map = load_data(data_root)
    _enriched_df, _analysis_results, insights = run_pipeline(
        war_df, fleet_df, borehole_df, era_map,
    )

    if args.dry_run:
        logger.info("Dry run -- skipping report generation")
        return

    paths = generate_reports(war_df, fleet_df, insights, Path(args.output_dir))
    logger.info("Done. Generated %d reports.", len(paths))


if __name__ == "__main__":
    main()
