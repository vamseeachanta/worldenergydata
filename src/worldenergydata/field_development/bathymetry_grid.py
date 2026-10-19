"""Bounded WGS84 grid reads and nearest-cell profiles, depths in metres.

Inspected source conventions determine depth sign. Land becomes NaN.
Antimeridian-spanning boxes are unsupported and rejected. Raster reprojection
uses nearest cells; nodata remains NaN. Profiles are straight in lon/lat space,
not geodesic routes or interpolated engineering surfaces.
"""

from __future__ import annotations

import math
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from .bathymetry import verify_file
from .terrain import TerrainFetchError, _validate_bbox


@dataclass(frozen=True)
class DepthGrid:
    """Cell-centre WGS84 axes with depth_m[latitude, longitude]."""

    longitude: Any
    latitude: Any
    depth_m: Any

    def __post_init__(self) -> None:
        for axis, limit in ((self.longitude, 180), (self.latitude, 90)):
            _validate_axis(axis, limit)
        if np.shape(self.depth_m) != (len(self.latitude), len(self.longitude)):
            raise ValueError("depth array does not match axes")


def _validate_axis(axis: Any, limit: int) -> None:
    if (
        np.ndim(axis) != 1
        or len(axis) == 0
        or not np.all(np.isfinite(axis))
        or np.any(np.abs(axis) > limit)
        or (
            len(axis) > 1
            and not (np.all(np.diff(axis) > 0) or np.all(np.diff(axis) < 0))
        )
    ):
        raise ValueError("grid axes must be finite monotonic WGS84 coordinates")


def _qualify_conventions(entry: dict[str, Any]) -> None:
    if (
        entry.get("units") != "m"
        or entry.get("vertical_convention")
        not in ("elevation_positive_up", "depth_positive_down")
        or entry.get("convention_evidence", {}).get("status") != "inspected"
    ):
        raise TerrainFetchError("source units/vertical conventions are not established")


def _cover_window(window: Any) -> tuple[int, int, int, int]:
    col, row = math.floor(window.col_off), math.floor(window.row_off)
    return (
        col,
        row,
        math.ceil(window.col_off + window.width) - col,
        math.ceil(window.row_off + window.height) - row,
    )


def clip_to_bbox(grid: DepthGrid, bbox: tuple[float, float, float, float]) -> DepthGrid:
    """Select centres inside a WGS84 box; reject empty intersections."""
    _validate_bbox(bbox)
    west, south, east, north = bbox
    x = np.flatnonzero((grid.longitude >= west) & (grid.longitude <= east))
    y = np.flatnonzero((grid.latitude >= south) & (grid.latitude <= north))
    if not len(x) or not len(y):
        raise ValueError("bbox has no grid cell centres")
    return DepthGrid(grid.longitude[x], grid.latitude[y], grid.depth_m[np.ix_(y, x)])


def depth_profile(
    grid: DepthGrid,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    samples: int = 100,
) -> Any:
    """Return nearest-cell depths along evenly spaced lon/lat points.

    Points outside the grid centre extent are refused; ties select the first
    axis cell. Missing bathymetry propagates as NaN without interpolation.
    """
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValueError("samples must be an integer of at least two")
    points = np.linspace(start, end, samples)
    if points.shape != (samples, 2) or not np.all(np.isfinite(points)):
        raise ValueError("points must be finite lon/lat pairs")
    for dim, axis in enumerate((grid.longitude, grid.latitude)):
        if np.any(points[:, dim] < min(axis)) or np.any(points[:, dim] > max(axis)):
            raise ValueError("profile point outside grid centre extent")
    x = [np.abs(grid.longitude - p).argmin() for p in points[:, 0]]
    y = [np.abs(grid.latitude - p).argmin() for p in points[:, 1]]
    return grid.depth_m[y, x]


def _member(archive: Path, suffix: str, member: str | None) -> str:
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise TerrainFetchError("unsafe archive member")
        candidates = [n for n in names if n.lower().endswith(suffix)]
        if member is not None:
            candidates = [n for n in candidates if n == member]
        if len(candidates) != 1:
            raise TerrainFetchError("select exactly one raster archive member")
        return candidates[0]


