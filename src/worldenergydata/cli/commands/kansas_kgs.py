"""CLI commands for Kansas Geological Survey data."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from worldenergydata.kansas_kgs.cli_support import build_pressure_observation_packet
from worldenergydata.kansas_kgs.raw_sources import DEFAULT_KANSAS_KGS_ROOT

app = typer.Typer(
    name="kansas-kgs",
    help="Kansas Geological Survey pressure and well data",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def kansas_kgs() -> None:
    """Kansas Geological Survey data operations."""


@app.command("build-pressure-observations")
def build_pressure_observations_command(
    root: Path = typer.Option(
        DEFAULT_KANSAS_KGS_ROOT,
        "--root",
        help="Kansas KGS storage root",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build summary without writing curated outputs",
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="Refresh official raw sources before building",
    ),
    allow_non_ace_root: bool = typer.Option(
        False,
        "--allow-non-ace-root",
        help="Allow non-/mnt/ace roots for isolated tests or sandboxes",
    ),
) -> None:
    """Build KGS per-well pressure observations from official bulk files."""
    try:
        result = build_pressure_observation_packet(
            root=root,
            dry_run=dry_run,
            refresh=refresh,
            allow_non_ace_root=allow_non_ace_root,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    _print_summary(result.row_count, result.quality)
    if dry_run:
        console.print("[yellow]Dry run:[/yellow] no curated outputs written")
        return
    if result.manifest is not None:
        console.print(
            "[green]Wrote Kansas KGS pressure observations[/green] "
            f"{result.row_count} rows -> {result.manifest.csv_path}"
        )


def _print_summary(row_count: int, quality: dict[str, object]) -> None:
    table = Table(
        title="Kansas KGS Pressure Observations",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Observation rows", str(row_count))
    table.add_row("Year min", str(quality.get("observation_year_min")))
    table.add_row("Year max", str(quality.get("observation_year_max")))
    console.print(table)
