# ABOUTME: Station management commands for metocean CLI.
# ABOUTME: Provides commands to list, search, and get info on metocean stations.

"""
Metocean CLI Station Commands

Commands for managing and querying metocean stations from NDBC and CO-OPS.
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from worldenergydata.metocean.cli_utils import (
    RegionChoice,
    SourceChoice,
    console,
    get_region_bbox,
    parse_bbox,
)
from worldenergydata.metocean.clients import COOPSClient, NDBCClient

# Station commands group
stations_app = typer.Typer(help="Manage metocean stations")


def _export_stations_to_file(stations: list, output: Path) -> None:
    """Export stations list to file."""
    data = [
        {
            "station_id": s.station_id,
            "name": s.name,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "station_type": (
                s.station_type.value
                if hasattr(s, "station_type") and s.station_type
                else None
            ),
        }
        for s in stations
    ]
    with open(output, "w") as f:
        json.dump(data, f, indent=2)


@stations_app.command("list")
def stations_list(
    source: SourceChoice = typer.Option(
        SourceChoice.ndbc, "--source", "-s", help="Data source"
    ),
    region: RegionChoice = typer.Option(
        RegionChoice.gom, "--region", "-r", help="Geographic region"
    ),
    active_only: bool = typer.Option(
        True, "--active/--all", help="Active stations only"
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max stations to display"),
) -> None:
    """List available metocean stations."""
    if source == SourceChoice.open_meteo:
        console.print(
            "[yellow]Open-Meteo uses coordinates, not stations. "
            "Use 'fetch open-meteo' with lat,lon instead.[/yellow]"
        )
        raise typer.Exit(0)

    bbox = get_region_bbox(region)

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Fetching stations..."),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            if source == SourceChoice.ndbc:
                with NDBCClient() as client:
                    result = client.fetch_stations(bbox=bbox, active_only=active_only)
            elif source == SourceChoice.coops:
                with COOPSClient() as client:
                    result = client.fetch_stations(bbox=bbox, active_only=active_only)
            else:
                console.print(f"[red]Unsupported source: {source}[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error fetching stations: {e}[/red]")
            raise typer.Exit(1)

    if result.had_errors:
        for err in result.error_messages[:5]:
            console.print(f"[yellow]Warning: {err}[/yellow]")

    table = Table(title=f"{source.value.upper()} Stations ({region.value.upper()})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Lat", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Type")

    for station in result.data[:limit]:
        station_type = ""
        if hasattr(station, "station_type") and station.station_type:
            station_type = station.station_type.value

        table.add_row(
            station.station_id,
            station.name[:40] if station.name else "",
            f"{station.latitude:.4f}",
            f"{station.longitude:.4f}",
            station_type,
        )

    console.print(table)
    console.print(f"\n[green]Found {result.records_count} stations[/green]")

    if result.records_count > limit:
        console.print(
            f"[dim]Showing first {limit} stations. Use --limit to see more.[/dim]"
        )

    if output:
        _export_stations_to_file(result.data, output)
        console.print(f"[green]Exported to {output}[/green]")


@stations_app.command("search")
def stations_search(
    bbox: str = typer.Option(
        ..., "--bbox", "-b", help="Bounding box: lon_min,lon_max,lat_min,lat_max"
    ),
    source: Optional[SourceChoice] = typer.Option(
        None, "--source", "-s", help="Filter by source"
    ),
) -> None:
    """Search for stations within a bounding box."""
    bbox_tuple = parse_bbox(bbox)
    sources = [source] if source else [SourceChoice.ndbc, SourceChoice.coops]

    for src in sources:
        if src == SourceChoice.open_meteo:
            continue

        console.print(f"\n[bold]{src.value.upper()}[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn(f"[cyan]Searching {src.value}..."),
            console=console,
        ) as progress:
            progress.add_task("search", total=None)

            try:
                if src == SourceChoice.ndbc:
                    with NDBCClient() as client:
                        result = client.fetch_stations(
                            bbox=bbox_tuple, active_only=True
                        )
                elif src == SourceChoice.coops:
                    with COOPSClient() as client:
                        result = client.fetch_stations(
                            bbox=bbox_tuple, active_only=True
                        )
                else:
                    continue
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

        if not result.data:
            console.print("[dim]No stations found in this region[/dim]")
            continue

        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Lat", justify="right")
        table.add_column("Lon", justify="right")

        for station in result.data[:20]:
            table.add_row(
                station.station_id,
                station.name[:30] if station.name else "",
                f"{station.latitude:.4f}",
                f"{station.longitude:.4f}",
            )

        console.print(table)
        console.print(f"[green]Found {result.records_count} stations[/green]")


@stations_app.command("info")
def stations_info(
    station_id: str = typer.Argument(..., help="Station ID (e.g., 41001)"),
    source: SourceChoice = typer.Option(
        SourceChoice.ndbc, "--source", "-s", help="Data source"
    ),
) -> None:
    """Get detailed information for a specific station."""
    if source == SourceChoice.open_meteo:
        console.print("[yellow]Open-Meteo uses coordinates, not stations.[/yellow]")
        raise typer.Exit(0)

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Fetching station info for {station_id}..."),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            if source == SourceChoice.ndbc:
                with NDBCClient() as client:
                    station = client.get_station_info(station_id)
            elif source == SourceChoice.coops:
                with COOPSClient() as client:
                    station = client.get_station_info(station_id)
            else:
                console.print(f"[red]Unsupported source: {source}[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error fetching station info: {e}[/red]")
            raise typer.Exit(1)

    if not station:
        console.print(f"[red]Station {station_id} not found[/red]")
        raise typer.Exit(1)

    panel_content = (
        f"[bold cyan]Station ID:[/bold cyan] {station.station_id}\n"
        f"[bold cyan]Name:[/bold cyan] {station.name}\n"
        f"[bold cyan]Location:[/bold cyan] {station.latitude:.4f}, {station.longitude:.4f}\n"
    )

    if hasattr(station, "station_type") and station.station_type:
        panel_content += f"[bold cyan]Type:[/bold cyan] {station.station_type.value}\n"

    if hasattr(station, "owner") and station.owner:
        panel_content += f"[bold cyan]Owner:[/bold cyan] {station.owner}\n"

    if hasattr(station, "water_depth_m") and station.water_depth_m:
        panel_content += (
            f"[bold cyan]Water Depth:[/bold cyan] {station.water_depth_m:.1f} m\n"
        )

    if hasattr(station, "has_water_level"):
        panel_content += f"[bold cyan]Water Level Data:[/bold cyan] {'Yes' if station.has_water_level else 'No'}\n"  # noqa: E501

    if hasattr(station, "has_currents"):
        panel_content += f"[bold cyan]Currents Data:[/bold cyan] {'Yes' if station.has_currents else 'No'}\n"  # noqa: E501

    if hasattr(station, "has_predictions"):
        panel_content += f"[bold cyan]Tide Predictions:[/bold cyan] {'Yes' if station.has_predictions else 'No'}\n"  # noqa: E501

    if hasattr(station, "metadata") and station.metadata:
        panel_content += "\n[bold cyan]Metadata:[/bold cyan]\n"
        for key, value in station.metadata.items():
            panel_content += f"  {key}: {value}\n"

    console.print(
        Panel(
            panel_content, title=f"{source.value.upper()} Station", border_style="cyan"
        )
    )
