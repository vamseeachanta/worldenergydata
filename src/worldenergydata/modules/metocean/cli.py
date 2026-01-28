# ABOUTME: Main metocean CLI entry point - orchestrates command groups.
# ABOUTME: Uses Typer for CLI framework and Rich for terminal output.

"""
Metocean CLI Interface

Main entry point that orchestrates all metocean CLI command groups.
This module registers sub-command groups for modular organization.

Usage:
    wed metocean --help
    wed metocean stations list --source ndbc --region gom
    wed metocean fetch ndbc 41001 --params wave,wind
    wed metocean historical 41001 2024-01-01 2024-12-31 --source ndbc
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from worldenergydata.modules.metocean.cli_cache import cache_app
from worldenergydata.modules.metocean.cli_db import db_app, display_config_status
from worldenergydata.modules.metocean.cli_export import export_app
from worldenergydata.modules.metocean.cli_fetch import fetch_app, historical_command
from worldenergydata.modules.metocean.cli_stations import stations_app
from worldenergydata.modules.metocean.cli_utils import SourceChoice, console

# Main application
app = typer.Typer(
    name="metocean",
    help="Metocean data management - fetch ocean and weather data from multiple sources",
    no_args_is_help=True,
)

# Register sub-command groups
app.add_typer(stations_app, name="stations")
app.add_typer(fetch_app, name="fetch")
app.add_typer(cache_app, name="cache")
app.add_typer(export_app, name="export")
app.add_typer(db_app, name="db")


# ==============================================================================
# TOP-LEVEL COMMANDS
# ==============================================================================


@app.command("historical")
def historical(
    identifier: str = typer.Argument(..., help="Station ID or lat,lon coordinates"),
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Argument(..., help="End date (YYYY-MM-DD)"),
    source: SourceChoice = typer.Option(
        SourceChoice.ndbc, "--source", "-s", help="Data source"
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    fuse: bool = typer.Option(
        False, "--fuse", help="Merge data from multiple sources (requires coords)"
    ),
) -> None:
    """Fetch historical data for a station or coordinates."""
    historical_command(identifier, start_date, end_date, source, output, fuse)


@app.command("info")
def info() -> None:
    """Display information about the metocean module."""
    info_text = """
[bold cyan]Metocean Data Module[/bold cyan]

[yellow]Purpose:[/yellow]
Fetch, store, and analyze ocean and weather data from:
- NDBC (National Data Buoy Center) - buoy observations
- CO-OPS (NOAA Tides & Currents) - water levels, currents
- Open-Meteo Marine - marine forecasts

[yellow]Data Types:[/yellow]
- Wave height, period, direction
- Wind speed and direction
- Sea surface temperature
- Water levels and tides
- Ocean currents
- Swell parameters

[yellow]Key Commands:[/yellow]
- stations list  - List available stations
- fetch ndbc     - Fetch NDBC buoy data
- fetch coops    - Fetch CO-OPS data
- fetch open-meteo - Fetch marine forecast
- historical     - Get historical data
- cache status   - View cache info
- db init        - Initialize database

[yellow]Examples:[/yellow]
  wed metocean stations list --source ndbc --region gom
  wed metocean fetch ndbc 41001
  wed metocean historical 41001 2024-01-01 2024-12-31
  wed metocean export csv -o data.csv -s 41001
"""
    console.print(Panel(info_text, border_style="cyan"))


@app.command("status")
def status() -> None:
    """Display metocean module status and configuration."""
    console.print(
        Panel(
            "[bold cyan]Metocean Module Status[/bold cyan]",
            border_style="cyan",
        )
    )
    display_config_status()


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


def main() -> None:
    """CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
