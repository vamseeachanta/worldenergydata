# ABOUTME: CLI commands for exporting marine safety incident data.
# ABOUTME: Supports CSV and JSON export formats from SQLite database.

"""
Marine Safety CLI - Export Commands

Commands for exporting marine safety incident data to CSV or JSON.
"""

import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.marine_safety.cli_utils import (
    console,
    create_progress_spinner,
)


def _default_db_path() -> Path:
    """Return the default SQLite database path.

    Carve-safe (#529): resolve via the common data resolver (WED_DATA_ROOT /
    workspace-root ``data/``) instead of a ``__file__``-relative parent walk,
    which broke once this domain moved into
    ``packages/worldenergydata-marine_safety/``.
    """
    return get_module_data_safe("marine_safety") / "marine_safety.db"


def _resolve_db_path(db_url: Optional[str]) -> Path:
    """Resolve a db-url string to a concrete Path."""
    if db_url:
        path_str = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        return Path(path_str)
    return _default_db_path()


@click.command()
@click.argument(
    "format",
    type=click.Choice(["csv", "json"], case_sensitive=False),
)
@click.option("--output", type=click.Path(), required=True, help="Output file path")
@click.option(
    "--source",
    type=click.Choice(
        ["all", "uscg", "ntsb", "bsee", "maib", "other"], case_sensitive=False
    ),
    default="all",
    help="Data source to export",
)
@click.option("--start-date", help="Start date filter (YYYY-MM-DD)")
@click.option("--end-date", help="End date filter (YYYY-MM-DD)")
@click.option("--limit", type=int, help="Limit number of records to export")
@click.option("--db-url", help="Database connection URL (defaults to SQLite)")
def export(
    format: str,
    output: str,
    source: str,
    start_date: Optional[str],
    end_date: Optional[str],
    limit: Optional[int],
    db_url: Optional[str],
):
    """
    Export marine safety incident data to CSV or JSON

    Examples:
        marine-safety export csv --output incidents.csv
        marine-safety export json --output incidents.json --source uscg
        marine-safety export csv --output recent.csv --start-date 2024-01-01
        marine-safety export json --output subset.json --limit 100
    """
    try:
        db_path = _resolve_db_path(db_url)

        if not db_path.exists():
            console.print("[red]Database not found.[/red] Run 'db init' first.")
            sys.exit(1)

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with create_progress_spinner("Exporting") as progress:
            task = progress.add_task(
                f"[cyan]Exporting data to {format.upper()}...", total=None
            )

            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            try:
                query = "SELECT * FROM incidents WHERE 1=1"
                params = []

                if source != "all":
                    query += " AND LOWER(source_agency) = ?"
                    params.append(source.lower())

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

                if not rows:
                    console.print(
                        "[yellow]No records match the filter criteria[/yellow]"
                    )
                    progress.update(task, completed=True)
                    return

                columns = [desc[0] for desc in cur.description]
                records = [dict(zip(columns, row)) for row in rows]

                if format.lower() == "csv":
                    with open(output_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=columns)
                        writer.writeheader()
                        writer.writerows(records)
                else:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(records, f, indent=2, default=str)

            finally:
                conn.close()

            progress.update(task, completed=True)

        panel = Panel(
            f"[green]Exported {len(records)} records to:[/green]\n{output_path}",
            title="Export Complete",
            border_style="green",
        )
        console.print(panel)

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@click.command()
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
