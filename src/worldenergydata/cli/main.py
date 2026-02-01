"""
Unified CLI for WorldEnergyData.

This module provides the main entry point for the WorldEnergyData command-line
interface, orchestrating all module-specific commands through a unified Typer
application with Rich console output.

Architecture:
    The CLI uses a modular architecture where each domain module (bsee,
    marine-safety, fdas) provides its own Typer sub-application that is
    registered with the main app.

Usage:
    worldenergydata <module> <command> [options]

    # Show help
    worldenergydata --help

    # Show available modules
    worldenergydata info

    # Module-specific commands
    worldenergydata bsee analyze --field "MC252"
    worldenergydata bsee report --block 759 --format excel
    worldenergydata marine-safety stats --source uscg
    worldenergydata fdas calculate-npv --discount-rate 0.10

Modules:
    bsee          - BSEE (Bureau of Safety and Environmental Enforcement) data
                    including well production, directional surveys, and reports
    marine-safety - Marine safety incident data from USCG, NTSB, MAIB, TSB
    fdas          - Field Development Analysis System for NPV, MIRR, IRR

Global Commands:
    version       - Display version information
    info          - Display information about available modules
    status        - Display system status and data availability

Dependencies:
    - typer: CLI framework
    - rich: Console formatting and progress display

See Also:
    - docs/CLI.md: Complete CLI reference documentation
    - src/worldenergydata/cli/commands/: Module-specific command implementations
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from worldenergydata.cli.commands import (
    bsee,
    canada,
    fdas,
    landman,
    lng_terminals,
    marine_safety,
    metocean,
    mexico_cnh,
    sodir,
    texas_rrc,
)

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
app.add_typer(bsee.app, name="bsee", help="BSEE data operations and analysis")
app.add_typer(
    marine_safety.app,
    name="marine-safety",
    help="Marine safety incident data management",
)
app.add_typer(fdas.app, name="fdas", help="Field Development Analysis System")
app.add_typer(
    sodir.app,
    name="sodir",
    help="SODIR (Norwegian Offshore Directorate) data operations",
)
app.add_typer(
    metocean.app, name="metocean", help="Metocean data - buoys, tides, marine weather"
)
app.add_typer(
    texas_rrc.app, name="texas-rrc", help="Texas Railroad Commission oil & gas data"
)
app.add_typer(canada.app, name="canada", help="Canadian oil & gas data (AER/BCER)")
app.add_typer(
    mexico_cnh.app,
    name="mexico-cnh",
    help="Mexico CNH oil & gas data (SIH dashboard)",
)
app.add_typer(
    landman.app,
    name="landman",
    help="Mineral ownership and lease data operations",
)
app.add_typer(
    lng_terminals.app,
    name="lng-terminals",
    help="Global LNG terminal dataset with engineering design data",
)


@app.command()
def version() -> None:
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
            border_style="cyan",
        )
    )


@app.command()
def info() -> None:
    """Display information about available modules."""
    table = Table(
        title="WorldEnergyData Modules", show_header=True, header_style="bold cyan"
    )

    table.add_column("Module", style="bold")
    table.add_column("Description")
    table.add_column("Key Commands", style="dim")

    table.add_row(
        "bsee", "BSEE data operations and analysis", "analyze, report, data, refresh"
    )
    table.add_row(
        "marine-safety", "Marine safety incident data", "scrape, stats, export, db"
    )
    table.add_row(
        "fdas",
        "Field Development Analysis System",
        "calculate-npv, calculate-mirr, analyze",
    )
    table.add_row(
        "sodir", "SODIR (Norwegian Offshore Directorate)", "collect, analyze, status"
    )
    table.add_row(
        "metocean",
        "Metocean data (buoys, tides, weather)",
        "stations, fetch, forecast, cache, db",
    )
    table.add_row(
        "texas-rrc",
        "Texas Railroad Commission oil & gas",
        "collect, analyze, status, validate-api",
    )
    table.add_row(
        "canada",
        "Canadian oil & gas (AER/BCER)",
        "collect, analyze, status, validate-uwi",
    )
    table.add_row(
        "mexico-cnh",
        "Mexico CNH oil & gas (SIH dashboard)",
        "scrape, download-open-data, status, validate-clave",
    )
    table.add_row(
        "landman",
        "Mineral ownership and lease data",
        "search, lookup, county-info, providers, status",
    )
    table.add_row(
        "lng-terminals",
        "Global LNG terminal dataset",
        "collect, process, export, report, pipeline",
    )

    console.print(table)

    console.print(
        "\n[dim]Use 'worldenergydata <module> --help' for module-specific commands[/dim]"
    )


@app.command()
def status() -> None:
    """Display system status and data availability."""
    from pathlib import Path

    console.print(Panel("[bold]System Status[/bold]", border_style="green"))

    # Check data directories
    data_paths = {
        "BSEE Data": Path("data/bsee"),
        "Marine Safety Data": Path("data/marine_safety"),
        "SODIR Data": Path("data/sodir"),
        "Metocean Data": Path("data/metocean"),
        "Texas RRC Data": Path("data/texas_rrc"),
        "Canada Data": Path("data/canada"),
        "Mexico CNH Data": Path("data/mexico_cnh"),
        "Landman Data": Path("data/landman"),
        "LNG Terminals Data": Path("data/modules/lng_terminals"),
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
                name, "[green]Available[/green]", f"{file_count} files"
            )
        else:
            status_table.add_row(name, "[yellow]Not Found[/yellow]", f"Path: {path}")

    console.print(status_table)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(  # noqa: B008  # noqa: B008
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
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
                border_style="cyan",
            )
        )
        raise typer.Exit()


if __name__ == "__main__":
    app()
