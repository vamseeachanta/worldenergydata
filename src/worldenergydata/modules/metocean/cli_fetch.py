# ABOUTME: Data fetching commands for metocean CLI.
# ABOUTME: Provides commands to fetch real-time and historical data from sources.

"""
Metocean CLI Fetch Commands

Commands for fetching real-time and historical data from NDBC, CO-OPS,
and Open-Meteo sources.
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from worldenergydata.modules.metocean.cli_utils import (
    SourceChoice,
    console,
    parse_coords,
    parse_date,
)
from worldenergydata.modules.metocean.clients import (
    COOPSClient,
    NDBCClient,
    OpenMeteoClient,
)

# Fetch commands group
fetch_app = typer.Typer(help="Fetch data from sources")


def export_observations_to_file(observations: list, output: Path) -> None:
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


def export_water_level_to_file(observations: list, output: Path) -> None:
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


def export_forecast_to_file(forecasts: list, output: Path) -> None:
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
        export_observations_to_file(result.data, output)
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
        export_water_level_to_file(result.data, output)
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
    lat, lon = parse_coords(coords)

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
        export_forecast_to_file(result.data, output)
        console.print(f"[green]Exported to {output}[/green]")


def historical_command(
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
    start = parse_date(start_date)
    end = parse_date(end_date)

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
                lat, lon = parse_coords(identifier)
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
            export_observations_to_file(result.data, output)
        elif data_type == "water_level":
            export_water_level_to_file(result.data, output)
        elif data_type == "forecast":
            export_forecast_to_file(result.data, output)
        console.print(f"[green]Exported to {output}[/green]")
