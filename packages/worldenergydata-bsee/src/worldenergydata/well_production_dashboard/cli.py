"""
Command-line interface for Well Production Dashboard.

Extends verification CLI patterns and provides dashboard management capabilities.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml

from worldenergydata.common import get_logger
from worldenergydata.common.logging import configure_logging

from .export_manager import ExportConfiguration
from .well_production import WellDashboardConfig, WellProductionDashboard


def setup_logging(verbose: bool):
    """Set up logging configuration."""
    level = "DEBUG" if verbose else "INFO"
    configure_logging(level=level)


logger = get_logger(__name__)


class DashboardCLI:
    """Command-line interface for dashboard operations."""

    def __init__(self):
        """Initialize CLI."""
        self.dashboard = None
        self.config = None

    def run(self, config_path: Optional[str] = None):
        """Run the dashboard."""
        if config_path:
            self.dashboard = WellProductionDashboard.from_yaml(config_path)
        else:
            self.dashboard = WellProductionDashboard()

        return self.dashboard.run()

    def configure(self, config_dict: Dict[str, Any]):
        """Configure the dashboard."""
        self.config = WellDashboardConfig(**config_dict)
        self.dashboard = WellProductionDashboard(self.config)

    def export(
        self,
        format: str = "pdf",
        output_path: Optional[str] = None,
        config: Optional[ExportConfiguration] = None,
    ):
        """Export dashboard with comprehensive report integration."""
        if not self.dashboard:
            raise ValueError("Dashboard not initialized")

        # Use provided config or create default
        if config is None:
            config = ExportConfiguration(formats=[format])

        # Export using new export manager
        base_path = (
            str(Path(output_path).with_suffix(""))
            if output_path
            else "dashboard_export"
        )
        results = self.dashboard.export_dashboard(base_path, config)

        # Return first result for backward compatibility
        if results:
            return results[0]

        return None

    def serve(self, *args, **kwargs):
        """Backward-compatible alias for running the dashboard server."""
        return self.run(*args, **kwargs)

    def report(self, wells=None, format: str = "pdf", output: Optional[str] = None):
        """Generate a dashboard report via the underlying dashboard/exporter."""
        if not self.dashboard:
            self.dashboard = WellProductionDashboard()

        output_path = output or f"well_dashboard_report.{format}"
        if hasattr(self.dashboard, "export_to_pdf") and format == "pdf":
            return self.dashboard.export_to_pdf(wells=wells, output_path=output_path)
        return self.export(format=format, output_path=output_path)

    def verify(self, well_id: Optional[str] = None):
        """Run dashboard data quality verification."""
        if not self.dashboard:
            self.dashboard = WellProductionDashboard()
        well_ids = [well_id] if well_id else None
        return self.dashboard.verify_data_quality(well_ids)

    def cache(self, *args, **kwargs):
        """Return dashboard cache manager for CLI compatibility."""
        if not self.dashboard:
            self.dashboard = WellProductionDashboard()
        return getattr(self.dashboard, "cache_manager", None)

    def monitor(self, *args, **kwargs):
        """Return dashboard monitor status for CLI compatibility."""
        return {"status": "available"}

    def get_export_parameters(self) -> Dict[str, Any]:
        """Get available export parameters."""
        return {
            "format": ["pdf", "excel", "json", "all"],
            "include_verification": "Include verification metadata",
            "include_charts": "Include charts and visualizations",
            "include_raw_data": "Include raw data tables",
            "include_field_aggregation": "Include field-level aggregations",
            "output_path": "Path to save export files",
        }


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Configuration file path"
)
@click.pass_context
def cli(ctx, verbose, config):
    """Well Production Dashboard CLI - Interactive dashboard for well analysis."""
    setup_logging(verbose)

    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config

    if config:
        logger.info(f"Using configuration from: {config}")


@cli.command()
@click.option("--port", "-p", default=8050, help="Port to run dashboard on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to run dashboard on")
@click.option("--debug", is_flag=True, help="Run in debug mode")
@click.option("--real-time", is_flag=True, help="Enable real-time updates")
@click.pass_context
def run(ctx, port, host, debug, real_time):
    """Run the interactive dashboard server."""
    config_path = ctx.obj.get("config")

    # Create dashboard
    if config_path:
        dashboard = WellProductionDashboard.from_yaml(config_path)
    else:
        dashboard = WellProductionDashboard()

    # Enable real-time if requested
    if real_time:
        dashboard.enable_real_time_updates()
        click.echo("Real-time updates enabled")

    # Run dashboard
    click.echo(f"Starting dashboard on http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")

    try:
        dashboard.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        click.echo("\nDashboard stopped")
    except Exception as e:
        click.echo(f"Error running dashboard: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("well_ids", nargs=-1, required=True)
@click.option(
    "--start-date", "-s", type=click.DateTime(), help="Start date for analysis"
)
@click.option("--end-date", "-e", type=click.DateTime(), help="End date for analysis")
@click.option("--verify", is_flag=True, help="Run verification on data")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.pass_context
def analyze(ctx, well_ids, start_date, end_date, verify, output):
    """Analyze specific wells."""
    config_path = ctx.obj.get("config")

    # Create dashboard
    if config_path:
        dashboard = WellProductionDashboard.from_yaml(config_path)
    else:
        dashboard = WellProductionDashboard()

    results = {}

    for well_id in well_ids:
        click.echo(f"Analyzing well: {well_id}")

        # Get well data (placeholder - would load from database)
        # well_data = load_well_data(well_id, start_date, end_date)

        # Create metrics
        metrics = dashboard.create_economic_metrics(well_id)
        decline = dashboard.create_decline_curve(well_id)

        # Verify if requested
        if verify:
            verification = dashboard.verify_well_data(None)  # Would pass actual data
            metrics["verification"] = verification

        results[well_id] = {
            "metrics": metrics,
            "decline_analysis": decline,
            "timestamp": datetime.now().isoformat(),
        }

        # Display results
        click.echo(f"  NPV: ${metrics.get('npv', 0):,.2f}")
        click.echo(f"  Total Revenue: ${metrics.get('total_revenue', 0):,.2f}")
        click.echo(f"  Decline Rate: {decline.get('decline_rate', 0):.2%}")

        if verify:
            quality = verification.get("quality_score", 0)
            status = verification.get("status", "unknown")
            click.echo(f"  Verification Status: {status}")
            click.echo(f"  Quality Score: {quality:.2f}")

    # Save results if output specified
    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        click.echo(f"Results saved to: {output}")


@cli.command()
@click.argument("format", type=click.Choice(["pdf", "excel", "json", "all"]))
@click.option(
    "--output", "-o", type=click.Path(), required=True, help="Output file path"
)
@click.option("--wells", "-w", multiple=True, help="Wells to include")
@click.option("--start-date", "-s", type=click.DateTime(), help="Start date")
@click.option("--end-date", "-e", type=click.DateTime(), help="End date")
@click.option(
    "--include-verification", is_flag=True, help="Include verification results"
)
@click.option(
    "--include-charts", is_flag=True, default=True, help="Include charts in export"
)
@click.option(
    "--include-raw-data", is_flag=True, default=False, help="Include raw data"
)
@click.option(
    "--include-field-aggregation", is_flag=True, help="Include field aggregation"
)
@click.pass_context
def export(
    ctx,
    format,
    output,
    wells,
    start_date,
    end_date,
    include_verification,
    include_charts,
    include_raw_data,
    include_field_aggregation,
):
    """Export dashboard to file with comprehensive report integration."""
    config_path = ctx.obj.get("config")

    # Create dashboard
    if config_path:
        dashboard = WellProductionDashboard.from_yaml(config_path)
    else:
        dashboard = WellProductionDashboard()

    # Determine formats
    if format == "all":
        formats = ["pdf", "excel", "json"]
        click.echo("Exporting dashboard to all formats (PDF, Excel, JSON)...")
    else:
        formats = [format]
        click.echo(f"Exporting dashboard to {format.upper()}...")

    # Apply filters if specified
    if wells:
        dashboard.add_filter("wells", list(wells))
    if start_date and end_date:
        dashboard.add_filter("date_range", [start_date, end_date])

    # Configure export options
    export_config = ExportConfiguration(
        formats=formats,
        include_verification=include_verification,
        include_charts=include_charts,
        include_raw_data=include_raw_data,
        include_field_aggregation=include_field_aggregation,
        wells_filter=list(wells) if wells else None,
        date_range=(start_date, end_date) if start_date and end_date else None,
    )

    try:
        # Export dashboard using new export manager
        base_path = str(Path(output).with_suffix(""))
        results = dashboard.export_dashboard(base_path, export_config)

        # Display results
        click.echo("\nExport Results:")
        for result in results:
            if result.success:
                click.echo(f"  ✓ {result.format.upper()}: {result.file_path}")
                if result.file_size:
                    size_mb = result.file_size / (1024 * 1024)
                    click.echo(f"    Size: {size_mb:.2f} MB")
            else:
                click.echo(
                    f"  ✗ {result.format.upper()}: Failed - {result.error_message}"
                )

        # Summary
        successful = sum(1 for r in results if r.success)
        total = len(results)
        click.echo(f"\nExported {successful}/{total} formats successfully")

    except Exception as e:
        click.echo(f"Export failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("field_name")
@click.option("--compare-to", "-c", help="Field to compare against")
@click.option("--metric", "-m", default="production", help="Metric to analyze")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.pass_context
def field(ctx, field_name, compare_to, metric, output):
    """Analyze field-level aggregated data."""
    config_path = ctx.obj.get("config")

    # Create dashboard
    if config_path:
        WellProductionDashboard.from_yaml(config_path)
    else:
        WellProductionDashboard()

    click.echo(f"Analyzing field: {field_name}")

    # Get field data (placeholder - would load from database)
    # field_data = load_field_data(field_name)

    # Perform field analysis
    from .well_production import FieldAggregator

    FieldAggregator()

    # Display field summary
    click.echo(f"Field: {field_name}")
    click.echo(f"Metric: {metric}")
    # click.echo(f"Total Wells: {field_summary['well_count']}")
    # click.echo(f"Total Production: {field_summary['total_production']:,.0f} bbl")

    if compare_to:
        click.echo(f"\nComparing to field: {compare_to}")
        # comparison = aggregator.compare_fields(field_data, compare_field_data)
        # click.echo(f"Performance Ratio: {comparison['performance_ratio']:.2f}")
        # click.echo(f"Trend Difference: {comparison['trend_comparison']:.2f}")

    # Save results if output specified
    if output:
        results = {
            "field": field_name,
            "metric": metric,
            "compare_to": compare_to,
            "timestamp": datetime.now().isoformat(),
        }
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        click.echo(f"Results saved to: {output}")


@cli.command()
@click.option("--cache-ttl", type=int, help="Cache TTL in seconds")
@click.option("--quality-threshold", type=float, help="Quality threshold (0-1)")
@click.option(
    "--enable-verification/--disable-verification",
    default=True,
    help="Enable verification",
)
@click.option(
    "--enable-real-time/--disable-real-time",
    default=False,
    help="Enable real-time updates",
)
@click.option("--save", "-s", type=click.Path(), help="Save configuration to file")
@click.pass_context
def configure(
    ctx, cache_ttl, quality_threshold, enable_verification, enable_real_time, save
):
    """Configure dashboard settings."""
    config = {}

    if cache_ttl:
        config["cache_ttl"] = cache_ttl
    if quality_threshold:
        config["quality_threshold"] = quality_threshold
    config["enable_verification"] = enable_verification
    config["enable_real_time"] = enable_real_time

    click.echo("Dashboard configuration:")
    for key, value in config.items():
        click.echo(f"  {key}: {value}")

    if save:
        dashboard_config = {"dashboard": config}
        with open(save, "w") as f:
            yaml.dump(dashboard_config, f)
        click.echo(f"Configuration saved to: {save}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show dashboard status and metrics."""
    config_path = ctx.obj.get("config")

    # Create dashboard
    if config_path:
        dashboard = WellProductionDashboard.from_yaml(config_path)
    else:
        dashboard = WellProductionDashboard()

    # Get performance metrics
    metrics = dashboard.get_performance_metrics()

    click.echo("Dashboard Status")
    click.echo("=" * 40)
    click.echo(f"Configuration: {config_path or 'Default'}")
    click.echo(f"Verification Enabled: {dashboard.verification_enabled}")
    click.echo(f"Real-time Enabled: {dashboard.real_time_enabled}")
    click.echo(f"Cache TTL: {dashboard.cache_ttl}s")
    click.echo(f"Quality Threshold: {dashboard.quality_threshold}")

    click.echo("\nPerformance Metrics")
    click.echo("-" * 40)
    click.echo(f"Cache Hit Rate: {metrics['cache_hit_rate']:.2%}")
    click.echo(f"Cache Hits: {metrics['cache_hits']}")
    click.echo(f"Total Requests: {metrics['total_requests']}")
    click.echo(f"Memory Usage: {metrics['memory_usage']:.2f} MB")

    # Show API endpoints
    endpoints = dashboard.get_api_endpoints()
    click.echo("\nAvailable API Endpoints")
    click.echo("-" * 40)
    for endpoint in endpoints:
        click.echo(f"  {endpoint}")


