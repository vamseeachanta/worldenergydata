#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate World Oil Lower Tertiary companion reports (WRK-024).

Usage:
    PYTHONPATH=src /usr/bin/python3 scripts/bsee/generate_world_oil_reports.py \
        --config config/input/world_oil_lower_tertiary.yaml --report all

Produces up to three interactive HTML reports:
  - Part 1: Performance Analysis
  - Part 2: Architecture Options Analysis
  - Executive: Combined Executive Summary
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

REPORT_KEYS = ("part1", "part2", "executive")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate World Oil Lower Tertiary companion reports",
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to the YAML config file (e.g. config/input/world_oil_lower_tertiary.yaml)",
    )
    parser.add_argument(
        "--report",
        choices=["part1", "part2", "executive", "all"],
        default="all",
        help="Which report(s) to generate (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory from YAML config",
    )
    return parser.parse_args()


def _resolve_output(config, report_key: str, override_dir: Path | None) -> tuple[Path, str]:
    """Resolve the output directory and filename for a report key.

    Returns (output_dir, filename).
    """
    report_cfg = config.output_config["reports"][report_key]
    output_dir = Path(override_dir) if override_dir else Path(report_cfg["output_dir"])
    filename = report_cfg["filename"]
    return output_dir, filename


def generate_reports(args: argparse.Namespace) -> list[Path]:
    """Load data, build analyzer, and generate requested reports."""
    from worldenergydata.bsee.analysis.lower_tertiary.config import LTConfig
    from worldenergydata.bsee.analysis.lower_tertiary.war_extractor import LTWarExtractor
    from worldenergydata.bsee.analysis.lower_tertiary.legacy_loader import LegacyProductionLoader
    from worldenergydata.bsee.analysis.lower_tertiary.analyzer import LTAnalyzer

    # Step 1: Load config
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    logger.info("Loading config: %s", config_path)
    config = LTConfig(config_path)

    # Step 2: Load WAR data
    war_zip_path = PROJECT_ROOT / config.data_paths["war_zip"]
    logger.info("Loading WAR data: %s", war_zip_path)
    war = LTWarExtractor(war_zip_path, config)

    # Step 3: Load legacy production data
    legacy = LegacyProductionLoader(config, PROJECT_ROOT)

    # Step 4: Create analyzer
    analyzer = LTAnalyzer(config, war, legacy)

    # Step 5: Determine which reports to generate
    if args.report == "all":
        keys = list(REPORT_KEYS)
    else:
        keys = [args.report]

    generated: list[Path] = []

    for key in keys:
        output_dir, filename = _resolve_output(config, key, args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        if key == "part1":
            from worldenergydata.bsee.analysis.lower_tertiary.report_part1 import Part1Report

            report = Part1Report(analyzer)
            result = report.generate(output_path)

        elif key == "part2":
            from worldenergydata.bsee.analysis.lower_tertiary.report_part2 import Part2Report

            report = Part2Report(analyzer)
            result = report.generate(output_path)

        elif key == "executive":
            from worldenergydata.bsee.analysis.lower_tertiary.report_executive import ExecutiveReport

            war_summary = analyzer.war_summary_table()
            report = ExecutiveReport(analyzer)
            result = report.generate(output_path)

        logger.info("Generated: %s", result)
        generated.append(Path(result))

    # Step 6: Copy reports to the shared reports directory (if configured)
    copy_to = config.output_config.get("copy_to")
    if copy_to:
        dest = PROJECT_ROOT / copy_to
        dest.mkdir(parents=True, exist_ok=True)
        for path in generated:
            target = dest / path.name
            shutil.copy2(path, target)
            logger.info("Copied: %s -> %s", path, target)

    return generated


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    args = parse_args()
    paths = generate_reports(args)
    logger.info("Done. Generated %d report(s).", len(paths))


if __name__ == "__main__":
    main()