def read_depth_grid(
    archive: Path,
    entry: dict[str, Any],
    bbox: tuple[float, float, float, float],
    *,
    member: str | None = None,
    max_cells: int = 1_000_000,
) -> DepthGrid:
    """Verify archive before reading a bounded clip; never auto-download.

    GeoTIFF requires optional rasterio; netCDF4 requires optional netCDF4.
    No reader dependency is added to the project. Both readers reject grids
    with unknown units/CRS rather than guessing. netCDF is opened read-only;
    only coordinate axes and clipped values are read, without derived files.
    ``max_cells`` must be a positive integer count; booleans and floats are
    refused before archive verification or optional reader imports.
    """
    _validate_bbox(bbox)
    # Issue #936's bounded-read contract: a cell count is positive and integral.
    # This is a resource budget, not a source-resolution or depth criterion.
    if (
        isinstance(max_cells, (bool, np.bool_))
        or not isinstance(max_cells, (int, np.integer))
        or max_cells <= 0
    ):
        raise ValueError("max_cells must be a positive integer")
    _qualify_conventions(entry)
    verify_file(archive, entry)
    if entry["source_id"] == "boem_gom_bathymetry":
        name = _member(archive, ".tif", member)
        return _read_tiff(archive, name, bbox, max_cells, entry["vertical_convention"])
    if entry["source_id"] == "gebco_global_bathymetry":
        return _read_netcdf(archive, bbox, max_cells, entry["vertical_convention"])
    raise ValueError("unsupported bathymetry source")


def _depth(elevation: Any, convention: str) -> Any:
    values = np.ma.asarray(elevation, dtype=float).filled(np.nan)
    # NumPy 2.3 isfinite, Notes/Examples (2025): NaN and +/-infinity are nonfinite.
    # https://numpy.org/doc/2.3/reference/generated/numpy.isfinite.html
    values = np.where(np.isfinite(values), values, np.nan)
    if convention == "elevation_positive_up":
        return np.where(values <= 0, -values, np.nan)
    if convention == "depth_positive_down":
        return np.where(values >= 0, values, np.nan)
    raise TerrainFetchError("unknown vertical convention")


def _read_tiff(
    archive: Path,
    member: str,
    bbox: tuple[float, float, float, float],
    max_cells: int,
    convention: str,
) -> DepthGrid:
    try:
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.vrt import WarpedVRT
        from rasterio.windows import Window, from_bounds
    except ImportError as exc:
        raise TerrainFetchError("GeoTIFF reader requires optional rasterio") from exc
    with rasterio.open(f"zip://{archive.resolve()}!{member}") as source:
        if source.units[0] not in (None, "m", "meters", "metres"):
            raise TerrainFetchError("raster units contradict metre source manifest")
        if source.crs is None:
            raise TerrainFetchError("raster CRS is not established")
        with WarpedVRT(
            source,
            crs="EPSG:4326",
            dtype="float64",
            nodata=np.nan,
            resampling=Resampling.nearest,
        ) as raster:
            window = from_bounds(*bbox, transform=raster.transform)
            window = Window(*_cover_window(window))
            try:
                window = window.intersection(Window(0, 0, raster.width, raster.height))
            except rasterio.errors.WindowError as exc:
                raise ValueError("bbox outside raster") from exc
            if window.width * window.height > max_cells:
                raise TerrainFetchError("clip exceeds max_cells")
            values = raster.read(1, window=window, masked=True)
            if values.size == 0:
                raise ValueError("bbox outside raster")
            transform = raster.transform
            lon = (
                transform.c
                + (np.arange(values.shape[1]) + window.col_off + 0.5) * transform.a
            )
            lat = (
                transform.f
                + (np.arange(values.shape[0]) + window.row_off + 0.5) * transform.e
            )
            return clip_to_bbox(DepthGrid(lon, lat, _depth(values, convention)), bbox)


def _read_netcdf(
    archive: Path,
    bbox: tuple[float, float, float, float],
    max_cells: int,
    convention: str,
) -> DepthGrid:
    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise TerrainFetchError("netCDF4 reader requires optional netCDF4") from exc
    with Dataset(archive, "r") as dataset:
        lon_var, lat_var = dataset.variables["lon"], dataset.variables["lat"]
        if (
            getattr(lon_var, "units", None) != "degrees_east"
            or getattr(lat_var, "units", None) != "degrees_north"
        ):
            raise TerrainFetchError(
                "netCDF coordinate units are not geographic degrees"
            )
        lon, lat = np.asarray(lon_var[:]), np.asarray(lat_var[:])
        _validate_axis(lon, 180)
        _validate_axis(lat, 90)
        elevation = dataset.variables["elevation"]
        if elevation.dimensions != ("lat", "lon") or elevation.units not in (
            "m",
            "meters",
        ):
            raise TerrainFetchError("unsupported elevation dimensions or units")
        west, south, east, north = bbox
        x = np.flatnonzero((lon >= west) & (lon <= east))
        y = np.flatnonzero((lat >= south) & (lat <= north))
        if not len(x) or not len(y):
            raise ValueError("bbox outside grid")
        if (x[-1] - x[0] + 1) * (y[-1] - y[0] + 1) > max_cells:
            raise TerrainFetchError("clip exceeds max_cells")
        values = elevation[y[0] : y[-1] + 1, x[0] : x[-1] + 1]
        return DepthGrid(lon[x], lat[y], _depth(values, convention))
