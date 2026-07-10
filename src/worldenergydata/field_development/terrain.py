# ABOUTME: Terrain/bathymetry public-source catalog loader + USGS 3DEP DEM fetch helper.
# ABOUTME: Issue #930 (epic #929, A1) — public DEM path for the onshore tracer (digitalmodel#1508).
"""
worldenergydata.field_development.terrain
=========================================

Verified public terrain & bathymetry sources for field-development layout and
screening, plus a small fetch helper for onshore US DEMs.

All endpoints live in :data:`TERRAIN_SOURCES_PATH` (``terrain_sources.yml``,
shipped next to this module) — **no URLs are hardcoded here**. Every catalog
entry records the license, format, resolution and the live-verification
evidence (``verified_on`` / ``verification``) for that source.

The one network helper, :func:`fetch_dem`, clips an arbitrary bounding box
from the USGS 3DEP dynamic image service and writes a small GeoTIFF — the
public-DEM path the onshore tracer (digitalmodel#1508) needs. Bulk products
(3DEP staged tiles, GEBCO, NOAA CRM, BOEM bathymetry) are catalogued for
fetch-on-demand use; they are hundreds of MB to GB and must never be
committed to git.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Optional

import requests
import yaml

__all__ = [
    "TERRAIN_SOURCES_PATH",
    "TerrainFetchError",
    "load_terrain_sources",
    "fetch_dem",
]

TERRAIN_SOURCES_PATH = Path(__file__).parent / "terrain_sources.yml"

#: Fields every catalog entry must carry (mirrors the texas_rrc source-catalog
#: convention, PR #667, adapted to remote-endpoint sources).
REQUIRED_SOURCE_FIELDS = {
    "name",
    "provider",
    "canonical_url",
    "access_method",
    "endpoints",
    "format",
    "resolution",
    "coverage",
    "license",
    "status",
    "verified_on",
    "verification",
    "consumers",
}

VALID_STATUSES = {"verified", "not_verified"}

#: GeoTIFF magic prefixes (little/big endian). The ArcGIS image service
#: reports errors as HTTP-200 JSON bodies, so content sniffing is required.
_TIFF_MAGICS = (b"II*\x00", b"MM\x00*")

_DEFAULT_DEM_SOURCE = "usgs_3dep_dem"
_DEFAULT_SIZE = (256, 256)
_DEFAULT_TIMEOUT_S = 120.0


class TerrainFetchError(RuntimeError):
    """A terrain/bathymetry endpoint returned something other than the data."""


def load_terrain_sources(
    path: Optional[Path] = None,
) -> dict[str, dict[str, Any]]:
    """Load and validate the terrain/bathymetry source catalog.

    Returns the ``sources`` mapping from ``terrain_sources.yml``. Raises
    :class:`ValueError` if any entry is missing required fields or carries an
    invalid status.
    """
    catalog_path = path or TERRAIN_SOURCES_PATH
    with catalog_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}

    sources = payload.get("sources", {})
    if not isinstance(sources, dict) or not sources:
        raise ValueError("terrain source catalog must contain a 'sources' mapping")
    validate_terrain_sources(sources)
    return sources


def validate_terrain_sources(sources: dict[str, dict[str, Any]]) -> None:
    """Validate catalog shape: required fields, status vocabulary, https URLs."""
    for source_id, entry in sources.items():
        if not isinstance(entry, dict):
            raise ValueError(f"catalog entry '{source_id}' must be a mapping")

        missing = REQUIRED_SOURCE_FIELDS.difference(entry)
        if missing:
            fields = ", ".join(sorted(missing))
            raise ValueError(f"catalog entry '{source_id}' is missing: {fields}")

        status = entry["status"]
        if status not in VALID_STATUSES:
            raise ValueError(
                f"catalog entry '{source_id}' has invalid status: {status!r}"
            )
        if status == "verified" and not str(entry["verification"]).strip():
            raise ValueError(
                f"catalog entry '{source_id}' is 'verified' but records no "
                "verification evidence"
            )

        endpoints = entry["endpoints"]
        if not isinstance(endpoints, dict) or not endpoints:
            raise ValueError(
                f"catalog entry '{source_id}' must define an 'endpoints' mapping"
            )
        for key, url in endpoints.items():
            if not str(url).startswith("https://"):
                raise ValueError(
                    f"catalog entry '{source_id}' endpoint '{key}' must be https"
                )


def _validate_bbox(bbox: tuple[float, float, float, float]) -> None:
    if len(bbox) != 4:
        raise ValueError("bbox must be (min_lon, min_lat, max_lon, max_lat)")
    min_lon, min_lat, max_lon, max_lat = bbox
    if not (-180.0 <= min_lon < max_lon <= 180.0):
        raise ValueError(f"bbox longitudes invalid: {min_lon}..{max_lon}")
    if not (-90.0 <= min_lat < max_lat <= 90.0):
        raise ValueError(f"bbox latitudes invalid: {min_lat}..{max_lat}")


def fetch_dem(
    bbox: tuple[float, float, float, float],
    out_path: Optional[Path] = None,
    *,
    size: tuple[int, int] = _DEFAULT_SIZE,
    source_id: str = _DEFAULT_DEM_SOURCE,
    catalog_path: Optional[Path] = None,
    timeout: float = _DEFAULT_TIMEOUT_S,
    session: Optional[requests.Session] = None,
) -> Path:
    """Fetch a clipped onshore-US DEM GeoTIFF for ``bbox`` (WGS84 degrees).

    Parameters
    ----------
    bbox:
        ``(min_lon, min_lat, max_lon, max_lat)`` in EPSG:4326.
    out_path:
        Destination file. Defaults to a deterministic name in the system
        temp directory — DEM rasters are fetch-on-demand artifacts and must
        not be committed to the repository.
    size:
        Output raster size ``(width, height)`` in pixels; the service clips
        and resamples, so small sizes stay small on disk.
    source_id:
        Catalog entry to use; must be ``status: verified`` and expose an
        ``export_image`` endpoint (default: USGS 3DEP dynamic image service).
    catalog_path:
        Override for the catalog YAML (tests use a tmp copy).
    session:
        Injectable ``requests.Session``-alike (anything with ``.get``) so
        unit tests never touch the network.

    Returns
    -------
    Path
        Path of the written GeoTIFF.
    """
    _validate_bbox(bbox)
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"size must be positive pixels, got {size}")

    sources = load_terrain_sources(catalog_path)
    entry = sources.get(source_id)
    if entry is None:
        raise KeyError(f"unknown terrain source '{source_id}'")
    if entry["status"] != "verified":
        raise TerrainFetchError(
            f"terrain source '{source_id}' is not verified; refusing to fetch"
        )
    export_url = entry["endpoints"].get("export_image")
    if not export_url:
        raise TerrainFetchError(
            f"terrain source '{source_id}' has no 'export_image' endpoint"
        )

    if out_path is None:
        min_lon, min_lat, max_lon, max_lat = bbox
        stem = (
            f"{source_id}_{min_lon:+08.3f}_{min_lat:+07.3f}"
            f"_{max_lon:+08.3f}_{max_lat:+07.3f}_{width}x{height}"
        ).replace(".", "p")
        out_path = Path(tempfile.gettempdir()) / f"{stem}.tif"
    out_path = Path(out_path)

    params = {
        "bbox": ",".join(f"{v:.6f}" for v in bbox),
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{width},{height}",
        "format": "tiff",
        "pixelType": "F32",
        "f": "image",
    }
    http = session or requests
    response = http.get(export_url, params=params, timeout=timeout)
    response.raise_for_status()

    content = response.content
    if not content.startswith(_TIFF_MAGICS):
        excerpt = content[:200].decode("utf-8", errors="replace")
        raise TerrainFetchError(
            f"terrain source '{source_id}' did not return a GeoTIFF "
            f"(the service reports errors as HTTP-200 JSON): {excerpt}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(content)
    return out_path