@cli.command()
@click.argument("well_id")
@click.pass_context
def verify(ctx, well_id):
    """Verify data quality for a specific well."""
    config_path = ctx.obj.get("config")

    # Create dashboard
    if config_path:
        dashboard = WellProductionDashboard.from_yaml(config_path)
    else:
        dashboard = WellProductionDashboard()

    click.echo(f"Verifying data for well: {well_id}")

    # Run verification (placeholder - would load actual data)
    # well_data = load_well_data(well_id)
    # verification_results = dashboard.verify_well_data(well_data)

    # Display verification results
    # click.echo(f"Status: {verification_results['status']}")
    # click.echo(f"Quality Score: {verification_results['quality_score']:.2f}")

    # if verification_results.get('anomalies'):
    #     click.echo("\nAnomalies Detected:")
    #     for anomaly in verification_results['anomalies']:
    #         click.echo(f"  - {anomaly}")

    # Get quality indicators
    indicators = dashboard.get_quality_indicators(well_id)
    click.echo(f"\nQuality Indicator: {indicators['indicator_color'].upper()}")

    # Get audit trail
    audit_trail = dashboard.get_audit_trail(well_id)
    if not audit_trail.empty:
        click.echo("\nRecent Audit Trail:")
        for _, entry in audit_trail.head(5).iterrows():
            click.echo(
                f"  {entry.get('timestamp', 'N/A')}: {entry.get('action', 'N/A')}"
            )


