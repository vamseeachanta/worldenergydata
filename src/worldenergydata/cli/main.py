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

from worldenergydata.cli.lazy_group import LazyDispatchGroup
from worldenergydata.cli.registry import COMMAND_FAMILIES, INFO_ROW_ORDER

# Initialize console for rich output
console = Console()

# Create main Typer app
app = typer.Typer(
    name="worldenergydata",
    cls=LazyDispatchGroup,
    help="World Energy Data - Global energy market data platform",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
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

    for name in INFO_ROW_ORDER:
        family = COMMAND_FAMILIES[name]
        table.add_row(name, family.info_desc, family.key_commands)

    console.print(table)

    console.print(
        "\n[dim]Use 'worldenergydata <module> --help' for module-specific commands[/dim]"
    )


@app.command()
def status() -> None:
    """Show data freshness status for all modules.

    Reads ``_metadata.json`` from each module under ``data/modules/`` and
    displays a colour-coded freshness table.  Green = refreshed within
    30 days, yellow = 30-90 days, red = older than 90 days or never.

    Run ``python3 scripts/generate_metadata.py`` to regenerate metadata.
    """
    import json
    from datetime import datetime, timezone
    from pathlib import Path

    from worldenergydata.common.data_resolver import DataNotFoundError, get_data_root

    console.print(Panel("[bold]Data Freshness Status[/bold]", border_style="green"))

    try:
        _data_root = get_data_root()
    except DataNotFoundError:
        _data_root = Path("data")

    modules_dir = _data_root / "modules"
    if not modules_dir.is_dir():
        console.print("[red]No data/modules directory found.[/red]")
        console.print(
            "[dim]Run 'make data' or 'python3 scripts/generate_metadata.py' first.[/dim]"
        )
        return

    now = datetime.now(tz=timezone.utc)

    status_table = Table(
        title="Module Freshness",
        show_header=True,
        header_style="bold cyan",
    )
    status_table.add_column("Module", style="bold")
    status_table.add_column("Last Refresh", justify="center")
    status_table.add_column("Age (days)", justify="right")
    status_table.add_column("Records", justify="right")
    status_table.add_column("Files", justify="right")
    status_table.add_column("Size", justify="right")

    def _human_size(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if abs(n) < 1024:
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024  # type: ignore[assignment]
        return f"{n:.1f} TB"

    module_dirs = sorted(p for p in modules_dir.iterdir() if p.is_dir())

    for mod_dir in module_dirs:
        meta_path = mod_dir / "_metadata.json"
        module_name = mod_dir.name

        if not meta_path.exists():
            status_table.add_row(
                module_name,
                "[dim]no metadata[/dim]",
                "-",
                "-",
                "-",
                "-",
            )
            continue

        try:
            meta = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            status_table.add_row(
                module_name,
                "[red]read error[/red]",
                "-",
                "-",
                "-",
                "-",
            )
            continue

        last_refresh = meta.get("last_refresh")
        if last_refresh:
            try:
                lr_dt = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
                age_days = (now - lr_dt).days
            except (ValueError, TypeError):
                lr_dt = None
                age_days = None
        else:
            lr_dt = None
            age_days = None

        # Colour-code by freshness
        if age_days is not None:
            if age_days <= 30:
                age_style = "green"
            elif age_days <= 90:
                age_style = "yellow"
            else:
                age_style = "red"
            age_str = f"[{age_style}]{age_days}[/{age_style}]"
            lr_str = f"[{age_style}]{last_refresh[:10]}[/{age_style}]"
        else:
            age_str = "[red]never[/red]"
            lr_str = "[red]never[/red]"

        record_count = meta.get("record_count", 0)
        file_count = meta.get("file_count", 0)
        total_size = meta.get("total_size_bytes", 0)

        status_table.add_row(
            module_name,
            lr_str,
            age_str,
            f"{record_count:,}",
            str(file_count),
            _human_size(total_size),
        )

    console.print(status_table)
    console.print(
        "\n[dim]Regenerate metadata: python3 scripts/generate_metadata.py[/dim]"
    )


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
