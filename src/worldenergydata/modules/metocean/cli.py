# ABOUTME: Metocean CLI interface for fetching and managing ocean/weather data.
# ABOUTME: Uses Typer for CLI framework and Rich for terminal output.

"""
Metocean CLI Interface

Provides command-line tools for fetching and managing metocean data from
multiple sources including NDBC, CO-OPS, and Open-Meteo.

Usage:
    wed metocean --help
    wed metocean stations list --source ndbc --region gom
    wed metocean fetch ndbc 41001 --params wave,wind
    wed metocean historical 41001 2024-01-01 2024-12-31 --source ndbc
"""

import csv
import json
import sys
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from worldenergydata.modules.metocean.cache import CacheManager
from worldenergydata.modules.metocean.clients import (
    COOPSClient,
    NDBCClient,
    OpenMeteoClient,
)
from worldenergydata.modules.metocean.config import get_config
from worldenergydata.modules.metocean.constants import (
    GOM_BBOX,
    REGION_BOUNDS,
    DataSource,
)
from worldenergydata.modules.metocean.database import init_database

console = Console()

app = typer.Typer(
    name="metocean",
    help="Metocean data management - fetch ocean and weather data from multiple sources",
    no_args_is_help=True,
)

# Sub-command groups
stations_app = typer.Typer(help="Manage metocean stations")
fetch_app = typer.Typer(help="Fetch data from sources")
cache_app = typer.Typer(help="Cache management")
export_app = typer.Typer(help="Export data to files")
db_app = typer.Typer(help="Database management")

app.add_typer(stations_app, name="stations")
app.add_typer(fetch_app, name="fetch")
app.add_typer(cache_app, name="cache")
app.add_typer(export_app, name="export")
app.add_typer(db_app, name="db")


class SourceChoice(str, Enum):
    """Available data sources for CLI commands."""

    ndbc = "ndbc"
    coops = "coops"
    open_meteo = "open-meteo"


class RegionChoice(str, Enum):
    """Geographic regions for station filtering."""

    gom = "gom"
    atlantic = "atlantic"
    pacific = "pacific"
    alaska = "alaska"
    caribbean = "caribbean"
    north_sea = "north_sea"
    all = "all"


class ExportFormat(str, Enum):
    """Supported export formats."""

    csv = "csv"
    json = "json"
    netcdf = "netcdf"


def _get_region_bbox(region: RegionChoice) -> Optional[tuple]:
    """Get bounding box for a region."""
    if region == RegionChoice.all:
        return None
    if region == RegionChoice.gom:
        return GOM_BBOX
    region_key = region.value.upper()
    if region_key in REGION_BOUNDS:
        bounds = REGION_BOUNDS[region_key]
        return (
            bounds["lon_min"],
            bounds["lon_max"],
            bounds["lat_min"],
            bounds["lat_max"],
        )
    return None


def _parse_coords(coords: str) -> tuple:
    """Parse latitude,longitude string to tuple."""
    try:
        parts = [float(x.strip()) for x in coords.split(",")]
        if len(parts) != 2:
            raise ValueError()
        lat, lon = parts
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError()
        return (lat, lon)
    except (ValueError, TypeError):
        console.print(
            "[red]Invalid coordinates format. Use: lat,lon (e.g., 28.5,-88.5)[/red]"
        )
        raise typer.Exit(1)


