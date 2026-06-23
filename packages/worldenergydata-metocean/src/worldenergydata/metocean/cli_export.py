# ABOUTME: Data export commands for metocean CLI.
# ABOUTME: Provides commands to export data in CSV, JSON, and NetCDF formats.

"""
Metocean CLI Export Commands

Commands for exporting metocean data to various file formats.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from worldenergydata.metocean.cli_fetch import (
    export_observations_to_file,
    export_water_level_to_file,
)
from worldenergydata.metocean.cli_utils import SourceChoice, console, parse_date
from worldenergydata.metocean.clients import COOPSClient, NDBCClient

# Export commands group
export_app = typer.Typer(help="Export data to files")


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
        parse_date(start)
        if start
        else datetime.now().replace(hour=0, minute=0, second=0)
    )
    end_dt = parse_date(end) if end else datetime.now()

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
    start_dt = parse_date(start) if start else None
    end_dt = parse_date(end) if end else None

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
                export_observations_to_file(result.data, output)
            elif source == SourceChoice.coops:
                with COOPSClient() as client:
                    if start_dt and end_dt:
                        result = client.fetch_historical(station, start_dt, end_dt)
                    else:
                        result = client.fetch_realtime(station)
                export_water_level_to_file(result.data, output)
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
