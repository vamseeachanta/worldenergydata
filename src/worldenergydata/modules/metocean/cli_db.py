# ABOUTME: Database management commands for metocean CLI.
# ABOUTME: Provides commands to initialize and check database status.

"""
Metocean CLI Database Commands

Commands for managing the metocean database schema.
"""

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from worldenergydata.modules.metocean.cli_utils import console
from worldenergydata.modules.metocean.config import get_config
from worldenergydata.modules.metocean.database import init_database

# Database commands group
db_app = typer.Typer(help="Database management")


@db_app.command("init")
def db_init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Force recreation of tables"
    ),
) -> None:
    """Initialize metocean database schema."""
    if force:
        if not typer.confirm("This will drop existing tables. Continue?"):
            raise typer.Abort()

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Initializing database..."),
        console=console,
    ) as progress:
        progress.add_task("init", total=None)

        try:
            init_database(force=force)
        except Exception as e:
            console.print(f"[red]Error initializing database: {e}[/red]")
            raise typer.Exit(1)

    console.print("[green]Database initialized successfully[/green]")


@db_app.command("status")
def db_status() -> None:
    """Show database status."""
    config = get_config()

    panel_content = (
        f"[bold]Database Configuration[/bold]\n\n"
        f"Host: {config.database.host}\n"
        f"Port: {config.database.port}\n"
        f"Database: {config.database.database}\n"
        f"Schema: {config.database.schema}\n"
        f"Pool Size: {config.database.pool_size}"
    )

    console.print(Panel(panel_content, title="Metocean Database", border_style="cyan"))


def display_config_status() -> None:
    """Display configuration status tables (used by main status command)."""
    config = get_config()

    config_table = Table(title="Configuration", show_header=True, header_style="bold")
    config_table.add_column("Setting", style="dim")
    config_table.add_column("Value")

    config_table.add_row("Environment", config.environment)
    config_table.add_row("Debug Mode", str(config.debug))
    config_table.add_row("Cache Enabled", str(config.cache.enabled))
    config_table.add_row("Cache TTL", f"{config.cache.ttl_hours} hours")
    config_table.add_row("Cache Path", str(config.cache.cache_path))
    config_table.add_row("API Timeout", f"{config.api.request_timeout}s")
    config_table.add_row("Max Retries", str(config.api.max_retries))

    console.print(config_table)

    sources_table = Table(
        title="Available Data Sources", show_header=True, header_style="bold"
    )
    sources_table.add_column("Source")
    sources_table.add_column("Description")
    sources_table.add_column("Status", style="green")

    sources_table.add_row(
        "NDBC", "NOAA National Data Buoy Center - buoys & stations", "Available"
    )
    sources_table.add_row(
        "CO-OPS", "NOAA Tides & Currents - water levels, currents", "Available"
    )
    sources_table.add_row(
        "Open-Meteo", "Marine weather forecasts - waves, wind", "Available"
    )

    console.print(sources_table)
