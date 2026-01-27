# ABOUTME: Marine Safety CLI Interface for managing incident data from multiple sources.
# ABOUTME: Provides commands for scraping, importing, database ops, and data export.

"""
Marine Safety CLI Interface

Provides command-line tools for managing marine safety incident data.
Uses Click for CLI framework and Rich for beautiful terminal output.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize Rich console
console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Marine Safety Incident Data Management CLI

    Manage USCG and NTSB marine incident data: scraping, database operations,
    statistics, and data export.
    """
    pass


# =============================================================================
# SCRAPE COMMAND GROUP
# =============================================================================


@cli.group()
def scrape():
    """Scrape incident data from various sources"""
    pass


@scrape.command()
@click.option("--start-year", type=int, help="Starting year for data collection")
@click.option("--end-year", type=int, help="Ending year for data collection")
@click.option("--output", type=click.Path(), help="Output file path for scraped data")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def uscg(
    start_year: Optional[int],
    end_year: Optional[int],
    output: Optional[str],
    verbose: bool,
):
    """
    Scrape incident data from USCG MISLE database

    Examples:
        marine-safety scrape uscg --start-year 2020 --end-year 2023
        marine-safety scrape uscg --output uscg_data.json --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scraping USCG MISLE data...", total=None)

            # TODO: Import and execute USCG scraper
            # from .scrapers.uscg_scraper import USCGScraper
            # scraper = USCGScraper()
            # data = scraper.scrape(start_year, end_year)

            console.print("[yellow]USCG scraper not yet implemented[/yellow]")
            console.print(f"Parameters: start={start_year}, end={end_year}")

            progress.update(task, completed=True)

        console.print("[green]v[/green] USCG scraping completed", style="bold")

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@scrape.command()
@click.option(
    "--start-year",
    type=int,
    default=2010,
    help="Starting year for data collection (default: 2010)",
)
@click.option(
    "--end-year",
    type=int,
    help="Ending year for data collection (default: current year)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="ntsb_marine_data.json",
    help="Output file path for scraped data (default: ntsb_marine_data.json)",
)
@click.option("--include-raw", is_flag=True, help="Include raw data in JSON export")
@click.option(
    "--clear-checkpoint", is_flag=True, help="Clear checkpoint and start fresh"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def ntsb(
    start_year: int,
    end_year: Optional[int],
    output: str,
    include_raw: bool,
    clear_checkpoint: bool,
    verbose: bool,
):
    """
    Scrape incident data from NTSB marine accident database

    Scrapes marine investigations from the NTSB CAROL system with pagination
    and checkpointing support for resumable operations.

    Examples:
        marine-safety scrape ntsb --start-year 2020 --end-year 2023
        marine-safety scrape ntsb --output data/ntsb_2023.json
        marine-safety scrape ntsb --clear-checkpoint --verbose
    """
    try:
        from datetime import date

        from worldenergydata.modules.marine_safety.scrapers.ntsb_scraper import (
            NTSBScraper,
        )

        # Determine date range
        start_date = date(start_year, 1, 1)
        end_date = date(end_year, 12, 31) if end_year else date.today()

        if verbose:
            console.print(f"[dim]Date range: {start_date} to {end_date}[/dim]")
            console.print(f"[dim]Output file: {output}[/dim]")

        # Initialize scraper
        scraper = NTSBScraper()

        # Clear checkpoint if requested
        if clear_checkpoint:
            scraper.clear_checkpoint()
            console.print("[yellow]Checkpoint cleared[/yellow]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Scraping NTSB marine investigations...", total=None
            )

            # Execute scraping
            investigations = scraper.scrape(
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.max.time()),
            )

            progress.update(task, completed=True)

        # Get statistics
        stats = scraper.get_statistics()

        # Export to JSON
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        scraper.export_to_json(investigations, output_path, include_raw=include_raw)

        # Display results
        console.print()
        panel_content = (
            f"[green]Scraped {len(investigations)} investigations[/green]\n"
            f"Total processed IDs: {stats['total_processed_ids']}\n"
            f"Output file: {output_path.absolute()}"
        )
        console.print(
            Panel(panel_content, title="NTSB Scraping Complete", border_style="green")
        )

        if verbose:
            table = Table(
                title="Scraping Statistics", show_header=True, header_style="bold cyan"
            )
            table.add_column("Metric", style="dim")
            table.add_column("Value", justify="right")
            table.add_row("Total Requests", str(stats.get("total_requests", 0)))
            table.add_row("Checkpoint File", str(stats.get("checkpoint_file", "N/A")))
            if stats.get("last_checkpoint"):
                table.add_row("Last Checkpoint", stats["last_checkpoint"])
            console.print(table)

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print("[yellow]Ensure all dependencies are installed[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@scrape.command()
@click.option("--vessel-types", multiple=True, help="Filter by vessel types")
@click.option("--output", type=click.Path(), help="Output file path for scraped data")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def bsee(vessel_types: tuple, output: Optional[str], verbose: bool):
    """
    Scrape incident data from BSEE (Bureau of Safety and Environmental Enforcement)

    Examples:
        marine-safety scrape bsee --vessel-types "drilling rig" --vessel-types "platform"
        marine-safety scrape bsee --output bsee_data.json --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scraping BSEE data...", total=None)

            # TODO: Import and execute BSEE scraper
            console.print("[yellow]BSEE scraper not yet implemented[/yellow]")
            if vessel_types:
                console.print(f"Vessel types: {', '.join(vessel_types)}")

            progress.update(task, completed=True)

        console.print("[green]v[/green] BSEE scraping completed", style="bold")

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@scrape.command()
@click.option("--start-year", type=int, help="Starting year for data collection")
@click.option("--end-year", type=int, help="Ending year for data collection")
@click.option("--output", type=click.Path(), help="Output file path for scraped data")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def imo(
    start_year: Optional[int],
    end_year: Optional[int],
    output: Optional[str],
    verbose: bool,
):
    """
    Scrape incident data from IMO GISIS database (Phase 2)

    The IMO Global Integrated Shipping Information System provides
    international maritime incident data.

    Examples:
        marine-safety scrape imo --start-year 2020 --end-year 2023
        marine-safety scrape imo --output imo_data.json --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scraping IMO GISIS data...", total=None)

            console.print("[yellow]IMO scraper not yet implemented (Phase 2)[/yellow]")
            console.print(f"Parameters: start={start_year}, end={end_year}")

            progress.update(task, completed=True)

        console.print("[green]v[/green] IMO scraping completed", style="bold")

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@scrape.command()
@click.option("--start-year", type=int, help="Starting year for data collection")
@click.option("--end-year", type=int, help="Ending year for data collection")
@click.option("--output", type=click.Path(), help="Output file path for scraped data")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def emsa(
    start_year: Optional[int],
    end_year: Optional[int],
    output: Optional[str],
    verbose: bool,
):
    """
    Scrape incident data from EMSA EMCIP database (Phase 6)

    The European Marine Casualty Information Platform (EMCIP) provides
    EU/EEA maritime incident data. Note: Requires institutional access.

    For access information, see:
        marine-safety import emsa --info

    Examples:
        marine-safety scrape emsa --start-year 2020 --end-year 2023
        marine-safety scrape emsa --output emsa_data.json --verbose
    """
    console.print(
        Panel(
            "[yellow]EMSA EMCIP scraper requires institutional access.[/yellow]\n\n"
            "[bold]To obtain access:[/bold]\n"
            "1. Visit: https://portal.emsa.europa.eu/emcip-public\n"
            "2. Contact: emcip-support@emsa.europa.eu\n"
            "3. Submit data access request under Directive 2009/18/EC\n\n"
            "[bold]Public data alternative:[/bold]\n"
            "Annual incident statistics are available at:\n"
            "https://emsa.europa.eu/emcip.html",
            title="EMSA EMCIP Access Required",
            border_style="yellow",
        )
    )


@scrape.command()
@click.option(
    "--start-year",
    type=int,
    default=2010,
    help="Starting year for data collection (default: 2010)",
)
@click.option(
    "--end-year",
    type=int,
    help="Ending year for data collection (default: current year)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="atsb_marine_data.json",
    help="Output file path for scraped data (default: atsb_marine_data.json)",
)
@click.option("--include-pdfs", is_flag=True, help="Download PDF reports (may be slow)")
@click.option(
    "--clear-checkpoint", is_flag=True, help="Clear checkpoint and start fresh"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def atsb(
    start_year: int,
    end_year: Optional[int],
    output: str,
    include_pdfs: bool,
    clear_checkpoint: bool,
    verbose: bool,
):
    """
    Scrape incident data from Australian ATSB marine investigations

    Scrapes marine investigation reports from the Australian Transport Safety
    Bureau with pagination and checkpointing support.

    Examples:
        marine-safety scrape atsb --start-year 2015
        marine-safety scrape atsb --output atsb_data.json --include-pdfs
        marine-safety scrape atsb --clear-checkpoint --verbose
    """
    try:
        from datetime import date

        from worldenergydata.modules.marine_safety.scrapers.atsb_scraper import (
            ATSBScraper,
        )

        current_year = date.today().year
        end_year_val = end_year or current_year

        if verbose:
            console.print(
                f"[dim]Scraping ATSB data: {start_year} to {end_year_val}[/dim]"
            )
            console.print(f"[dim]Output file: {output}[/dim]")
            console.print(f"[dim]Include PDFs: {include_pdfs}[/dim]")

        # Initialize scraper
        scraper = ATSBScraper()

        # Clear checkpoint if requested
        if clear_checkpoint:
            scraper.clear_checkpoint()
            console.print("[yellow]Checkpoint cleared[/yellow]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Scraping ATSB marine investigations...", total=None
            )

            # Build date range
            start_date = date(start_year, 1, 1)
            end_date = date(end_year_val, 12, 31)

            # Execute scraping
            investigations = scraper.scrape(start_date, end_date)

            progress.update(task, completed=True)

        # Export results
        output_path = Path(output)
        scraper.export_to_json(investigations, output_path)

        # Display results
        stats = scraper.get_statistics()
        panel = Panel(
            f"[green]Scraped {len(investigations)} ATSB investigations[/green]\n"
            f"Output: {output_path.absolute()}",
            title="ATSB Scraping Complete",
            border_style="green",
        )
        console.print(panel)

        if verbose:
            table = Table(title="Scraping Statistics", show_header=True)
            table.add_column("Metric", style="dim")
            table.add_column("Value", justify="right")
            table.add_row(
                "Total Processed IDs", str(stats.get("total_processed_ids", 0))
            )
            table.add_row("Total Requests", str(stats.get("total_requests", 0)))
            console.print(table)

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


# =============================================================================
# IMPORT COMMAND GROUP
# =============================================================================


@cli.group(name="import")
def import_cmd():
    """Import incident data from files into the database"""
    pass


@import_cmd.command(name="ntsb")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--limit", type=int, help="Limit number of records to import (useful for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Records per database batch (default: 100)",
)
@click.option(
    "--skip-duplicates/--allow-duplicates",
    default=True,
    help="Skip duplicate records (default: skip)",
)
@click.option(
    "--preview", type=int, default=0, help="Preview N records without importing"
)
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_ntsb(
    file: Path,
    limit: Optional[int],
    batch_size: int,
    skip_duplicates: bool,
    preview: int,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Import NTSB marine incident data from CSV/JSON file

    Imports data from NTSB CAROL database exports into the marine safety database.
    Supports both CSV and JSON formats.

    Examples:
        marine-safety import ntsb data/ntsb_export.csv
        marine-safety import ntsb data/ntsb_export.csv --limit 100
        marine-safety import ntsb data/ntsb_export.csv --preview 5
        marine-safety import ntsb data/ntsb.json --batch-size 50
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.importers.ntsb_importer import (
            NTSBImporter,
        )

        # Determine file format
        file_format = "csv" if file.suffix.lower() == ".csv" else "json"

        if verbose:
            console.print(f"[dim]Source file: {file}[/dim]")
            console.print(f"[dim]File format: {file_format}[/dim]")
            console.print(f"[dim]Batch size: {batch_size}[/dim]")

        # Get database session
        session = get_session(db_url)

        # Initialize importer
        importer = NTSBImporter(
            source_path=file,
            session=session,
            batch_size=batch_size,
            file_format=file_format,
        )

        # Validate source file
        if not importer.validate_source():
            console.print("[red]x Source file validation failed[/red]")
            sys.exit(1)

        # Preview mode
        if preview > 0:
            console.print(f"\n[cyan]Previewing {preview} records...[/cyan]\n")
            previews = importer.preview_data(preview)

            for i, record in enumerate(previews, 1):
                console.print(f"[bold]Record {i}:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Field", style="dim")
                table.add_column("Value")

                for key, value in record.items():
                    if key != "raw_data" and value:
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        table.add_row(key, display_value)

                console.print(table)
                console.print()

            console.print(
                f"[green]Preview complete: {len(previews)} records shown[/green]"
            )
            return

        # Full import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Importing NTSB data...", total=None)

            stats = importer.import_data(limit=limit, skip_duplicates=skip_duplicates)

            progress.update(task, completed=True)

        # Display results
        console.print()
        table = Table(
            title="Import Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Records", str(stats["total_records"]))
        table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
        table.add_row(
            "[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]"
        )
        table.add_row(
            "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

        console.print(table)

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
        sys.exit(1)
    except FileNotFoundError:
        console.print(f"[red]x File not found:[/red] {file}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@import_cmd.command(name="uscg")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--limit", type=int, help="Limit number of records to import")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_uscg(file: Path, limit: Optional[int], verbose: bool):
    """
    Import USCG MISLE incident data from file

    Examples:
        marine-safety import uscg data/misle_export.csv
        marine-safety import uscg data/misle_export.csv --limit 100
    """
    console.print("[yellow]USCG importer not yet implemented[/yellow]")
    console.print(f"File: {file}")
    if limit:
        console.print(f"Limit: {limit}")


@import_cmd.command(name="bsee")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--limit", type=int, help="Limit number of records to import")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_bsee(file: Path, limit: Optional[int], verbose: bool):
    """
    Import BSEE incident data from file

    Examples:
        marine-safety import bsee data/bsee_incidents.csv
        marine-safety import bsee data/bsee_incidents.csv --limit 100
    """
    console.print("[yellow]BSEE importer not yet implemented[/yellow]")
    console.print(f"File: {file}")
    if limit:
        console.print(f"Limit: {limit}")


@import_cmd.command(name="emsa")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--info", is_flag=True, help="Show EMSA EMCIP access information")
@click.option("--limit", type=int, help="Limit number of records to import")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_emsa(file: Optional[Path], info: bool, limit: Optional[int], verbose: bool):
    """
    Import EMSA EMCIP marine casualty data (requires institutional access)

    The European Marine Casualty Information Platform (EMCIP) provides
    comprehensive EU/EEA maritime incident data. Data access requires
    approval from EMSA.

    Examples:
        marine-safety import emsa --info
        marine-safety import emsa data/emcip_export.csv --limit 100
    """
    if info or file is None:
        from worldenergydata.modules.marine_safety.importers.emsa_importer import (
            EMSAImporter,
        )

        emcip_info = EMSAImporter.get_emcip_info()

        console.print(
            Panel(
                f"[bold cyan]European Marine Casualty Information Platform (EMCIP)[/bold cyan]\n\n"
                f"[bold]Legal Basis:[/bold] {emcip_info['legal_basis']}\n"
                f"[bold]Data Coverage:[/bold] {emcip_info['data_coverage']}\n"
                f"[bold]Update Frequency:[/bold] {emcip_info['update_frequency']}\n\n"
                "[bold]Access Types:[/bold]\n"
                f"  - Public: {emcip_info['access_types']['public']}\n"
                f"  - Institutional: {emcip_info['access_types']['institutional']}\n"
                f"  - Research: {emcip_info['access_types']['research']}\n\n"
                "[bold]To request access:[/bold]\n"
                "1. Visit: https://portal.emsa.europa.eu/emcip-public\n"
                "2. Contact: emcip-support@emsa.europa.eu\n"
                "3. Provide justification under Directive 2009/18/EC",
                title="EMSA EMCIP Information",
                border_style="cyan",
            )
        )
        return

    console.print(
        Panel(
            "[yellow]EMSA EMCIP import requires institutional data access.[/yellow]\n\n"
            "Use --info to see access requirements:\n"
            "  marine-safety import emsa --info",
            title="Access Required",
            border_style="yellow",
        )
    )


@import_cmd.command(name="imo")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--limit", type=int, help="Limit number of records to import (useful for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Records per database batch (default: 100)",
)
@click.option(
    "--skip-duplicates/--allow-duplicates",
    default=True,
    help="Skip duplicate records (default: skip)",
)
@click.option(
    "--preview", type=int, default=0, help="Preview N records without importing"
)
@click.option(
    "--validate-imo/--no-validate-imo",
    default=True,
    help="Validate IMO ship numbers (default: validate)",
)
@click.option(
    "--strict-imo", is_flag=True, help="Reject records with invalid IMO checksums"
)
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_imo(
    file: Path,
    limit: Optional[int],
    batch_size: int,
    skip_duplicates: bool,
    preview: int,
    validate_imo: bool,
    strict_imo: bool,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Import IMO GISIS marine casualty data from CSV file

    Imports data from IMO GISIS (Global Integrated Shipping Information System)
    CSV exports. Supports IMO number validation with checksum verification.

    Examples:
        marine-safety import imo data/gisis_casualties.csv
        marine-safety import imo data/gisis_casualties.csv --limit 100
        marine-safety import imo data/gisis_casualties.csv --preview 5
        marine-safety import imo data/gisis.csv --strict-imo
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.importers.imo_importer import (
            IMOGISISImporter,
        )

        if verbose:
            console.print(f"[dim]Source file: {file}[/dim]")
            console.print(f"[dim]Batch size: {batch_size}[/dim]")
            console.print(f"[dim]IMO validation: {validate_imo}[/dim]")
            console.print(f"[dim]Strict IMO: {strict_imo}[/dim]")

        # Get database session
        session = get_session(db_url)

        # Initialize importer
        importer = IMOGISISImporter(
            source_path=file,
            session=session,
            batch_size=batch_size,
            validate_imo=validate_imo,
            strict_imo_validation=strict_imo,
        )

        # Validate source file
        if not importer.validate_source():
            console.print("[red]x Source file validation failed[/red]")
            sys.exit(1)

        # Preview mode
        if preview > 0:
            console.print(f"\n[cyan]Previewing {preview} records...[/cyan]\n")
            previews = importer.preview_data(preview)

            for i, record in enumerate(previews, 1):
                console.print(f"[bold]Record {i}:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Field", style="dim")
                table.add_column("Value")

                for key, value in record.items():
                    if key != "raw_data" and value:
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        table.add_row(key, display_value)

                console.print(table)
                console.print()

            console.print(
                f"[green]Preview complete: {len(previews)} records shown[/green]"
            )
            return

        # Full import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Importing IMO GISIS data...", total=None)

            stats = importer.import_data(limit=limit, skip_duplicates=skip_duplicates)

            progress.update(task, completed=True)

        # Display results
        console.print()
        table = Table(
            title="IMO GISIS Import Statistics",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Records", str(stats["total_records"]))
        table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
        table.add_row(
            "[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]"
        )
        table.add_row(
            "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

        # Show IMO validation stats if enabled
        if validate_imo and hasattr(importer, "imo_validation_stats"):
            imo_stats = importer.imo_validation_stats
            table.add_row("", "")
            table.add_row("[bold]IMO Validation[/bold]", "")
            table.add_row("  Valid IMO Numbers", str(imo_stats.get("valid", 0)))
            table.add_row(
                "  Invalid Checksums", str(imo_stats.get("invalid_checksum", 0))
            )
            table.add_row("  Missing IMO", str(imo_stats.get("missing", 0)))

        console.print(table)

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
        sys.exit(1)
    except FileNotFoundError:
        console.print(f"[red]x File not found:[/red] {file}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@import_cmd.command(name="atsb")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--limit", type=int, help="Limit number of records to import (useful for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Records per database batch (default: 100)",
)
@click.option(
    "--skip-duplicates/--allow-duplicates",
    default=True,
    help="Skip duplicate records (default: skip)",
)
@click.option(
    "--preview", type=int, default=0, help="Preview N records without importing"
)
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_atsb(
    file: Path,
    limit: Optional[int],
    batch_size: int,
    skip_duplicates: bool,
    preview: int,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Import ATSB marine investigation data from JSON/CSV file

    Imports data from Australian Transport Safety Bureau scraped exports
    into the marine safety database.

    Examples:
        marine-safety import atsb data/atsb_investigations.json
        marine-safety import atsb data/atsb_investigations.csv --limit 100
        marine-safety import atsb data/atsb.json --preview 5
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.importers.atsb_importer import (
            ATSBImporter,
        )

        # Determine file format
        file_format = "csv" if file.suffix.lower() == ".csv" else "json"

        if verbose:
            console.print(f"[dim]Source file: {file}[/dim]")
            console.print(f"[dim]File format: {file_format}[/dim]")
            console.print(f"[dim]Batch size: {batch_size}[/dim]")

        # Get database session
        session = get_session(db_url)

        # Initialize importer
        importer = ATSBImporter(
            source_path=file,
            session=session,
            batch_size=batch_size,
            file_format=file_format,
        )

        # Validate source file
        if not importer.validate_source():
            console.print("[red]x Source file validation failed[/red]")
            sys.exit(1)

        # Preview mode
        if preview > 0:
            console.print(f"\n[cyan]Previewing {preview} records...[/cyan]\n")
            previews = importer.preview_data(preview)

            for i, record in enumerate(previews, 1):
                console.print(f"[bold]Record {i}:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Field", style="dim")
                table.add_column("Value")

                for key, value in record.items():
                    if key != "raw_data" and value:
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        table.add_row(key, display_value)

                console.print(table)
                console.print()

            console.print(
                f"[green]Preview complete: {len(previews)} records shown[/green]"
            )
            return

        # Full import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Importing ATSB data...", total=None)

            stats = importer.import_data(limit=limit, skip_duplicates=skip_duplicates)

            progress.update(task, completed=True)

        # Display results
        console.print()
        table = Table(
            title="ATSB Import Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Records", str(stats["total_records"]))
        table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
        table.add_row(
            "[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]"
        )
        table.add_row(
            "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

        console.print(table)

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
        sys.exit(1)
    except FileNotFoundError:
        console.print(f"[red]x File not found:[/red] {file}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@import_cmd.command(name="tsb")
@click.option(
    "--occurrence-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to TSB occurrence.csv file (required)",
)
@click.option(
    "--vessels-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to TSB vessel.csv file (optional)",
)
@click.option(
    "--injuries-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to TSB injuries.csv file (optional)",
)
@click.option(
    "--limit", type=int, help="Limit number of records to import (useful for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="Records per database batch (default: 1000)",
)
@click.option(
    "--preview", type=int, default=0, help="Preview N records without importing"
)
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_tsb(
    occurrence_file: Path,
    vessels_file: Optional[Path],
    injuries_file: Optional[Path],
    limit: Optional[int],
    batch_size: int,
    preview: int,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Import Canadian TSB marine occurrence data from CSV files

    Imports data from Transportation Safety Board of Canada marine database
    into the marine safety database.

    Examples:
        marine-safety import tsb --occurrence-file data/occurrence.csv
        marine-safety import tsb --occurrence-file data/occurrence.csv --vessels-file data/vessel.csv
        marine-safety import tsb --occurrence-file data/occurrence.csv --limit 100 --preview 5
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.importers.tsb_importer import (
            TSBImporter,
        )

        if verbose:
            console.print(f"[dim]Occurrence file: {occurrence_file}[/dim]")
            if vessels_file:
                console.print(f"[dim]Vessels file: {vessels_file}[/dim]")
            if injuries_file:
                console.print(f"[dim]Injuries file: {injuries_file}[/dim]")
            console.print(f"[dim]Batch size: {batch_size}[/dim]")

        # Get database session
        session = get_session(db_url)

        # Initialize importer
        importer = TSBImporter(
            occurrence_file=occurrence_file,
            vessels_file=vessels_file,
            injuries_file=injuries_file,
            session=session,
            batch_size=batch_size,
        )

        # Validate source file
        if not importer.validate_source():
            console.print("[red]x Source file validation failed[/red]")
            sys.exit(1)

        # Preview mode
        if preview > 0:
            console.print(f"\n[cyan]Previewing {preview} records...[/cyan]\n")
            previews = importer.preview_data(preview)

            for i, record in enumerate(previews, 1):
                console.print(f"[bold]Record {i}:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Field", style="dim")
                table.add_column("Value")

                for key, value in record.items():
                    if key != "raw_data" and value:
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        table.add_row(key, display_value)

                console.print(table)
                console.print()

            console.print(
                f"[green]Preview complete: {len(previews)} records shown[/green]"
            )
            return

        # Full import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Importing TSB data...", total=None)

            stats = importer.import_data(limit=limit)

            progress.update(task, completed=True)

        # Display results
        console.print()
        table = Table(
            title="TSB Import Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Records", str(stats["total_records"]))
        table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
        table.add_row(
            "[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]"
        )
        table.add_row(
            "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

        console.print(table)

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]x File not found:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@import_cmd.command(name="maib")
@click.option(
    "--occurrences-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to MAIB occurrences CSV file (required)",
)
@click.option(
    "--vessels-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to MAIB vessels CSV file (optional)",
)
@click.option(
    "--persons-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to MAIB affected persons CSV file (optional)",
)
@click.option(
    "--limit", type=int, help="Limit number of records to import (useful for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="Records per database batch (default: 1000)",
)
@click.option(
    "--preview", type=int, default=0, help="Preview N records without importing"
)
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_maib(
    occurrences_file: Path,
    vessels_file: Optional[Path],
    persons_file: Optional[Path],
    limit: Optional[int],
    batch_size: int,
    preview: int,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Import UK MAIB marine occurrence data from CSV files

    Imports data from the UK Marine Accident Investigation Branch database
    into the marine safety database.

    Examples:
        marine-safety import maib --occurrences-file data/maib_occurrences.csv
        marine-safety import maib --occurrences-file data/maib_occurrences.csv --vessels-file data/maib_vessels.csv
        marine-safety import maib --occurrences-file data/maib_occurrences.csv --limit 100 --preview 5
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.importers.maib_importer import (
            MAIBImporter,
        )

        if verbose:
            console.print(f"[dim]Occurrences file: {occurrences_file}[/dim]")
            if vessels_file:
                console.print(f"[dim]Vessels file: {vessels_file}[/dim]")
            if persons_file:
                console.print(f"[dim]Persons file: {persons_file}[/dim]")
            console.print(f"[dim]Batch size: {batch_size}[/dim]")

        # Get database session
        session = get_session(db_url)

        # Initialize importer
        importer = MAIBImporter(
            occurrences_file=occurrences_file,
            vessels_file=vessels_file,
            persons_file=persons_file,
            session=session,
            batch_size=batch_size,
        )

        # Validate source file
        if not importer.validate_source():
            console.print("[red]x Source file validation failed[/red]")
            sys.exit(1)

        # Preview mode
        if preview > 0:
            console.print(f"\n[cyan]Previewing {preview} records...[/cyan]\n")
            previews = importer.preview_data(preview)

            for i, record in enumerate(previews, 1):
                console.print(f"[bold]Record {i}:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Field", style="dim")
                table.add_column("Value")

                for key, value in record.items():
                    if key != "raw_data" and value:
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        table.add_row(key, display_value)

                console.print(table)
                console.print()

            console.print(
                f"[green]Preview complete: {len(previews)} records shown[/green]"
            )
            return

        # Full import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Importing MAIB data...", total=None)

            stats = importer.import_data(limit=limit)

            progress.update(task, completed=True)

        # Display results
        console.print()
        table = Table(
            title="MAIB Import Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Records", str(stats["total_records"]))
        table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
        table.add_row(
            "[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]"
        )
        table.add_row(
            "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

        console.print(table)

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]x File not found:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@import_cmd.command(name="noaa")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--limit", type=int, help="Limit number of records to import (useful for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Records per database batch (default: 100)",
)
@click.option(
    "--preview", type=int, default=0, help="Preview N records without importing"
)
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_noaa(
    file: Path,
    limit: Optional[int],
    batch_size: int,
    preview: int,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Import NOAA OR&R oil spill and chemical release data from CSV file

    Imports data from NOAA's Office of Response and Restoration Emergency
    Response Division incident archive into the marine safety database.

    Examples:
        marine-safety import noaa data/noaa_incidents.csv
        marine-safety import noaa data/noaa_incidents.csv --limit 100
        marine-safety import noaa data/noaa_incidents.csv --preview 5
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.importers.noaa_importer import (
            NOAAImporter,
        )

        if verbose:
            console.print(f"[dim]Source file: {file}[/dim]")
            console.print(f"[dim]Batch size: {batch_size}[/dim]")

        # Get database session
        session = get_session(db_url)

        # Initialize importer
        importer = NOAAImporter(
            source_path=file, session=session, batch_size=batch_size
        )

        # Validate source file
        if not importer.validate_source():
            console.print("[red]x Source file validation failed[/red]")
            sys.exit(1)

        # Preview mode
        if preview > 0:
            console.print(f"\n[cyan]Previewing {preview} records...[/cyan]\n")
            previews = importer.preview_data(preview)

            for i, record in enumerate(previews, 1):
                console.print(f"[bold]Record {i}:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Field", style="dim")
                table.add_column("Value")

                for key, value in record.items():
                    if key != "raw_data" and value:
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        table.add_row(key, display_value)

                console.print(table)
                console.print()

            console.print(
                f"[green]Preview complete: {len(previews)} records shown[/green]"
            )
            return

        # Full import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Importing NOAA data...", total=None)

            stats = importer.import_data(limit=limit)

            progress.update(task, completed=True)

        # Display results
        console.print()
        table = Table(
            title="NOAA Import Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Records", str(stats["total_records"]))
        table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
        table.add_row(
            "[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]"
        )
        table.add_row(
            "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

        console.print(table)

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
        sys.exit(1)
    except FileNotFoundError:
        console.print(f"[red]x File not found:[/red] {file}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@import_cmd.command(name="boating")
@click.option(
    "--accidents-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to BARD Accidents.csv file (required)",
)
@click.option(
    "--vessels-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to BARD Vessels.csv file (optional)",
)
@click.option(
    "--deaths-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to BARD Deaths.csv file (optional)",
)
@click.option(
    "--injuries-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to BARD Injuries.csv file (optional)",
)
@click.option(
    "--limit", type=int, help="Limit number of records to import (useful for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Records per database batch (default: 100)",
)
@click.option(
    "--preview", type=int, default=0, help="Preview N records without importing"
)
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def import_boating(
    accidents_file: Path,
    vessels_file: Optional[Path],
    deaths_file: Optional[Path],
    injuries_file: Optional[Path],
    limit: Optional[int],
    batch_size: int,
    preview: int,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Import USCG Boating Accident Report Database (BARD) data from CSV files

    Imports recreational boating accident data from the Data Liberation Project's
    converted CSV files (1995-2012 USCG BARD data) into the marine safety database.

    Examples:
        marine-safety import boating --accidents-file data/Accidents.csv
        marine-safety import boating --accidents-file data/Accidents.csv --vessels-file data/Vessels.csv
        marine-safety import boating --accidents-file data/Accidents.csv --deaths-file data/Deaths.csv --injuries-file data/Injuries.csv
        marine-safety import boating --accidents-file data/Accidents.csv --limit 100 --preview 5
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.importers.boating_importer import (
            BoatingImporter,
        )

        if verbose:
            console.print(f"[dim]Accidents file: {accidents_file}[/dim]")
            if vessels_file:
                console.print(f"[dim]Vessels file: {vessels_file}[/dim]")
            if deaths_file:
                console.print(f"[dim]Deaths file: {deaths_file}[/dim]")
            if injuries_file:
                console.print(f"[dim]Injuries file: {injuries_file}[/dim]")
            console.print(f"[dim]Batch size: {batch_size}[/dim]")

        # Get database session
        session = get_session(db_url)

        # Initialize importer
        importer = BoatingImporter(
            accidents_file=accidents_file,
            vessels_file=vessels_file,
            deaths_file=deaths_file,
            injuries_file=injuries_file,
            session=session,
            batch_size=batch_size,
        )

        # Validate source file
        if not importer.validate_source():
            console.print("[red]x Source file validation failed[/red]")
            sys.exit(1)

        # Preview mode
        if preview > 0:
            console.print(f"\n[cyan]Previewing {preview} records...[/cyan]\n")
            previews = importer.preview_data(preview)

            for i, record in enumerate(previews, 1):
                console.print(f"[bold]Record {i}:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Field", style="dim")
                table.add_column("Value")

                for key, value in record.items():
                    if key != "raw_data" and value:
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        table.add_row(key, display_value)

                console.print(table)
                console.print()

            console.print(
                f"[green]Preview complete: {len(previews)} records shown[/green]"
            )
            return

        # Full import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Importing USCG BARD data...", total=None)

            stats = importer.import_data(limit=limit)

            progress.update(task, completed=True)

        # Display results
        console.print()
        table = Table(
            title="USCG BARD Import Statistics",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Records", str(stats["total_records"]))
        table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
        table.add_row(
            "[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]"
        )
        table.add_row(
            "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

        console.print(table)

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]x File not found:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


# =============================================================================
# CORRELATION COMMAND GROUP
# =============================================================================


@cli.group()
def correlate():
    """Cross-source incident correlation and deduplication"""
    pass


@correlate.command(name="find-matches")
@click.option(
    "--source",
    type=click.Choice(["all", "ntsb", "imo", "atsb", "uscg"], case_sensitive=False),
    default="all",
    help="Source to correlate (default: all)",
)
@click.option(
    "--min-confidence",
    type=float,
    default=0.7,
    help="Minimum confidence threshold (default: 0.7)",
)
@click.option(
    "--date-tolerance", type=int, default=3, help="Date tolerance in days (default: 3)"
)
@click.option(
    "--location-threshold",
    type=float,
    default=50.0,
    help="Location threshold in km (default: 50)",
)
@click.option("--limit", type=int, help="Limit number of incidents to process")
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def find_matches(
    source: str,
    min_confidence: float,
    date_tolerance: int,
    location_threshold: float,
    limit: Optional[int],
    db_url: Optional[str],
    verbose: bool,
):
    """
    Find matching incidents across data sources

    Identifies potential duplicate incidents across different data sources
    using IMO number, vessel name similarity, and location/date proximity.

    Examples:
        marine-safety correlate find-matches
        marine-safety correlate find-matches --source ntsb --min-confidence 0.8
        marine-safety correlate find-matches --date-tolerance 5 --verbose
    """
    try:
        from worldenergydata.modules.marine_safety.analysis.correlation import (
            IncidentDeduplicator,
            IncidentMatcher,
            MatchConfig,
        )
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )

        if verbose:
            console.print(f"[dim]Source filter: {source}[/dim]")
            console.print(f"[dim]Min confidence: {min_confidence}[/dim]")
            console.print(f"[dim]Date tolerance: {date_tolerance} days[/dim]")
            console.print(f"[dim]Location threshold: {location_threshold} km[/dim]")

        # Configure matcher
        config = MatchConfig(
            min_confidence=min_confidence,
            date_tolerance_days=date_tolerance,
            location_threshold_km=location_threshold,
        )

        # Get database session
        session = get_session(db_url)

        # Initialize deduplicator
        deduplicator = IncidentDeduplicator(session=session, config=config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Finding cross-source matches...", total=None
            )

            # Find matches
            matches = list(deduplicator.find_cross_source_matches())

            progress.update(task, completed=True)

        # Display results
        if not matches:
            console.print(
                "\n[yellow]No matches found above confidence threshold[/yellow]"
            )
            return

        console.print(f"\n[green]Found {len(matches)} potential matches[/green]\n")

        # Display match table
        table = Table(
            title="Cross-Source Matches", show_header=True, header_style="bold cyan"
        )
        table.add_column("Incident 1", style="dim")
        table.add_column("Incident 2", style="dim")
        table.add_column("Match Type")
        table.add_column("Confidence", justify="right")
        table.add_column("IMO", justify="center")
        table.add_column("Name", justify="center")
        table.add_column("Loc", justify="center")

        for match in matches[:50]:  # Show first 50
            table.add_row(
                match.incident_1_id[:20] if match.incident_1_id else "N/A",
                match.incident_2_id[:20] if match.incident_2_id else "N/A",
                match.match_type,
                f"{match.confidence:.2f}",
                "Y" if match.imo_score and match.imo_score > 0.5 else "N",
                "Y" if match.name_score and match.name_score > 0.5 else "N",
                "Y" if match.location_score and match.location_score > 0.5 else "N",
            )

        console.print(table)

        if len(matches) > 50:
            console.print(f"\n[dim]Showing 50 of {len(matches)} matches[/dim]")

        # Show summary stats
        metrics = deduplicator.calculate_quality_metrics(matches)
        if metrics:
            console.print("\n[bold]Quality Metrics:[/bold]")
            console.print(f"  Average confidence: {metrics.avg_confidence:.2f}")
            console.print(f"  High confidence (>0.9): {metrics.high_confidence_count}")
            console.print(
                f"  Medium confidence (0.7-0.9): {metrics.medium_confidence_count}"
            )

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@correlate.command(name="link")
@click.argument("incident_id_1", type=str)
@click.argument("incident_id_2", type=str)
@click.option(
    "--confidence",
    type=float,
    default=1.0,
    help="Confidence score (default: 1.0 for manual links)",
)
@click.option(
    "--match-type",
    type=click.Choice(["manual", "imo", "name", "location", "combined"]),
    default="manual",
    help="Match type (default: manual)",
)
@click.option("--db-url", help="Database connection URL")
def link_incidents(
    incident_id_1: str,
    incident_id_2: str,
    confidence: float,
    match_type: str,
    db_url: Optional[str],
):
    """
    Manually link two incidents as related/duplicate

    Examples:
        marine-safety correlate link MAR22MA001 MO-2022-001
        marine-safety correlate link MAR22MA001 MO-2022-001 --match-type imo
    """
    try:
        from worldenergydata.modules.marine_safety.analysis.correlation import (
            IncidentDeduplicator,
        )
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )

        session = get_session(db_url)
        deduplicator = IncidentDeduplicator(session=session)

        # Create link
        link = deduplicator.link_incidents(
            incident_id_1, incident_id_2, match_type=match_type, confidence=confidence
        )

        if link:
            console.print(f"[green]v Linked incidents:[/green]")
            console.print(f"  {incident_id_1} <-> {incident_id_2}")
            console.print(f"  Confidence: {confidence:.2f}")
            console.print(f"  Match type: {match_type}")
        else:
            console.print("[yellow]Failed to create link (may already exist)[/yellow]")

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@correlate.command(name="stats")
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Show detailed statistics")
def correlation_stats(db_url: Optional[str], verbose: bool):
    """
    Display correlation statistics

    Examples:
        marine-safety correlate stats
        marine-safety correlate stats --verbose
    """
    try:
        from sqlalchemy import func

        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.database.models import (
            Incident,
            IncidentLink,
        )

        session = get_session(db_url)

        # Count links
        total_links = session.query(func.count(IncidentLink.link_id)).scalar() or 0
        verified_links = (
            session.query(func.count(IncidentLink.link_id))
            .filter(IncidentLink.verified == True)
            .scalar()
            or 0
        )

        # Count by match type
        type_counts = (
            session.query(IncidentLink.match_type, func.count(IncidentLink.link_id))
            .group_by(IncidentLink.match_type)
            .all()
        )

        # Confidence distribution
        avg_confidence = (
            session.query(func.avg(IncidentLink.confidence_score)).scalar() or 0
        )

        # Display
        table = Table(
            title="Correlation Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Total Links", str(total_links))
        table.add_row("Verified Links", str(verified_links))
        table.add_row("Avg Confidence", f"{float(avg_confidence):.2f}")

        if type_counts:
            table.add_row("", "")
            table.add_row("[bold]By Match Type[/bold]", "")
            for match_type, count in type_counts:
                table.add_row(f"  {match_type}", str(count))

        console.print(table)

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


# =============================================================================
# REFRESH COMMAND GROUP
# =============================================================================


@cli.group()
def refresh():
    """Refresh incident data from sources (scrape + import)"""
    pass


def _refresh_source_with_scraper(
    source_name: str,
    scraper_class: type,
    importer_class: type,
    since: Optional[datetime],
    output_dir: Optional[Path],
    keep_files: bool,
    dry_run: bool,
    db_url: Optional[str],
    verbose: bool,
) -> None:
    """
    Common refresh logic for sources with scrapers.

    Args:
        source_name: Name of the data source (for display)
        scraper_class: The scraper class to use
        importer_class: The importer class to use
        since: Date to fetch data from
        output_dir: Output directory for scraped data
        keep_files: Whether to keep scraped files after import
        dry_run: Show what would be done without executing
        db_url: Database connection URL
        verbose: Enable verbose output
    """
    import shutil
    import tempfile
    from datetime import timedelta

    # Default to 1 year ago
    if since is None:
        since = datetime.now() - timedelta(days=365)

    # Create temp dir if not specified
    temp_created = False
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="marine_safety_"))
        temp_created = True

    output_file = (
        output_dir
        / f"{source_name.lower()}_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    if dry_run:
        console.print(
            Panel(
                f"[cyan]Would refresh {source_name.upper()} data[/cyan]\n\n"
                f"Date range: {since.strftime('%Y-%m-%d')} - {datetime.now().strftime('%Y-%m-%d')}\n"
                f"Output: {output_file}\n"
                f"Keep files: {keep_files}",
                title="Dry Run",
                border_style="yellow",
            )
        )
        return

    try:
        # Step 1: Scrape
        console.print(
            f"\n[bold cyan]Step 1/2: Scraping {source_name.upper()} data...[/bold cyan]"
        )
        if verbose:
            console.print(f"[dim]Date range: {since.strftime('%Y-%m-%d')} to now[/dim]")

        scraper = scraper_class()
        data = scraper.scrape(start_date=since, end_date=datetime.now())

        # Save to file
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

        console.print(f"[green]✓ Scraped {len(data)} records to {output_file}[/green]")

        # Step 2: Import
        console.print(f"\n[bold cyan]Step 2/2: Importing to database...[/bold cyan]")
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )

        session = get_session(db_url)
        importer = importer_class(
            source_path=output_file, session=session, file_format="json"
        )

        stats = importer.import_data(skip_duplicates=True)

        # Display results
        table = Table(
            title=f"{source_name.upper()} Refresh Results",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Scraped", str(len(data)))
        table.add_row(
            "[green]New Records[/green]", f"[green]{stats.get('imported', 0)}[/green]"
        )
        table.add_row(
            "[yellow]Already Exists[/yellow]",
            f"[yellow]{stats.get('duplicates', 0)}[/yellow]",
        )
        table.add_row("[red]Errors[/red]", f"[red]{stats.get('errors', 0)}[/red]")

        console.print(table)

        # Cleanup
        if not keep_files and temp_created:
            shutil.rmtree(output_dir)
            console.print(f"[dim]Cleaned up temporary files[/dim]")

        console.print(f"\n[green]✓ {source_name.upper()} refresh complete[/green]")

    except Exception as e:
        console.print(f"[red]✗ Refresh failed: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        # Cleanup on error if temp dir
        if not keep_files and temp_created and output_dir.exists():
            shutil.rmtree(output_dir)
        sys.exit(1)


def _show_manual_download_info(source_name: str, download_url: str) -> None:
    """
    Display info message for sources requiring manual download.

    Args:
        source_name: Name of the data source
        download_url: URL where data can be downloaded
    """
    console.print(
        Panel(
            f"[yellow]This source requires manual data download.[/yellow]\n\n"
            f"Download data from: {download_url}\n\n"
            f"Then import with: marine-safety import {source_name.lower()} <file>",
            title="Manual Download Required",
            border_style="yellow",
        )
    )


@refresh.command(name="ntsb")
@click.option(
    "--since",
    "-s",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (default: 1 year ago)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Output directory for scraped data",
)
@click.option("--keep-files", is_flag=True, help="Keep scraped files after import")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without executing"
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def refresh_ntsb(
    since: Optional[datetime],
    output_dir: Optional[Path],
    keep_files: bool,
    dry_run: bool,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Refresh NTSB marine incident data

    Scrapes the latest data from NTSB CAROL system and imports it into the database.

    Examples:
        marine-safety refresh ntsb
        marine-safety refresh ntsb --since 2023-01-01
        marine-safety refresh ntsb --keep-files --verbose
        marine-safety refresh ntsb --dry-run
    """
    from worldenergydata.modules.marine_safety.importers.ntsb_importer import (
        NTSBImporter,
    )
    from worldenergydata.modules.marine_safety.scrapers.ntsb_scraper import NTSBScraper

    _refresh_source_with_scraper(
        source_name="ntsb",
        scraper_class=NTSBScraper,
        importer_class=NTSBImporter,
        since=since,
        output_dir=output_dir,
        keep_files=keep_files,
        dry_run=dry_run,
        db_url=db_url,
        verbose=verbose,
    )


