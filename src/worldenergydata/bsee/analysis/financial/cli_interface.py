"""
Command-line interface for SME financial analysis

This module provides a CLI for running the financial analysis pipeline
with comprehensive configuration options.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from worldenergydata.common import get_logger

from .analyzer import AnalysisConfig, AnalysisResult, FinancialAnalyzer
from .config_loader import SMEConfigLoader

# CLI utilities will be defined locally

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser with all SME-specific parameters

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="SME Financial Analysis for BSEE Oil & Gas Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis with default settings
  %(prog)s --input-directory /data/bsee --output-file analysis.xlsx

  # Specify date range and developments
  %(prog)s -d /data/bsee -o output.xlsx --start-date 2020-01-01 --end-date 2023-12-31 --developments Stones,Anchor

  # Use configuration file
  %(prog)s --config config.yaml

  # Advanced options with custom parameters
  %(prog)s -d /data/bsee -o analysis.xlsx --oil-price high --discount-rate 0.08 --tax-rate 0.30
        """,
    )

    # Input/Output options
    io_group = parser.add_argument_group("Input/Output Options")
    io_group.add_argument(
        "--input-directory",
        "--directory",
        "-d",
        type=str,
        dest="input_directory",
        help="Input directory containing BSEE data files",
    )
    io_group.add_argument(
        "--output-file",
        "--output",
        "-o",
        type=str,
        dest="output_file",
        help="Output Excel file path for analysis results",
    )
    io_group.add_argument(
        "--config",
        "-c",
        type=str,
        help="Configuration file (YAML or JSON) with analysis parameters",
    )

    # Date range options
    date_group = parser.add_argument_group("Date Range Options")
    date_group.add_argument(
        "--start-date",
        type=str,
        default="2020-01-01",
        help="Start date for analysis (YYYY-MM-DD format)",
    )
    date_group.add_argument(
        "--end-date",
        type=str,
        default="2024-12-31",
        help="End date for analysis (YYYY-MM-DD format)",
    )

    # Development options
    dev_group = parser.add_argument_group("Development Options")
    dev_group.add_argument(
        "--developments",
        type=str,
        help="Comma-separated list of development names (e.g., Stones,Anchor)",
    )
    dev_group.add_argument(
        "--auto-detect",
        action="store_true",
        help="Automatically detect developments from data",
    )

    # Economic parameters
    econ_group = parser.add_argument_group("Economic Parameters")
    econ_group.add_argument(
        "--oil-price",
        choices=["low", "mid", "high", "custom"],
        default="mid",
        help="Oil price scenario for revenue calculations",
    )
    econ_group.add_argument(
        "--custom-oil-price",
        type=float,
        help="Custom oil price ($/bbl) when --oil-price=custom",
    )
    econ_group.add_argument(
        "--discount-rate",
        type=float,
        default=0.10,
        help="Discount rate for NPV calculation (default: 0.10)",
    )
    econ_group.add_argument(
        "--tax-rate",
        type=float,
        default=0.35,
        help="Tax rate for cash flow calculations (default: 0.35)",
    )
    econ_group.add_argument(
        "--working-interest",
        type=float,
        default=1.0,
        help="Working interest fraction (default: 1.0)",
    )
    econ_group.add_argument(
        "--net-revenue-interest",
        type=float,
        default=0.875,
        help="Net revenue interest fraction (default: 0.875)",
    )

    # Processing options
    proc_group = parser.add_argument_group("Processing Options")
    proc_group.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Enable parallel processing (default: enabled)",
    )
    proc_group.add_argument(
        "--no-parallel",
        dest="parallel",
        action="store_false",
        help="Disable parallel processing",
    )
    proc_group.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers (default: 4)"
    )
    proc_group.add_argument(
        "--chunk-size",
        type=int,
        default=10000,
        help="Chunk size for data processing (default: 10000)",
    )
    proc_group.add_argument(
        "--use-cache",
        action="store_true",
        default=True,
        help="Use cached data when available (default: enabled)",
    )
    proc_group.add_argument(
        "--no-cache", dest="use_cache", action="store_false", help="Disable cache usage"
    )

    # Output format options
    format_group = parser.add_argument_group("Output Format Options")
    format_group.add_argument(
        "--version",
        choices=["V18", "V19", "V20"],
        default="V20",
        help="Output format version (default: V20)",
    )
    format_group.add_argument(
        "--include-charts", action="store_true", help="Include charts in Excel output"
    )
    format_group.add_argument(
        "--summary-only", action="store_true", help="Generate summary sheets only"
    )

    # Logging options
    log_group = parser.add_argument_group("Logging Options")
    log_group.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase output verbosity (use multiple times for more detail)",
    )
    log_group.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress all output except errors"
    )
    log_group.add_argument("--log-file", type=str, help="Write logs to specified file")

    # Utility options
    util_group = parser.add_argument_group("Utility Options")
    util_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform analysis without generating output files",
    )
    util_group.add_argument(
        "--list-developments",
        action="store_true",
        help="List available developments and exit",
    )
    util_group.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate input data without running analysis",
    )
    util_group.add_argument(
        "--export-config", type=str, help="Export current configuration to file"
    )

    return parser


