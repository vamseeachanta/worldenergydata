# ABOUTME: Shared utilities, enums, and parsing functions for metocean CLI.
# ABOUTME: Provides common types and helper functions used across CLI modules.

"""
Metocean CLI Utilities

Shared types, enums, and helper functions used by CLI command modules.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

import typer
from rich.console import Console

from worldenergydata.modules.metocean.constants import GOM_BBOX, REGION_BOUNDS

# Shared console instance for all CLI modules
console = Console()


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


def get_region_bbox(region: RegionChoice) -> Optional[tuple]:
    """Get bounding box for a region.

    Args:
        region: The region to get bounding box for.

    Returns:
        Tuple of (lon_min, lon_max, lat_min, lat_max) or None for 'all'.
    """
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


def parse_coords(coords: str) -> tuple:
    """Parse latitude,longitude string to tuple.

    Args:
        coords: String in format "lat,lon" (e.g., "28.5,-88.5").

    Returns:
        Tuple of (latitude, longitude).

    Raises:
        typer.Exit: If format is invalid.
    """
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


def parse_bbox(bbox: str) -> tuple:
    """Parse bounding box string to tuple.

    Args:
        bbox: String in format "lon_min,lon_max,lat_min,lat_max".

    Returns:
        Tuple of (lon_min, lon_max, lat_min, lat_max).

    Raises:
        typer.Exit: If format is invalid.
    """
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


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime.

    Args:
        date_str: Date string in YYYY-MM-DD format.

    Returns:
        datetime object.

    Raises:
        typer.Exit: If format is invalid.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
        raise typer.Exit(1)
