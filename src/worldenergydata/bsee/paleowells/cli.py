"""
CLI interface for the BSEE Paleowells module.

Usage:
    python -m worldenergydata.bsee.paleowells [command] [options]
"""

import argparse
import json
import sys
from pathlib import Path

from worldenergydata.common import get_logger
from worldenergydata.common.logging import configure_logging

from .data_downloader import BSEEDataDownloader
from .data_processor import PaleowellsDataProcessor
from .visualizer import PaleowellsVisualizer

logger = get_logger(__name__)


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = "DEBUG" if verbose else "INFO"
    configure_logging(level=level)


def process_command(args):
    """Process paleowells data."""
    processor = PaleowellsDataProcessor(args.data_directory)

    if args.input_file:
        df = processor.process_paleowells_data(
            raw_data_file=Path(args.input_file),
            output_directory=(
                Path(args.output_directory) if args.output_directory else None
            ),
        )
        logger.info(f"Processed {len(df)} records")

        if args.analyze:
            analysis = processor.analyze_well_epochs(df)
            logger.info("\nAnalysis Results:")
            logger.info(json.dumps(analysis, indent=2, default=str))
    else:
        # Try to process existing data
        df = processor.parse_fixed_width_file(
            Path(args.data_directory) / "lower_tertiary_wells.txt",
            (
                Path(args.output_directory) / "paleowells.csv"
                if args.output_directory
                else None
            ),
        )
        logger.info(f"Parsed {len(df)} records")


def download_command(args):
    """Download BSEE/BOEM data."""
    downloader = BSEEDataDownloader(args.data_directory)

    if args.info:
        # Just show available datasets
        info = downloader.get_latest_data_info()
        logger.info("\nAvailable BSEE/BOEM Datasets:")
        logger.info("-" * 60)
        for name, details in info.items():
            logger.info(f"\n{name}:")
            logger.info(f"  Description: {details['description']}")
            logger.info(f"  Available: {details.get('available', 'Unknown')}")
            if details.get("size") and details["size"] != "Unknown":
                size_mb = int(details["size"]) / (1024 * 1024)
                logger.info(f"  Size: {size_mb:.2f} MB")
    else:
        # Download datasets
        datasets = args.datasets if args.datasets else None
        results = downloader.download_all_datasets(
            datasets=datasets, extract=args.extract, overwrite=args.overwrite
        )

        # Print summary
        logger.info("\nDownload Summary:")
        logger.info("-" * 60)
        for result in results:
            status = "✓" if result["download_success"] else "✗"
            logger.info(f"{status} {result['dataset']}: {result['description']}")
            if result["extract_success"]:
                logger.info(f"  Extracted {len(result['extracted_files'])} files")


def visualize_command(args):
    """Visualize paleowells data."""
    visualizer = PaleowellsVisualizer()

    # Load data
    import pandas as pd

    if args.csv_file:
        df = pd.read_csv(args.csv_file)
    else:
        # Try default location
        default_csv = Path(args.data_directory) / "paleowells.csv"
        if not default_csv.exists():
            logger.info(
                "Error: No CSV file found. Please specify with --csv-file or run process command first."
            )
            sys.exit(1)
        df = pd.read_csv(default_csv)

    logger.info(f"Loaded {len(df)} records for visualization")

    # Create output directory
    output_dir = (
        Path(args.output_directory)
        if args.output_directory
        else Path.cwd() / "paleowells_figures"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.report:
        # Generate comprehensive report
        figures = visualizer.create_comprehensive_report(df, output_dir)
        logger.info(f"\nGenerated {len(figures)} figures in {output_dir}")
        for name, path in figures.items():
            logger.info(f"  - {name}: {path}")
    else:
        # Generate individual plots based on options
        if args.epochs:
            fig = visualizer.plot_wells_by_epoch(df, output_dir / "wells_by_epoch.png")
            logger.info("Created epoch distribution plot")

        if args.depth:
            fig = visualizer.plot_depth_distribution(
                df,
                depth_type=args.depth_type,
                save_path=output_dir
                / f"{args.depth_type.lower().replace(' ', '_')}_distribution.png",
            )
            logger.info("Created depth distribution plot")

        if args.classification:
            fig = visualizer.plot_classification_pie(
                df, output_dir / "classification.png"
            )
            logger.info("Created classification pie chart")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BSEE Paleowells Data Processing and Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Process command
    process_parser = subparsers.add_parser("process", help="Process paleowells data")
    process_parser.add_argument(
        "--input-file", "-i", help="Input file with raw paleo data"
    )
    process_parser.add_argument(
        "--data-directory",
        "-d",
        default="data/modules/bsee/paleowells",
        help="Data directory (default: data/modules/bsee/paleowells)",
    )
    process_parser.add_argument(
        "--output-directory", "-o", help="Output directory for processed files"
    )
    process_parser.add_argument(
        "--analyze",
        "-a",
        action="store_true",
        help="Perform analysis on processed data",
    )

    # Download command
    download_parser = subparsers.add_parser("download", help="Download BSEE/BOEM data")
    download_parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["borehole", "company", "lease_owner", "production", "field"],
        help="Specific datasets to download",
    )
    download_parser.add_argument(
        "--data-directory",
        "-d",
        default="data/modules/bsee/downloads",
        help="Directory to store downloads",
    )
    download_parser.add_argument(
        "--extract",
        "-e",
        action="store_true",
        default=True,
        help="Extract ZIP files after download",
    )
    download_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing files"
    )
    download_parser.add_argument(
        "--info",
        action="store_true",
        help="Show available datasets without downloading",
    )

    # Visualize command
    viz_parser = subparsers.add_parser("visualize", help="Visualize paleowells data")
    viz_parser.add_argument(
        "--csv-file", "-f", help="CSV file with processed paleo data"
    )
    viz_parser.add_argument(
        "--data-directory",
        "-d",
        default="data/modules/bsee/paleowells",
        help="Data directory",
    )
    viz_parser.add_argument(
        "--output-directory", "-o", help="Output directory for figures"
    )
    viz_parser.add_argument(
        "--report",
        "-r",
        action="store_true",
        help="Generate comprehensive visual report",
    )
    viz_parser.add_argument("--epochs", action="store_true", help="Plot wells by epoch")
    viz_parser.add_argument(
        "--depth", action="store_true", help="Plot depth distribution"
    )
    viz_parser.add_argument(
        "--depth-type",
        choices=["True Vertical Depth", "Measured Depth"],
        default="True Vertical Depth",
        help="Type of depth to plot",
    )
    viz_parser.add_argument(
        "--classification", action="store_true", help="Plot classification pie chart"
    )

    # Parse arguments
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Execute command
    if args.command == "process":
        process_command(args)
    elif args.command == "download":
        download_command(args)
    elif args.command == "visualize":
        visualize_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
