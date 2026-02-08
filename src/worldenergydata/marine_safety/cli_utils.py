# ABOUTME: Shared utilities for Marine Safety CLI modules.
# ABOUTME: Contains Rich console instance, common imports, and helper functions.

"""
Marine Safety CLI Utilities

Shared utilities, console instance, and helper functions used across CLI modules.
"""

import sys
# from datetime import datetime  # noqa: F401
# from pathlib import Path  # noqa: F401
# from typing import Optional  # noqa: F401

# import click  # noqa: F401
from rich.console import Console
# from rich.panel import Panel  # noqa: F401
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize Rich console - shared across all CLI modules
console = Console()


def display_import_stats(stats: dict, title: str = "Import Statistics") -> None:
    """
    Display standardized import statistics table.

    Args:
        stats: Dictionary containing import statistics
        title: Title for the statistics table
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Count", justify="right")

    table.add_row("Total Records", str(stats["total_records"]))
    table.add_row("[green]Imported[/green]", f"[green]{stats['imported']}[/green]")
    table.add_row("[yellow]Skipped[/yellow]", f"[yellow]{stats['skipped']}[/yellow]")
    table.add_row(
        "[yellow]Duplicates[/yellow]", f"[yellow]{stats['duplicates']}[/yellow]"
    )
    table.add_row("[red]Errors[/red]", f"[red]{stats['errors']}[/red]")

    console.print(table)


def display_preview_records(previews: list, record_label: str = "Record") -> None:
    """
    Display preview records in standardized format.

    Args:
        previews: List of record dictionaries to preview
        record_label: Label to use for each record
    """
    for i, record in enumerate(previews, 1):
        console.print(f"[bold]{record_label} {i}:[/bold]")
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

    console.print(f"[green]Preview complete: {len(previews)} records shown[/green]")


def handle_import_error(error: Exception, verbose: bool = False) -> None:
    """
    Handle common import errors with standardized output.

    Args:
        error: The exception that occurred
        verbose: Whether to show full traceback
    """
    if isinstance(error, ImportError):
        console.print(f"[red]x Import Error:[/red] {str(error)}", style="bold")
        console.print(
            "[yellow]Ensure database is initialized: marine-safety db init[/yellow]"
        )
    elif isinstance(error, FileNotFoundError):
        console.print(f"[red]x File not found:[/red] {str(error)}", style="bold")
    else:
        console.print(f"[red]x Error:[/red] {str(error)}", style="bold")

    if verbose:
        import traceback

        console.print(traceback.format_exc())

    sys.exit(1)


def create_progress_spinner(description: str):
    """
    Create a standardized progress spinner.

    Args:
        description: Description to show in the spinner

    Returns:
        Progress context manager
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def get_source_enum(source: str):
    """
    Convert source string to DataSource enum.

    Args:
        source: Source name string

    Returns:
        DataSource enum value or None
    """
    from worldenergydata.marine_safety.constants import DataSource

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