def parse_developments(dev_string: str) -> List[str]:
    """Parse comma-separated development names"""
    if not dev_string:
        return []
    return [d.strip() for d in dev_string.split(",")]


def build_config(args: argparse.Namespace) -> AnalysisConfig:
    """
    Build analysis configuration from command-line arguments

    Args:
        args: Parsed command-line arguments

    Returns:
        AnalysisConfig instance
    """
    # If config file specified, load it first
    if args.config:
        config_loader = SMEConfigLoader()
        config_dict = config_loader.load_config(args.config)
    else:
        config_dict = {}

    # Override with command-line arguments
    if args.input_directory:
        config_dict["input_path"] = args.input_directory

    if args.output_file:
        output_path = Path(args.output_file).parent
        config_dict["output_path"] = str(output_path)

    if args.start_date:
        config_dict["start_date"] = args.start_date

    if args.end_date:
        config_dict["end_date"] = args.end_date

    if args.developments:
        config_dict["developments"] = parse_developments(args.developments)
    elif args.auto_detect:
        config_dict["developments"] = []  # Will auto-detect

    # Economic parameters
    config_dict["oil_price_scenario"] = args.oil_price
    config_dict["discount_rate"] = args.discount_rate
    config_dict["tax_rate"] = args.tax_rate
    config_dict["working_interest"] = args.working_interest
    config_dict["net_revenue_interest"] = args.net_revenue_interest

    # Processing options
    config_dict["parallel_processing"] = args.parallel
    config_dict["max_workers"] = args.workers
    config_dict["chunk_size"] = args.chunk_size
    config_dict["use_cache"] = args.use_cache

    # Output format
    config_dict["version"] = args.version

    # Validate required fields
    if "input_path" not in config_dict:
        raise ValueError(
            "Input directory must be specified (--input-directory or in config file)"
        )

    if "output_path" not in config_dict:
        config_dict["output_path"] = "."

    return AnalysisConfig(**config_dict)


def setup_logging_cli(args: argparse.Namespace):
    """Setup logging based on CLI arguments"""
    if args.quiet:
        level = logging.ERROR
    elif args.verbose == 0:
        level = logging.WARNING
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))

    logging.basicConfig(level=level, format=log_format, handlers=handlers)


