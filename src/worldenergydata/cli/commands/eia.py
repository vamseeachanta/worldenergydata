"""CLI commands for EIA weekly feed ingestion.

Provides the eia-sync command for manual trigger of EIA API v2
weekly petroleum and natural gas data ingestion.

Usage:
    worldenergydata eia-sync
    worldenergydata eia-sync --feed petroleum
    worldenergydata eia-sync --feed gas-storage
    worldenergydata eia-sync --output ./data/eia --state-dir ./data/eia/state
"""

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = typer.Typer(
    name="eia",
    help="EIA API v2 weekly feed ingestion (crude, gas storage)",
    no_args_is_help=True,
)


class FeedChoice(str, Enum):
    """Available EIA feed options."""

    petroleum = "petroleum"
    gas_storage = "gas-storage"
    all = "all"


@app.command(name="sync")
def sync(
    feed: FeedChoice = typer.Option(
        FeedChoice.all,
        "--feed",
        "-f",
        help="Feed to sync: petroleum, gas-storage, or all",
    ),
    output: Path = typer.Option(
        Path("./data/eia"),
        "--output",
        "-o",
        help="Output directory for JSONL files",
    ),
    state_dir: Optional[Path] = typer.Option(
        None,
        "--state-dir",
        "-s",
        help="Directory for ingestion state file (defaults to --output)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """Sync EIA weekly petroleum and natural gas data to JSONL files.

    Performs incremental ingestion: only records newer than the last
    run are fetched and appended. The EIA_API_KEY environment variable
    must be set before running.

    Examples:
        worldenergydata eia sync
        worldenergydata eia sync --feed petroleum
        worldenergydata eia sync --feed gas-storage --output ./data/eia
    """
    try:
        from worldenergydata.eia.ingestion import EIAIngestionSync
        from worldenergydata.eia.client import EIAKeyError
    except ImportError as exc:
        console.print(f"[red]Import error:[/red] {exc}")
        raise typer.Exit(1)

    try:
        resolved_state_dir = state_dir or output
        sync_runner = EIAIngestionSync(
            output_dir=output,
            state_dir=resolved_state_dir,
        )
    except EIAKeyError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        console.print("[dim]Set EIA_API_KEY environment variable before running.[/dim]")
        raise typer.Exit(1)

    params_table = Table(show_header=False)
    params_table.add_column("Parameter", style="dim")
    params_table.add_column("Value")
    params_table.add_row("Feed", feed.value)
    params_table.add_row("Output Directory", str(output))
    params_table.add_row(
        "State Directory", str(resolved_state_dir)
    )
    console.print(Panel(params_table, title="EIA Sync Parameters", border_style="cyan"))

    results = []
    try:
        if feed == FeedChoice.petroleum:
            results.append(sync_runner.run_petroleum_sync())
        elif feed == FeedChoice.gas_storage:
            results.append(sync_runner.run_gas_storage_sync())
        else:
            results = sync_runner.run_all()
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Sync error:[/red] {exc}")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)

    results_table = Table(
        title="EIA Sync Results", show_header=True, header_style="bold cyan"
    )
    results_table.add_column("Feed")
    results_table.add_column("Records Written", justify="right")
    results_table.add_column("Latest Period")

    for result in results:
        results_table.add_row(
            result["feed"],
            str(result["records_written"]),
            result.get("latest_period") or "-",
        )

    console.print(results_table)
    total_written = sum(r["records_written"] for r in results)
    console.print(
        f"\n[green]EIA sync complete.[/green] "
        f"Total records written: [bold]{total_written}[/bold]"
    )


@app.callback()
def callback() -> None:
    """EIA (Energy Information Administration) weekly feed ingestion.

    Syncs weekly petroleum status and natural gas storage reports
    from EIA API v2 to local JSONL files with incremental updates.

    Requires EIA_API_KEY environment variable.
    """
