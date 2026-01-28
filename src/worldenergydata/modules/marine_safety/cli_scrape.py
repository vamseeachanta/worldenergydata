# ABOUTME: CLI commands for scraping marine safety incident data from various sources.
# ABOUTME: Includes scrapers for USCG, NTSB, BSEE, IMO, EMSA, and ATSB.

"""
Marine Safety CLI - Scrape Commands

Commands for scraping incident data from various maritime safety data sources.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from worldenergydata.modules.marine_safety.cli_utils import (
    console,
    create_progress_spinner,
)


@click.group()
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
        with create_progress_spinner("Scraping") as progress:
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

        with create_progress_spinner("Scraping") as progress:
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
        with create_progress_spinner("Scraping") as progress:
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
        with create_progress_spinner("Scraping") as progress:
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

        with create_progress_spinner("Scraping") as progress:
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