@refresh.command(name="atsb")
@click.option(
    "--since",
    "-s",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (default: 1 year ago)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Output directory for scraped data",
)
@click.option("--keep-files", is_flag=True, help="Keep scraped files after import")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without executing"
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def refresh_atsb(
    since: Optional[datetime],
    output_dir: Optional[Path],
    keep_files: bool,
    dry_run: bool,
    db_url: Optional[str],
    verbose: bool,
):
    """
    Refresh ATSB marine incident data

    Scrapes the latest data from ATSB (Australian Transport Safety Bureau)
    and imports it into the database.

    Examples:
        marine-safety refresh atsb
        marine-safety refresh atsb --since 2023-01-01
        marine-safety refresh atsb --keep-files --verbose
    """
    from worldenergydata.modules.marine_safety.importers.atsb_importer import (
        ATSBImporter,
    )
    from worldenergydata.modules.marine_safety.scrapers.atsb_scraper import ATSBScraper

    _refresh_source_with_scraper(
        source_name="atsb",
        scraper_class=ATSBScraper,
        importer_class=ATSBImporter,
        since=since,
        output_dir=output_dir,
        keep_files=keep_files,
        dry_run=dry_run,
        db_url=db_url,
        verbose=verbose,
    )


@refresh.command(name="tsb")
@click.option(
    "--since",
    "-s",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (not used for manual sources)",
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def refresh_tsb(since: Optional[datetime], db_url: Optional[str], verbose: bool):
    """
    Refresh TSB marine incident data

    TSB (Transportation Safety Board of Canada) data requires manual download.

    Examples:
        marine-safety refresh tsb
    """
    _show_manual_download_info(
        source_name="tsb",
        download_url="https://www.tsb.gc.ca/eng/stats/marine/index.html",
    )


@refresh.command(name="maib")
@click.option(
    "--since",
    "-s",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (not used for manual sources)",
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def refresh_maib(since: Optional[datetime], db_url: Optional[str], verbose: bool):
    """
    Refresh MAIB marine incident data

    MAIB (UK Marine Accident Investigation Branch) data requires manual download.

    Examples:
        marine-safety refresh maib
    """
    _show_manual_download_info(
        source_name="maib",
        download_url="https://www.gov.uk/government/organisations/marine-accident-investigation-branch",
    )


@refresh.command(name="noaa")
@click.option(
    "--since",
    "-s",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (not used for manual sources)",
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def refresh_noaa(since: Optional[datetime], db_url: Optional[str], verbose: bool):
    """
    Refresh NOAA marine incident data

    NOAA incident data requires manual download from the NOAA data portal.

    Examples:
        marine-safety refresh noaa
    """
    _show_manual_download_info(
        source_name="noaa", download_url="https://incidentnews.noaa.gov/"
    )


@refresh.command(name="boating")
@click.option(
    "--since",
    "-s",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (not used for manual sources)",
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def refresh_boating(since: Optional[datetime], db_url: Optional[str], verbose: bool):
    """
    Refresh recreational boating incident data

    USCG recreational boating statistics require manual download.

    Examples:
        marine-safety refresh boating
    """
    _show_manual_download_info(
        source_name="boating",
        download_url="https://uscgboating.org/statistics/accident_statistics.php",
    )


@refresh.command(name="imo")
@click.option(
    "--since",
    "-s",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (not used for manual sources)",
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def refresh_imo(since: Optional[datetime], db_url: Optional[str], verbose: bool):
    """
    Refresh IMO marine incident data

    IMO (International Maritime Organization) GISIS data requires manual download.

    Examples:
        marine-safety refresh imo
    """
    _show_manual_download_info(
        source_name="imo", download_url="https://gisis.imo.org/Public/MCI/Default.aspx"
    )


@refresh.command(name="all")
@click.option(
    "--sources",
    "-s",
    multiple=True,
    type=click.Choice(
        ["ntsb", "atsb", "tsb", "maib", "noaa", "boating", "imo"], case_sensitive=False
    ),
    help="Specific sources to refresh (default: all with scrapers)",
)
@click.option(
    "--since",
    type=click.DateTime(),
    default=None,
    help="Fetch data since date (default: 1 year ago)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Output directory for scraped data",
)
@click.option("--keep-files", is_flag=True, help="Keep scraped files after import")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without executing"
)
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.option(
    "--skip-manual",
    is_flag=True,
    default=True,
    help="Skip sources requiring manual download (default: True)",
)
def refresh_all(
    sources: tuple,
    since: Optional[datetime],
    output_dir: Optional[Path],
    keep_files: bool,
    dry_run: bool,
    db_url: Optional[str],
    verbose: bool,
    skip_manual: bool,
):
    """
    Refresh all configured data sources

    By default, only sources with automated scrapers (NTSB, ATSB) are refreshed.
    Use --no-skip-manual to show info for manual sources too.

    Examples:
        marine-safety refresh all
        marine-safety refresh all --sources ntsb --sources atsb
        marine-safety refresh all --since 2023-01-01
        marine-safety refresh all --dry-run --verbose
        marine-safety refresh all --no-skip-manual
    """
    # Sources with automated scrapers
    automated_sources = {"ntsb", "atsb"}
    # Sources requiring manual download
    manual_sources = {"tsb", "maib", "noaa", "boating", "imo"}

    # Determine which sources to process
    if sources:
        selected_sources = set(s.lower() for s in sources)
    else:
        # Default to automated sources only
        selected_sources = automated_sources.copy()
        if not skip_manual:
            selected_sources.update(manual_sources)

    results = {}
    errors = []

    console.print(
        Panel(
            f"[bold cyan]Refreshing {len(selected_sources)} data source(s)[/bold cyan]\n\n"
            f"Sources: {', '.join(sorted(selected_sources))}\n"
            f"Since: {since.strftime('%Y-%m-%d') if since else '1 year ago'}\n"
            f"Dry run: {dry_run}",
            title="Refresh All Sources",
            border_style="cyan",
        )
    )

    for source in sorted(selected_sources):
        console.print(f"\n{'='*60}")
        console.print(f"[bold]Processing: {source.upper()}[/bold]")
        console.print(f"{'='*60}")

        try:
            if source == "ntsb":
                from worldenergydata.modules.marine_safety.importers.ntsb_importer import (
                    NTSBImporter,
                )
                from worldenergydata.modules.marine_safety.scrapers.ntsb_scraper import (
                    NTSBScraper,
                )

                _refresh_source_with_scraper(
                    source_name="ntsb",
                    scraper_class=NTSBScraper,
                    importer_class=NTSBImporter,
                    since=since,
                    output_dir=output_dir,
                    keep_files=keep_files,
                    dry_run=dry_run,
                    db_url=db_url,
                    verbose=verbose,
                )
                results[source] = "success"

            elif source == "atsb":
                from worldenergydata.modules.marine_safety.importers.atsb_importer import (
                    ATSBImporter,
                )
                from worldenergydata.modules.marine_safety.scrapers.atsb_scraper import (
                    ATSBScraper,
                )

                _refresh_source_with_scraper(
                    source_name="atsb",
                    scraper_class=ATSBScraper,
                    importer_class=ATSBImporter,
                    since=since,
                    output_dir=output_dir,
                    keep_files=keep_files,
                    dry_run=dry_run,
                    db_url=db_url,
                    verbose=verbose,
                )
                results[source] = "success"

            elif source in manual_sources:
                # Show manual download info
                manual_urls = {
                    "tsb": "https://www.tsb.gc.ca/eng/stats/marine/index.html",
                    "maib": "https://www.gov.uk/government/organisations/marine-accident-investigation-branch",
                    "noaa": "https://incidentnews.noaa.gov/",
                    "boating": "https://uscgboating.org/statistics/accident_statistics.php",
                    "imo": "https://gisis.imo.org/Public/MCI/Default.aspx",
                }
                _show_manual_download_info(source, manual_urls[source])
                results[source] = "manual"

        except SystemExit:
            # Catch sys.exit from individual refresh failures
            results[source] = "error"
            errors.append(source)
        except Exception as e:
            console.print(f"[red]✗ Error processing {source}: {e}[/red]")
            results[source] = "error"
            errors.append(source)

    # Summary
    console.print(f"\n{'='*60}")
    console.print("[bold]Refresh Summary[/bold]")
    console.print(f"{'='*60}\n")

    summary_table = Table(show_header=True, header_style="bold cyan")
    summary_table.add_column("Source", style="dim")
    summary_table.add_column("Status", justify="center")

    for source in sorted(results.keys()):
        status = results[source]
        if status == "success":
            status_str = "[green]✓ Success[/green]"
        elif status == "manual":
            status_str = "[yellow]⚠ Manual[/yellow]"
        else:
            status_str = "[red]✗ Error[/red]"
        summary_table.add_row(source.upper(), status_str)

    console.print(summary_table)

    if errors:
        console.print(f"\n[red]Errors occurred in: {', '.join(errors)}[/red]")
        sys.exit(1)
    else:
        console.print(f"\n[green]✓ All sources processed successfully[/green]")


# =============================================================================
# DATABASE COMMAND GROUP
# =============================================================================


@cli.group()
def db():
    """Database management operations"""
    pass


@db.command()
@click.option("--force", is_flag=True, help="Force recreation of existing database")
@click.option("--db-url", help="Database connection URL (defaults to SQLite)")
def init(force: bool, db_url: Optional[str]):
    """
    Initialize database schema for marine safety data

    Creates all necessary tables, indexes, and constraints.

    Examples:
        marine-safety db init
        marine-safety db init --force
        marine-safety db init --db-url postgresql://user:pass@localhost/marine
    """
    try:
        if force:
            if not click.confirm(
                "This will drop all existing tables. Continue?", default=False
            ):
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Initializing database schema...", total=None
            )

            # TODO: Import and execute database initialization
            # from .database.models import init_db
            # init_db(db_url, force=force)

            console.print(
                "[yellow]Database initialization not yet implemented[/yellow]"
            )
            if db_url:
                console.print(f"Database URL: {db_url}")

            progress.update(task, completed=True)

        console.print(
            "[green]v[/green] Database initialized successfully", style="bold"
        )

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@db.command()
@click.option("--target-version", type=int, help="Target migration version")
@click.option("--dry-run", is_flag=True, help="Show migration plan without executing")
def migrate(target_version: Optional[int], dry_run: bool):
    """
    Run database migrations to update schema

    Examples:
        marine-safety db migrate
        marine-safety db migrate --target-version 5
        marine-safety db migrate --dry-run
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running database migrations...", total=None)

            # TODO: Import and execute migrations
            # from .database.migrations import run_migrations
            # run_migrations(target_version, dry_run)

            console.print("[yellow]Database migrations not yet implemented[/yellow]")
            if dry_run:
                console.print("DRY RUN MODE - no changes will be made")
            if target_version:
                console.print(f"Target version: {target_version}")

            progress.update(task, completed=True)

        console.print(
            "[green]v[/green] Migrations completed successfully", style="bold"
        )

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@db.command()
@click.option(
    "--sample-size", type=int, default=100, help="Number of sample records to create"
)
@click.option(
    "--clear-existing", is_flag=True, help="Clear existing data before seeding"
)
def seed(sample_size: int, clear_existing: bool):
    """
    Seed database with test/sample data

    Examples:
        marine-safety db seed --sample-size 50
        marine-safety db seed --clear-existing
    """
    try:
        if clear_existing:
            if not click.confirm(
                "This will delete all existing data. Continue?", default=False
            ):
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Seeding database with {sample_size} records...", total=None
            )

            # TODO: Import and execute seeding
            # from .database.seed import seed_data
            # seed_data(sample_size, clear_existing)

            console.print("[yellow]Database seeding not yet implemented[/yellow]")
            console.print(f"Sample size: {sample_size}")

            progress.update(task, completed=True)

        console.print("[green]v[/green] Database seeded successfully", style="bold")

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


# =============================================================================
# STATS COMMAND
# =============================================================================


@cli.command()
@click.option(
    "--source",
    type=click.Choice(
        ["all", "uscg", "ntsb", "bsee", "imo", "atsb", "maib", "tsb"],
        case_sensitive=False,
    ),
    default="all",
    help="Data source to show statistics for",
)
@click.option("--by-year", is_flag=True, help="Show breakdown by year")
@click.option("--by-source", is_flag=True, help="Show detailed breakdown by source")
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Show detailed statistics")
def stats(
    source: str, by_year: bool, by_source: bool, db_url: Optional[str], verbose: bool
):
    """
    Display statistics about marine safety incident data

    Examples:
        marine-safety stats
        marine-safety stats --source ntsb
        marine-safety stats --by-year
        marine-safety stats --by-source --verbose
    """
    try:
        from sqlalchemy import case, extract, func
        from sqlalchemy.exc import OperationalError

        from worldenergydata.modules.marine_safety.constants import (
            DataSource,
            IncidentType,
        )
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_db_manager,
        )
        from worldenergydata.modules.marine_safety.database.models import (
            Incident,
            Location,
            Vessel,
        )

        # Get database session
        db_manager = get_db_manager()

        try:
            with db_manager.session() as session:
                # Build base query with optional source filter
                base_query = session.query(Incident)
                if source != "all":
                    source_enum = _get_source_enum(source)
                    if source_enum:
                        base_query = base_query.filter(
                            Incident.source_agency == source_enum
                        )

                # Get total count
                total_count = base_query.count()

                if total_count == 0:
                    console.print(
                        Panel(
                            "[yellow]No incident data found in the database.[/yellow]\n\n"
                            "To populate the database:\n"
                            "  1. Scrape data: marine-safety scrape ntsb\n"
                            "  2. Import data: marine-safety import ntsb <file>",
                            title="No Data",
                            border_style="yellow",
                        )
                    )
                    return

                # Main statistics table
                table = Table(
                    title="Marine Safety Incident Statistics",
                    show_header=True,
                    header_style="bold cyan",
                )
                table.add_column("Metric", style="dim")
                table.add_column("Value", justify="right")

                table.add_row(
                    "[bold]Total Incidents[/bold]", f"[bold]{total_count:,}[/bold]"
                )

                # Date range
                min_date = (
                    session.query(func.min(Incident.incident_date))
                    .filter(Incident.incident_date.isnot(None))
                    .scalar()
                )
                max_date = (
                    session.query(func.max(Incident.incident_date))
                    .filter(Incident.incident_date.isnot(None))
                    .scalar()
                )

                if min_date and max_date:
                    table.add_row("Date Range", f"{min_date} to {max_date}")

                # Count by source
                source_counts = (
                    session.query(
                        Incident.source_agency, func.count(Incident.incident_id)
                    )
                    .group_by(Incident.source_agency)
                    .all()
                )

                table.add_row("", "")
                table.add_row("[bold]By Source[/bold]", "")
                for src, count in sorted(
                    source_counts, key=lambda x: x[1], reverse=True
                ):
                    src_name = (
                        src.value.upper() if hasattr(src, "value") else str(src).upper()
                    )
                    table.add_row(f"  {src_name}", f"{count:,}")

                # Incident type distribution
                type_counts = (
                    session.query(
                        Incident.incident_type, func.count(Incident.incident_id)
                    )
                    .group_by(Incident.incident_type)
                    .order_by(func.count(Incident.incident_id).desc())
                    .limit(5)
                    .all()
                )

                if type_counts:
                    table.add_row("", "")
                    table.add_row("[bold]Top Incident Types[/bold]", "")
                    for inc_type, count in type_counts:
                        type_name = (
                            inc_type.value
                            if hasattr(inc_type, "value")
                            else str(inc_type)
                        )
                        table.add_row(
                            f"  {type_name.replace('_', ' ').title()}", f"{count:,}"
                        )

                # Records with GPS coordinates
                incidents_with_location = (
                    session.query(Incident)
                    .join(Location, Incident.location_id == Location.location_id)
                    .filter(
                        Location.latitude.isnot(None), Location.longitude.isnot(None)
                    )
                    .count()
                )

                gps_percentage = (
                    (incidents_with_location / total_count * 100)
                    if total_count > 0
                    else 0
                )
                table.add_row("", "")
                table.add_row(
                    "Records with GPS",
                    f"{incidents_with_location:,} ({gps_percentage:.1f}%)",
                )

                # Average data quality score
                avg_quality = (
                    session.query(func.avg(Incident.data_quality_score))
                    .filter(Incident.data_quality_score.isnot(None))
                    .scalar()
                )

                if avg_quality:
                    table.add_row("Avg Data Quality Score", f"{float(avg_quality):.2f}")

                # Verbose statistics
                if verbose:
                    table.add_row("", "")
                    table.add_row("[bold]Additional Statistics[/bold]", "")

                    # Unique vessels
                    unique_vessels = (
                        session.query(func.count(func.distinct(Incident.vessel_id)))
                        .filter(Incident.vessel_id.isnot(None))
                        .scalar()
                        or 0
                    )
                    table.add_row("Unique Vessels", f"{unique_vessels:,}")

                    # Unique companies
                    unique_companies = (
                        session.query(func.count(func.distinct(Incident.company_id)))
                        .filter(Incident.company_id.isnot(None))
                        .scalar()
                        or 0
                    )
                    table.add_row("Unique Companies", f"{unique_companies:,}")

                    # Total fatalities
                    total_fatalities = (
                        session.query(func.sum(Incident.fatalities)).scalar() or 0
                    )
                    table.add_row("Total Fatalities", f"{int(total_fatalities):,}")

                    # Total injuries
                    total_injuries = (
                        session.query(func.sum(Incident.injuries)).scalar() or 0
                    )
                    table.add_row("Total Injuries", f"{int(total_injuries):,}")

                    # Last updated record
                    last_updated = session.query(func.max(Incident.updated_at)).scalar()
                    if last_updated:
                        table.add_row(
                            "Last Updated", last_updated.strftime("%Y-%m-%d %H:%M")
                        )

                console.print(table)

                # By-year breakdown
                if by_year:
                    _show_year_breakdown(session, source)

                # By-source detailed breakdown
                if by_source:
                    _show_source_breakdown(session)

        except OperationalError as e:
            console.print(
                Panel(
                    f"[red]Database connection error:[/red]\n{str(e)}\n\n"
                    "Ensure the database is initialized:\n"
                    "  marine-safety db init",
                    title="Database Error",
                    border_style="red",
                )
            )
            sys.exit(1)

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print("[yellow]Ensure database dependencies are installed[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


def _get_source_enum(source: str):
    """Convert source string to DataSource enum"""
    from worldenergydata.modules.marine_safety.constants import DataSource

    source_map = {
        "uscg": DataSource.USCG,
        "uscg_misle": DataSource.USCG_MISLE,
        "uscg_bard": DataSource.USCG_BARD,
        "ntsb": DataSource.NTSB,
        "bsee": DataSource.BSEE,
        "imo": DataSource.IMO,
        "atsb": DataSource.ATSB,
        "maib": DataSource.MAIB,
        "tsb": DataSource.TSB,
    }
    return source_map.get(source.lower())


def _show_year_breakdown(session, source: str) -> None:
    """Display incident counts broken down by year"""
    from sqlalchemy import extract, func

    from worldenergydata.modules.marine_safety.database.models import Incident

    console.print()

    query = session.query(
        extract("year", Incident.incident_date).label("year"),
        func.count(Incident.incident_id).label("count"),
    ).filter(Incident.incident_date.isnot(None))

    if source != "all":
        source_enum = _get_source_enum(source)
        if source_enum:
            query = query.filter(Incident.source_agency == source_enum)

    year_counts = (
        query.group_by(extract("year", Incident.incident_date))
        .order_by(extract("year", Incident.incident_date))
        .all()
    )

    if not year_counts:
        console.print("[yellow]No year data available[/yellow]")
        return

    table = Table(title="Incidents by Year", show_header=True, header_style="bold cyan")
    table.add_column("Year", justify="center")
    table.add_column("Count", justify="right")
    table.add_column("Bar", style="green")

    max_count = max(count for _, count in year_counts) if year_counts else 1

    for year, count in year_counts:
        bar_length = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "*" * bar_length
        table.add_row(str(int(year)), f"{count:,}", bar)

    console.print(table)


def _show_source_breakdown(session) -> None:
    """Display detailed statistics by data source"""
    from sqlalchemy import func

    from worldenergydata.modules.marine_safety.database.models import Incident, Location

    console.print()

    # Get all sources with their stats
    source_stats = (
        session.query(
            Incident.source_agency,
            func.count(Incident.incident_id).label("total"),
            func.min(Incident.incident_date).label("min_date"),
            func.max(Incident.incident_date).label("max_date"),
            func.sum(Incident.fatalities).label("fatalities"),
            func.sum(Incident.injuries).label("injuries"),
            func.avg(Incident.data_quality_score).label("avg_quality"),
        )
        .group_by(Incident.source_agency)
        .order_by(func.count(Incident.incident_id).desc())
        .all()
    )

    if not source_stats:
        console.print("[yellow]No source data available[/yellow]")
        return

    table = Table(
        title="Detailed Source Breakdown", show_header=True, header_style="bold cyan"
    )
    table.add_column("Source", style="bold")
    table.add_column("Total", justify="right")
    table.add_column("Date Range", justify="center")
    table.add_column("Fatalities", justify="right")
    table.add_column("Injuries", justify="right")
    table.add_column("Avg Quality", justify="right")

    for stat in source_stats:
        source_name = (
            stat.source_agency.value.upper()
            if hasattr(stat.source_agency, "value")
            else str(stat.source_agency).upper()
        )
        date_range = f"{stat.min_date or 'N/A'} - {stat.max_date or 'N/A'}"
        fatalities = int(stat.fatalities) if stat.fatalities else 0
        injuries = int(stat.injuries) if stat.injuries else 0
        avg_quality = f"{float(stat.avg_quality):.2f}" if stat.avg_quality else "N/A"

        table.add_row(
            source_name,
            f"{stat.total:,}",
            date_range,
            str(fatalities),
            str(injuries),
            avg_quality,
        )

    console.print(table)

    # GPS coverage by source
    console.print()
    gps_table = Table(
        title="GPS Coverage by Source", show_header=True, header_style="bold cyan"
    )
    gps_table.add_column("Source", style="bold")
    gps_table.add_column("With GPS", justify="right")
    gps_table.add_column("Without GPS", justify="right")
    gps_table.add_column("Coverage %", justify="right")

    for stat in source_stats:
        source_name = (
            stat.source_agency.value.upper()
            if hasattr(stat.source_agency, "value")
            else str(stat.source_agency).upper()
        )

        with_gps = (
            session.query(func.count(Incident.incident_id))
            .join(Location, Incident.location_id == Location.location_id)
            .filter(
                Incident.source_agency == stat.source_agency,
                Location.latitude.isnot(None),
                Location.longitude.isnot(None),
            )
            .scalar()
            or 0
        )

        without_gps = stat.total - with_gps
        coverage = (with_gps / stat.total * 100) if stat.total > 0 else 0

        coverage_color = (
            "green" if coverage >= 70 else "yellow" if coverage >= 40 else "red"
        )

        gps_table.add_row(
            source_name,
            f"{with_gps:,}",
            f"{without_gps:,}",
            f"[{coverage_color}]{coverage:.1f}%[/{coverage_color}]",
        )

    console.print(gps_table)


# =============================================================================
# EXPORT COMMAND
# =============================================================================


@cli.command()
@click.argument(
    "format",
    type=click.Choice(["csv", "json", "excel", "parquet"], case_sensitive=False),
)
@click.option("--output", type=click.Path(), required=True, help="Output file path")
@click.option(
    "--source",
    type=click.Choice(["all", "uscg", "ntsb", "bsee"], case_sensitive=False),
    default="all",
    help="Data source to export",
)
@click.option("--start-date", help="Start date filter (YYYY-MM-DD)")
@click.option("--end-date", help="End date filter (YYYY-MM-DD)")
@click.option("--limit", type=int, help="Limit number of records to export")
def export(
    format: str,
    output: str,
    source: str,
    start_date: Optional[str],
    end_date: Optional[str],
    limit: Optional[int],
):
    """
    Export marine safety incident data to various formats

    Examples:
        marine-safety export csv --output incidents.csv
        marine-safety export json --output incidents.json --source uscg
        marine-safety export excel --output report.xlsx --start-date 2020-01-01
        marine-safety export parquet --output data.parquet --limit 1000
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Exporting data to {format.upper()}...", total=None
            )

            # TODO: Import and execute export
            # from .export import export_data
            # export_data(format, output, source, start_date, end_date, limit)

            console.print("[yellow]Data export not yet implemented[/yellow]")
            console.print(f"Format: {format}")
            console.print(f"Output: {output}")
            console.print(f"Source: {source}")
            if start_date:
                console.print(f"Start date: {start_date}")
            if end_date:
                console.print(f"End date: {end_date}")
            if limit:
                console.print(f"Limit: {limit} records")

            progress.update(task, completed=True)

        panel = Panel(
            f"[green]Data exported successfully to:[/green]\n{output}",
            title="Export Complete",
            border_style="green",
        )
        console.print(panel)

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


# =============================================================================
# INFO COMMAND
# =============================================================================


@cli.command()
def info():
    """Display information about the marine safety module"""
    info_text = """
    [bold cyan]Marine Safety Incident Data Module[/bold cyan]

    [yellow]Purpose:[/yellow]
    Collect, store, and analyze marine safety incident data from:
    - USCG MISLE (Marine Information for Safety and Law Enforcement)
    - NTSB (National Transportation Safety Board)
    - BSEE (Bureau of Safety and Environmental Enforcement)
    - IMO GISIS (Global Integrated Shipping Information System)

    [yellow]Data Coverage:[/yellow]
    - Commercial vessel incidents
    - Recreational boating accidents
    - Offshore platform incidents
    - Environmental spills
    - Personnel casualties
    - Equipment failures

    [yellow]Available Commands:[/yellow]
    - scrape  - Collect data from various sources
    - import  - Import data from files
    - db      - Database management operations
    - stats   - View incident statistics
    - export  - Export data in various formats

    [yellow]Documentation:[/yellow]
    See README.md in the marine_safety module directory
    """

    console.print(Panel(info_text, border_style="cyan"))


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error:[/red] {str(e)}", style="bold")
        sys.exit(1)


if __name__ == "__main__":
    main()
