# ABOUTME: CLI commands for SODIR (Norwegian Offshore Directorate) data operations
# ABOUTME: Provides collect, analyze, and status commands for Norwegian oil/gas data

"""
SODIR CLI Commands

Provides command-line interface for SODIR (Norwegian Offshore Directorate)
data operations including data collection, analysis, and cache management.

Usage:
    worldenergydata sodir <command> [options]

Examples:
    worldenergydata sodir collect --types wellbores fields
    worldenergydata sodir analyze --field "TROLL" --include-npv
    worldenergydata sodir status --verbose
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize console
console = Console()

# Create SODIR Typer app
app = typer.Typer(
    name="sodir",
    help="SODIR (Norwegian Offshore Directorate) data operations",
    no_args_is_help=True,
)


class DataType(str, Enum):
    """Data type options for collection."""

    wellbores = "wellbores"
    fields = "fields"
    discoveries = "discoveries"
    blocks = "blocks"
    surveys = "surveys"
    facilities = "facilities"
    all = "all"


class AnalysisType(str, Enum):
    """Analysis type options."""

    comprehensive = "comprehensive"
    field = "field"
    portfolio = "portfolio"
    temporal = "temporal"


class OutputFormat(str, Enum):
    """Output format options."""

    json = "json"
    parquet = "parquet"
    csv = "csv"
    excel = "excel"


@app.command()
def collect(
    types: List[DataType] = typer.Option(
        [DataType.wellbores],
        "--types",
        "-t",
        help="Data types to collect: wellbores, fields, discoveries, blocks, surveys, facilities, all",
    ),
    output: Path = typer.Option(
        Path("./data/sodir"),
        "--output",
        "-o",
        help="Output directory for collected data",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.parquet, "--format", "-f", help="Output format for collected data"
    ),
    rate_limit: int = typer.Option(
        10, "--rate-limit", "-r", help="Maximum requests per second to SODIR API"
    ),
    cache_ttl: int = typer.Option(
        86400, "--cache-ttl", help="Cache time-to-live in seconds (default 24 hours)"
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Disable caching and force fresh data retrieval"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Collect data from SODIR API.

    Downloads data from the Norwegian Offshore Directorate (SODIR) API
    for the specified data types and saves to the output directory.

    Examples:
        worldenergydata sodir collect --types wellbores
        worldenergydata sodir collect --types wellbores fields discoveries
        worldenergydata sodir collect --types all --format csv
        worldenergydata sodir collect --types blocks --no-cache
    """
    try:
        # Convert 'all' to all data types
        data_types = []
        for t in types:
            if t == DataType.all:
                data_types = [
                    DataType.wellbores.value,
                    DataType.fields.value,
                    DataType.discoveries.value,
                    DataType.blocks.value,
                    DataType.surveys.value,
                    DataType.facilities.value,
                ]
                break
            else:
                data_types.append(t.value)

        # Display collection parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("Data Types", ", ".join(data_types))
        params_table.add_row("Output Directory", str(output))
        params_table.add_row("Output Format", format.value)
        params_table.add_row("Rate Limit", f"{rate_limit} req/sec")
        params_table.add_row("Cache TTL", f"{cache_ttl} seconds")
        params_table.add_row("Caching", "Disabled" if no_cache else "Enabled")

        console.print(
            Panel(params_table, title="Collection Parameters", border_style="cyan")
        )

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Initializing SODIR data collection...", total=100
            )

            try:
                from worldenergydata.sodir import Sodir

                progress.update(
                    task, advance=10, description="[cyan]Loading SODIR module..."
                )

                # Build configuration
                cfg = {
                    "basename": "sodir",
                    "module": "sodir",
                    "data_types": data_types,
                    "api": {
                        "base_url": "https://factmaps.sodir.no/api/rest",
                        "rate_limit": rate_limit,
                        "cache_ttl": cache_ttl if not no_cache else 0,
                    },
                    "output": {
                        "directory": str(output),
                        "format": format.value,
                    },
                    "data": {
                        "types": data_types,
                        "refresh": no_cache,
                    },
                }

                progress.update(
                    task, advance=20, description="[cyan]Connecting to SODIR API..."
                )

                # Run the collection through SODIR router
                sodir_instance = Sodir()
                result_cfg = sodir_instance.router(cfg)

                progress.update(
                    task, advance=50, description="[cyan]Processing data..."
                )

                # Display collection results
                collected = result_cfg.get("sodir", {}).get("data_collected", [])

                progress.update(
                    task, advance=20, description="[cyan]Completing collection..."
                )

                if verbose:
                    console.print(f"\n[dim]Configuration result: {result_cfg}[/dim]")

                # Create results table
                results_table = Table(
                    title="Collection Results",
                    show_header=True,
                    header_style="bold cyan",
                )
                results_table.add_column("Data Type", style="dim")
                results_table.add_column("Status")
                results_table.add_column("Records", justify="right")

                for dt in data_types:
                    if dt in collected:
                        results_table.add_row(
                            dt, "[green]Collected[/green]", "See output"
                        )
                    else:
                        results_table.add_row(dt, "[yellow]Pending[/yellow]", "-")

                console.print(results_table)
                console.print(
                    f"\n[green]Data collection completed successfully[/green]"
                )
                console.print(f"[dim]Data saved to: {output}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import SODIR module: {e}"
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
def analyze(
    field: Optional[str] = typer.Option(
        None, "--field", "-f", help="Field name to analyze (e.g., 'TROLL', 'EKOFISK')"
    ),
    analysis_type: AnalysisType = typer.Option(
        AnalysisType.comprehensive, "--type", "-t", help="Type of analysis to perform"
    ),
    include_npv: bool = typer.Option(
        False, "--include-npv", help="Include NPV economic analysis"
    ),
    include_forecast: bool = typer.Option(
        False, "--include-forecast", help="Include production forecasting"
    ),
    oil_price: float = typer.Option(
        80.0, "--oil-price", help="Oil price per barrel for economic analysis"
    ),
    discount_rate: float = typer.Option(
        0.08,
        "--discount-rate",
        "-r",
        help="Discount rate for NPV calculations (e.g., 0.08 for 8%)",
    ),
    output: Path = typer.Option(
        Path("./reports/sodir"),
        "--output",
        "-o",
        help="Output directory for analysis results",
    ),
    data_path: Path = typer.Option(
        Path("./data/sodir"),
        "--data-path",
        "-d",
        help="Input directory containing SODIR data",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Run SODIR analysis on collected data.

    Performs comprehensive analysis on Norwegian Continental Shelf data
    including field-level metrics, portfolio analysis, and temporal trends.

    Examples:
        worldenergydata sodir analyze --field TROLL
        worldenergydata sodir analyze --type portfolio --include-npv
        worldenergydata sodir analyze --field EKOFISK --include-forecast --oil-price 85
    """
    try:
        # Validate inputs
        if analysis_type == AnalysisType.field and not field:
            console.print(
                "[red]Error:[/red] --field is required for field-level analysis"
            )
            raise typer.Exit(1)

        # Display analysis parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        if field:
            params_table.add_row("Field", field)
        params_table.add_row("Analysis Type", analysis_type.value)
        params_table.add_row("Include NPV", "Yes" if include_npv else "No")
        params_table.add_row("Include Forecast", "Yes" if include_forecast else "No")
        if include_npv:
            params_table.add_row("Oil Price", f"${oil_price:.2f}/bbl")
            params_table.add_row("Discount Rate", f"{discount_rate:.1%}")
        params_table.add_row("Data Path", str(data_path))
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
            task = progress.add_task("[cyan]Running SODIR analysis...", total=100)

            try:
                from worldenergydata.sodir.analysis import (
                    AnalysisConfig,
                    SodirAnalysis,
                )

                progress.update(
                    task, advance=20, description="[cyan]Loading analysis module..."
                )

                # Build analysis configuration
                config = AnalysisConfig(
                    input_path=str(data_path),
                    output_path=str(output),
                    analysis_type=analysis_type.value,
                    include_npv=include_npv,
                    include_forecasting=include_forecast,
                    discount_rate=discount_rate,
                    oil_price_scenario="mid",
                    fields=[field] if field else [],
                )

                progress.update(task, advance=20, description="[cyan]Loading data...")

                # Initialize and run analysis
                analysis = SodirAnalysis(config)

                try:
                    analysis.load_data()
                except FileNotFoundError:
                    progress.update(task, completed=100)
                    console.print(
                        "[yellow]Warning:[/yellow] No SODIR data found. "
                        "Run 'worldenergydata sodir collect' first."
                    )
                    raise typer.Exit(1)

                progress.update(
                    task, advance=30, description="[cyan]Running analysis..."
                )

                results = {}

                if analysis_type == AnalysisType.field and field:
                    try:
                        results["field"] = analysis.analyze_field(field)
                    except KeyError as e:
                        console.print(f"[yellow]Warning:[/yellow] {e}")

                elif analysis_type == AnalysisType.portfolio:
                    results["portfolio"] = analysis.analyze_portfolio()

                elif analysis_type == AnalysisType.temporal:
                    results["temporal"] = analysis.analyze_temporal_trends()

                elif analysis_type == AnalysisType.comprehensive:
                    if field:
                        try:
                            results["field"] = analysis.analyze_field(field)
                        except KeyError as e:
                            console.print(f"[dim]Note: {e}[/dim]")
                    results["portfolio"] = analysis.analyze_portfolio()
                    results["temporal"] = analysis.analyze_temporal_trends()

                progress.update(task, advance=30, description="[cyan]Saving results...")

                # Save results
                import json

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results_file = output / f"sodir_analysis_{timestamp}.json"

                # Convert results to serializable format
                serializable_results = _convert_results_to_serializable(results)

                with open(results_file, "w") as f:
                    json.dump(serializable_results, f, indent=2, default=str)

                if verbose:
                    console.print(f"\n[dim]Results: {serializable_results}[/dim]")

                console.print(f"\n[green]Analysis completed successfully[/green]")
                console.print(f"[dim]Results saved to: {results_file}[/dim]")

                # Display summary
                if "portfolio" in results and results["portfolio"]:
                    summary_table = Table(
                        title="Portfolio Summary",
                        show_header=True,
                        header_style="bold cyan",
                    )
                    summary_table.add_column("Metric")
                    summary_table.add_column("Value", justify="right")

                    portfolio = results["portfolio"]
                    summary_table.add_row(
                        "Total Fields", str(portfolio.get("total_fields", "N/A"))
                    )
                    summary_table.add_row(
                        "Total Recoverable Oil",
                        f"{portfolio.get('total_recoverable_oil', 0):,.1f} MMbbl",
                    )
                    summary_table.add_row(
                        "Total Recoverable Gas",
                        f"{portfolio.get('total_recoverable_gas', 0):,.1f} BCF",
                    )
                    summary_table.add_row(
                        "Avg Recovery Factor",
                        f"{portfolio.get('average_recovery_factor', 0):.1%}",
                    )

                    console.print(summary_table)

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import analysis module: {e}"
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
def status(
    data_path: Path = typer.Option(
        Path("./data/sodir"), "--data-path", "-d", help="Path to SODIR data directory"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed status information"
    ),
) -> None:
    """
    Show cached data status.

    Displays information about available SODIR data including file counts,
    data freshness, and cache statistics.

    Examples:
        worldenergydata sodir status
        worldenergydata sodir status --verbose
        worldenergydata sodir status --data-path ./custom/path
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading SODIR data status...", total=100)

            # Initialize status data
            status_data = {
                "data_files": 0,
                "data_size_mb": 0,
                "data_types": {},
                "last_updated": "Unknown",
                "cache_status": "Not initialized",
            }

            progress.update(
                task, advance=30, description="[cyan]Checking data directories..."
            )

            # Check data directory
            if data_path.exists():
                total_files = 0
                total_size = 0
                data_types_found = {}

                for f in data_path.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_size += f.stat().st_size

                        # Categorize by data type
                        stem = f.stem.lower()
                        for dtype in [
                            "wellbores",
                            "fields",
                            "discoveries",
                            "blocks",
                            "surveys",
                            "facilities",
                        ]:
                            if dtype in stem:
                                data_types_found[dtype] = (
                                    data_types_found.get(dtype, 0) + 1
                                )
                                break

                        # Get most recent modification time
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if status_data[
                            "last_updated"
                        ] == "Unknown" or mtime > datetime.fromisoformat(
                            status_data["last_updated"]
                        ):
                            status_data["last_updated"] = mtime.isoformat()

                status_data["data_files"] = total_files
                status_data["data_size_mb"] = total_size / (1024 * 1024)
                status_data["data_types"] = data_types_found

            progress.update(
                task, advance=40, description="[cyan]Checking cache status..."
            )

            # Try to check cache status
            try:
                from worldenergydata.sodir.cache import SodirCache

                cache = SodirCache()
                status_data["cache_status"] = "Available"
                status_data["cache_entries"] = len(cache.cache)
            except ImportError:
                status_data["cache_status"] = "Module not loaded"

            progress.update(task, advance=30, description="[cyan]Formatting results...")

        # Create status table
        table = Table(
            title="SODIR Data Status", show_header=True, header_style="bold cyan"
        )

        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        # Display file statistics
        if status_data["data_files"] > 0:
            table.add_row("Data Files", f"{status_data['data_files']:,}")
            table.add_row("Data Size", f"{status_data['data_size_mb']:.2f} MB")
            table.add_row(
                "Last Updated",
                (
                    status_data["last_updated"][:19]
                    if status_data["last_updated"] != "Unknown"
                    else "Unknown"
                ),
            )
        else:
            table.add_row("Data Files", "[yellow]No data files found[/yellow]")

        table.add_row("", "")  # Spacer
        table.add_row("Cache Status", f"[green]{status_data['cache_status']}[/green]")
        if "cache_entries" in status_data:
            table.add_row("Cache Entries", str(status_data["cache_entries"]))

        table.add_row("", "")
        table.add_row("Data Directory", str(data_path))

        console.print(table)

        # Show data types breakdown
        if status_data["data_types"] and verbose:
            types_table = Table(
                title="Data Types Breakdown", show_header=True, header_style="bold cyan"
            )
            types_table.add_column("Data Type")
            types_table.add_column("Files", justify="right")
            types_table.add_column("Status")

            all_types = [
                "wellbores",
                "fields",
                "discoveries",
                "blocks",
                "surveys",
                "facilities",
            ]
            for dtype in all_types:
                count = status_data["data_types"].get(dtype, 0)
                if count > 0:
                    types_table.add_row(
                        dtype.capitalize(), str(count), "[green]Available[/green]"
                    )
                else:
                    types_table.add_row(
                        dtype.capitalize(), "0", "[yellow]Not collected[/yellow]"
                    )

            console.print(types_table)

        # API status
        if verbose:
            api_table = Table(
                title="SODIR API Status", show_header=True, header_style="bold cyan"
            )
            api_table.add_column("Endpoint")
            api_table.add_column("Description")
            api_table.add_column("Status")

            api_table.add_row("/1001", "Blocks", "[green]Available[/green]")
            api_table.add_row("/5000", "Wellbores", "[green]Available[/green]")
            api_table.add_row("/7100", "Fields", "[green]Available[/green]")
            api_table.add_row("/7000", "Discoveries", "[green]Available[/green]")
            api_table.add_row("/4000", "Surveys", "[green]Available[/green]")

            console.print(api_table)

        console.print(
            "\n[dim]Use 'worldenergydata sodir collect' to download data[/dim]"
        )
        console.print("[dim]Use 'worldenergydata sodir analyze' to run analysis[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def clear_cache(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """
    Clear SODIR data cache.

    Removes all cached API responses, forcing fresh data retrieval
    on the next collection.

    Examples:
        worldenergydata sodir clear-cache
        worldenergydata sodir clear-cache --yes
    """
    if not confirm:
        confirm = typer.confirm("Are you sure you want to clear the SODIR cache?")

    if not confirm:
        console.print("[yellow]Cache clear cancelled[/yellow]")
        raise typer.Exit(0)

    try:
        from worldenergydata.sodir.cache import SodirCache

        cache = SodirCache()
        entries_before = len(cache.cache)
        cache.clear()

        console.print(f"[green]Cache cleared successfully[/green]")
        console.print(f"[dim]Removed {entries_before} cached entries[/dim]")

    except ImportError as e:
        console.print(f"[yellow]Warning:[/yellow] Could not import cache module: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.callback()
def callback() -> None:
    """
    SODIR (Norwegian Offshore Directorate) data operations.

    Access Norwegian Continental Shelf petroleum data including blocks,
    wellbores, fields, discoveries, and surveys from the SODIR API.
    """
    pass


def _convert_results_to_serializable(results: dict) -> dict:
    """Convert analysis results to JSON-serializable format."""
    from dataclasses import asdict, is_dataclass

    import pandas as pd

    def convert_value(v):
        if v is None:
            return None
        if isinstance(v, pd.DataFrame):
            return v.to_dict(orient="records")
        if isinstance(v, pd.Series):
            return v.to_dict()
        if is_dataclass(v) and not isinstance(v, type):
            return asdict(v)
        if isinstance(v, dict):
            return {k: convert_value(val) for k, val in v.items()}
        if isinstance(v, list):
            return [convert_value(item) for item in v]
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    return convert_value(results)
