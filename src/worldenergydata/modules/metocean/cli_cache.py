# ABOUTME: Cache management commands for metocean CLI.
# ABOUTME: Provides commands to view status, clear, and cleanup cache.

"""
Metocean CLI Cache Commands

Commands for managing the metocean data cache.
"""

from typing import Optional

import typer
from rich.panel import Panel

from worldenergydata.modules.metocean.cache import CacheManager
from worldenergydata.modules.metocean.cli_utils import SourceChoice, console
from worldenergydata.modules.metocean.constants import DataSource

# Cache commands group
cache_app = typer.Typer(help="Cache management")


@cache_app.command("status")
def cache_status() -> None:
    """Show cache status."""
    try:
        cache = CacheManager()
        status = cache.status()
    except Exception as e:
        console.print(f"[red]Error getting cache status: {e}[/red]")
        raise typer.Exit(1)

    content = (
        f"[bold]Cache Status[/bold]\n\n"
        f"Enabled: {'Yes' if status['enabled'] else 'No'}\n"
        f"Entries: {status['entries']}\n"
        f"Active: {status['active']}\n"
        f"Expired: {status['expired']}\n"
        f"Total Hits: {status['total_hits']}\n"
        f"Size: {status['size_mb']:.2f} MB / {status['max_size_mb']} MB\n"
        f"TTL: {status['ttl_hours']} hours\n"
        f"Path: {status['cache_dir']}"
    )

    if status.get("by_source"):
        content += "\n\n[bold]By Source:[/bold]"
        for src, count in status["by_source"].items():
            content += f"\n  {src}: {count}"

    console.print(Panel(content, title="Metocean Cache", border_style="cyan"))


@cache_app.command("clear")
def cache_clear(
    source: Optional[SourceChoice] = typer.Option(
        None, "--source", "-s", help="Clear only this source"
    ),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Clear cache entries."""
    try:
        cache = CacheManager()
    except Exception as e:
        console.print(f"[red]Error accessing cache: {e}[/red]")
        raise typer.Exit(1)

    if not confirm:
        if source:
            msg = f"Clear all cache entries for {source.value}?"
        else:
            msg = "Clear ALL cache entries?"
        if not typer.confirm(msg):
            raise typer.Abort()

    try:
        if source:
            source_value = source.value.replace("-", "_")
            source_enum = DataSource(source_value)
            count = cache.invalidate_source(source_enum)
        else:
            count = cache.clear()
    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Cleared {count} cache entries[/green]")


@cache_app.command("cleanup")
def cache_cleanup() -> None:
    """Remove expired cache entries."""
    try:
        cache = CacheManager()
        count = cache.cleanup_expired()
    except Exception as e:
        console.print(f"[red]Error cleaning cache: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Removed {count} expired entries[/green]")
