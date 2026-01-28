# ABOUTME: CLI commands for importing marine safety incident data from files.
# ABOUTME: Supports NTSB, USCG, BSEE, EMSA, IMO, ATSB, TSB, MAIB, NOAA, and boating data.

"""
Marine Safety CLI - Import Commands

Commands for importing incident data from files into the database.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from worldenergydata.modules.marine_safety.cli_utils import (
    console,
    create_progress_spinner,
    display_import_stats,
    display_preview_records,
    handle_import_error,
)


@click.group(name="import")
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
            display_preview_records(previews)
            return

        # Full import
        with create_progress_spinner("Importing") as progress:
            task = progress.add_task("[cyan]Importing NTSB data...", total=None)
            stats = importer.import_data(limit=limit, skip_duplicates=skip_duplicates)
            progress.update(task, completed=True)

        # Display results
        console.print()
        display_import_stats(stats, "Import Statistics")

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except Exception as e:
        handle_import_error(e, verbose)


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
            display_preview_records(previews)
            return

        # Full import
        with create_progress_spinner("Importing") as progress:
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

    except Exception as e:
        handle_import_error(e, verbose)


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
            display_preview_records(previews)
            return

        # Full import
        with create_progress_spinner("Importing") as progress:
            task = progress.add_task("[cyan]Importing ATSB data...", total=None)
            stats = importer.import_data(limit=limit, skip_duplicates=skip_duplicates)
            progress.update(task, completed=True)

        # Display results
        console.print()
        display_import_stats(stats, "ATSB Import Statistics")

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except Exception as e:
        handle_import_error(e, verbose)


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
            display_preview_records(previews)
            return

        # Full import
        with create_progress_spinner("Importing") as progress:
            task = progress.add_task("[cyan]Importing TSB data...", total=None)
            stats = importer.import_data(limit=limit)
            progress.update(task, completed=True)

        # Display results
        console.print()
        display_import_stats(stats, "TSB Import Statistics")

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except Exception as e:
        handle_import_error(e, verbose)


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
            display_preview_records(previews)
            return

        # Full import
        with create_progress_spinner("Importing") as progress:
            task = progress.add_task("[cyan]Importing MAIB data...", total=None)
            stats = importer.import_data(limit=limit)
            progress.update(task, completed=True)

        # Display results
        console.print()
        display_import_stats(stats, "MAIB Import Statistics")

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except Exception as e:
        handle_import_error(e, verbose)


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
            display_preview_records(previews)
            return

        # Full import
        with create_progress_spinner("Importing") as progress:
            task = progress.add_task("[cyan]Importing NOAA data...", total=None)
            stats = importer.import_data(limit=limit)
            progress.update(task, completed=True)

        # Display results
        console.print()
        display_import_stats(stats, "NOAA Import Statistics")

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except Exception as e:
        handle_import_error(e, verbose)


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
            display_preview_records(previews)
            return

        # Full import
        with create_progress_spinner("Importing") as progress:
            task = progress.add_task("[cyan]Importing USCG BARD data...", total=None)
            stats = importer.import_data(limit=limit)
            progress.update(task, completed=True)

        # Display results
        console.print()
        display_import_stats(stats, "USCG BARD Import Statistics")

        if stats["imported"] > 0:
            console.print(
                f"\n[green]v Successfully imported {stats['imported']} records[/green]"
            )
        else:
            console.print("\n[yellow]No new records imported[/yellow]")

    except Exception as e:
        handle_import_error(e, verbose)
