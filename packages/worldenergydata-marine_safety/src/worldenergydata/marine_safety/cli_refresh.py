# ABOUTME: CLI commands for refreshing marine safety data from sources.
# ABOUTME: Combines scraping and importing operations for data updates.

"""
Marine Safety CLI - Refresh Commands

Commands for refreshing incident data from sources (scrape + import).
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from worldenergydata.marine_safety.cli_utils import console


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
                f"Date range: {since.strftime('%Y-%m-%d')} - {datetime.now().strftime('%Y-%m-%d')}\n"  # noqa: E501
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

        console.print(f"[green]v Scraped {len(data)} records to {output_file}[/green]")

        # Step 2: Import
        console.print("\n[bold cyan]Step 2/2: Importing to database...[/bold cyan]")
        from worldenergydata.marine_safety.database.db_manager import (
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
            console.print("[dim]Cleaned up temporary files[/dim]")

        console.print(f"\n[green]v {source_name.upper()} refresh complete[/green]")

    except Exception as e:
        console.print(f"[red]x Refresh failed: {e}[/red]")
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


@click.group()
def refresh():
    """Refresh incident data from sources (scrape + import)"""
    pass


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
    from worldenergydata.marine_safety.importers.ntsb_importer import (
        NTSBImporter,
    )
    from worldenergydata.marine_safety.scrapers.ntsb_scraper import NTSBScraper

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
    from worldenergydata.marine_safety.importers.atsb_importer import (
        ATSBImporter,
    )
    from worldenergydata.marine_safety.scrapers.atsb_scraper import ATSBScraper

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
        download_url="https://www.gov.uk/government/organisations/marine-accident-investigation-branch",  # noqa: E501
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
                from worldenergydata.marine_safety.importers.ntsb_importer import (
                    NTSBImporter,
                )
                from worldenergydata.marine_safety.scrapers.ntsb_scraper import (
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
                from worldenergydata.marine_safety.importers.atsb_importer import (
                    ATSBImporter,
                )
                from worldenergydata.marine_safety.scrapers.atsb_scraper import (
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
                    "maib": "https://www.gov.uk/government/organisations/marine-accident-investigation-branch",  # noqa: E501
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
            console.print(f"[red]x Error processing {source}: {e}[/red]")
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
            status_str = "[green]v Success[/green]"
        elif status == "manual":
            status_str = "[yellow]! Manual[/yellow]"
        else:
            status_str = "[red]x Error[/red]"
        summary_table.add_row(source.upper(), status_str)

    console.print(summary_table)

    if errors:
        console.print(f"\n[red]Errors occurred in: {', '.join(errors)}[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]v All sources processed successfully[/green]")