def _parse_bbox(bbox: str) -> tuple:
    """Parse bounding box string to tuple."""
    try:
        parts = [float(x.strip()) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError()
        return tuple(parts)
    except (ValueError, TypeError):
        console.print(
            "[red]Invalid bbox format. Use: lon_min,lon_max,lat_min,lat_max[/red]"
        )
        raise typer.Exit(1)


def _parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
        raise typer.Exit(1)


# ==============================================================================
# STATIONS COMMANDS
# ==============================================================================


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

    bbox = _get_region_bbox(region)

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
    bbox_tuple = _parse_bbox(bbox)
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
        panel_content += f"[bold cyan]Water Level Data:[/bold cyan] {'Yes' if station.has_water_level else 'No'}\n"

    if hasattr(station, "has_currents"):
        panel_content += f"[bold cyan]Currents Data:[/bold cyan] {'Yes' if station.has_currents else 'No'}\n"

    if hasattr(station, "has_predictions"):
        panel_content += f"[bold cyan]Tide Predictions:[/bold cyan] {'Yes' if station.has_predictions else 'No'}\n"

    if hasattr(station, "metadata") and station.metadata:
        panel_content += "\n[bold cyan]Metadata:[/bold cyan]\n"
        for key, value in station.metadata.items():
            panel_content += f"  {key}: {value}\n"

    console.print(
        Panel(
            panel_content, title=f"{source.value.upper()} Station", border_style="cyan"
        )
    )


# ==============================================================================
# FETCH COMMANDS
# ==============================================================================


@fetch_app.command("ndbc")
def fetch_ndbc(
    station_id: str = typer.Argument(..., help="NDBC station ID (e.g., 41001)"),
    params: str = typer.Option(
        "wave,wind", "--params", "-p", help="Parameters: wave,wind,temp,all"
    ),
    hours: int = typer.Option(24, "--hours", help="Hours of recent data to display"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
) -> None:
    """Fetch real-time data from NDBC buoy."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Fetching NDBC data for {station_id}..."),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            with NDBCClient() as client:
                result = client.fetch_realtime(station_id)
        except Exception as e:
            console.print(f"[red]Error fetching data: {e}[/red]")
            raise typer.Exit(1)

    if not result.data:
        console.print(f"[yellow]No data available for station {station_id}[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[green]Fetched {result.records_count} observations[/green]")

    table = Table(title=f"NDBC {station_id} Recent Data")
    table.add_column("Time", style="cyan")
    table.add_column("Wave Ht (m)", justify="right")
    table.add_column("Wave Per (s)", justify="right")
    table.add_column("Wind (m/s)", justify="right")
    table.add_column("Wind Dir", justify="right")
    table.add_column("SST (C)", justify="right")

    display_count = min(hours, len(result.data))
    for obs in result.data[-display_count:]:
        table.add_row(
            obs.observation_time.strftime("%Y-%m-%d %H:%M"),
            f"{obs.wave_height_m:.1f}" if obs.wave_height_m else "-",
            f"{obs.dominant_wave_period_s:.1f}" if obs.dominant_wave_period_s else "-",
            f"{obs.wind_speed_ms:.1f}" if obs.wind_speed_ms else "-",
            f"{obs.wind_direction_deg:.0f}" if obs.wind_direction_deg else "-",
            f"{obs.sea_surface_temp_c:.1f}" if obs.sea_surface_temp_c else "-",
        )

    console.print(table)

    if output:
        _export_observations_to_file(result.data, output)
        console.print(f"[green]Exported to {output}[/green]")


@fetch_app.command("coops")
def fetch_coops(
    station_id: str = typer.Argument(..., help="CO-OPS station ID (e.g., 8761724)"),
    params: str = typer.Option(
        "water_level",
        "--params",
        "-p",
        help="Parameters: water_level,currents,predictions",
    ),
    hours: int = typer.Option(48, "--hours", help="Hours of data"),
    datum: str = typer.Option("MLLW", "--datum", "-d", help="Vertical datum"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
) -> None:
    """Fetch tides/currents from NOAA CO-OPS."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Fetching CO-OPS data for {station_id}..."),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            with COOPSClient() as client:
                result = client.fetch_realtime(station_id)
        except Exception as e:
            console.print(f"[red]Error fetching data: {e}[/red]")
            raise typer.Exit(1)

    if not result.data:
        console.print(f"[yellow]No data available for station {station_id}[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[green]Fetched {result.records_count} observations[/green]")

    table = Table(title=f"CO-OPS {station_id} Water Level")
    table.add_column("Time", style="cyan")
    table.add_column("Water Level (m)", justify="right")
    table.add_column("Sigma", justify="right")
    table.add_column("Quality", justify="center")

    display_count = min(hours, len(result.data))
    for obs in result.data[-display_count:]:
        table.add_row(
            obs.observation_time.strftime("%Y-%m-%d %H:%M"),
            f"{obs.water_level_m:.3f}",
            f"{obs.sigma:.3f}" if obs.sigma else "-",
            obs.quality_flag,
        )

    console.print(table)

    if output:
        _export_water_level_to_file(result.data, output)
        console.print(f"[green]Exported to {output}[/green]")


@fetch_app.command("open-meteo")
def fetch_open_meteo(
    coords: str = typer.Argument(..., help="Latitude,Longitude (e.g., 28.5,-88.5)"),
    days: int = typer.Option(7, "--days", "-d", help="Forecast days (1-16)"),
    params: str = typer.Option(
        "wave,swell,current", "--params", "-p", help="Parameters to fetch"
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
) -> None:
    """Fetch marine forecast from Open-Meteo."""
    lat, lon = _parse_coords(coords)

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Fetching Open-Meteo forecast for ({lat}, {lon})..."),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            with OpenMeteoClient() as client:
                result = client.fetch_forecast(lat, lon, forecast_days=days)
        except Exception as e:
            console.print(f"[red]Error fetching forecast: {e}[/red]")
            raise typer.Exit(1)

    if not result.data:
        console.print("[yellow]No forecast data available[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[green]Fetched {result.records_count} forecast points[/green]")

    table = Table(title=f"Open-Meteo Marine Forecast ({lat}, {lon})")
    table.add_column("Time", style="cyan")
    table.add_column("Wave Ht (m)", justify="right")
    table.add_column("Wave Per (s)", justify="right")
    table.add_column("Wave Dir", justify="right")
    table.add_column("Swell Ht (m)", justify="right")
    table.add_column("Current (m/s)", justify="right")

    display_count = min(48, len(result.data))
    for forecast in result.data[:display_count]:
        table.add_row(
            forecast.forecast_time.strftime("%Y-%m-%d %H:%M"),
            f"{forecast.wave_height_m:.1f}" if forecast.wave_height_m else "-",
            f"{forecast.wave_period_s:.1f}" if forecast.wave_period_s else "-",
            (
                f"{forecast.wave_direction_deg:.0f}"
                if forecast.wave_direction_deg
                else "-"
            ),
            (
                f"{forecast.swell_wave_height_m:.1f}"
                if forecast.swell_wave_height_m
                else "-"
            ),
            f"{forecast.current_speed_ms:.2f}" if forecast.current_speed_ms else "-",
        )

    console.print(table)

    if output:
        _export_forecast_to_file(result.data, output)
        console.print(f"[green]Exported to {output}[/green]")


def _export_observations_to_file(observations: list, output: Path) -> None:
    """Export NDBC observations to file."""
    data = [
        {
            "station_id": o.station_id,
            "observation_time": o.observation_time.isoformat(),
            "wave_height_m": o.wave_height_m,
            "dominant_wave_period_s": o.dominant_wave_period_s,
            "wind_speed_ms": o.wind_speed_ms,
            "wind_direction_deg": o.wind_direction_deg,
            "sea_surface_temp_c": o.sea_surface_temp_c,
            "pressure_hpa": o.pressure_hpa,
        }
        for o in observations
    ]
    with open(output, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _export_water_level_to_file(observations: list, output: Path) -> None:
    """Export CO-OPS water level data to file."""
    data = [
        {
            "station_id": o.station_id,
            "observation_time": o.observation_time.isoformat(),
            "water_level_m": o.water_level_m,
            "sigma": o.sigma,
            "quality_flag": o.quality_flag,
            "datum": o.datum,
        }
        for o in observations
    ]
    with open(output, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _export_forecast_to_file(forecasts: list, output: Path) -> None:
    """Export Open-Meteo forecast data to file."""
    data = [
        {
            "latitude": f.latitude,
            "longitude": f.longitude,
            "forecast_time": f.forecast_time.isoformat(),
            "wave_height_m": f.wave_height_m,
            "wave_period_s": f.wave_period_s,
            "wave_direction_deg": f.wave_direction_deg,
            "swell_wave_height_m": f.swell_wave_height_m,
            "current_speed_ms": f.current_speed_ms,
            "current_direction_deg": f.current_direction_deg,
        }
        for f in forecasts
    ]
    with open(output, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ==============================================================================
# HISTORICAL COMMAND
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
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if end <= start:
        console.print("[red]End date must be after start date[/red]")
        raise typer.Exit(1)

    is_coords = "," in identifier and len(identifier.split(",")) == 2

    with Progress(
        SpinnerColumn(),
        TextColumn(
            f"[cyan]Fetching historical data from {start_date} to {end_date}..."
        ),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            if is_coords and source == SourceChoice.open_meteo:
                lat, lon = _parse_coords(identifier)
                with OpenMeteoClient() as client:
                    result = client.fetch_historical(lat, lon, start, end)
                    data_type = "forecast"
            elif source == SourceChoice.ndbc:
                with NDBCClient() as client:
                    result = client.fetch_historical(identifier, start, end)
                    data_type = "observation"
            elif source == SourceChoice.coops:
                with COOPSClient() as client:
                    result = client.fetch_historical(identifier, start, end)
                    data_type = "water_level"
            else:
                console.print(
                    f"[red]Unsupported source for historical data: {source}[/red]"
                )
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error fetching historical data: {e}[/red]")
            raise typer.Exit(1)

    if result.had_errors:
        for err in result.error_messages[:3]:
            console.print(f"[yellow]Warning: {err}[/yellow]")

    console.print(f"\n[green]Fetched {result.records_count} records[/green]")

    if result.data:
        first = result.data[0]
        last = result.data[-1]
        if hasattr(first, "observation_time"):
            time_range = f"{first.observation_time} to {last.observation_time}"
        elif hasattr(first, "forecast_time"):
            time_range = f"{first.forecast_time} to {last.forecast_time}"
        else:
            time_range = "N/A"
        console.print(f"[dim]Time range: {time_range}[/dim]")

    if output:
        if data_type == "observation":
            _export_observations_to_file(result.data, output)
        elif data_type == "water_level":
            _export_water_level_to_file(result.data, output)
        elif data_type == "forecast":
            _export_forecast_to_file(result.data, output)
        console.print(f"[green]Exported to {output}[/green]")


# ==============================================================================
# CACHE COMMANDS
# ==============================================================================


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


# ==============================================================================
# DATABASE COMMANDS
# ==============================================================================


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


# ==============================================================================
# EXPORT COMMANDS
# ==============================================================================


@export_app.command("csv")
def export_csv(
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    station: str = typer.Option(..., "--station", "-s", help="Station ID"),
    source: SourceChoice = typer.Option(
        SourceChoice.ndbc, "--source", help="Data source"
    ),
    start: Optional[str] = typer.Option(
        None, "--start", help="Start date (YYYY-MM-DD)"
    ),
    end: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
) -> None:
    """Export data to CSV."""
    start_dt = (
        _parse_date(start)
        if start
        else datetime.now().replace(hour=0, minute=0, second=0)
    )
    end_dt = _parse_date(end) if end else datetime.now()

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Fetching data for {station}..."),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            if source == SourceChoice.ndbc:
                with NDBCClient() as client:
                    if start and end:
                        result = client.fetch_historical(station, start_dt, end_dt)
                    else:
                        result = client.fetch_realtime(station)
                headers = [
                    "station_id",
                    "observation_time",
                    "wave_height_m",
                    "dominant_wave_period_s",
                    "wind_speed_ms",
                    "wind_direction_deg",
                    "sea_surface_temp_c",
                    "pressure_hpa",
                ]
            elif source == SourceChoice.coops:
                with COOPSClient() as client:
                    if start and end:
                        result = client.fetch_historical(station, start_dt, end_dt)
                    else:
                        result = client.fetch_realtime(station)
                headers = [
                    "station_id",
                    "observation_time",
                    "water_level_m",
                    "sigma",
                    "quality_flag",
                    "datum",
                ]
            else:
                console.print("[red]CSV export not supported for this source[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error fetching data: {e}[/red]")
            raise typer.Exit(1)

    if not result.data:
        console.print("[yellow]No data to export[/yellow]")
        raise typer.Exit(0)

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for obs in result.data:
            if source == SourceChoice.ndbc:
                row = [
                    obs.station_id,
                    obs.observation_time.isoformat(),
                    obs.wave_height_m,
                    obs.dominant_wave_period_s,
                    obs.wind_speed_ms,
                    obs.wind_direction_deg,
                    obs.sea_surface_temp_c,
                    obs.pressure_hpa,
                ]
            else:
                row = [
                    obs.station_id,
                    obs.observation_time.isoformat(),
                    obs.water_level_m,
                    obs.sigma,
                    obs.quality_flag,
                    obs.datum,
                ]
            writer.writerow(row)

    console.print(f"[green]Exported {len(result.data)} records to {output}[/green]")


@export_app.command("json")
def export_json(
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    station: str = typer.Option(..., "--station", "-s", help="Station ID"),
    source: SourceChoice = typer.Option(
        SourceChoice.ndbc, "--source", help="Data source"
    ),
    start: Optional[str] = typer.Option(
        None, "--start", help="Start date (YYYY-MM-DD)"
    ),
    end: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
) -> None:
    """Export data to JSON."""
    start_dt = _parse_date(start) if start else None
    end_dt = _parse_date(end) if end else None

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Fetching data for {station}..."),
        console=console,
    ) as progress:
        progress.add_task("fetch", total=None)

        try:
            if source == SourceChoice.ndbc:
                with NDBCClient() as client:
                    if start_dt and end_dt:
                        result = client.fetch_historical(station, start_dt, end_dt)
                    else:
                        result = client.fetch_realtime(station)
                _export_observations_to_file(result.data, output)
            elif source == SourceChoice.coops:
                with COOPSClient() as client:
                    if start_dt and end_dt:
                        result = client.fetch_historical(station, start_dt, end_dt)
                    else:
                        result = client.fetch_realtime(station)
                _export_water_level_to_file(result.data, output)
            else:
                console.print("[red]JSON export not supported for this source[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error fetching data: {e}[/red]")
            raise typer.Exit(1)

    console.print(f"[green]Exported {len(result.data)} records to {output}[/green]")


@export_app.command("netcdf")
def export_netcdf(
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    station: str = typer.Option(..., "--station", "-s", help="Station ID"),
    source: SourceChoice = typer.Option(
        SourceChoice.ndbc, "--source", help="Data source"
    ),
    start: Optional[str] = typer.Option(
        None, "--start", help="Start date (YYYY-MM-DD)"
    ),
    end: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
) -> None:
    """Export data to CF-compliant NetCDF."""
    try:
        import netCDF4  # noqa: F401
    except ImportError:
        console.print(
            "[yellow]NetCDF export requires netCDF4 package.[/yellow]\n"
            "[dim]Install with: pip install netCDF4[/dim]"
        )
        raise typer.Exit(1)

    console.print("[yellow]NetCDF export is not yet fully implemented.[/yellow]")
    console.print("[dim]Consider using CSV or JSON export for now.[/dim]")


# ==============================================================================
# INFO AND STATUS COMMANDS
# ==============================================================================


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
    config = get_config()

    console.print(
        Panel(
            "[bold cyan]Metocean Module Status[/bold cyan]",
            border_style="cyan",
        )
    )

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
