"""
Unified CLI for WorldEnergyData.

Usage:
    worldenergydata <module> <command> [options]

Examples:
    worldenergydata bsee analyze --field "MC252"
    worldenergydata bsee report --block 759 --format excel
    worldenergydata marine-safety stats --source uscg
    worldenergydata fdas calculate-npv --discount-rate 0.10

Modules:
    bsee          - BSEE (Bureau of Safety and Environmental Enforcement) data
    marine-safety - Marine safety incident data management
    fdas          - Field Development Analysis System
"""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from worldenergydata.cli.commands import bsee, marine_safety, fdas

# Initialize console for rich output
console = Console()

# Create main Typer app
app = typer.Typer(
    name="worldenergydata",
    help="World Energy Data - Global energy market data platform",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Add module subcommands
app.add_typer(
    bsee.app,
    name="bsee",
    help="BSEE data operations and analysis"
)
app.add_typer(
    marine_safety.app,
    name="marine-safety",
    help="Marine safety incident data management"
)
app.add_typer(
    fdas.app,
    name="fdas",
    help="Field Development Analysis System"
)


@app.command()
def version():
    """Display version information."""
    try:
        from worldenergydata import __version__
    except ImportError:
        __version__ = "0.1.0"

    console.print(
        Panel(
            f"[bold cyan]WorldEnergyData[/bold cyan]\n"
            f"Version: [green]{__version__}[/green]\n"
            f"Global energy market data aggregation platform",
            title="About",
            border_style="cyan"
        )
    )


@app.command()
def info():
    """Display information about available modules."""
    table = Table(
        title="WorldEnergyData Modules",
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Module", style="bold")
    table.add_column("Description")
    table.add_column("Key Commands", style="dim")

    table.add_row(
        "bsee",
        "BSEE data operations and analysis",
        "analyze, report, data, refresh"
    )
    table.add_row(
        "marine-safety",
        "Marine safety incident data",
        "scrape, stats, export, db"
    )
    table.add_row(
        "fdas",
        "Field Development Analysis System",
        "calculate-npv, calculate-mirr, analyze"
    )

    console.print(table)

    console.print("\n[dim]Use 'worldenergydata <module> --help' for module-specific commands[/dim]")


@app.command()
def status():
    """Display system status and data availability."""
    from pathlib import Path
    import os

    console.print(
        Panel(
            "[bold]System Status[/bold]",
            border_style="green"
        )
    )

    # Check data directories
    data_paths = {
        "BSEE Data": Path("data/bsee"),
        "Marine Safety Data": Path("data/marine_safety"),
        "Reports": Path("reports"),
    }

    status_table = Table(show_header=True, header_style="bold")
    status_table.add_column("Component")
    status_table.add_column("Status")
    status_table.add_column("Details", style="dim")

    for name, path in data_paths.items():
        if path.exists():
            file_count = len(list(path.rglob("*"))) if path.is_dir() else 1
            status_table.add_row(
                name,
                "[green]Available[/green]",
                f"{file_count} files"
            )
        else:
            status_table.add_row(
                name,
                "[yellow]Not Found[/yellow]",
                f"Path: {path}"
            )

    console.print(status_table)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    WorldEnergyData CLI - Global energy market data platform.

    Access BSEE production data, marine safety incidents, and field development
    analysis tools through a unified command-line interface.
    """
    if ctx.invoked_subcommand is None:
        # Show help if no subcommand provided
        console.print(
            Panel(
                "[bold cyan]WorldEnergyData[/bold cyan]\n\n"
                "Global energy market data aggregation, analysis, and visualization platform.\n\n"
                "[dim]Use --help for available commands[/dim]",
                border_style="cyan"
            )
        )
        raise typer.Exit()


if __name__ == "__main__":
    app()