@cli.command()
@click.option(
    "--output", "-o", type=click.Path(), required=True, help="Output file path"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["pdf", "excel", "json", "all"]),
    default="pdf",
    help="Export format",
)
@click.option("--wells", "-w", multiple=True, help="Wells to include in report")
@click.option(
    "--quality-threshold", type=float, help="Minimum quality score to include"
)
@click.pass_context
def verification_report(ctx, output, format, wells, quality_threshold):
    """Export comprehensive verification report with audit trails."""
    config_path = ctx.obj.get("config")

    # Create dashboard
    if config_path:
        dashboard = WellProductionDashboard.from_yaml(config_path)
    else:
        dashboard = WellProductionDashboard()

    click.echo("Generating verification report...")

    # Configure export for verification focus
    ExportConfiguration(
        formats=[format] if format != "all" else ["pdf", "excel", "json"],
        include_verification=True,
        include_charts=True,
        include_raw_data=False,
        include_field_aggregation=False,
        wells_filter=list(wells) if wells else None,
        quality_threshold=quality_threshold,
    )

    try:
        # Export with verification focus
        base_path = str(Path(output).with_suffix(""))
        results = dashboard.export_with_verification(base_path)

        # Display results
        click.echo("\nVerification Report Export Results:")
        for result in results:
            if result.success:
                click.echo(f"  ✓ {result.format.upper()}: {result.file_path}")
            else:
                click.echo(
                    f"  ✗ {result.format.upper()}: Failed - {result.error_message}"
                )

        # Display verification summary
        metadata = dashboard._get_verification_metadata()
        click.echo("\nVerification Summary:")
        click.echo(f"  Quality Score: {metadata.quality_score:.2%}")
        click.echo(f"  Status: {metadata.verification_status}")
        click.echo(f"  Anomalies: {metadata.anomalies_detected}")
        click.echo(f"  Completeness: {metadata.data_completeness:.2%}")

    except Exception as e:
        click.echo(f"Verification report export failed: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
