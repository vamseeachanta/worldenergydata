# ABOUTME: CLI commands for Canadian oil and gas data operations
# ABOUTME: Provides collect, analyze, and UWI validation for AER and BCER data

"""
Canada CLI Commands

Provides command-line interface for Canadian oil and gas data operations
including data collection from AER (Alberta) and BCER (British Columbia),
analysis, and UWI validation.

Usage:
    worldenergydata canada <command> [options]

Examples:
    worldenergydata canada collect --provinces AB BC
    worldenergydata canada analyze --province AB
    worldenergydata canada status --verbose
    worldenergydata canada validate-uwi 100/06-01-048-09W4/0
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

# Create Canada Typer app
app = typer.Typer(
    name="canada",
    help="Canadian oil & gas data operations (AER/BCER)",
    no_args_is_help=True,
)


class Province(str, Enum):
    """Canadian provinces with oil and gas data."""

    AB = "AB"  # Alberta
    BC = "BC"  # British Columbia


class DataType(str, Enum):
    """Data type options for collection."""

    wells = "wells"
    production = "production"
    facilities = "facilities"
    licenses = "licenses"
    all = "all"


class OutputFormat(str, Enum):
    """Output format options."""

    json = "json"
    parquet = "parquet"
    csv = "csv"
    excel = "excel"


# Province configuration
PROVINCE_CONFIG = {
    "AB": {
        "name": "Alberta",
        "regulator": "AER",
        "full_name": "Alberta Energy Regulator",
    },
    "BC": {
        "name": "British Columbia",
        "regulator": "BCER",
        "full_name": "BC Energy Regulator",
    },
}


@app.command()
def collect(
    provinces: List[Province] = typer.Option(
        [Province.AB],
        "--provinces",
        "-p",
        help="Provinces: AB (Alberta), BC (British Columbia)",
    ),
    data_types: List[DataType] = typer.Option(
        [DataType.wells],
        "--types",
        "-t",
        help="Data types: wells, production, facilities, licenses, all",
    ),
    output: Path = typer.Option(
        Path("./data/canada"),
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
    Collect data from Canadian regulators.

    Downloads oil and gas data from AER (Alberta Energy Regulator)
    and BCER (BC Energy Regulator) for the specified data types.

    Examples:
        worldenergydata canada collect --provinces AB
        worldenergydata canada collect --provinces AB BC --types wells production
        worldenergydata canada collect --types all --format csv
    """
    try:
        # Convert 'all' to all data types
        types_to_collect = []
        for t in data_types:
            if t == DataType.all:
                types_to_collect = [
                    DataType.wells.value,
                    DataType.production.value,
                    DataType.facilities.value,
                    DataType.licenses.value,
                ]
                break
            else:
                types_to_collect.append(t.value)

        province_list = [p.value for p in provinces]

        # Display collection parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("Provinces", ", ".join(province_list))
        params_table.add_row("Data Types", ", ".join(types_to_collect))
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
                "[cyan]Initializing Canada data collection...", total=100
            )

            try:
                from worldenergydata.canada.canada import Canada

                progress.update(
                    task, advance=10, description="[cyan]Loading Canada module..."
                )

                # Build configuration
                cfg = {
                    "basename": "canada",
                    "module": "canada",
                    "provinces": province_list,
                    "data_types": types_to_collect,
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
                    task, advance=20, description="[cyan]Connecting to regulators..."
                )

                # Run the collection through Canada router
                canada = Canada()
                result_cfg = canada.router(cfg)

                progress.update(
                    task, advance=50, description="[cyan]Processing data..."
                )

                collected = result_cfg.get("canada", {}).get("data_collected", [])

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
                results_table.add_column("Province", style="dim")
                results_table.add_column("Data Type")
                results_table.add_column("Status")

                for prov in province_list:
                    for dt in types_to_collect:
                        key = f"{prov}_{dt}"
                        if key in collected or dt in collected:
                            results_table.add_row(
                                PROVINCE_CONFIG[prov]["name"],
                                dt,
                                "[green]Collected[/green]",
                            )
                        else:
                            results_table.add_row(
                                PROVINCE_CONFIG[prov]["name"],
                                dt,
                                "[yellow]Pending[/yellow]",
                            )

                console.print(results_table)
                console.print(
                    f"\n[green]Data collection completed successfully[/green]"
                )
                console.print(f"[dim]Data saved to: {output}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import Canada module: {e}"
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
    province: Optional[Province] = typer.Option(
        None,
        "--province",
        "-p",
        help="Province to analyze: AB (Alberta), BC (British Columbia)",
    ),
    field: Optional[str] = typer.Option(
        None, "--field", "-f", help="Field name to analyze"
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
        Path("./reports/canada"),
        "--output",
        "-o",
        help="Output directory for analysis results",
    ),
    data_path: Path = typer.Option(
        Path("./data/canada"),
        "--data-path",
        help="Input directory containing Canada data",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Run Canadian data analysis.

    Performs analysis on Canadian oil and gas data including production
    statistics, well counts, and optionally economic metrics.

    Examples:
        worldenergydata canada analyze
        worldenergydata canada analyze --province AB
        worldenergydata canada analyze --field "PEMBINA" --include-economics
    """
    try:
        # Display analysis parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        if province:
            params_table.add_row("Province", PROVINCE_CONFIG[province.value]["name"])
        if field:
            params_table.add_row("Field", field)
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
            task = progress.add_task(
                "[cyan]Running Canadian data analysis...", total=100
            )

            try:
                from worldenergydata.canada.analysis import CanadaAnalysis

                progress.update(
                    task, advance=20, description="[cyan]Loading analysis module..."
                )

                # Build analysis configuration
                config = {
                    "input_path": str(data_path),
                    "output_path": str(output),
                    "province": province.value if province else None,
                    "field": field,
                    "operator": operator,
                    "include_economics": include_economics,
                }

                progress.update(task, advance=20, description="[cyan]Loading data...")

                analysis = CanadaAnalysis(config)
                results = analysis.run()

                progress.update(
                    task, advance=40, description="[cyan]Generating report..."
                )

                # Save results
                import json

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results_file = output / f"canada_analysis_{timestamp}.json"

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
                    "[dim]Run 'worldenergydata canada collect' first to download data.[/dim]"
                )
                raise typer.Exit(1)
            except FileNotFoundError:
                progress.update(task, completed=100)
                console.print(
                    "[yellow]Warning:[/yellow] No Canada data found. "
                    "Run 'worldenergydata canada collect' first."
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


@app.command("validate-uwi")
def validate_uwi(
    uwi: str = typer.Argument(
        ..., help="Canadian UWI to validate (e.g., '100/06-01-048-09W4/0')"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed validation information"
    ),
) -> None:
    """
    Validate and parse a Canadian UWI.

    Checks if the provided Unique Well Identifier follows Canadian
    format standards and displays parsed components.

    Examples:
        worldenergydata canada validate-uwi 100/06-01-048-09W4/0
        worldenergydata canada validate-uwi 100062604809W400
        worldenergydata canada validate-uwi 200D096062305W600
    """
    try:
        # UWI Format: LSD-SEC-TWP-RGE-MER/EVENT
        # Example: 100/06-01-048-09W4/0
        # 1 = Location Exception Code
        # 00 = Unique Event Sequence
        # 06 = Legal Subdivision (LSD)
        # 01 = Section
        # 048 = Township
        # 09 = Range
        # W4 = Meridian (West of 4th)
        # 0 = Event Sequence

        validation_result = {
            "valid": False,
            "format": None,
            "location_exception": None,
            "unique_event": None,
            "lsd": None,
            "section": None,
            "township": None,
            "range": None,
            "meridian": None,
            "event_sequence": None,
            "errors": [],
        }

        # Remove common separators for parsing
        cleaned = uwi.replace("/", "").replace("-", "").replace(" ", "").upper()

        # Check minimum length
        if len(cleaned) < 14:
            validation_result["errors"].append(
                f"UWI too short: {len(cleaned)} characters (minimum 14)"
            )
        elif len(cleaned) > 16:
            validation_result["errors"].append(
                f"UWI too long: {len(cleaned)} characters (maximum 16)"
            )
        else:
            try:
                # Parse UWI components
                # Standard format: LEEAABBCCCDDWMMS
                # L = Location Exception Code (1 digit)
                # EE = Unique Event Sequence (2 digits)
                # AA = LSD (2 digits)
                # BB = Section (2 digits)
                # CCC = Township (3 digits)
                # DD = Range (2 digits)
                # W = Direction (W or E)
                # MM = Meridian (1-6)
                # S = Event Sequence (1 digit, optional)

                idx = 0
                validation_result["location_exception"] = cleaned[idx]
                idx += 1

                validation_result["unique_event"] = cleaned[idx : idx + 2]
                idx += 2

                validation_result["lsd"] = cleaned[idx : idx + 2]
                idx += 2

                validation_result["section"] = cleaned[idx : idx + 2]
                idx += 2

                validation_result["township"] = cleaned[idx : idx + 3]
                idx += 3

                validation_result["range"] = cleaned[idx : idx + 2]
                idx += 2

                # Direction and meridian
                if idx < len(cleaned):
                    direction_meridian = cleaned[idx:]
                    if direction_meridian.startswith(
                        "W"
                    ) or direction_meridian.startswith("E"):
                        validation_result["meridian"] = direction_meridian[:2]
                        if len(direction_meridian) > 2:
                            validation_result["event_sequence"] = direction_meridian[2:]
                    else:
                        validation_result["errors"].append(
                            f"Invalid direction: expected W or E, got '{direction_meridian[0]}'"
                        )

                # Validate numeric fields
                numeric_fields = [
                    ("location_exception", 1),
                    ("unique_event", 2),
                    ("lsd", 2),
                    ("section", 2),
                    ("township", 3),
                    ("range", 2),
                ]

                for field_name, expected_len in numeric_fields:
                    value = validation_result[field_name]
                    if value and not value.isdigit():
                        validation_result["errors"].append(
                            f"Invalid {field_name}: '{value}' (must be numeric)"
                        )

                # Validate LSD (1-16)
                if validation_result["lsd"] and validation_result["lsd"].isdigit():
                    lsd_val = int(validation_result["lsd"])
                    if lsd_val < 1 or lsd_val > 16:
                        validation_result["errors"].append(
                            f"Invalid LSD: {lsd_val} (must be 1-16)"
                        )

                # Validate Section (1-36)
                if (
                    validation_result["section"]
                    and validation_result["section"].isdigit()
                ):
                    sec_val = int(validation_result["section"])
                    if sec_val < 1 or sec_val > 36:
                        validation_result["errors"].append(
                            f"Invalid section: {sec_val} (must be 1-36)"
                        )

                # Validate Meridian
                if validation_result["meridian"]:
                    mer_num = (
                        validation_result["meridian"][1:]
                        if len(validation_result["meridian"]) > 1
                        else ""
                    )
                    if mer_num and mer_num.isdigit():
                        mer_val = int(mer_num)
                        if mer_val < 1 or mer_val > 6:
                            validation_result["errors"].append(
                                f"Invalid meridian: {mer_val} (must be 1-6)"
                            )

                if not validation_result["errors"]:
                    validation_result["valid"] = True
                    validation_result["format"] = "DLS"  # Dominion Land Survey

            except (IndexError, ValueError) as e:
                validation_result["errors"].append(f"Parse error: {str(e)}")

        # Display results
        if validation_result["valid"]:
            console.print(
                Panel(
                    f"[bold green]Valid Canadian UWI[/bold green]\n\n"
                    f"Input: {uwi}\n"
                    f"Format: {validation_result['format']} (Dominion Land Survey)",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]Invalid UWI[/bold red]\n\n"
                    f"Input: {uwi}\n"
                    f"Errors: {'; '.join(validation_result['errors'])}",
                    border_style="red",
                )
            )

        # Show parsed components
        components_table = Table(
            title="UWI Components", show_header=True, header_style="bold cyan"
        )
        components_table.add_column("Component")
        components_table.add_column("Value")
        components_table.add_column("Description")

        if validation_result["location_exception"]:
            components_table.add_row(
                "Location Exception",
                validation_result["location_exception"],
                "Surface location indicator",
            )
        if validation_result["unique_event"]:
            components_table.add_row(
                "Unique Event",
                validation_result["unique_event"],
                "Unique event sequence",
            )
        if validation_result["lsd"]:
            components_table.add_row(
                "LSD", validation_result["lsd"], "Legal Subdivision (1-16)"
            )
        if validation_result["section"]:
            components_table.add_row(
                "Section", validation_result["section"], "Section (1-36)"
            )
        if validation_result["township"]:
            components_table.add_row(
                "Township", validation_result["township"], "Township number"
            )
        if validation_result["range"]:
            components_table.add_row(
                "Range", validation_result["range"], "Range number"
            )
        if validation_result["meridian"]:
            components_table.add_row(
                "Meridian", validation_result["meridian"], "West of meridian (W1-W6)"
            )
        if validation_result["event_sequence"]:
            components_table.add_row(
                "Event Sequence",
                validation_result["event_sequence"],
                "Event sequence code",
            )

        console.print(components_table)

        # Format examples
        if verbose or not validation_result["valid"]:
            console.print("\n[dim]Valid Canadian UWI formats:[/dim]")
            console.print("[dim]  100/06-01-048-09W4/0  (standard DLS format)[/dim]")
            console.print("[dim]  100062604809W400     (compact format)[/dim]")
            console.print("[dim]  200D096062305W600    (with event code)[/dim]")
            console.print("\n[dim]Components: L-EE/AA-BB-CCC-DD-WM/S[/dim]")
            console.print("[dim]  L = Location Exception, EE = Event, AA = LSD[/dim]")
            console.print("[dim]  BB = Section, CCC = Township, DD = Range[/dim]")
            console.print("[dim]  W = Direction, M = Meridian, S = Sequence[/dim]")

        if not validation_result["valid"]:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def status(
    data_path: Path = typer.Option(
        Path("./data/canada"), "--data-path", "-d", help="Path to Canada data directory"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed status information"
    ),
) -> None:
    """
    Show Canadian data status.

    Displays information about available Canadian oil and gas data
    including file counts, data freshness, and province coverage.

    Examples:
        worldenergydata canada status
        worldenergydata canada status --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading Canada data status...", total=100)

            status_data = {
                "data_files": 0,
                "data_size_mb": 0,
                "data_types": {},
                "provinces_covered": [],
                "last_updated": "Unknown",
            }

            progress.update(
                task, advance=30, description="[cyan]Checking data directories..."
            )

            if data_path.exists():
                total_files = 0
                total_size = 0
                data_types_found = {}
                provinces_found = set()

                for f in data_path.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_size += f.stat().st_size

                        stem = f.stem.lower()
                        parent = f.parent.name.lower()

                        # Check for data types
                        for dtype in ["wells", "production", "facilities", "licenses"]:
                            if dtype in stem or dtype in parent:
                                data_types_found[dtype] = (
                                    data_types_found.get(dtype, 0) + 1
                                )
                                break

                        # Check for provinces
                        for prov in ["ab", "alberta", "bc", "british_columbia"]:
                            if prov in stem or prov in parent:
                                if prov in ["ab", "alberta"]:
                                    provinces_found.add("AB")
                                elif prov in ["bc", "british_columbia"]:
                                    provinces_found.add("BC")

                        # Track last modified
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
                status_data["provinces_covered"] = sorted(list(provinces_found))

            progress.update(task, advance=70, description="[cyan]Formatting results...")

        # Create status table
        table = Table(
            title="Canada Data Status", show_header=True, header_style="bold cyan"
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
            if status_data["provinces_covered"]:
                province_names = [
                    PROVINCE_CONFIG[p]["name"] for p in status_data["provinces_covered"]
                ]
                table.add_row("Provinces Covered", ", ".join(province_names))
        else:
            table.add_row("Data Files", "[yellow]No data files found[/yellow]")

        table.add_row("", "")
        table.add_row("Data Directory", str(data_path))

        console.print(table)

        # Show provinces breakdown
        if verbose:
            provinces_table = Table(
                title="Province Coverage", show_header=True, header_style="bold cyan"
            )
            provinces_table.add_column("Province")
            provinces_table.add_column("Regulator")
            provinces_table.add_column("Status")

            for prov_code, prov_info in PROVINCE_CONFIG.items():
                if prov_code in status_data["provinces_covered"]:
                    provinces_table.add_row(
                        prov_info["name"],
                        prov_info["full_name"],
                        "[green]Data Available[/green]",
                    )
                else:
                    provinces_table.add_row(
                        prov_info["name"],
                        prov_info["full_name"],
                        "[yellow]No data[/yellow]",
                    )

            console.print(provinces_table)

        # Show data types breakdown
        if status_data["data_types"] and verbose:
            types_table = Table(
                title="Data Types Breakdown", show_header=True, header_style="bold cyan"
            )
            types_table.add_column("Data Type")
            types_table.add_column("Files", justify="right")
            types_table.add_column("Status")

            all_types = ["wells", "production", "facilities", "licenses"]
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

        console.print(
            "\n[dim]Use 'worldenergydata canada collect' to download data[/dim]"
        )
        console.print("[dim]Use 'worldenergydata canada analyze' to run analysis[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.callback()
def callback() -> None:
    """
    Canadian oil and gas data operations.

    Access Canadian oil and gas data from AER (Alberta Energy Regulator)
    and BCER (BC Energy Regulator) including well information,
    production statistics, facilities, and licenses.
    """
    pass
