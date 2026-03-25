# ABOUTME: CLI commands for Mexico CNH oil and gas data operations
# ABOUTME: Provides scrape, analyze, and validation commands for Mexican data

"""
Mexico CNH CLI Commands

Provides command-line interface for Mexican oil and gas data operations
including Selenium-based scraping from CNH SIH dashboard, open data downloads,
and Clave del Pozo (well key) validation.

Usage:
    worldenergydata mexico-cnh <command> [options]

Examples:
    worldenergydata mexico-cnh scrape --types production wells
    worldenergydata mexico-cnh download-open-data --output ./data/mexico_cnh
    worldenergydata mexico-cnh status --verbose
    worldenergydata mexico-cnh validate-clave 01-01-01-00001
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

# Create Mexico CNH Typer app
app = typer.Typer(
    name="mexico-cnh",
    help="Mexico CNH oil & gas data operations (Selenium scraping)",
    no_args_is_help=True,
)


class DataType(str, Enum):
    """Data type options for collection."""

    production = "production"
    wells = "wells"
    fields = "fields"
    contracts = "contracts"
    reserves = "reserves"
    all = "all"


class OutputFormat(str, Enum):
    """Output format options."""

    json = "json"
    parquet = "parquet"
    csv = "csv"
    excel = "excel"


class DataSource(str, Enum):
    """Data source options."""

    sih = "sih"  # Sistema de Informacion de Hidrocarburos (requires Selenium)
    open_data = "open_data"  # Datos Abiertos (direct download)
    all = "all"


# Data source configuration
DATA_SOURCES = {
    "sih": {
        "name": "SIH Dashboard",
        "full_name": "Sistema de Informacion de Hidrocarburos",
        "requires_selenium": True,
        "url": "https://sih.hidrocarburos.gob.mx",
    },
    "open_data": {
        "name": "Datos Abiertos",
        "full_name": "CNH Open Data Portal",
        "requires_selenium": False,
        "url": "https://datos.gob.mx/busca/organization/cnh",
    },
}


@app.command()
def scrape(
    data_types: List[DataType] = typer.Option(
        [DataType.production],
        "--types",
        "-t",
        help="Data types: production, wells, fields, contracts, reserves, all",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
    output: Path = typer.Option(
        Path("./data/mexico_cnh"),
        "--output",
        "-o",
        help="Output directory for scraped data",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.csv,
        "--format",
        "-f",
        help="Output format for scraped data",
    ),
    timeout: int = typer.Option(
        60,
        "--timeout",
        help="Page load timeout in seconds",
    ),
    start_date: Optional[str] = typer.Option(
        None,
        "--start-date",
        help="Start date for data scraping (YYYY-MM-DD)",
    ),
    end_date: Optional[str] = typer.Option(
        None,
        "--end-date",
        help="End date for data scraping (YYYY-MM-DD)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """
    Scrape data from CNH SIH dashboard (requires Selenium).

    Downloads oil and gas data from the CNH Sistema de Informacion de
    Hidrocarburos (SIH) dashboard using Selenium WebDriver.

    Note: Requires Chrome/Chromium and ChromeDriver to be installed.

    Examples:
        worldenergydata mexico-cnh scrape --types production
        worldenergydata mexico-cnh scrape --types wells fields --no-headless
        worldenergydata mexico-cnh scrape --types all --format csv
    """
    try:
        # Convert 'all' to all data types
        types_to_scrape = []
        for t in data_types:
            if t == DataType.all:
                types_to_scrape = [
                    DataType.production.value,
                    DataType.wells.value,
                    DataType.fields.value,
                    DataType.contracts.value,
                    DataType.reserves.value,
                ]
                break
            else:
                types_to_scrape.append(t.value)

        # Display scraping parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("Data Types", ", ".join(types_to_scrape))
        params_table.add_row("Browser Mode", "Headless" if headless else "Visible")
        params_table.add_row("Output Directory", str(output))
        params_table.add_row("Output Format", format.value)
        params_table.add_row("Timeout", f"{timeout} seconds")
        if start_date:
            params_table.add_row("Start Date", start_date)
        if end_date:
            params_table.add_row("End Date", end_date)

        console.print(
            Panel(params_table, title="Scraping Parameters", border_style="cyan")
        )

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Initializing Mexico CNH data scraping...", total=100
            )

            try:
                from worldenergydata.mexico_cnh.mexico_cnh import MexicoCNH

                progress.update(
                    task, advance=10, description="[cyan]Loading Mexico CNH module..."
                )

                # Build configuration
                cfg = {
                    "basename": "mexico_cnh",
                    "module": "mexico_cnh",
                    "data_types": types_to_scrape,
                    "scraper": {
                        "headless": headless,
                        "timeout": timeout,
                    },
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
                    task, advance=20, description="[cyan]Initializing Selenium..."
                )

                # Run the scraping through Mexico CNH router
                mexico = MexicoCNH()
                result_cfg = mexico.router(cfg)

                progress.update(task, advance=50, description="[cyan]Scraping data...")

                scraped = result_cfg.get("mexico_cnh", {}).get("data_scraped", [])

                progress.update(
                    task, advance=20, description="[cyan]Completing scraping..."
                )

                if verbose:
                    console.print(f"\n[dim]Configuration result: {result_cfg}[/dim]")

                # Create results table
                results_table = Table(
                    title="Scraping Results",
                    show_header=True,
                    header_style="bold cyan",
                )
                results_table.add_column("Data Type")
                results_table.add_column("Status")
                results_table.add_column("Records", justify="right")

                for dt in types_to_scrape:
                    if dt in scraped or any(dt in s for s in scraped):
                        record_count = result_cfg.get("mexico_cnh", {}).get(
                            f"{dt}_count", "N/A"
                        )
                        results_table.add_row(
                            dt.capitalize(),
                            "[green]Scraped[/green]",
                            str(record_count),
                        )
                    else:
                        results_table.add_row(
                            dt.capitalize(),
                            "[yellow]Pending[/yellow]",
                            "-",
                        )

                console.print(results_table)
                console.print(f"\n[green]Data scraping completed successfully[/green]")
                console.print(f"[dim]Data saved to: {output}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import Mexico CNH module: {e}"
                )
                console.print(
                    "[dim]Ensure Selenium and ChromeDriver are installed.[/dim]"
                )
                console.print(
                    "[dim]Install with: pip install selenium webdriver-manager[/dim]"
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


@app.command("download-open-data")
def download_open_data(
    data_types: List[DataType] = typer.Option(
        [DataType.production],
        "--types",
        "-t",
        help="Data types to download: production, wells, fields, contracts, reserves, all",
    ),
    output: Path = typer.Option(
        Path("./data/mexico_cnh/open_data"),
        "--output",
        "-o",
        help="Output directory for downloaded data",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.csv,
        "--format",
        "-f",
        help="Output format for downloaded data",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """
    Download data from CNH open data portal (no Selenium needed).

    Downloads oil and gas data from the CNH Datos Abiertos portal
    using direct HTTP requests. This is faster than scraping but
    may have less current data than the SIH dashboard.

    Examples:
        worldenergydata mexico-cnh download-open-data
        worldenergydata mexico-cnh download-open-data --types production wells
        worldenergydata mexico-cnh download-open-data --format parquet
    """
    try:
        # Convert 'all' to all data types
        types_to_download = []
        for t in data_types:
            if t == DataType.all:
                types_to_download = [
                    DataType.production.value,
                    DataType.wells.value,
                    DataType.fields.value,
                    DataType.contracts.value,
                    DataType.reserves.value,
                ]
                break
            else:
                types_to_download.append(t.value)

        # Display download parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("Data Types", ", ".join(types_to_download))
        params_table.add_row("Output Directory", str(output))
        params_table.add_row("Output Format", format.value)
        params_table.add_row("Source", DATA_SOURCES["open_data"]["full_name"])

        console.print(
            Panel(params_table, title="Download Parameters", border_style="cyan")
        )

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Downloading from CNH Open Data portal...", total=100
            )

            try:
                from worldenergydata.mexico_cnh.mexico_cnh import MexicoCNH

                progress.update(
                    task, advance=20, description="[cyan]Loading Mexico CNH module..."
                )

                # Build configuration for open data download
                cfg = {
                    "basename": "mexico_cnh",
                    "module": "mexico_cnh",
                    "source": "open_data",
                    "data_types": types_to_download,
                    "output": {
                        "directory": str(output),
                        "format": format.value,
                    },
                }

                progress.update(
                    task, advance=30, description="[cyan]Connecting to CNH..."
                )

                # Run the download through Mexico CNH router
                mexico = MexicoCNH()
                result_cfg = mexico.router(cfg)

                progress.update(
                    task, advance=30, description="[cyan]Processing data..."
                )

                downloaded = result_cfg.get("mexico_cnh", {}).get("data_downloaded", [])

                progress.update(
                    task, advance=20, description="[cyan]Completing download..."
                )

                if verbose:
                    console.print(f"\n[dim]Configuration result: {result_cfg}[/dim]")

                # Create results table
                results_table = Table(
                    title="Download Results",
                    show_header=True,
                    header_style="bold cyan",
                )
                results_table.add_column("Data Type")
                results_table.add_column("Status")
                results_table.add_column("File Size", justify="right")

                for dt in types_to_download:
                    if dt in downloaded:
                        file_size = result_cfg.get("mexico_cnh", {}).get(
                            f"{dt}_size", "N/A"
                        )
                        results_table.add_row(
                            dt.capitalize(),
                            "[green]Downloaded[/green]",
                            str(file_size),
                        )
                    else:
                        results_table.add_row(
                            dt.capitalize(),
                            "[yellow]Pending[/yellow]",
                            "-",
                        )

                console.print(results_table)
                console.print(f"\n[green]Download completed successfully[/green]")
                console.print(f"[dim]Data saved to: {output}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import Mexico CNH module: {e}"
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


@app.command("validate-clave")
def validate_clave(
    clave: str = typer.Argument(
        ...,
        help="Mexican well key (Clave del Pozo) to validate (e.g., '01-01-01-00001')",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed validation information",
    ),
) -> None:
    """
    Validate and parse a Mexican well key (Clave del Pozo).

    Checks if the provided well key follows CNH format standards
    and displays parsed components including region, basin, and well number.

    Examples:
        worldenergydata mexico-cnh validate-clave 01-01-01-00001
        worldenergydata mexico-cnh validate-clave 02-03-05-00123 --verbose
    """
    try:
        # Mexican well key format: RR-CC-AA-NNNNN
        # RR = Region code (01-07)
        # CC = Basin/Cuenca code
        # AA = Area/Activo code
        # NNNNN = Well number (5 digits)

        validation_result = {
            "valid": False,
            "format": None,
            "region_code": None,
            "region_name": None,
            "basin_code": None,
            "area_code": None,
            "well_number": None,
            "errors": [],
        }

        # Region names mapping
        regions = {
            "01": "Noroeste",
            "02": "Norte",
            "03": "Sur",
            "04": "Golfo de Mexico Norte",
            "05": "Golfo de Mexico Sur",
            "06": "Sureste Terrestre",
            "07": "Aguas Profundas",
        }

        # Remove common separators for parsing
        cleaned = clave.replace("-", "").replace(" ", "").upper()

        # Check length
        if len(cleaned) < 11:
            validation_result["errors"].append(
                f"Clave too short: {len(cleaned)} characters (expected 11+)"
            )
        elif len(cleaned) > 14:
            validation_result["errors"].append(
                f"Clave too long: {len(cleaned)} characters (expected 11-14)"
            )
        else:
            try:
                # Parse clave components
                # Standard format: RRCCAANNNNN
                idx = 0

                validation_result["region_code"] = cleaned[idx : idx + 2]
                idx += 2

                validation_result["basin_code"] = cleaned[idx : idx + 2]
                idx += 2

                validation_result["area_code"] = cleaned[idx : idx + 2]
                idx += 2

                validation_result["well_number"] = cleaned[idx:]

                # Validate region code
                region = validation_result["region_code"]
                if region in regions:
                    validation_result["region_name"] = regions[region]
                else:
                    validation_result["errors"].append(
                        f"Invalid region code: {region} (expected 01-07)"
                    )

                # Validate numeric fields
                for field_name, value in [
                    ("basin_code", validation_result["basin_code"]),
                    ("area_code", validation_result["area_code"]),
                    ("well_number", validation_result["well_number"]),
                ]:
                    if value and not value.isdigit():
                        validation_result["errors"].append(
                            f"Invalid {field_name}: '{value}' (must be numeric)"
                        )

                # Validate well number length
                well_num = validation_result["well_number"]
                if well_num and len(well_num) < 5:
                    validation_result["errors"].append(
                        f"Well number too short: {len(well_num)} digits (expected 5+)"
                    )

                if not validation_result["errors"]:
                    validation_result["valid"] = True
                    validation_result["format"] = "CNH Standard"

            except (IndexError, ValueError) as e:
                validation_result["errors"].append(f"Parse error: {str(e)}")

        # Display results
        if validation_result["valid"]:
            console.print(
                Panel(
                    f"[bold green]Valid Mexican Well Key (Clave del Pozo)[/bold green]\n\n"
                    f"Input: {clave}\n"
                    f"Format: {validation_result['format']}",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]Invalid Clave del Pozo[/bold red]\n\n"
                    f"Input: {clave}\n"
                    f"Errors: {'; '.join(validation_result['errors'])}",
                    border_style="red",
                )
            )

        # Show parsed components
        components_table = Table(
            title="Clave Components", show_header=True, header_style="bold cyan"
        )
        components_table.add_column("Component")
        components_table.add_column("Value")
        components_table.add_column("Description")

        if validation_result["region_code"]:
            components_table.add_row(
                "Region Code",
                validation_result["region_code"],
                validation_result.get("region_name", "Unknown region"),
            )
        if validation_result["basin_code"]:
            components_table.add_row(
                "Basin Code",
                validation_result["basin_code"],
                "Cuenca (Basin) identifier",
            )
        if validation_result["area_code"]:
            components_table.add_row(
                "Area Code",
                validation_result["area_code"],
                "Activo (Area/Asset) identifier",
            )
        if validation_result["well_number"]:
            components_table.add_row(
                "Well Number",
                validation_result["well_number"],
                "Unique well sequence number",
            )

        console.print(components_table)

        # Format examples
        if verbose or not validation_result["valid"]:
            console.print("\n[dim]Valid Mexican Clave del Pozo formats:[/dim]")
            console.print("[dim]  01-01-01-00001  (standard format with dashes)[/dim]")
            console.print("[dim]  0101010001      (compact format)[/dim]")
            console.print("\n[dim]Components: RR-CC-AA-NNNNN[/dim]")
            console.print("[dim]  RR = Region code (01-07)[/dim]")
            console.print("[dim]  CC = Basin/Cuenca code[/dim]")
            console.print("[dim]  AA = Area/Activo code[/dim]")
            console.print("[dim]  NNNNN = Well sequence number[/dim]")
            console.print("\n[dim]Regions:[/dim]")
            for code, name in regions.items():
                console.print(f"[dim]  {code} = {name}[/dim]")

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
        Path("./data/mexico_cnh"),
        "--data-path",
        "-d",
        help="Path to Mexico CNH data directory",
    ),
    check_selenium: bool = typer.Option(
        False,
        "--check-selenium",
        help="Check if Selenium and ChromeDriver are available",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed status information",
    ),
) -> None:
    """
    Show Mexico CNH data status.

    Displays information about available Mexican oil and gas data
    including file counts, data freshness, and Selenium availability.

    Examples:
        worldenergydata mexico-cnh status
        worldenergydata mexico-cnh status --check-selenium
        worldenergydata mexico-cnh status --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Loading Mexico CNH data status...", total=100
            )

            status_data = {
                "data_files": 0,
                "data_size_mb": 0,
                "data_types": {},
                "sources": [],
                "last_updated": "Unknown",
                "selenium_available": None,
            }

            progress.update(
                task, advance=30, description="[cyan]Checking data directories..."
            )

            if data_path.exists():
                total_files = 0
                total_size = 0
                data_types_found = {}
                sources_found = set()

                for f in data_path.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_size += f.stat().st_size

                        stem = f.stem.lower()
                        parent = f.parent.name.lower()

                        # Check for data types
                        for dtype in [
                            "production",
                            "wells",
                            "fields",
                            "contracts",
                            "reserves",
                        ]:
                            if dtype in stem or dtype in parent:
                                data_types_found[dtype] = (
                                    data_types_found.get(dtype, 0) + 1
                                )
                                break

                        # Check for sources
                        if "sih" in stem or "sih" in parent:
                            sources_found.add("sih")
                        if "open_data" in stem or "open_data" in parent:
                            sources_found.add("open_data")

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
                status_data["sources"] = sorted(list(sources_found))

            progress.update(
                task, advance=40, description="[cyan]Checking dependencies..."
            )

            # Check Selenium availability if requested
            if check_selenium:
                try:
                    from selenium import webdriver
                    from selenium.webdriver.chrome.service import Service

                    status_data["selenium_available"] = True
                except ImportError:
                    status_data["selenium_available"] = False

            progress.update(task, advance=30, description="[cyan]Formatting results...")

        # Create status table
        table = Table(
            title="Mexico CNH Data Status",
            show_header=True,
            header_style="bold cyan",
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
            if status_data["sources"]:
                source_names = [DATA_SOURCES[s]["name"] for s in status_data["sources"]]
                table.add_row("Data Sources", ", ".join(source_names))
        else:
            table.add_row("Data Files", "[yellow]No data files found[/yellow]")

        table.add_row("", "")
        table.add_row("Data Directory", str(data_path))

        if status_data["selenium_available"] is not None:
            if status_data["selenium_available"]:
                table.add_row("Selenium", "[green]Available[/green]")
            else:
                table.add_row("Selenium", "[red]Not installed[/red]")

        console.print(table)

        # Show data sources info
        if verbose:
            sources_table = Table(
                title="Data Sources",
                show_header=True,
                header_style="bold cyan",
            )
            sources_table.add_column("Source")
            sources_table.add_column("Full Name")
            sources_table.add_column("Requires Selenium")
            sources_table.add_column("Status")

            for source_id, source_info in DATA_SOURCES.items():
                selenium_req = "Yes" if source_info["requires_selenium"] else "No"
                if source_id in status_data["sources"]:
                    status_str = "[green]Data Available[/green]"
                else:
                    status_str = "[yellow]No data[/yellow]"
                sources_table.add_row(
                    source_info["name"],
                    source_info["full_name"],
                    selenium_req,
                    status_str,
                )

            console.print(sources_table)

        # Show data types breakdown
        if status_data["data_types"] and verbose:
            types_table = Table(
                title="Data Types Breakdown",
                show_header=True,
                header_style="bold cyan",
            )
            types_table.add_column("Data Type")
            types_table.add_column("Files", justify="right")
            types_table.add_column("Status")

            all_types = ["production", "wells", "fields", "contracts", "reserves"]
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
            "\n[dim]Use 'worldenergydata mexico-cnh scrape' to scrape SIH data[/dim]"
        )
        console.print(
            "[dim]Use 'worldenergydata mexico-cnh download-open-data' for direct downloads[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.callback()
def callback() -> None:
    """
    Mexico CNH oil and gas data operations.

    Access Mexican oil and gas data from CNH (Comision Nacional de
    Hidrocarburos) including production statistics, well information,
    field data, and contract details.

    Data Sources:
        - SIH Dashboard: Requires Selenium for web scraping
        - Open Data Portal: Direct HTTP download (no Selenium)
    """
    pass
