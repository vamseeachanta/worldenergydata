"""Offline worked example: discover a synthetic DEM product and save a receipt.

Run with an output directory outside the repository. No network is used.
The seven-byte signature stub demonstrates transport, not terrain elevation.
See docs/data-sources/terrain/staged-dem-download.md for live-source usage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import requests

from worldenergydata.field_development.terrain import find_dem_tiles
from worldenergydata.field_development.terrain_tiles import download_dem_tile

# Synthetic caller inputs, not measured terrain or engineering acceptance limits.
# Independent count: four TIFF signature bytes plus b"abc" = seven bytes.
# Signature source: libtiff tiff.h, TIFF_VERSION_CLASSIC / TIFF_LITTLEENDIAN,
# https://raw.githubusercontent.com/libsdl-org/libtiff/master/libtiff/tiff.h
# (accessed 2026-10-21).
_DATA = b"II*\x00abc"
_PRODUCT = {
    "sourceId": "synthetic-tile",
    "format": "GeoTIFF",
    "downloadURL": (
        "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/"
        "current/synthetic/tile.tif"
    ),
    "sizeInBytes": 7,
    "publicationDate": "2026-01-01",
}


class _Response:
    """Transport stub implementing the small response protocol used here."""

    status_code = requests.codes.ok

    def __init__(self) -> None:
        self.headers = {"Content-Length": "7"}

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"total": 1, "items": [_PRODUCT]}

    def iter_content(self, chunk_size: int):
        yield _DATA

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _OfflineSession:
    def get(self, url: str, **kwargs) -> _Response:
        return _Response()


def run_example(output_dir: Path) -> dict[str, Any]:
    """Save the synthetic tile and receipt; do not overwrite an existing tile."""
    session = _OfflineSession()
    # Synthetic ordered rectangle and explicit caller limits. No map-distance
    # conversion, raster resampling or terrain suitability calculation is made.
    page = find_dem_tiles((-96, 29, -95, 30), max_items=1, session=session)
    result = download_dem_tile(
        page["items"][0],
        output_dir / "tile.tif",
        max_bytes=7,
        timeout=10,
        session=session,
    )
    manifest = result.to_manifest()
    with (output_dir / "tile.manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_example(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
