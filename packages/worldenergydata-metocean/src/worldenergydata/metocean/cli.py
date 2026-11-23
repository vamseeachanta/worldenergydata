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
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from worldenergydata.metocean.cli_cache import cache_app
from worldenergydata.metocean.cli_db import db_app, display_config_status
from worldenergydata.metocean.cli_export import export_app
from worldenergydata.metocean.cli_fetch import fetch_app, historical_command
from worldenergydata.metocean.cli_stations import stations_app
from worldenergydata.metocean.cli_utils import SourceChoice, console

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
    source: Annotated[
        SourceChoice, typer.Option("--source", "-s", help="Data source")
    ] = SourceChoice.ndbc,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file")
    ] = None,
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


@app.command("unified")
def unified(
    lat: float = typer.Option(..., "--lat", help="Latitude in decimal degrees"),
    lon: float = typer.Option(..., "--lon", help="Longitude in decimal degrees"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    parameters: str = typer.Option(
        "Hs,Tp,wind_speed,current_speed",
        "--parameters",
        "-p",
        help="Comma-separated list of parameters to fetch",
    ),
    erddap_dataset: str | None = typer.Option(
        None, "--erddap-dataset", help="Explicit ERDDAP tabledap dataset ID"
    ),
    erddap_bbox: str | None = typer.Option(
        None, "--erddap-bbox", help="Bounds: lon_min,lon_max,lat_min,lat_max"
    ),
    dashboard: Annotated[
        Path | None,
        typer.Option(
            "--dashboard", "-d", help="Save Plotly HTML dashboard to this file"
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Save harmonised data as CSV to this file"),
    ] = None,
) -> None:
    """
    Query multiple metocean sources simultaneously for a location and time range.

    Auto-selects relevant data sources based on geographic coverage and runs
    queries in parallel.  Results are harmonised to a unified long-format table.

    Examples:

        python -m worldenergydata.metocean unified --lat 28.5 --lon -88.5
            --start 2023-01-01 --end 2023-12-31

        python -m worldenergydata.metocean unified --lat 57.0 --lon 3.5
            --start 2023-06-01 --end 2023-06-30
            --dashboard /tmp/north_sea.html
    """
    from worldenergydata.metocean.unified.dashboard import MetoceanDashboard
    from worldenergydata.metocean.unified.unified_query import (
        MetoceanQuery,
        UnifiedMetoceanClient,
    )

    # Parse dates
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
    except ValueError as exc:
        console.print(f"[red]Invalid date format: {exc}[/red]")
        raise typer.Exit(1)

    if start_dt > end_dt:
        console.print("[red]Start date must not follow end date[/red]")
        raise typer.Exit(1)

    params_list = tuple(p.strip() for p in parameters.split(",") if p.strip())

    console.print(
        Panel(
            f"[bold cyan]Unified Metocean Query[/bold cyan]\n"
            f"Location: ({lat}, {lon})\n"
            f"Period:   {start} to {end}\n"
            f"Params:   {', '.join(params_list)}",
            border_style="cyan",
        )
    )

    try:
        query = MetoceanQuery(
            lat=lat,
            lon=lon,
            start_date=start_dt,
            end_date=end_dt,
            parameters=params_list,
        )
        bounds = (
            tuple(float(v) for v in erddap_bbox.split(",")) if erddap_bbox else None
        )
        client = UnifiedMetoceanClient(
            erddap_dataset=erddap_dataset,
            erddap_bbox=bounds,
        )
    except ValueError as exc:
        console.print(f"[red]Invalid query: {exc}[/red]")
        raise typer.Exit(1) from None

    with console.status("[bold green]Fetching data from all sources…"):
        result = client.query(query)

    for source, status in result.source_status.items():
        console.print(f"{source}: {status}")

    # Display summary
    console.print(
        f"\n[bold]Sources used:[/bold] {', '.join(result.sources_used) or 'none'}"
    )
    console.print(f"[bold]Total rows:[/bold]  {len(result.data)}")

    if result.coverage_gaps:
        console.print("\n[yellow]Coverage gaps detected:[/yellow]")
        for gap in result.coverage_gaps:
            console.print(
                f"  - {gap.get('parameter', '?')}: {gap.get('start')} → {gap.get('end')}"
            )

    if not result.data.empty:
        # Build summary stats table
        table = Table(title="Summary Statistics", show_header=True)
        for col in ["source", "parameter", "count", "mean", "min", "max"]:
            table.add_column(col)

        dash = MetoceanDashboard()
        stats = dash.build_summary_stats(result)
        for _, row in stats.iterrows():
            table.add_row(
                str(row.get("source", "")),
                str(row.get("parameter", "")),
                str(int(row.get("count", 0))),
                f"{row.get('mean', 0):.3f}",
                f"{row.get('min', 0):.3f}",
                f"{row.get('max', 0):.3f}",
            )
        console.print(table)

    # Optional CSV export
    if output is not None:
        result.data.to_csv(output, index=False)
        console.print(f"\n[green]Data saved to {output}[/green]")

    # Optional dashboard export
    if dashboard is not None:
        dash = MetoceanDashboard()
        dash.save(result, str(dashboard))
        console.print(f"[green]Dashboard saved to {dashboard}[/green]")


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


@app.command("update")
def update(
    config: Annotated[Path, typer.Option("--config", exists=True, readable=True)],
    data_root: Annotated[
        Path, typer.Option("--data-root", help="Archive root outside the repository")
    ],
    refresh: bool = typer.Option(
        False, "--refresh", help="Check retained publisher revisions"
    ),
) -> None:
    """Update configured completed-year archives and print a JSON run report."""
    import json

    from worldenergydata.metocean.update import update_archive

    report = update_archive(
        json.loads(config.read_text(encoding="utf-8")), data_root, refresh=refresh
    )
    typer.echo(json.dumps(report, indent=2))
    if report["failures"]:
        raise typer.Exit(1)


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
