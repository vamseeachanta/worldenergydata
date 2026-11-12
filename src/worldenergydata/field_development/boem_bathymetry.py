"""Offline-first BOEM metre-grid access by published east or west half.

Source: BOEM, Northern deepwater bathymetry grid from 3D seismic,
"The Bathymetry Grid" and "Downloads" (public page accessed 2026-10-19).
The published products are split into eastern and western halves. Select the
metre GeoTIFF endpoints from terrain_sources.yml via the pinned manifest;
never infer a half boundary, combine halves, or substitute hillshade data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .bathymetry import MANIFEST_PATH, fetch_bathymetry, load_manifest
from .bathymetry_grid import DepthGrid, _qualify_conventions, read_depth_grid
from .terrain import TerrainFetchError, _validate_bbox


def boem_manifest_entry(
    half: str, *, manifest_path: Path = MANIFEST_PATH
) -> dict[str, Any]:
    """Select exactly one BOEM metre GeoTIFF record, without network access.

    Endpoint names come from terrain_sources.yml, boem_gom_bathymetry.endpoints.
    Source sizes, hashes and vertical conventions stay in the manifest.
    """
    if half not in ("east", "west"):
        raise ValueError("half must be 'east' or 'west'")
    entries = [
        entry
        for entry in load_manifest(manifest_path)
        if entry["source_id"] == "boem_gom_bathymetry"
        and entry.get("endpoint") == f"{half}_meters_geotiff_zip"
    ]
    if len(entries) != 1:
        raise TerrainFetchError("manifest must select exactly one BOEM half")
    entry = entries[0]
    filename = entry.get("filename")
    if (
        not isinstance(filename, str)
        or not filename
        or filename in (".", "..")
        or Path(filename).name != filename
        or "\\" in filename
    ):
        raise TerrainFetchError("BOEM archive filename must be a basename")
    return entry


def read_boem_depth_grid(
    half: str,
    bbox: tuple[float, float, float, float],
    *,
    data_root: Path,
    max_cells: int,
    download: bool = False,
    manifest_path: Path = MANIFEST_PATH,
) -> DepthGrid:
    """Read a verified local BOEM half as positive-down metre depths.

    ``bbox`` is (west, south, east, north) in WGS84 degrees. ``max_cells`` is
    a caller-supplied memory budget, not a source-resolution or accuracy limit.
    The existing reader checks this budget before reading raster values.

    No directory or connection is created unless ``download=True`` and the
    selected archive is absent. Downloads use the existing serial, resumable
    fetcher with pinned integrity checks; corrupt cached files are refused and
    retained. Curation of unknown digests remains a separate explicit action.
    Units and inspected sign evidence are required before any download.
    Optional rasterio is required to read the archive. Nodata/land become NaN;
    reprojection and nearest-cell sampling follow ``read_depth_grid``.
    """
    _validate_bbox(bbox)
    if isinstance(max_cells, bool) or not isinstance(max_cells, int) or max_cells <= 0:
        raise ValueError("max_cells must be a positive integer")
    if not isinstance(download, bool):
        raise ValueError("download must be a boolean")
    entry = boem_manifest_entry(half, manifest_path=manifest_path)
    _qualify_conventions(entry)
    archive = Path(data_root) / entry["filename"]
    if not archive.exists():
        if not download:
            raise TerrainFetchError(
                "BOEM archive is not cached; fetch explicitly or set download=True"
            )
        archive = fetch_bathymetry(
            entry["source_id"],
            entry["filename"],
            Path(data_root),
            manifest_path=manifest_path,
        )
    return read_depth_grid(archive, entry, bbox, max_cells=max_cells)
