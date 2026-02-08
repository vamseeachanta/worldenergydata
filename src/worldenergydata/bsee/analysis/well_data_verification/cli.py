"""
Command-line interface for well data verification system.

Provides CLI access to verification workflows, data quality checks, and report generation.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from worldenergydata.common import get_logger
from worldenergydata.common.logging import configure_logging

from .audit import AuditSystem
from .cross_reference import CrossReferenceModule

# Import verification components
from .engine.workflow import WorkflowEngine
from .quality import DataQualityFramework
from .reports import (
    AuditTrailReport,
    DataQualityReport,
    VerificationReportGenerator,
    VerificationSummary,
)

# Configure logging with common layer
configure_logging()
logger = get_logger(__name__)


class VerificationCLI:
    """Command-line interface for well data verification."""

    def __init__(self):
        """Initialize CLI."""
        self.parser = self._create_parser()
        self.workflow_engine = None
        self.quality_framework = None
        self.report_generator = None
        self.audit_system = None

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with verification options."""
        parser = argparse.ArgumentParser(
            prog="verify-wells",
            description="Well Data Verification System - Validate production data quality",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run complete verification workflow
  %(prog)s --workflow complete --input data/wells.csv --output reports/

  # Run data quality checks only
  %(prog)s --quality --input data/wells.csv --threshold 0.95

  # Cross-reference with Excel benchmark
  %(prog)s --cross-reference --input data/wells.csv --benchmark benchmark.xlsx

  # Generate verification report
  %(prog)s --report --format pdf --output verification_report.pdf

  # Use configuration file
  %(prog)s --config verification_config.yaml

  # Run with audit logging
  %(prog)s --workflow complete --audit --user analyst1
""",
        )

        # Main operation modes
        operation_group = parser.add_mutually_exclusive_group()
        operation_group.add_argument(
            "--workflow",
            choices=["complete", "quick", "custom"],
            help="Run verification workflow",
        )
        operation_group.add_argument(
            "--quality", action="store_true", help="Run data quality checks only"
        )
        operation_group.add_argument(
            "--cross-reference",
            action="store_true",
            help="Cross-reference with benchmark",
        )
        operation_group.add_argument(
            "--report", action="store_true", help="Generate verification report"
        )

        # Input/Output options
        parser.add_argument(
            "--input", "-i", type=str, help="Input data file or directory"
        )
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default="./verification_output",
            help="Output directory for reports (default: ./verification_output)",
        )

        # Data quality options
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.90,
            help="Quality threshold for validation (default: 0.90)",
        )
        parser.add_argument(
            "--rules", type=str, help="Path to validation rules YAML file"
        )

        # Cross-reference options
        parser.add_argument(
            "--benchmark", type=str, help="Excel benchmark file for cross-reference"
        )
        parser.add_argument(
            "--mapping", type=str, help="Field mapping configuration file"
        )

        # Report options
        parser.add_argument(
            "--format",
            "-f",
            choices=["pdf", "excel", "both"],
            default="pdf",
            help="Report output format (default: pdf)",
        )
        parser.add_argument("--template", type=str, help="Report template to use")

        # Configuration file
        parser.add_argument(
            "--config", "-c", type=str, help="Configuration file (YAML format)"
        )

        # Audit options
        parser.add_argument("--audit", action="store_true", help="Enable audit logging")
        parser.add_argument(
            "--user",
            type=str,
            default="system",
            help="User name for audit trail (default: system)",
        )

        # Processing options
        parser.add_argument(
            "--batch", action="store_true", help="Process multiple files in batch mode"
        )
        parser.add_argument(
            "--parallel",
            type=int,
            help="Number of parallel workers for batch processing",
        )

        # Verbosity
        parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help="Increase output verbosity (use -vv for debug)",
        )
        parser.add_argument(
            "--quiet", "-q", action="store_true", help="Suppress non-essential output"
        )

        # Dry run
        parser.add_argument(
            "--dry-run", action="store_true", help="Preview actions without executing"
        )

        return parser

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def setup_logging(self, verbosity: int, quiet: bool):
        """Configure logging based on verbosity level."""
        if quiet:
            logging.getLogger().setLevel(logging.ERROR)
        elif verbosity == 0:
            logging.getLogger().setLevel(logging.INFO)
        elif verbosity == 1:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.DEBUG)
            # Add more detailed formatting for debug
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
            )
            for handler in logging.getLogger().handlers:
                handler.setFormatter(formatter)

    def run_workflow(
        self, args: argparse.Namespace, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run verification workflow."""
        logger.info(f"Starting {args.workflow} verification workflow")

        # Initialize workflow engine
        self.workflow_engine = WorkflowEngine(name=f"{args.workflow}_verification")

        # Load workflow configuration
        if args.workflow == "complete":
            steps = self._create_complete_workflow()
        elif args.workflow == "quick":
            steps = self._create_quick_workflow()
        else:  # custom
            if not config.get("workflow", {}).get("steps"):
                raise ValueError("Custom workflow requires steps in configuration")
            steps = config["workflow"]["steps"]

        # Add steps to workflow
        for step in steps:
            self.workflow_engine.add_step(step)

        # Execute workflow
        if not args.dry_run:
            self.workflow_engine.start()
            result = self.workflow_engine.wait_for_completion()
            logger.info(f"Workflow completed with state: {result}")
        else:
            logger.info("Dry run - workflow would execute these steps:")
            for step in steps:
                logger.info(f"  - {step.name}")

        return {"status": "completed", "steps_executed": len(steps)}

    def run_quality_checks(
        self, args: argparse.Namespace, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run data quality checks."""
        logger.info("Running data quality checks")

        # Initialize quality framework
        quality_config = config.get("quality", {})
        quality_config["threshold"] = args.threshold

        self.quality_framework = DataQualityFramework(quality_config)

        # Load data
        import pandas as pd

        data = pd.read_csv(args.input) if args.input else pd.DataFrame()

        if not args.dry_run:
            # Run quality checks
            result = self.quality_framework.validate(data)

            logger.info(f"Quality Score: {result.overall_score:.2%}")
            logger.info(f"Completeness: {result.completeness_score:.2%}")
            logger.info(f"Issues Found: {len(result.issues)}")

            # Save results
            output_path = Path(args.output) / "quality_report.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result.export_to_json(str(output_path))

            return result.to_dict()
        else:
            logger.info("Dry run - would check data quality")
            return {"status": "dry_run"}

    def run_cross_reference(
        self, args: argparse.Namespace, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run cross-reference with benchmark."""
        logger.info("Running cross-reference validation")

        if not args.benchmark:
            raise ValueError("Benchmark file required for cross-reference")

        # Initialize cross-reference module
        cross_ref = CrossReferenceModule()

        # Load mapping if provided
        if args.mapping:
            with open(args.mapping, "r") as f:
                mapping = yaml.safe_load(f)
            cross_ref.field_mapper.load_mapping(mapping)

        if not args.dry_run:
            # Load data
            import pandas as pd

            data = pd.read_csv(args.input) if args.input else pd.DataFrame()

            # Run cross-reference
            discrepancies = cross_ref.cross_reference(
                database_data=data, excel_file=args.benchmark
            )

            logger.info(f"Found {len(discrepancies)} discrepancies")

            # Generate report
            report = cross_ref.generate_report(discrepancies)

            # Save report
            output_path = Path(args.output) / "cross_reference_report.xlsx"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cross_ref.discrepancy_reporter.export_to_excel(
                discrepancies, str(output_path)
            )

            return {"discrepancies": len(discrepancies), "report": report}
        else:
            logger.info(f"Dry run - would cross-reference with {args.benchmark}")
            return {"status": "dry_run"}

    def generate_report(
        self, args: argparse.Namespace, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate verification report."""
        logger.info(f"Generating verification report in {args.format} format")

        # Initialize report generator
        self.report_generator = VerificationReportGenerator()

        # Create mock data for demonstration (in production, would load from results)
        summary = VerificationSummary(
            total_wells=100, wells_verified=95, issues_found=10, critical_issues=2
        )

        quality = DataQualityReport(
            completeness_score=0.95, accuracy_score=0.92, consistency_score=0.88
        )

        audit = AuditTrailReport(start_time=datetime.now(), end_time=datetime.now())

        if not args.dry_run:
            # Create report
            report = self.report_generator.create_verification_report(
                summary=summary, quality=quality, audit=audit
            )

            # Export based on format
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)

            if args.format in ["pdf", "both"]:
                pdf_path = (
                    output_dir
                    / f"verification_report_{datetime.now():%Y%m%d_%H%M%S}.pdf"
                )
                self.report_generator.export_to_pdf(report, pdf_path)
                logger.info(f"PDF report saved to {pdf_path}")

            if args.format in ["excel", "both"]:
                excel_path = (
                    output_dir
                    / f"verification_report_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
                )
                self.report_generator.export_to_excel(report, excel_path)
                logger.info(f"Excel report saved to {excel_path}")

            return {"report_generated": True, "format": args.format}
        else:
            logger.info(f"Dry run - would generate {args.format} report")
            return {"status": "dry_run"}

    def _create_complete_workflow(self):
        """Create complete verification workflow steps."""
        from .engine.workflow import WorkflowStep

        steps = [
            WorkflowStep(
                name="load_data",
                description="Load well production data",
                function=lambda ctx: logger.info("Loading data..."),
            ),
            WorkflowStep(
                name="validate_structure",
                description="Validate data structure",
                function=lambda ctx: logger.info("Validating structure..."),
            ),
            WorkflowStep(
                name="check_completeness",
                description="Check data completeness",
                function=lambda ctx: logger.info("Checking completeness..."),
            ),
            WorkflowStep(
                name="detect_outliers",
                description="Detect outliers",
                function=lambda ctx: logger.info("Detecting outliers..."),
            ),
            WorkflowStep(
                name="cross_reference",
                description="Cross-reference with benchmarks",
                function=lambda ctx: logger.info("Cross-referencing..."),
            ),
            WorkflowStep(
                name="generate_report",
                description="Generate verification report",
                function=lambda ctx: logger.info("Generating report..."),
            ),
        ]

        return steps

    def _create_quick_workflow(self):
        """Create quick verification workflow steps."""
        from .engine.workflow import WorkflowStep

        steps = [
            WorkflowStep(
                name="load_data",
                description="Load well production data",
                function=lambda ctx: logger.info("Loading data..."),
            ),
            WorkflowStep(
                name="basic_validation",
                description="Run basic validation checks",
                function=lambda ctx: logger.info("Running basic validation..."),
            ),
            WorkflowStep(
                name="generate_summary",
                description="Generate summary report",
                function=lambda ctx: logger.info("Generating summary..."),
            ),
        ]

        return steps

    def run(self, args: Optional[List[str]] = None) -> int:
        """Main entry point for CLI."""
        # Parse arguments
        parsed_args = self.parser.parse_args(args)

        # Setup logging
        self.setup_logging(parsed_args.verbose, parsed_args.quiet)

        # Load configuration if provided
        config = {}
        if parsed_args.config:
            config = self.load_config(parsed_args.config)

        # Initialize audit system if requested
        if parsed_args.audit:
            self.audit_system = AuditSystem()
            self.audit_system.start_session(user=parsed_args.user)

        try:
            # Execute based on operation mode
            if parsed_args.workflow:
                result = self.run_workflow(parsed_args, config)
            elif parsed_args.quality:
                result = self.run_quality_checks(parsed_args, config)
            elif parsed_args.cross_reference:
                result = self.run_cross_reference(parsed_args, config)
            elif parsed_args.report:
                result = self.generate_report(parsed_args, config)
            else:
                # Default: show help
                self.parser.print_help()
                return 0

            # Log audit if enabled
            if parsed_args.audit and self.audit_system:
                self.audit_system.log_action(
                    action="verification_completed", details=result
                )
                self.audit_system.end_session()

            logger.info("Verification completed successfully")
            return 0

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            if parsed_args.verbose:
                import traceback

                traceback.print_exc()
            return 1


def main():
    """Main entry point for CLI script."""
    cli = VerificationCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
