#!/usr/bin/env python
"""Buckskin field BSEE data analysis runner.

Extracts data from BSEE binary archives, analyzes production and wellbore
metrics, and generates an HTML report for the Buckskin field (Keathley Canyon
blocks 785, 828, 829, 830, 871, 872).

Usage:
    python scripts/bsee/analyze_buckskin.py [--output PATH] [--csv DIR]
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
_BIN_DIR = _ROOT / "data" / "modules" / "bsee" / "bin"
_WAR_ZIP = _ROOT / "data" / "modules" / "bsee" / ".local" / "war" / "eWellWARRawData.zip"
_DEFAULT_OUTPUT = _ROOT / "reports" / "bsee" / "buckskin_analysis.html"
_DEFAULT_CSV_DIR = _ROOT / "reports" / "bsee" / "buckskin"


def main() -> int:
    parser = argparse.ArgumentParser(description="Buckskin field BSEE analysis")
    parser.add_argument(
        "--output", type=Path, default=_DEFAULT_OUTPUT,
        help="HTML report output path",
    )
    parser.add_argument(
        "--csv", type=Path, default=None,
        help="Directory for CSV exports (optional)",
    )
    args = parser.parse_args()

    # Late imports so PYTHONPATH can be set before running
    from worldenergydata.bsee.analysis.buckskin.extractor import BuckskinExtractor
    from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
    from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

    # 1. Extract
    logger.info("Extracting Buckskin data from %s", _BIN_DIR)
    war_path = _WAR_ZIP if _WAR_ZIP.exists() else None
    extractor = BuckskinExtractor(bin_dir=_BIN_DIR, war_zip_path=war_path)
    data = extractor.extract_all()

    for name, df in data.items():
        logger.info("  %s: %d rows", name, len(df))

    # 2. Analyze
    analyzer = BuckskinAnalyzer(data=data)
    prod = analyzer.production_summary()
    inv = analyzer.wellbore_inventory()
    benchmarks = analyzer.validate_benchmarks()

    logger.info("Production: %.3f MMBBL oil, %d wells, first oil %s",
                prod["cumulative_oil_mmbbl"],
                prod["producing_well_count"],
                prod["first_production_year"])
    logger.info("Wellbore: %d total (%d dev, %d exp)",
                inv["total_wells"], inv["development_count"],
                inv["exploration_count"])
    logger.info("Benchmark: first oil match=%s, formation=%s",
                benchmarks["first_oil_year_match"],
                benchmarks["geological_era"])

    # 3. Decline curve analysis (optional — requires forecasting module)
    decline_results = analyzer.decline_curve_analysis(product="oil")
    if decline_results:
        logger.info("Decline: best=%s, EUR=%s",
                     decline_results["comparison"].best_model,
                     {k: f"{v:,.0f}" for k, v in decline_results["eur"].items()})
    else:
        logger.info("Decline curve analysis: skipped (insufficient data)")

    # 4. Generate report
    report = BuckskinReport(analyzer)
    out = report.generate_html(args.output, decline_results=decline_results)
    logger.info("HTML report: %s", out)

    # 4. Optional CSV exports
    if args.csv is not None:
        csv_dir = Path(args.csv)
        csv_dir.mkdir(parents=True, exist_ok=True)
        for name, df in data.items():
            if not df.empty:
                csv_path = csv_dir / f"buckskin_{name}.csv"
                df.to_csv(csv_path, index=False)
                logger.info("CSV: %s (%d rows)", csv_path, len(df))

    return 0


if __name__ == "__main__":
    sys.exit(main())