def print_analysis_banner():
    """Print analysis banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║       SME Financial Analysis - BSEE Oil & Gas Data          ║
    ║                    Version 20 (V20)                         ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    logger.info(banner)


def print_results_summary(result: AnalysisResult):
    """Print analysis results summary"""
    if result.success:
        logger.info("\n✅ Analysis completed successfully!")
        logger.info(f"   Output file: {result.output_file}")

        if result.metrics_summary:
            logger.info("\n📊 Summary Metrics:")
            logger.info(
                f"   Total NPV: ${result.metrics_summary.get('total_npv', 0):,.0f}"
            )
            logger.info(
                f"   Total Oil: {result.metrics_summary.get('total_oil_bbls', 0):,.0f} bbls"
            )
            logger.info(
                f"   Developments: {result.metrics_summary.get('development_count', 0)}"
            )
            logger.info(f"   Execution Time: {result.execution_time:.2f} seconds")
    else:
        logger.info(f"\n❌ Analysis failed: {result.error_message}")


def list_developments(config: AnalysisConfig):
    """List available developments in the data"""
    analyzer = FinancialAnalyzer(config)

    # Load production data to detect developments
    prod_data, _ = analyzer.load_data()

    # Get unique development names from data
    if "development" in prod_data.columns:
        developments = prod_data["development"].unique().tolist()
    elif "lease" in prod_data.columns:
        # Group by lease patterns
        developments = ["Development1", "Development2"]  # Placeholder
    else:
        developments = []

    logger.info("\n📋 Available Developments:")
    for i, dev in enumerate(developments, 1):
        logger.info(f"   {i}. {dev}")

    logger.info(f"\nTotal: {len(developments)} developments found")


def validate_data(config: AnalysisConfig):
    """Validate input data without running full analysis"""
    analyzer = FinancialAnalyzer(config)

    logger.info("\n🔍 Validating input data...")

    try:
        # Load data
        prod_data, drill_data = analyzer.load_data()

        # Validate
        prod_valid = analyzer.validator.validate_production_data(prod_data)
        drill_valid = analyzer.validator.validate_drilling_data(drill_data)

        if prod_valid and drill_valid:
            logger.info("✅ Data validation passed!")
            logger.info(f"   Production records: {len(prod_data):,}")
            logger.info(f"   Drilling records: {len(drill_data):,}")
        else:
            logger.info("❌ Data validation failed!")

    except Exception as e:
        logger.info(f"❌ Validation error: {str(e)}")


def export_config(args: argparse.Namespace):
    """Export current configuration to file"""
    config = build_config(args)
    config_dict = {
        "input_path": config.input_path,
        "output_path": config.output_path,
        "start_date": str(config.start_date),
        "end_date": str(config.end_date),
        "developments": config.developments,
        "oil_price_scenario": config.oil_price_scenario,
        "discount_rate": config.discount_rate,
        "tax_rate": config.tax_rate,
        "working_interest": config.working_interest,
        "net_revenue_interest": config.net_revenue_interest,
        "version": config.version,
        "parallel_processing": config.parallel_processing,
        "max_workers": config.max_workers,
        "chunk_size": config.chunk_size,
        "use_cache": config.use_cache,
    }

    export_path = Path(args.export_config)

    if export_path.suffix == ".json":
        with open(export_path, "w") as f:
            json.dump(config_dict, f, indent=2, default=str)
    else:
        with open(export_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)

    logger.info(f"✅ Configuration exported to: {export_path}")


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI

    Args:
        argv: Command-line arguments (for testing)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    setup_logging_cli(args)

    try:
        # Handle utility commands
        if args.export_config:
            export_config(args)
            return 0

        # Build configuration
        config = build_config(args)

        # Handle list developments
        if args.list_developments:
            list_developments(config)
            return 0

        # Handle validate only
        if args.validate_only:
            validate_data(config)
            return 0

        # Print banner
        if not args.quiet:
            print_analysis_banner()

        # Create analyzer
        analyzer = FinancialAnalyzer(config)

        # Run analysis
        if args.dry_run:
            logger.info("\n🔄 Dry run mode - no files will be generated")
            result = analyzer.run_analysis(output_path=None)
        else:
            output_path = (
                args.output_file
                or f"financial_analysis_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
            )
            result = analyzer.run_analysis(output_path=output_path)

        # Print results
        if not args.quiet:
            print_results_summary(result)

        return 0 if result.success else 1

    except Exception as e:
        logger.error(f"CLI execution failed: {str(e)}")
        if not args.quiet:
            logger.info(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
