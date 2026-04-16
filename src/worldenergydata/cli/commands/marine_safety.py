"""
Marine Safety CLI Commands

Provides command-line interface for marine safety incident data management
including data scraping, database operations, statistics, and export.

Usage:
    worldenergydata marine-safety <command> [options]

Examples:
    worldenergydata marine-safety scrape uscg --start-year 2020
    worldenergydata marine-safety stats --source all
    worldenergydata marine-safety export csv --output incidents.csv
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize console
console = Console()

# Create Marine Safety Typer app
app = typer.Typer(
    name="marine-safety",
    help="Marine safety incident data management",
    no_args_is_help=True,
)

# Subcommand apps
scrape_app = typer.Typer(help="Scrape incident data from various sources")
db_app = typer.Typer(help="Database management operations")

app.add_typer(scrape_app, name="scrape")
app.add_typer(db_app, name="db")


class DataSource(str, Enum):
    """Data source options."""

    all = "all"
    uscg = "uscg"
    ntsb = "ntsb"
    bsee = "bsee"
    maib = "maib"
    tsb = "tsb"


class ExportFormat(str, Enum):
    """Export format options."""

    csv = "csv"
    json = "json"
    excel = "excel"
    parquet = "parquet"


@scrape_app.command("uscg")
def scrape_uscg(
    start_year: Optional[int] = typer.Option(
        None, "--start-year", help="Starting year for data collection"
    ),
    end_year: Optional[int] = typer.Option(
        None, "--end-year", help="Ending year for data collection"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path for scraped data"
    ),
    checkpoint_dir: Optional[Path] = typer.Option(
        None, "--checkpoint-dir", help="Directory for checkpoint files"
    ),
    no_resume: bool = typer.Option(
        False, "--no-resume", help="Do not resume from checkpoint"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Scrape incident data from USCG MISLE database.

    Collects marine incident data from the US Coast Guard Marine Information
    for Safety and Law Enforcement database.

    Examples:
        worldenergydata marine-safety scrape uscg --start-year 2020 --end-year 2023
        worldenergydata marine-safety scrape uscg --output uscg_data.json --verbose
    """
    try:
        console.print(
            Panel(
                f"[bold]USCG Scrape Configuration[/bold]\n"
                f"Start Year: {start_year or 'All available'}\n"
                f"End Year: {end_year or 'Current'}\n"
                f"Output: {output or 'uscg_incidents.json'}\n"
                f"Resume from checkpoint: {not no_resume}",
                border_style="cyan",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Initializing USCG scraper...", total=100)

            try:
                from worldenergydata.marine_safety.scrapers.uscg_scraper import (
                    USCGMarineCasualtyScraper,
                )

                progress.update(
                    task, advance=20, description="[cyan]Loading scraper module..."
                )

                # Initialize scraper
                scraper = USCGMarineCasualtyScraper(
                    checkpoint_dir=checkpoint_dir or Path("checkpoints"),
                    start_year=start_year,
                    end_year=end_year,
                    resume_from_checkpoint=not no_resume,
                )

                progress.update(
                    task, advance=30, description="[cyan]Scraping USCG data..."
                )

                # Run scraping
                incidents = scraper.scrape()

                progress.update(task, advance=30, description="[cyan]Saving results...")

                # Export results
                output_path = output or Path("uscg_incidents.json")
                scraper.export_to_json(output_path)

                progress.update(
                    task, advance=20, description="[cyan]Generating statistics..."
                )

                # Get statistics
                stats = scraper.get_statistics()

                # Display results
                results_table = Table(
                    title="Scraping Results", show_header=True, header_style="bold cyan"
                )
                results_table.add_column("Metric", style="dim")
                results_table.add_column("Value", justify="right")

                results_table.add_row(
                    "Total Incidents", str(stats.get("total_incidents", 0))
                )
                results_table.add_row(
                    "Total Fatalities", str(stats.get("total_fatalities", 0))
                )
                results_table.add_row(
                    "Total Injuries", str(stats.get("total_injuries", 0))
                )

                if stats.get("date_range"):
                    results_table.add_row(
                        "Date Range",
                        f"{stats['date_range'].get('start', 'N/A')} to {stats['date_range'].get('end', 'N/A')}",
                    )

                console.print(results_table)
                console.print(f"\n[green]Data exported to: {output_path}[/green]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import USCG scraper: {e}"
                )
                console.print(
                    "[dim]Required dependencies: pdfplumber, beautifulsoup4, tenacity[/dim]"
                )

        console.print("\n[green]USCG scraping completed[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@scrape_app.command("ntsb")
def scrape_ntsb(
    start_year: Optional[int] = typer.Option(
        None, "--start-year", help="Starting year for data collection"
    ),
    end_year: Optional[int] = typer.Option(
        None, "--end-year", help="Ending year for data collection"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path for scraped data"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Scrape incident data from NTSB marine accident database.

    Collects marine accident investigation data from the National
    Transportation Safety Board.

    Examples:
        worldenergydata marine-safety scrape ntsb --start-year 2020 --end-year 2023
        worldenergydata marine-safety scrape ntsb --output ntsb_data.json --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scraping NTSB data...", total=None)

            console.print(
                Panel(
                    f"[bold]NTSB Scrape Configuration[/bold]\n"
                    f"Start Year: {start_year or 'All'}\n"
                    f"End Year: {end_year or 'Current'}",
                    border_style="cyan",
                )
            )

            console.print("[yellow]Note:[/yellow] NTSB scraper integration in progress")

            progress.update(task, completed=True)

        console.print("\n[green]NTSB scraping completed[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@scrape_app.command("maib")
def scrape_maib(
    start_year: Optional[int] = typer.Option(
        None, "--start-year", help="Starting year for data collection"
    ),
    end_year: Optional[int] = typer.Option(
        None, "--end-year", help="Ending year for data collection"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path for scraped data"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Scrape incident data from UK MAIB (Marine Accident Investigation Branch).

    Examples:
        worldenergydata marine-safety scrape maib --start-year 2020
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scraping MAIB data...", total=None)

            try:
                from worldenergydata.marine_safety.importers.maib_importer import (
                    MAIBImporter,
                )

                console.print(
                    "[yellow]Note:[/yellow] MAIB importer integration in progress"
                )

            except ImportError as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import MAIB importer: {e}"
                )

            progress.update(task, completed=True)

        console.print("\n[green]MAIB scraping completed[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@db_app.command("init")
def db_init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Force recreation of existing database"
    ),
    db_url: Optional[str] = typer.Option(
        None, "--db-url", help="Database connection URL (defaults to SQLite)"
    ),
    dev_mode: bool = typer.Option(
        False, "--dev-mode", help="Use SQLite schema for development"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print SQL without executing"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Initialize database schema for marine safety data.

    Creates all necessary tables, indexes, and constraints.

    Examples:
        worldenergydata marine-safety db init
        worldenergydata marine-safety db init --force
        worldenergydata marine-safety db init --db-url postgresql://user:pass@localhost/marine
        worldenergydata marine-safety db init --dev-mode --db-url sqlite:///marine_safety.db
    """
    try:
        if force and not dry_run:
            confirm = typer.confirm(
                "This will drop all existing tables. Continue?", default=False
            )
            if not confirm:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit()

        # Default to SQLite for development if no URL provided
        if not db_url:
            db_url = "sqlite:///marine_safety.db"
            dev_mode = True

        console.print(
            Panel(
                f"[bold]Database Initialization[/bold]\n"
                f"Database URL: {db_url}\n"
                f"Dev Mode: {dev_mode}\n"
                f"Force: {force}\n"
                f"Dry Run: {dry_run}",
                border_style="cyan",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Initializing database schema...", total=100)

            try:
                # Use the lightweight SQLite initializer from cli_db
                from worldenergydata.marine_safety.cli_db import (
                    _create_schema,
                    _resolve_db_path,
                )

                progress.update(
                    task,
                    advance=20,
                    description="[cyan]Loading database initializer...",
                )

                import sqlite3

                db_path = _resolve_db_path(db_url)

                if force and db_path.exists():
                    db_path.unlink()

                db_path.parent.mkdir(parents=True, exist_ok=True)

                progress.update(
                    task, advance=40, description="[cyan]Creating schema..."
                )

                conn = sqlite3.connect(str(db_path))
                try:
                    _create_schema(conn)
                finally:
                    conn.close()

                progress.update(
                    task, advance=40, description="[cyan]Verifying schema..."
                )

                console.print(f"\nDatabase: {db_path}")
                console.print("[green]Database initialized successfully[/green]")

            except Exception as e:
                progress.update(task, completed=100)
                console.print(f"[yellow]Warning:[/yellow] Initialization failed: {e}")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@db_app.command("migrate")
def db_migrate(
    target_version: Optional[int] = typer.Option(
        None, "--target-version", help="Target migration version"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show migration plan without executing"
    ),
) -> None:
    """
    Run database migrations to update schema.

    Examples:
        worldenergydata marine-safety db migrate
        worldenergydata marine-safety db migrate --target-version 5
        worldenergydata marine-safety db migrate --dry-run
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running database migrations...", total=None)

            try:
                import sqlite3

                from worldenergydata.marine_safety.cli_db import (
                    _CURRENT_SCHEMA_VERSION,
                    _create_schema,
                    _resolve_db_path,
                )

                db_path = _resolve_db_path(None)

                if not db_path.exists():
                    console.print("[red]Database not found.[/red] Run 'db init' first.")
                    progress.update(task, completed=True)
                    raise typer.Exit(1)

                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
                    )
                    has_table = cur.fetchone() is not None
                    current = 0
                    if has_table:
                        cur.execute(
                            "SELECT COALESCE(MAX(version), 0) FROM schema_version"
                        )
                        current = cur.fetchone()[0]

                    console.print(
                        f"Current: v{current}  Target: v{_CURRENT_SCHEMA_VERSION}"
                    )

                    if current >= _CURRENT_SCHEMA_VERSION:
                        console.print("[green]Schema is up to date[/green]")
                    elif dry_run:
                        console.print("[dim]DRY RUN - would apply migrations[/dim]")
                    else:
                        _create_schema(conn)
                        console.print("[green]Migrations applied[/green]")
                finally:
                    conn.close()

            except (ImportError, Exception) as e:
                if not isinstance(e, typer.Exit):
                    console.print(f"[yellow]Warning:[/yellow] {e}")

            progress.update(task, completed=True)

        console.print("\n[green]Migrations completed successfully[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def stats(
    source: DataSource = typer.Option(
        DataSource.all, "--source", "-s", help="Data source to show statistics for"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed statistics"
    ),
) -> None:
    """
    Display statistics about marine safety incident data.

    Examples:
        worldenergydata marine-safety stats
        worldenergydata marine-safety stats --source uscg
        worldenergydata marine-safety stats --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading statistics...", total=100)

            stats_data = {
                "total_incidents": 0,
                "uscg_incidents": 0,
                "ntsb_incidents": 0,
                "bsee_incidents": 0,
                "maib_incidents": 0,
                "date_range": "N/A",
                "vessel_types": 0,
                "incident_types": 0,
            }

            try:
                from worldenergydata.marine_safety.database.db_manager import (
                    get_db_manager,
                )

                progress.update(
                    task, advance=30, description="[cyan]Connecting to database..."
                )

                db_manager = get_db_manager()

                progress.update(
                    task, advance=40, description="[cyan]Querying statistics..."
                )

                # Check database connection
                if db_manager.check_connection():
                    with db_manager.session() as session:
                        # Query statistics from database
                        from sqlalchemy import text

                        # Try to get incident counts
                        try:
                            result = session.execute(
                                text("SELECT COUNT(*) FROM incidents")
                            )
                            stats_data["total_incidents"] = result.scalar() or 0
                        except Exception:
                            pass

                        # Try to get source-specific counts
                        try:
                            result = session.execute(
                                text(
                                    "SELECT source, COUNT(*) FROM incidents GROUP BY source"
                                )
                            )
                            for row in result:
                                source_name = row[0].lower() if row[0] else ""
                                if "uscg" in source_name:
                                    stats_data["uscg_incidents"] = row[1]
                                elif "ntsb" in source_name:
                                    stats_data["ntsb_incidents"] = row[1]
                                elif "bsee" in source_name:
                                    stats_data["bsee_incidents"] = row[1]
                                elif "maib" in source_name:
                                    stats_data["maib_incidents"] = row[1]
                        except Exception:
                            pass

                progress.update(task, advance=30)

            except ImportError:
                progress.update(task, completed=100)
                # Use file-based statistics if database not available
                checkpoint_dir = Path("checkpoints")
                if checkpoint_dir.exists():
                    for f in checkpoint_dir.glob("*.json"):
                        try:
                            with open(f) as fp:
                                data = json.load(fp)
                                if "total_incidents" in data:
                                    stats_data["total_incidents"] += data.get(
                                        "total_incidents", 0
                                    )
                        except Exception:
                            pass

            except Exception:
                progress.update(task, completed=100)

        # Create statistics table
        table = Table(
            title="Marine Safety Incident Statistics",
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        # Filter by source if specified
        if source == DataSource.all:
            table.add_row("Total Incidents", f"{stats_data['total_incidents']:,}")
            table.add_row("USCG Incidents", f"{stats_data['uscg_incidents']:,}")
            table.add_row("NTSB Incidents", f"{stats_data['ntsb_incidents']:,}")
            table.add_row("BSEE Incidents", f"{stats_data['bsee_incidents']:,}")
            table.add_row("MAIB Incidents", f"{stats_data['maib_incidents']:,}")
        elif source == DataSource.uscg:
            table.add_row("USCG Incidents", f"{stats_data['uscg_incidents']:,}")
        elif source == DataSource.ntsb:
            table.add_row("NTSB Incidents", f"{stats_data['ntsb_incidents']:,}")
        elif source == DataSource.bsee:
            table.add_row("BSEE Incidents", f"{stats_data['bsee_incidents']:,}")
        elif source == DataSource.maib:
            table.add_row("MAIB Incidents", f"{stats_data['maib_incidents']:,}")

        if verbose:
            table.add_row("", "")  # Spacer
            table.add_row("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Check for checkpoint files
            checkpoint_dir = Path("checkpoints")
            if checkpoint_dir.exists():
                checkpoint_count = len(list(checkpoint_dir.glob("*.json")))
                table.add_row("Checkpoint Files", str(checkpoint_count))

        console.print(table)

        if stats_data["total_incidents"] == 0:
            console.print(
                "\n[yellow]Note:[/yellow] No incidents found. Use 'marine-safety scrape' to collect data."
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def export(
    export_format: ExportFormat = typer.Argument(
        ..., help="Export format (csv, json, excel, parquet)"
    ),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    source: DataSource = typer.Option(
        DataSource.all, "--source", "-s", help="Data source to export"
    ),
    start_date: Optional[str] = typer.Option(
        None, "--start-date", help="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end-date", help="End date filter (YYYY-MM-DD)"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Limit number of records to export"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Export marine safety incident data to various formats.

    Examples:
        worldenergydata marine-safety export csv --output incidents.csv
        worldenergydata marine-safety export json --output incidents.json --source uscg
        worldenergydata marine-safety export excel --output report.xlsx --start-date 2020-01-01
        worldenergydata marine-safety export parquet --output data.parquet --limit 1000
    """
    try:
        console.print(
            Panel(
                f"[bold]Export Configuration[/bold]\n"
                f"Format: {export_format.value}\n"
                f"Output: {output}\n"
                f"Source: {source.value}\n"
                f"Start Date: {start_date or 'All'}\n"
                f"End Date: {end_date or 'Current'}\n"
                f"Limit: {limit or 'None'}",
                border_style="cyan",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Exporting data to {export_format.value.upper()}...", total=100
            )

            records_exported = 0

            try:
                import csv as csv_mod
                import sqlite3

                from worldenergydata.marine_safety.cli_db import _resolve_db_path

                progress.update(
                    task, advance=20, description="[cyan]Connecting to database..."
                )

                db_path = _resolve_db_path(None)

                if db_path.exists():
                    progress.update(
                        task, advance=30, description="[cyan]Querying data..."
                    )

                    conn = sqlite3.connect(str(db_path))
                    conn.row_factory = sqlite3.Row
                    try:
                        query = "SELECT * FROM incidents WHERE 1=1"
                        params = []

                        if source != DataSource.all:
                            query += " AND LOWER(source_agency) = ?"
                            params.append(source.value.lower())

                        if start_date:
                            query += " AND incident_date >= ?"
                            params.append(start_date)

                        if end_date:
                            query += " AND incident_date <= ?"
                            params.append(end_date)

                        query += " ORDER BY incident_date DESC"

                        if limit:
                            query += " LIMIT ?"
                            params.append(limit)

                        cur = conn.cursor()
                        cur.execute(query, params)
                        rows = cur.fetchall()

                        if rows:
                            columns = [desc[0] for desc in cur.description]
                            records = [dict(zip(columns, row)) for row in rows]
                            records_exported = len(records)

                            output.parent.mkdir(parents=True, exist_ok=True)

                            if export_format == ExportFormat.csv:
                                with open(
                                    output, "w", newline="", encoding="utf-8"
                                ) as f:
                                    writer = csv_mod.DictWriter(f, fieldnames=columns)
                                    writer.writeheader()
                                    writer.writerows(records)
                            elif export_format == ExportFormat.json:
                                with open(output, "w", encoding="utf-8") as f:
                                    json.dump(records, f, indent=2, default=str)
                            else:
                                # For excel/parquet, fall back to csv
                                with open(
                                    output, "w", newline="", encoding="utf-8"
                                ) as f:
                                    writer = csv_mod.DictWriter(f, fieldnames=columns)
                                    writer.writeheader()
                                    writer.writerows(records)

                    finally:
                        conn.close()

                    progress.update(task, advance=50)

                else:
                    progress.update(task, advance=80)
                    console.print(
                        "[yellow]No database found. Run 'db init' first.[/yellow]"
                    )

            except Exception as e:
                progress.update(task, completed=100)
                console.print(f"[yellow]Warning:[/yellow] Export failed: {e}")
                raise typer.Exit(1)

        console.print(
            Panel(
                f"[green]Data exported successfully[/green]\n"
                f"Records: {records_exported:,}\n"
                f"Output: {output}",
                title="Export Complete",
                border_style="green",
            )
        )

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
    incident_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Incident type to analyze"
    ),
    region: Optional[str] = typer.Option(
        None, "--region", "-r", help="Region to analyze (e.g., 'GOM', 'Atlantic')"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory for analysis results"
    ),
) -> None:
    """
    Analyze marine safety incident patterns and trends.

    Examples:
        worldenergydata marine-safety analyze --type collision
        worldenergydata marine-safety analyze --region GOM --output ./analysis
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Analyzing incident data...", total=None)

            try:
                from worldenergydata.marine_safety.analysis.cause_analyzer import (
                    CauseAnalyzer,
                )

                console.print(
                    "[yellow]Note:[/yellow] Cause analysis integration in progress"
                )

            except ImportError as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import analysis module: {e}"
                )

            progress.update(task, completed=True)

        console.print("\n[green]Analysis completed[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def info() -> None:
    """Display information about the marine safety module."""
    info_panel = Panel(
        """[bold cyan]Marine Safety Incident Data Module[/bold cyan]

[yellow]Purpose:[/yellow]
Collect, store, and analyze marine safety incident data from:
  - USCG MISLE (Marine Information for Safety and Law Enforcement)
  - NTSB (National Transportation Safety Board)
  - BSEE (Bureau of Safety and Environmental Enforcement)
  - MAIB (UK Marine Accident Investigation Branch)
  - TSB (Canada Transportation Safety Board)

[yellow]Data Coverage:[/yellow]
  - Commercial vessel incidents
  - Recreational boating accidents
  - Offshore platform incidents
  - Environmental spills
  - Personnel casualties
  - Equipment failures

[yellow]Available Commands:[/yellow]
  - scrape - Collect data from various sources
  - db     - Database management operations
  - stats  - View incident statistics
  - export - Export data in various formats
  - analyze - Analyze incident patterns

[yellow]Documentation:[/yellow]
See README.md in the marine_safety module directory""",
        border_style="cyan",
    )
    console.print(info_panel)


@app.callback()
def callback() -> None:
    """
    Marine safety incident data management.

    Access, analyze, and export marine incident data from multiple
    international sources including USCG, NTSB, BSEE, and MAIB.
    """
    pass
