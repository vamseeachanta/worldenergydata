"""CLI entry point for BSEE decline curve analysis.

Usage:
    python -m worldenergydata.bsee.analysis.forecasting --field "Buckskin"
    python -m worldenergydata.bsee.analysis.forecasting --lease OCS-G-25823
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
    BseeDeclineAdapter,
)
from worldenergydata.bsee.analysis.forecasting.decline_analysis import (
    DeclineAnalysis,
)
from worldenergydata.bsee.analysis.forecasting.decline_plots import (
    generate_html_report,
)
from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

_DEFAULT_PROD_BIN = (
    get_module_data_safe("bsee") / "bin" / "production_raw" / "mv_productionsum.bin"
)


def _resolve_field_leases(field_name: str) -> list:
    """Resolve field name to lease numbers using FieldNameResolver.

    Falls back to using field_name as a field code for direct filtering.
    """
    try:
        from worldenergydata.bsee.data.field_names import FieldNameResolver

        resolver = FieldNameResolver()
        all_names = resolver.get_all_field_names()
        # Reverse lookup: find field code from name
        for code, name in all_names.items():
            if name.lower() == field_name.lower():
                return [code]
        # Try as code directly
        if field_name.upper() in all_names:
            return [field_name.upper()]
    except Exception as e:
        logger.debug("FieldNameResolver unavailable: %s", e)

    return [field_name]


def main(argv=None):
    """Run decline curve analysis from CLI."""
    parser = argparse.ArgumentParser(
        description="BSEE Decline Curve Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--field", help="BSEE field name or code")
    group.add_argument("--lease", help="BOEM lease number (e.g. OCS-G-25823)")

    parser.add_argument(
        "--product",
        choices=["oil", "gas", "water"],
        default="oil",
        help="Product type to analyze (default: oil)",
    )
    parser.add_argument(
        "--forecast-periods",
        type=int,
        default=10,
        help="Number of periods to forecast (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output HTML file path (default: stdout summary)",
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        help="Path to production .bin file (default: auto-detect)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Load production data
    adapter = BseeDeclineAdapter()

    if args.data_file:
        bin_path = args.data_file
    else:
        bin_path = _DEFAULT_PROD_BIN

    production_df = adapter.load_production_binary(bin_path)
    if production_df is None:
        logger.error(
            "Cannot load production data from %s. "
            "Run 'make data' or provide --data-file.",
            bin_path,
        )
        sys.exit(1)

    # Extract time series
    if args.field:
        codes = _resolve_field_leases(args.field)
        ts = adapter.extract_field_production(
            production_df, codes[0], product=args.product
        )
    else:
        ts = adapter.extract_lease_production(
            production_df, args.lease, product=args.product
        )

    # Fit models
    analysis = DeclineAnalysis(forecast_periods=args.forecast_periods)
    comparison = analysis.fit_all_models(ts)

    # Print summary
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Decline Curve Analysis: {ts.field_name}")
    logger.info(f"Product: {ts.product_type} | Points: {ts.n_after_filter}")
    logger.info(f"Best model: {comparison.best_model}")
    logger.info(f"{'=' * 60}")
    logger.info(comparison.summary_table().to_string(index=False))

    # Forecast
    forecast = analysis.forecast(comparison)
    eur = analysis.calculate_eur(comparison)

    logger.info(f"\nEUR by model:")
    for model, value in eur.items():
        logger.info(f"  {model}: {value:,.0f}")

    logger.info(f"\nForecast ({args.forecast_periods} periods):")
    forecast_df = forecast.to_dataframe()
    logger.info(forecast_df.to_string(index=False))

    # Generate HTML report
    if args.output:
        html = generate_html_report(ts, comparison, forecast, eur)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
        logger.info("Report written to %s", args.output)


if __name__ == "__main__":
    main()
