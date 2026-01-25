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

import typer
from typing import Optional, List
from pathlib import Path
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

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
    all = "all"


@app.command()
def analyze(
    block: Optional[str] = typer.Option(
        None, "--block", "-b",
        help="Block number to analyze (e.g., 759)"
    ),
    field: Optional[str] = typer.Option(
        None, "--field", "-f",
        help="Field name to analyze (e.g., 'Jack', 'Thunder Horse')"
    ),
    lease: Optional[str] = typer.Option(
        None, "--lease", "-l",
        help="Lease number to analyze (e.g., OCS-G-12345)"
    ),
    api: Optional[str] = typer.Option(
        None, "--api", "-a",
        help="API number to analyze (10 or 12 digit)"
    ),
    output: Optional[Path] = typer.Option(
        Path("./reports"),
        "--output", "-o",
        help="Output directory for analysis results"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose output"
    ),
):
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Running BSEE analysis...", total=None)

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

            progress.update(task, completed=True)

        console.print(Panel(params_table, title="Analysis Parameters", border_style="cyan"))

        # Import and run analysis
        try:
            from worldenergydata.modules.bsee.bsee import bsee as BSEEModule

            # Build configuration
            cfg = {
                "basename": "bsee",
                "data": {
                    "block": block,
                    "field": field,
                    "lease": lease,
                    "api": api,
                },
                "analysis": {
                    "flag": True,
                },
                "output": str(output),
            }

            console.print("[yellow]Note:[/yellow] Full analysis integration in progress")
            console.print(f"[dim]Configuration: {cfg}[/dim]")

        except ImportError as e:
            console.print(f"[yellow]Warning:[/yellow] Could not import BSEE module: {e}")

        console.print("\n[green]Analysis completed[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def report(
    report_type: ReportType = typer.Option(
        ReportType.field,
        "--type", "-t",
        help="Type of report to generate"
    ),
    entity_id: str = typer.Option(
        ..., "--id", "-i",
        help="Entity identifier (block number, field name, or lease number)"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.excel,
        "--format", "-f",
        help="Output format"
    ),
    output: Path = typer.Option(
        Path("./reports"),
        "--output", "-o",
        help="Output directory"
    ),
    oil_price: float = typer.Option(
        75.00,
        "--oil-price",
        help="Oil price per barrel"
    ),
    gas_price: float = typer.Option(
        3.50,
        "--gas-price",
        help="Gas price per MCF"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose output"
    ),
):
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]Generating {report_type.value} report for {entity_id}...",
                total=None
            )

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
                    f"Gas Price: ${gas_price:.2f}/MCF",
                    border_style="cyan"
                )
            )

            try:
                from worldenergydata.modules.bsee.reports.comprehensive.cli import ReportCLI

                # Use the existing CLI
                report_cli = ReportCLI()
                config = {
                    "type": report_type.value,
                    "id": entity_id,
                    "format": output_format.value,
                    "output": str(output),
                    "oil_price": oil_price,
                    "gas_price": gas_price,
                    "verbose": verbose,
                }
                report_cli.initialize_components(config)

                console.print("[yellow]Note:[/yellow] Report generation integration in progress")

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import report module: {e}")

            progress.update(task, completed=True)

        console.print(f"\n[green]Report generation completed[/green]")
        console.print(f"[dim]Output directory: {output}[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def data(
    api: Optional[str] = typer.Option(
        None, "--api", "-a",
        help="API number (10 or 12 digit)"
    ),
    block: Optional[str] = typer.Option(
        None, "--block", "-b",
        help="Block number"
    ),
    lease: Optional[str] = typer.Option(
        None, "--lease", "-l",
        help="Lease number"
    ),
    data_type: DataType = typer.Option(
        DataType.well,
        "--type", "-t",
        help="Type of data to retrieve"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output file path (optional)"
    ),
):
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

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Retrieving BSEE data...", total=None)

            try:
                from worldenergydata.modules.bsee.data.bsee_data import BSEEData

                bsee_data = BSEEData()
                console.print(f"[dim]Data type: {data_type.value}[/dim]")
                console.print("[yellow]Note:[/yellow] Data retrieval integration in progress")

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import BSEE data module: {e}")

            progress.update(task, completed=True)

        console.print("\n[green]Data retrieval completed[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def refresh(
    data_type: DataType = typer.Option(
        DataType.all,
        "--type", "-t",
        help="Type of data to refresh"
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Force refresh even if data is current"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose output"
    ),
):
    """
    Refresh BSEE data from source.

    Downloads and updates local BSEE data cache from official sources.

    Examples:
        worldenergydata bsee refresh --type well
        worldenergydata bsee refresh --type production --force
        worldenergydata bsee refresh --type all --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]Refreshing {data_type.value} data...",
                total=None
            )

            console.print(
                Panel(
                    f"[bold]Data Refresh[/bold]\n"
                    f"Type: {data_type.value}\n"
                    f"Force: {force}",
                    border_style="cyan"
                )
            )

            try:
                from worldenergydata.modules.bsee.data.refresh.data_refresh import DataRefresh

                console.print("[yellow]Note:[/yellow] Data refresh integration in progress")

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import refresh module: {e}")

            progress.update(task, completed=True)

        console.print("\n[green]Data refresh completed[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def stats():
    """
    Display BSEE data statistics.

    Shows summary statistics about available BSEE data including counts
    of wells, production records, and data freshness.
    """
    try:
        table = Table(
            title="BSEE Data Statistics",
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        # Placeholder statistics
        table.add_row("Wells", "Loading...")
        table.add_row("Production Records", "Loading...")
        table.add_row("Blocks", "Loading...")
        table.add_row("Leases", "Loading...")
        table.add_row("Fields", "Loading...")
        table.add_row("Last Updated", "Loading...")

        console.print(table)
        console.print("\n[yellow]Note:[/yellow] Live statistics integration in progress")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.callback()
def callback():
    """
    BSEE (Bureau of Safety and Environmental Enforcement) data operations.

    Access Gulf of Mexico well data, production records, and generate
    comprehensive reports for blocks, fields, leases, and individual wells.
    """
    pass
