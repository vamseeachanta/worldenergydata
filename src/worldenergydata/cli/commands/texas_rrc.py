# ABOUTME: CLI commands for Texas Railroad Commission data operations
# ABOUTME: Provides collect, analyze, and status commands for Texas oil/gas data

"""
Texas RRC CLI Commands

Provides command-line interface for Texas Railroad Commission (RRC)
data operations including data collection, analysis, and validation.

Usage:
    worldenergydata texas-rrc <command> [options]

Examples:
    worldenergydata texas-rrc collect --types production wells
    worldenergydata texas-rrc analyze --district 08
    worldenergydata texas-rrc status --verbose
    worldenergydata texas-rrc validate-api 42-123-12345
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

# Create Texas RRC Typer app
app = typer.Typer(
    name="texas-rrc",
    help="Texas Railroad Commission oil & gas data operations",
    no_args_is_help=True,
)


class DataType(str, Enum):
    """Data type options for collection."""

    production = "production"
    wells = "wells"
    permits = "permits"
    completions = "completions"
    drilling = "drilling"
    all = "all"


class OutputFormat(str, Enum):
    """Output format options."""

    json = "json"
    parquet = "parquet"
    csv = "csv"
    excel = "excel"


# Valid RRC districts
VALID_DISTRICTS = [
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "7B",
    "7C",
    "08",
    "8A",
    "09",
    "10",
]


@app.command()
def collect(
    data_types: List[DataType] = typer.Option(
        [DataType.production],
        "--types",
        "-t",
        help="Data types: production, wells, permits, completions, drilling, all",
    ),
    districts: Optional[List[str]] = typer.Option(
        None,
        "--districts",
        "-d",
        help="RRC districts: 01-10, 7B, 7C, 8A (omit for all districts)",
    ),
    output: Path = typer.Option(
        Path("./data/texas_rrc"),
        "--output",
        "-o",
        help="Output directory for collected data",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.csv, "--format", "-f", help="Output format for collected data"
    ),
    start_date: Optional[str] = typer.Option(
        None, "--start-date", help="Start date for data collection (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end-date", help="End date for data collection (YYYY-MM-DD)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Collect data from Texas RRC.

    Downloads oil and gas data from the Texas Railroad Commission
    for the specified data types and districts.

    Examples:
        worldenergydata texas-rrc collect --types production
        worldenergydata texas-rrc collect --types wells permits --districts 08 8A
        worldenergydata texas-rrc collect --types all --format csv
    """
    try:
        # Validate districts
        if districts:
            for d in districts:
                if d.upper() not in [x.upper() for x in VALID_DISTRICTS]:
                    console.print(f"[red]Error:[/red] Invalid district '{d}'")
                    console.print(
                        f"[dim]Valid districts: {', '.join(VALID_DISTRICTS)}[/dim]"
                    )
                    raise typer.Exit(1)

        # Convert 'all' to all data types
        types_to_collect = []
        for t in data_types:
            if t == DataType.all:
                types_to_collect = [
                    DataType.production.value,
                    DataType.wells.value,
                    DataType.permits.value,
                    DataType.completions.value,
                    DataType.drilling.value,
                ]
                break
            else:
                types_to_collect.append(t.value)

        # Display collection parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("Data Types", ", ".join(types_to_collect))
        params_table.add_row("Districts", ", ".join(districts) if districts else "All")
        params_table.add_row("Output Directory", str(output))
        params_table.add_row("Output Format", format.value)
        if start_date:
            params_table.add_row("Start Date", start_date)
        if end_date:
            params_table.add_row("End Date", end_date)

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
                "[cyan]Initializing Texas RRC data collection...", total=100
            )

            try:
                from worldenergydata.texas_rrc.texas_rrc import TexasRRC

                progress.update(
                    task, advance=10, description="[cyan]Loading Texas RRC module..."
                )

                # Build configuration
                cfg = {
                    "basename": "texas_rrc",
                    "module": "texas_rrc",
                    "data_types": types_to_collect,
                    "districts": districts or VALID_DISTRICTS,
                    "output": {
                        "directory": str(output),
                        "format": format.value,
                    },
                    "date_range": {
                        "start": start_date,
                        "end": end_date,
                    },
                }

                progress.update(
                    task, advance=20, description="[cyan]Connecting to Texas RRC..."
                )

                # Run the collection through Texas RRC router
                texas_rrc = TexasRRC()
                result_cfg = texas_rrc.router(cfg)

                progress.update(
                    task, advance=50, description="[cyan]Processing data..."
                )

                collected = result_cfg.get("texas_rrc", {}).get("data_collected", [])

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

                for dt in types_to_collect:
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
                    f"[yellow]Warning:[/yellow] Could not import Texas RRC module: {e}"
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
    district: Optional[str] = typer.Option(
        None, "--district", "-d", help="RRC district to analyze (e.g., '08', '7B')"
    ),
    county: Optional[str] = typer.Option(
        None, "--county", "-c", help="County name to analyze"
    ),
    operator: Optional[str] = typer.Option(
        None, "--operator", help="Operator name to filter analysis"
    ),
    include_economics: bool = typer.Option(
        False,
        "--include-economics",
        help="Include economic analysis (production value, etc.)",
    ),
    output: Path = typer.Option(
        Path("./reports/texas_rrc"),
        "--output",
        "-o",
        help="Output directory for analysis results",
    ),
    data_path: Path = typer.Option(
        Path("./data/texas_rrc"),
        "--data-path",
        help="Input directory containing Texas RRC data",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Run Texas RRC analysis.

    Performs analysis on Texas oil and gas data including production
    statistics, well counts, and optionally economic metrics.

    Examples:
        worldenergydata texas-rrc analyze
        worldenergydata texas-rrc analyze --district 08
        worldenergydata texas-rrc analyze --county "MIDLAND" --include-economics
    """
    try:
        # Validate district if provided
        if district and district.upper() not in [x.upper() for x in VALID_DISTRICTS]:
            console.print(f"[red]Error:[/red] Invalid district '{district}'")
            console.print(f"[dim]Valid districts: {', '.join(VALID_DISTRICTS)}[/dim]")
            raise typer.Exit(1)

        # Display analysis parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        if district:
            params_table.add_row("District", district)
        if county:
            params_table.add_row("County", county)
        if operator:
            params_table.add_row("Operator", operator)
        params_table.add_row("Include Economics", "Yes" if include_economics else "No")
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
            task = progress.add_task("[cyan]Running Texas RRC analysis...", total=100)

            try:
                from worldenergydata.texas_rrc.analysis import TexasRRCAnalysis

                progress.update(
                    task, advance=20, description="[cyan]Loading analysis module..."
                )

                # Build analysis configuration
                config = {
                    "input_path": str(data_path),
                    "output_path": str(output),
                    "district": district,
                    "county": county,
                    "operator": operator,
                    "include_economics": include_economics,
                }

                progress.update(task, advance=20, description="[cyan]Loading data...")

                analysis = TexasRRCAnalysis(config)
                results = analysis.run()

                progress.update(
                    task, advance=40, description="[cyan]Generating report..."
                )

                # Save results
                import json

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results_file = output / f"texas_rrc_analysis_{timestamp}.json"

                with open(results_file, "w") as f:
                    json.dump(results, f, indent=2, default=str)

                progress.update(
                    task, advance=20, description="[cyan]Completing analysis..."
                )

                if verbose:
                    console.print(f"\n[dim]Results: {results}[/dim]")

                console.print(f"\n[green]Analysis completed successfully[/green]")
                console.print(f"[dim]Results saved to: {results_file}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import analysis module: {e}"
                )
                console.print(
                    "[dim]Run 'worldenergydata texas-rrc collect' first to download data.[/dim]"
                )
                raise typer.Exit(1)
            except FileNotFoundError:
                progress.update(task, completed=100)
                console.print(
                    "[yellow]Warning:[/yellow] No Texas RRC data found. "
                    "Run 'worldenergydata texas-rrc collect' first."
                )
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
        Path("./data/texas_rrc"),
        "--data-path",
        "-d",
        help="Path to Texas RRC data directory",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed status information"
    ),
) -> None:
    """
    Show Texas RRC data status.

    Displays information about available Texas RRC data including
    file counts, data freshness, and district coverage.

    Examples:
        worldenergydata texas-rrc status
        worldenergydata texas-rrc status --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Loading Texas RRC data status...", total=100
            )

            status_data = {
                "data_files": 0,
                "data_size_mb": 0,
                "data_types": {},
                "districts_covered": [],
                "last_updated": "Unknown",
            }

            progress.update(
                task, advance=30, description="[cyan]Checking data directories..."
            )

            if data_path.exists():
                total_files = 0
                total_size = 0
                data_types_found = {}
                districts_found = set()

                for f in data_path.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_size += f.stat().st_size

                        stem = f.stem.lower()
                        for dtype in [
                            "production",
                            "wells",
                            "permits",
                            "completions",
                            "drilling",
                        ]:
                            if dtype in stem:
                                data_types_found[dtype] = (
                                    data_types_found.get(dtype, 0) + 1
                                )
                                break

                        # Check for district in filename
                        for dist in VALID_DISTRICTS:
                            if (
                                dist.lower() in stem
                                or f"district_{dist.lower()}" in stem
                            ):
                                districts_found.add(dist)

                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if status_data["last_updated"] == "Unknown":
                            status_data["last_updated"] = mtime.isoformat()
                        else:
                            existing = datetime.fromisoformat(
                                status_data["last_updated"]
                            )
                            if mtime > existing:
                                status_data["last_updated"] = mtime.isoformat()

                status_data["data_files"] = total_files
                status_data["data_size_mb"] = total_size / (1024 * 1024)
                status_data["data_types"] = data_types_found
                status_data["districts_covered"] = sorted(list(districts_found))

            progress.update(task, advance=70, description="[cyan]Formatting results...")

        # Create status table
        table = Table(
            title="Texas RRC Data Status", show_header=True, header_style="bold cyan"
        )

        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

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
            if status_data["districts_covered"]:
                table.add_row(
                    "Districts Covered", ", ".join(status_data["districts_covered"])
                )
        else:
            table.add_row("Data Files", "[yellow]No data files found[/yellow]")

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

            all_types = ["production", "wells", "permits", "completions", "drilling"]
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

        # Show districts table if verbose
        if verbose:
            districts_table = Table(
                title="RRC Districts", show_header=True, header_style="bold cyan"
            )
            districts_table.add_column("District")
            districts_table.add_column("Region")
            districts_table.add_column("Status")

            district_regions = {
                "01": "San Antonio Area",
                "02": "Refugio Area",
                "03": "Southeast Texas",
                "04": "Deep South Texas",
                "05": "East Central Texas",
                "06": "East Texas",
                "7B": "West Central Texas",
                "7C": "West Central Texas",
                "08": "Permian Basin - Midland",
                "8A": "Permian Basin - Lubbock",
                "09": "North Texas",
                "10": "Panhandle",
            }

            for dist in VALID_DISTRICTS:
                region = district_regions.get(dist, "Unknown")
                if dist in status_data["districts_covered"]:
                    districts_table.add_row(
                        dist, region, "[green]Data Available[/green]"
                    )
                else:
                    districts_table.add_row(dist, region, "[yellow]No data[/yellow]")

            console.print(districts_table)

        console.print(
            "\n[dim]Use 'worldenergydata texas-rrc collect' to download data[/dim]"
        )
        console.print(
            "[dim]Use 'worldenergydata texas-rrc analyze' to run analysis[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command("validate-api")
def validate_api(
    api_number: str = typer.Argument(
        ..., help="Texas API number to validate (e.g., '42-123-12345' or '4212312345')"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed validation information"
    ),
) -> None:
    """
    Validate a Texas API number.

    Checks if the provided API number follows Texas RRC format
    and displays parsed components.

    Examples:
        worldenergydata texas-rrc validate-api 42-123-12345
        worldenergydata texas-rrc validate-api 4212312345
        worldenergydata texas-rrc validate-api 42-123-12345-00-00
    """
    try:
        # Remove dashes and spaces for parsing
        cleaned = api_number.replace("-", "").replace(" ", "")

        # Texas API format: 42-CCC-WWWWW[-SS-EE]
        # 42 = Texas state code
        # CCC = County code (3 digits)
        # WWWWW = Well number (5 digits)
        # SS = Sidetrack (optional, 2 digits)
        # EE = Completion (optional, 2 digits)

        validation_result = {
            "valid": False,
            "state_code": None,
            "county_code": None,
            "well_number": None,
            "sidetrack": None,
            "completion": None,
            "errors": [],
        }

        if len(cleaned) < 10:
            validation_result["errors"].append(
                f"API number too short: {len(cleaned)} digits (minimum 10)"
            )
        elif len(cleaned) > 14:
            validation_result["errors"].append(
                f"API number too long: {len(cleaned)} digits (maximum 14)"
            )
        else:
            # Check if all digits
            if not cleaned.isdigit():
                validation_result["errors"].append(
                    "API number must contain only digits"
                )
            else:
                validation_result["state_code"] = cleaned[:2]
                validation_result["county_code"] = cleaned[2:5]
                validation_result["well_number"] = cleaned[5:10]

                if validation_result["state_code"] != "42":
                    validation_result["errors"].append(
                        f"Invalid state code: {validation_result['state_code']} (Texas = 42)"
                    )

                if len(cleaned) >= 12:
                    validation_result["sidetrack"] = cleaned[10:12]
                if len(cleaned) >= 14:
                    validation_result["completion"] = cleaned[12:14]

                if not validation_result["errors"]:
                    validation_result["valid"] = True

        # Display results
        if validation_result["valid"]:
            console.print(
                Panel(
                    f"[bold green]Valid Texas API Number[/bold green]\n\n"
                    f"Input: {api_number}",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]Invalid API Number[/bold red]\n\n"
                    f"Input: {api_number}\n"
                    f"Errors: {'; '.join(validation_result['errors'])}",
                    border_style="red",
                )
            )

        # Show parsed components
        components_table = Table(
            title="API Number Components", show_header=True, header_style="bold cyan"
        )
        components_table.add_column("Component")
        components_table.add_column("Value")
        components_table.add_column("Description")

        if validation_result["state_code"]:
            components_table.add_row(
                "State Code",
                validation_result["state_code"],
                (
                    "42 = Texas"
                    if validation_result["state_code"] == "42"
                    else "[red]Invalid[/red]"
                ),
            )
        if validation_result["county_code"]:
            components_table.add_row(
                "County Code",
                validation_result["county_code"],
                "3-digit county identifier",
            )
        if validation_result["well_number"]:
            components_table.add_row(
                "Well Number",
                validation_result["well_number"],
                "5-digit well identifier",
            )
        if validation_result["sidetrack"]:
            components_table.add_row(
                "Sidetrack", validation_result["sidetrack"], "Sidetrack number"
            )
        if validation_result["completion"]:
            components_table.add_row(
                "Completion", validation_result["completion"], "Completion number"
            )

        console.print(components_table)

        # Format examples
        if verbose or not validation_result["valid"]:
            console.print("\n[dim]Valid Texas API formats:[/dim]")
            console.print("[dim]  42-CCC-WWWWW       (10 digits)[/dim]")
            console.print("[dim]  42-CCC-WWWWW-SS    (12 digits with sidetrack)[/dim]")
            console.print("[dim]  42-CCC-WWWWW-SS-EE (14 digits with completion)[/dim]")

        if not validation_result["valid"]:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.callback()
def callback() -> None:
    """
    Texas Railroad Commission data operations.

    Access Texas oil and gas data including production statistics,
    well information, drilling permits, and completions from the
    Texas Railroad Commission.
    """
    pass
