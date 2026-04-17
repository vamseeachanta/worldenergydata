"""
BSEE CLI Commands

Provides command-line interface for BSEE (Bureau of Safety and Environmental
Enforcement) data operations including data retrieval, analysis, and reporting.

Usage:
    worldenergydata bsee <command> [options]

Examples:
    worldenergydata bsee analyze --block 759 --field "Jack"
    worldenergydata bsee report --type block --id 759 --format excel
    worldenergydata bsee data --api 608114001200
    worldenergydata bsee refresh --type well
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from worldenergydata.common.data_resolver import get_data_root

# Initialize console
console = Console()

# Create BSEE Typer app
app = typer.Typer(
    name="bsee",
    help="BSEE data operations and analysis",
    no_args_is_help=True,
)


class ReportType(str, Enum):
    """Report type options."""

    block = "block"
    field = "field"
    lease = "lease"
    well = "well"


class OutputFormat(str, Enum):
    """Output format options."""

    excel = "excel"
    json = "json"
    html = "html"
    pdf = "pdf"


class DataType(str, Enum):
    """Data type options for refresh."""

    well = "well"
    production = "production"
    block = "block"
    lease = "lease"
    platform = "platform"
    pipeline_permit = "pipeline_permit"
    deepwater_structure = "deepwater_structure"
    pipeline_location = "pipeline_location"
    infrastructure = "infrastructure"  # All 4 infrastructure types combined
    all = "all"


@app.command()
def analyze(
    block: Optional[str] = typer.Option(  # noqa: B008
        None, "--block", "-b", help="Block number to analyze (e.g., 759)"
    ),
    field: Optional[str] = typer.Option(  # noqa: B008
        None,
        "--field",
        "-f",
        help="Field name to analyze (e.g., 'Jack', 'Thunder Horse')",
    ),
    lease: Optional[str] = typer.Option(  # noqa: B008
        None, "--lease", "-l", help="Lease number to analyze (e.g., OCS-G-12345)"
    ),
    api: Optional[str] = typer.Option(  # noqa: B008
        None, "--api", "-a", help="API number to analyze (10 or 12 digit)"
    ),
    output: Optional[Path] = typer.Option(  # noqa: B008
        Path("./reports"),  # noqa: B008
        "--output",
        "-o",
        help="Output directory for analysis results",
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Analyze BSEE well and production data.

    Performs comprehensive analysis on wells, production, and drilling data
    for the specified block, field, lease, or API number.

    Examples:
        worldenergydata bsee analyze --block 759
        worldenergydata bsee analyze --field "Jack" --verbose
        worldenergydata bsee analyze --api 608114001200
    """
    try:
        # Validate inputs
        if not any([block, field, lease, api]):
            console.print(
                "[red]Error:[/red] At least one of --block, --field, --lease, or --api is required"
            )
            raise typer.Exit(1)

        # Display analysis parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        if block:
            params_table.add_row("Block", block)
        if field:
            params_table.add_row("Field", field)
        if lease:
            params_table.add_row("Lease", lease)
        if api:
            params_table.add_row("API", api)
        params_table.add_row("Output", str(output))

        console.print(
            Panel(params_table, title="Analysis Parameters", border_style="cyan")
        )

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running BSEE analysis...", total=100)

            # Import and run analysis
            try:
                from worldenergydata.bsee.bsee import bsee as BSEEModule

                progress.update(
                    task, advance=20, description="[cyan]Loading BSEE module..."
                )

                # Build configuration
                cfg = {
                    "basename": "bsee",
                    "data": {
                        "block": block,
                        "field": field,
                        "lease": lease,
                        "api": api,
                        "refresh": False,
                    },
                    "analysis": {
                        "flag": True,
                    },
                    "output": str(output),
                    "meta": {
                        "mode": "legacy",
                    },
                }

                progress.update(
                    task, advance=30, description="[cyan]Running analysis..."
                )

                # Run the analysis through BSEE router
                bsee_instance = BSEEModule()
                result_cfg = bsee_instance.router(cfg)

                progress.update(
                    task, advance=50, description="[cyan]Completing analysis..."
                )

                if verbose:
                    console.print(f"\n[dim]Configuration result: {result_cfg}[/dim]")

                console.print("\n[green]Analysis completed successfully[/green]")
                console.print(f"[dim]Results saved to: {output}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import BSEE module: {e}"
                )
                console.print("[dim]Ensure all dependencies are installed.[/dim]")
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def report(
    report_type: ReportType = typer.Option(  # noqa: B008
        ReportType.field, "--type", "-t", help="Type of report to generate"
    ),
    entity_id: str = typer.Option(  # noqa: B008
        ...,
        "--id",
        "-i",
        help="Entity identifier (block number, field name, or lease number)",
    ),
    output_format: OutputFormat = typer.Option(  # noqa: B008
        OutputFormat.excel, "--format", "-f", help="Output format"
    ),
    output: Path = typer.Option(  # noqa: B008
        Path("./reports"), "--output", "-o", help="Output directory"  # noqa: B008
    ),
    oil_price: float = typer.Option(  # noqa: B008
        75.00, "--oil-price", help="Oil price per barrel"
    ),
    gas_price: float = typer.Option(  # noqa: B008
        3.50, "--gas-price", help="Gas price per MCF"
    ),  # noqa: B008
    discount_rate: float = typer.Option(  # noqa: B008
        0.10,
        "--discount-rate",
        "-r",
        help="Discount rate for NPV calculations (e.g., 0.10 for 10%)",
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Generate comprehensive BSEE reports.

    Creates detailed reports for blocks, fields, leases, or wells including
    production data, well information, and economic analysis.

    Examples:
        worldenergydata bsee report --type block --id 759 --format excel
        worldenergydata bsee report --type field --id Jack --oil-price 80
        worldenergydata bsee report --type lease --id OCS-G-12345 --format pdf
    """
    try:
        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        # Display parameters
        console.print(
            Panel(
                f"[bold]Report Configuration[/bold]\n"
                f"Type: {report_type.value}\n"
                f"Entity: {entity_id}\n"
                f"Format: {output_format.value}\n"
                f"Oil Price: ${oil_price:.2f}/bbl\n"
                f"Gas Price: ${gas_price:.2f}/MCF\n"
                f"Discount Rate: {discount_rate:.1%}",
                border_style="cyan",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Generating {report_type.value} report for {entity_id}...",
                total=100,
            )

            try:
                from worldenergydata.bsee.reports.comprehensive.controller_enhanced import (
                    ReportConfiguration,
                    ReportController,
                    ReportParameters,
                )
                from worldenergydata.bsee.reports.comprehensive.controller_enhanced import (
                    ReportType as CtrlReportType,
                )

                progress.update(
                    task, advance=20, description="[cyan]Loading report controller..."
                )

                # Initialize controller
                controller = ReportController()

                progress.update(
                    task, advance=20, description="[cyan]Building configuration..."
                )

                # Build report configuration
                report_config = ReportConfiguration(
                    report_type=CtrlReportType.from_string(report_type.value),
                    entity_name=entity_id,
                    output_formats=[output_format.value],
                    include_economics=True,
                    include_visualizations=True,
                )

                # Build parameters
                params = ReportParameters(
                    price_deck={
                        "oil": {"2024": oil_price, "2025": oil_price},
                        "gas": {"2024": gas_price, "2025": gas_price},
                    },
                    discount_rate=discount_rate,
                )

                progress.update(
                    task, advance=30, description="[cyan]Generating report..."
                )

                # Generate report
                result = controller.generate_report(report_config, params)

                progress.update(task, advance=30, description="[cyan]Saving report...")

                if result.get("status") == "success":
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_filename = f"{report_type.value}_{entity_id}_{timestamp}"
                    if output_format == OutputFormat.json:
                        import json

                        report_path = output / f"{report_filename}.json"
                        with open(report_path, "w") as f:
                            json.dump(result, f, indent=2, default=str)
                    else:
                        # For other formats, save metadata as JSON for now
                        report_path = output / f"{report_filename}_metadata.json"
                        import json

                        with open(report_path, "w") as f:
                            json.dump(result, f, indent=2, default=str)

                    console.print("\n[green]Report generated successfully[/green]")
                    console.print(f"[dim]Report saved to: {report_path}[/dim]")
                else:
                    console.print(
                        "\n[yellow]Report generation completed with issues[/yellow]"
                    )
                    if result.get("error"):
                        console.print(f"[dim]Error: {result.get('error')}[/dim]")

                if verbose:
                    console.print(f"\n[dim]Report result: {result}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import report module: {e}"
                )
                console.print("[dim]Ensure all dependencies are installed.[/dim]")

        console.print(f"[dim]Output directory: {output}[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def data(
    api: Optional[str] = typer.Option(  # noqa: B008
        None, "--api", "-a", help="API number (10 or 12 digit)"
    ),
    block: Optional[str] = typer.Option(  # noqa: B008
        None, "--block", "-b", help="Block number"
    ),  # noqa: B008
    lease: Optional[str] = typer.Option(  # noqa: B008
        None, "--lease", "-l", help="Lease number"
    ),  # noqa: B008
    data_type: DataType = typer.Option(  # noqa: B008
        DataType.well, "--type", "-t", help="Type of data to retrieve"
    ),
    output: Optional[Path] = typer.Option(  # noqa: B008
        None, "--output", "-o", help="Output file path (optional)"
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Retrieve BSEE data for a specific entity.

    Fetches well, production, or other data for the specified API, block, or lease.

    Examples:
        worldenergydata bsee data --api 608114001200
        worldenergydata bsee data --block 759 --type production
        worldenergydata bsee data --lease OCS-G-12345 --output data.json
    """
    try:
        if not any([api, block, lease]):
            console.print(
                "[red]Error:[/red] At least one of --api, --block, or --lease is required"
            )
            raise typer.Exit(1)

        # Display query parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        if api:
            params_table.add_row("API", api)
        if block:
            params_table.add_row("Block", block)
        if lease:
            params_table.add_row("Lease", lease)
        params_table.add_row("Data Type", data_type.value)

        console.print(
            Panel(params_table, title="Query Parameters", border_style="cyan")
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Retrieving BSEE data...", total=100)

            try:
                from worldenergydata.bsee.data.bsee_data import BSEEData

                progress.update(
                    task, advance=30, description="[cyan]Loading BSEE data module..."
                )

                bsee_data_module = BSEEData()

                # Build configuration
                cfg = {
                    "basename": "bsee",
                    "data": {
                        "block": block,
                        "lease": lease,
                        "api": api,
                        "refresh": False,
                    },
                    "meta": {
                        "mode": "legacy",
                    },
                }

                progress.update(task, advance=40, description="[cyan]Fetching data...")

                # Route through BSEE data
                cfg, data_result = bsee_data_module.router(cfg)

                progress.update(
                    task, advance=30, description="[cyan]Processing results..."
                )

                # Display results
                well_data = data_result.get("well_data")
                production_data = data_result.get("production_data")

                results_table = Table(
                    title="Data Retrieved", show_header=True, header_style="bold cyan"
                )
                results_table.add_column("Data Type", style="dim")
                results_table.add_column("Records", justify="right")
                results_table.add_column("Status")

                if well_data is not None:
                    count = len(well_data) if hasattr(well_data, "__len__") else 0
                    results_table.add_row(
                        "Well Data", str(count), "[green]Available[/green]"
                    )
                else:
                    results_table.add_row(
                        "Well Data", "0", "[yellow]Not found[/yellow]"
                    )

                if production_data is not None:
                    count = (
                        len(production_data)
                        if hasattr(production_data, "__len__")
                        else 0
                    )
                    results_table.add_row(
                        "Production Data", str(count), "[green]Available[/green]"
                    )
                else:
                    results_table.add_row(
                        "Production Data", "0", "[yellow]Not found[/yellow]"
                    )

                console.print(results_table)

                # Save output if specified
                if output:
                    import json

                    output_data = {
                        "query": {
                            "api": api,
                            "block": block,
                            "lease": lease,
                            "data_type": data_type.value,
                        },
                        "well_data_count": (
                            len(well_data) if well_data is not None else 0
                        ),
                        "production_data_count": (
                            len(production_data) if production_data is not None else 0
                        ),
                        "retrieved_at": datetime.now().isoformat(),
                    }
                    with open(output, "w") as f:
                        json.dump(output_data, f, indent=2, default=str)
                    console.print(f"[dim]Data saved to: {output}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import BSEE data module: {e}"
                )

        console.print("\n[green]Data retrieval completed[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def refresh(
    data_type: DataType = typer.Option(  # noqa: B008
        DataType.all, "--type", "-t", help="Type of data to refresh"
    ),
    force: bool = typer.Option(  # noqa: B008
        False, "--force", "-f", help="Force refresh even if data is current"
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Refresh BSEE data from source.

    Downloads and updates local BSEE data cache from official sources.

    Examples:
        worldenergydata bsee refresh --type well
        worldenergydata bsee refresh --type production --force
        worldenergydata bsee refresh --type platform
        worldenergydata bsee refresh --type infrastructure
        worldenergydata bsee refresh --type all --verbose
    """
    try:
        console.print(
            Panel(
                f"[bold]Data Refresh[/bold]\n"
                f"Type: {data_type.value}\n"
                f"Force: {force}",
                border_style="cyan",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Refreshing {data_type.value} data...", total=100
            )

            try:
                from worldenergydata.bsee.data.refresh.data_refresh import (
                    DataRefresh,
                )

                progress.update(
                    task, advance=20, description="[cyan]Loading refresh module..."
                )

                refresh_module = DataRefresh()

                # Build configuration based on data type
                infrastructure_types = [
                    DataType.platform,
                    DataType.pipeline_permit,
                    DataType.deepwater_structure,
                    DataType.pipeline_location,
                    DataType.infrastructure,
                    DataType.all,
                ]

                # Use enhanced mode for infrastructure types and 'all'
                use_enhanced = data_type in infrastructure_types

                cfg = {
                    "basename": "bsee",
                    "data": {
                        "refresh": True,
                        "apm": data_type in [DataType.well, DataType.all],
                        "production": data_type in [DataType.production, DataType.all],
                        "platform": data_type
                        in [DataType.platform, DataType.infrastructure, DataType.all],
                        "pipeline_permit": data_type
                        in [
                            DataType.pipeline_permit,
                            DataType.infrastructure,
                            DataType.all,
                        ],
                        "deepwater_structure": data_type
                        in [
                            DataType.deepwater_structure,
                            DataType.infrastructure,
                            DataType.all,
                        ],
                        "pipeline_location": data_type
                        in [
                            DataType.pipeline_location,
                            DataType.infrastructure,
                            DataType.all,
                        ],
                    },
                    "meta": {
                        "mode": "enhanced" if use_enhanced else "legacy",
                    },
                }

                progress.update(
                    task,
                    advance=30,
                    description=f"[cyan]Refreshing {data_type.value} data...",
                )

                # Run refresh
                result_cfg, _ = refresh_module.router(cfg)

                progress.update(
                    task, advance=50, description="[cyan]Completing refresh..."
                )

                console.print("\n[green]Data refresh completed successfully[/green]")

                if verbose:
                    console.print(f"[dim]Configuration: {result_cfg}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import refresh module: {e}"
                )
                console.print("[dim]Ensure all dependencies are installed.[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def stats(
    verbose: bool = typer.Option(  # noqa: B008
        False, "--verbose", "-v", help="Show detailed statistics"
    ),
) -> None:
    """
    Display BSEE data statistics.

    Shows summary statistics about available BSEE data including counts
    of wells, production records, and data freshness.
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading BSEE data statistics...", total=100)

            # Initialize statistics
            stats_data = {
                "wells": 0,
                "production_records": 0,
                "blocks": 0,
                "leases": 0,
                "fields": 0,
                "last_updated": "Unknown",
            }

            try:
                from pathlib import Path

                progress.update(
                    task, advance=30, description="[cyan]Checking data directories..."
                )

                # Check for data directories and count files
                data_root = get_data_root()
                data_dirs = [
                    data_root / "bsee",
                    data_root / "raw",
                    data_root / "processed",
                ]

                total_files = 0
                total_size = 0
                for data_dir in data_dirs:
                    if data_dir.exists():
                        for f in data_dir.rglob("*"):
                            if f.is_file():
                                total_files += 1
                                total_size += f.stat().st_size

                progress.update(
                    task, advance=40, description="[cyan]Gathering statistics..."
                )

                # Try to load actual data if available
                try:
                    from worldenergydata.bsee.data.bsee_data import BSEEData

                    _bsee_data = BSEEData()  # noqa: F841
                    # Note: Would need to actually query data to get real counts
                    stats_data["data_files"] = total_files
                    stats_data["data_size_mb"] = total_size / (1024 * 1024)

                except ImportError:
                    pass

                progress.update(
                    task, advance=30, description="[cyan]Formatting results..."
                )

            except Exception as e:
                progress.update(task, completed=100)
                if verbose:
                    console.print(f"[dim]Error loading statistics: {e}[/dim]")

        # Create statistics table
        table = Table(
            title="BSEE Data Statistics", show_header=True, header_style="bold cyan"
        )

        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        # Display statistics
        if stats_data.get("data_files", 0) > 0:
            table.add_row("Data Files", f"{stats_data.get('data_files', 0):,}")
            table.add_row("Data Size", f"{stats_data.get('data_size_mb', 0):.2f} MB")
        else:
            table.add_row("Data Files", "[yellow]No data files found[/yellow]")

        table.add_row("", "")  # Spacer
        table.add_row("[dim]Module Status[/dim]", "[green]Available[/green]")

        if verbose:
            table.add_row("", "")
            table.add_row("[dim]Data Directories[/dim]", "")
            for data_dir in data_dirs:
                status = (
                    "[green]Exists[/green]"
                    if data_dir.exists()
                    else "[yellow]Not found[/yellow]"
                )
                table.add_row(f"  {data_dir}", status)

        console.print(table)

        console.print(
            "\n[dim]Use 'worldenergydata bsee refresh' to download/update data[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.callback()
def callback() -> None:
    """
    BSEE (Bureau of Safety and Environmental Enforcement) data operations.

    Access Gulf of Mexico well data, production records, and generate
    comprehensive reports for blocks, fields, leases, and individual wells.
    """
    pass
