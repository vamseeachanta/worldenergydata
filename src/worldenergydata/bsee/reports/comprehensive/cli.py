"""
Command-line interface for comprehensive BSEE report generation
Provides easy access to hierarchical reporting functionality
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from worldenergydata.common import get_logger
from worldenergydata.common.logging import configure_logging

from .hierarchical_aggregator import CostStructure, HierarchicalAggregator, PriceDeck
from .report_builder import GoByReportBuilder

# Configure logging with common layer
configure_logging()
logger = get_logger(__name__)


class ReportCLI:
    """Command-line interface for comprehensive report generation"""

    def __init__(self):
        """Initialize CLI"""
        self.parser = self._create_parser()
        self.aggregator = None
        self.report_builder = None

    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create argument parser with comprehensive options

        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            prog="bsee-reports",
            description="Generate comprehensive BSEE well and production reports",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Generate block report for Block 759
  %(prog)s --type block --id 759 --format excel --output ./reports

  # Generate field report with custom price deck
  %(prog)s --type field --id Jack --oil-price 80 --gas-price 4.0

  # Generate multiple lease reports
  %(prog)s --type lease --ids OCS-G-12345,OCS-G-12346 --format pdf

  # Use configuration file
  %(prog)s --config report_config.yaml

  # Generate report with progress bar
  %(prog)s --type block --id 525 --progress --verbose
            """,
        )

        # Report type and entity
        parser.add_argument(
            "--type",
            "-t",
            choices=["block", "field", "lease", "well"],
            default="field",
            help="Type of report to generate (default: field)",
        )

        parser.add_argument(
            "--id",
            "-i",
            type=str,
            help="Single entity identifier (block number, field name, or lease number)",
        )

        parser.add_argument(
            "--ids", type=str, help="Multiple entity identifiers (comma-separated)"
        )

        # Output options
        parser.add_argument(
            "--format",
            "-f",
            choices=["excel", "pdf", "html", "json", "all"],
            default="excel",
            help="Output format (default: excel)",
        )

        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default="./reports",
            help="Output directory (default: ./reports)",
        )

        parser.add_argument(
            "--filename",
            type=str,
            help="Custom output filename (auto-generated if not specified)",
        )

        # Price deck options
        parser.add_argument(
            "--oil-price",
            type=float,
            default=75.00,
            help="Oil price per barrel (default: 75.00)",
        )

        parser.add_argument(
            "--gas-price",
            type=float,
            default=3.50,
            help="Gas price per MCF (default: 3.50)",
        )

        parser.add_argument(
            "--ngl-price",
            type=float,
            default=30.00,
            help="NGL price per barrel (default: 30.00)",
        )

        # Cost structure options
        parser.add_argument(
            "--operating-cost",
            type=float,
            default=12.50,
            help="Operating cost per BOE (default: 12.50)",
        )

        parser.add_argument(
            "--royalty-rate",
            type=float,
            default=0.1875,
            help="Royalty rate (default: 0.1875)",
        )

        parser.add_argument(
            "--tax-rate",
            type=float,
            default=0.05,
            help="Severance tax rate (default: 0.05)",
        )

        # Configuration file
        parser.add_argument(
            "--config", "-c", type=str, help="YAML configuration file path"
        )

        # Processing options
        parser.add_argument(
            "--batch",
            action="store_true",
            help="Enable batch processing for multiple entities",
        )

        parser.add_argument(
            "--parallel",
            type=int,
            default=1,
            help="Number of parallel workers for batch processing (default: 1)",
        )

        parser.add_argument(
            "--cache",
            action="store_true",
            help="Enable data caching for improved performance",
        )

        # Display options
        parser.add_argument(
            "--progress",
            action="store_true",
            help="Show progress bar during generation",
        )

        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose logging"
        )

        parser.add_argument(
            "--quiet",
            "-q",
            action="store_true",
            help="Suppress all output except errors",
        )

        # Data source options
        parser.add_argument("--data-path", type=str, help="Path to BSEE data directory")

        parser.add_argument(
            "--refresh-data",
            action="store_true",
            help="Force refresh of BSEE data before generating report",
        )

        return parser

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        logger.info(f"Loading configuration from {config_path}")

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        return config

    def merge_args_with_config(
        self, args: argparse.Namespace, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge command-line arguments with configuration file

        Args:
            args: Parsed command-line arguments
            config: Configuration from file

        Returns:
            Merged configuration dictionary
        """
        # Convert args to dictionary
        args_dict = vars(args)

        # Command-line args override config file
        for key, value in args_dict.items():
            if value is not None:
                config[key] = value

        return config

    def initialize_components(self, config: Dict[str, Any]):
        """
        Initialize report generation components

        Args:
            config: Configuration dictionary
        """
        # Create price deck
        price_deck = PriceDeck(
            oil_price=config.get("oil_price", 75.00),
            gas_price=config.get("gas_price", 3.50),
            ngl_price=config.get("ngl_price", 30.00),
        )

        # Create cost structure
        cost_structure = CostStructure(
            operating_cost_per_bbl=config.get("operating_cost", 12.50),
            royalty_rate=config.get("royalty_rate", 0.1875),
            severance_tax_rate=config.get("tax_rate", 0.05),
        )

        # Initialize aggregator
        self.aggregator = HierarchicalAggregator(
            price_deck=price_deck, cost_structure=cost_structure
        )

        # Initialize report builder
        self.report_builder = GoByReportBuilder(aggregator=self.aggregator)

        logger.info("Components initialized successfully")

    def generate_single_report(
        self,
        report_type: str,
        entity_id: str,
        output_format: str,
        output_path: Path,
        config: Dict[str, Any],
    ) -> Path:
        """
        Generate a single report

        Args:
            report_type: Type of report
            entity_id: Entity identifier
            output_format: Output format
            output_path: Output directory
            config: Configuration dictionary

        Returns:
            Path to generated report
        """
        logger.info(f"Generating {report_type} report for {entity_id}")

        # Build report
        report = self.report_builder.build_report(
            report_type=report_type, entity_identifier=entity_id, cfg=config
        )

        # Export based on format
        if output_format == "excel":
            report_path = self.report_builder.export_to_excel(
                report=report, output_path=output_path, filename=config.get("filename")
            )
        elif output_format == "json":
            report_path = self.export_to_json(report, output_path, entity_id)
        elif output_format == "html":
            report_path = self.export_to_html(report, output_path, entity_id)
        elif output_format == "pdf":
            report_path = self.export_to_pdf(report, output_path, entity_id)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

        logger.info(f"Report generated: {report_path}")
        return report_path

    def generate_batch_reports(
        self,
        report_type: str,
        entity_ids: List[str],
        output_format: str,
        output_path: Path,
        config: Dict[str, Any],
    ) -> List[Path]:
        """
        Generate multiple reports in batch

        Args:
            report_type: Type of report
            entity_ids: List of entity identifiers
            output_format: Output format
            output_path: Output directory
            config: Configuration dictionary

        Returns:
            List of paths to generated reports
        """
        logger.info(f"Generating {len(entity_ids)} reports in batch mode")

        report_paths = []
        total = len(entity_ids)

        for idx, entity_id in enumerate(entity_ids, 1):
            if config.get("progress"):
                print(f"Processing {idx}/{total}: {entity_id}")

            try:
                report_path = self.generate_single_report(
                    report_type=report_type,
                    entity_id=entity_id,
                    output_format=output_format,
                    output_path=output_path,
                    config=config,
                )
                report_paths.append(report_path)

            except Exception as e:
                logger.error(f"Failed to generate report for {entity_id}: {e}")
                if not config.get("continue_on_error", True):
                    raise

        logger.info(
            f"Batch generation complete: {len(report_paths)}/{total} successful"
        )
        return report_paths

    def export_to_json(
        self, report: Dict[str, Any], output_path: Path, entity_id: str
    ) -> Path:
        """
        Export report to JSON format

        Args:
            report: Report data
            output_path: Output directory
            entity_id: Entity identifier

        Returns:
            Path to JSON file
        """
        output_path.mkdir(parents=True, exist_ok=True)
        filename = f"{report['metadata']['report_type']}_{entity_id}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = output_path / filename

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return filepath

    def export_to_html(
        self, report: Dict[str, Any], output_path: Path, entity_id: str
    ) -> Path:
        """
        Export report to HTML format

        Args:
            report: Report data
            output_path: Output directory
            entity_id: Entity identifier

        Returns:
            Path to HTML file
        """
        output_path.mkdir(parents=True, exist_ok=True)
        filename = f"{report['metadata']['report_type']}_{entity_id}_{datetime.now().strftime('%Y%m%d')}.html"
        filepath = output_path / filename

        # Create simple HTML report
        html_content = self._generate_html_report(report)

        with open(filepath, "w") as f:
            f.write(html_content)

        return filepath

    def export_to_pdf(
        self, report: Dict[str, Any], output_path: Path, entity_id: str
    ) -> Path:
        """
        Export report to PDF format

        Args:
            report: Report data
            output_path: Output directory
            entity_id: Entity identifier

        Returns:
            Path to PDF file
        """
        # For now, return a placeholder
        # Full PDF generation would require additional libraries
        logger.warning("PDF export not fully implemented, generating JSON instead")
        return self.export_to_json(report, output_path, entity_id)

    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """
        Generate HTML content for report

        Args:
            report: Report data

        Returns:
            HTML string
        """
        metadata = report.get("metadata", {})
        summary = report.get("summary", {})

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{metadata.get('report_type', '').upper()} Report - {metadata.get('entity', '')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ margin: 10px 0; }}
                .metric-label {{ font-weight: bold; }}
                .metric-value {{ margin-left: 10px; }}
            </style>
        </head>
        <body>
            <h1>{metadata.get('report_type', '').upper()} Report</h1>
            <h2>Entity: {metadata.get('entity', '')}</h2>
            <p>Generated: {metadata.get('generated_date', '')} {metadata.get('generated_time', '')}</p>

            <h2>Summary</h2>
        """

        for key, value in summary.items():
            html += f'<div class="metric"><span class="metric-label">{key.replace("_", " ").title()}:</span>'
            html += f'<span class="metric-value">{value}</span></div>\n'

        html += """
        </body>
        </html>
        """

        return html

    def run(self, argv: Optional[List[str]] = None) -> int:
        """
        Run the CLI application

        Args:
            argv: Command-line arguments (None uses sys.argv)

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            # Parse arguments
            args = self.parser.parse_args(argv)

            # Set logging level
            if args.quiet:
                logging.getLogger().setLevel(logging.ERROR)
            elif args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)

            # Load configuration
            config = {}
            if args.config:
                config = self.load_config(args.config)

            # Merge args with config
            config = self.merge_args_with_config(args, config)

            # Validate inputs
            if not config.get("id") and not config.get("ids"):
                self.parser.error("Either --id or --ids must be specified")

            # Initialize components
            self.initialize_components(config)

            # Prepare output path
            output_path = Path(config.get("output", "./reports"))
            output_path.mkdir(parents=True, exist_ok=True)

            # Generate reports
            if config.get("ids"):
                # Batch processing
                entity_ids = config["ids"].split(",")
                report_paths = self.generate_batch_reports(
                    report_type=config["type"],
                    entity_ids=entity_ids,
                    output_format=config["format"],
                    output_path=output_path,
                    config=config,
                )

                print(f"\n✅ Generated {len(report_paths)} reports:")
                for path in report_paths:
                    print(f"  - {path}")

            else:
                # Single report
                report_path = self.generate_single_report(
                    report_type=config["type"],
                    entity_id=config["id"],
                    output_format=config["format"],
                    output_path=output_path,
                    config=config,
                )

                print("\n✅ Report generated successfully:")
                print(f"  {report_path}")

            return 0

        except KeyboardInterrupt:
            print("\n⚠️ Operation cancelled by user")
            return 130

        except Exception as e:
            logger.error(
                f"Error: {e}", exc_info=args.verbose if "args" in locals() else False
            )
            print(f"\n❌ Error: {e}")
            return 1


def main():
    """Main entry point"""
    cli = ReportCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
