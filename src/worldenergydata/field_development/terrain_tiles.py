"""Bounded retrieval of a selected staged USGS DEM product.

Discovery remains in :func:`terrain.find_dem_tiles`. A successful download
establishes byte transport only: TIFF structure, CRS, vertical datum, coverage,
NoData and suitability for engineering use remain NOT_EVALUATED.
"""

from __future__ import annotations

import math
import os
import shutil
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from worldenergydata.field_development.terrain import (
    TerrainFetchError,
    load_terrain_sources,
)

__all__ = ["DemTileDownload", "download_dem_tile"]

# libtiff tiff.h (accessed 2026-10-21): TIFF_VERSION_CLASSIC=42,
# TIFF_VERSION_BIG=43, TIFF_LITTLEENDIAN=0x4949, TIFF_BIGENDIAN=0x4d4d.
# https://raw.githubusercontent.com/libsdl-org/libtiff/master/libtiff/tiff.h
# These signatures identify TIFF transport; they do not validate GeoTIFF tags.
_TIFF_SIGNATURES = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")
_SOURCE_ID = "usgs_3dep_staged_tiles"


@dataclass(frozen=True)
class DemTileDownload:
    """Transport receipt retaining a snapshot of the selected TNM product."""

    path: Path
    size_bytes: int
    sha256: str
    product: dict[str, Any]
    retrieved_at: str

    def to_manifest(self) -> dict[str, Any]:
        """Return JSON-ready provenance without a machine-specific file path."""
        return {
            "source_id": _SOURCE_ID,
            "file": self.path.name,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "product": deepcopy(self.product),
            "retrieved_at": self.retrieved_at,
            "qualification": "NOT_EVALUATED",
        }


def _validate_product(product: dict[str, Any], root_url: str) -> str:
    """Accept only explicit GeoTIFF products within the catalog download root.

    Field names follow USGS TNM Access API v1, ProductsResponse (2026 access):
    https://tnmaccess.nationalmap.gov/api/v1/docs . The root permits current
    and historical products, but not arbitrary URLs from supplied metadata.
    """
    if not isinstance(product, dict):
        raise TypeError("product must be a TNM product mapping")
    if not isinstance(product.get("sourceId"), str) or not product["sourceId"].strip():
        raise ValueError("product must retain a nonempty sourceId")
    if product.get("format") != "GeoTIFF":
        raise ValueError("product format must be GeoTIFF")
    size = product.get("sizeInBytes")
    if size is not None and (type(size) is not int or size < 0):
        raise ValueError("product sizeInBytes must be a nonnegative integer")
    url = product.get("downloadURL")
    if not isinstance(url, str) or not url:
        raise ValueError("product must contain downloadURL")
    root = urlsplit(root_url)
    parsed = urlsplit(url)
    if (
        root.scheme != "https"
        or not root.netloc
        or not root.path.endswith("/")
        or parsed.scheme != "https"
        or parsed.netloc != root.netloc
        or not parsed.path.startswith(root.path)
        or not parsed.path.lower().endswith(".tif")
        or parsed.query
        or parsed.fragment
        or any(part in {".", ".."} for part in parsed.path.split("/"))
        or any(char in url for char in ("%", "\\"))
        or any(char.isspace() or ord(char) < ord(" ") for char in url)
    ):
        raise ValueError("product downloadURL must be a direct catalog-root TIFF URL")
    return url


def download_dem_tile(
    product: dict[str, Any],
    out_path: Path,
    *,
    max_bytes: int,
    timeout: float,
    catalog_path: Path | None = None,
    session: requests.Session | None = None,
) -> DemTileDownload:
    """Stream one selected TNM GeoTIFF with an explicit byte budget and timeout.

    ``product`` is an item returned by ``terrain.find_dem_tiles``; source
    metadata is copied without resolution or datum inference. ``max_bytes``
    and ``timeout`` are caller resource limits, not terrain acceptance limits.
    A missing or zero product size is treated as unknown. Positive advertised
    sizes and any HTTP Content-Length must match the received byte count.

    Redirects and non-identity encodings are refused. Files appear at out_path
    only after the complete stream passes byte-count and TIFF-signature checks.
    Existing files (including ones created during transfer) are never replaced.
    Temporary staging is on the destination filesystem; failures remove only
    that staging file. Hard-link publication requires filesystem support.
    HTTP and filesystem exceptions propagate; invalid transport raises
    :class:`TerrainFetchError`. No bulk download or retry loop is implicit.
    """
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be finite and positive")
    entry = load_terrain_sources(catalog_path)[_SOURCE_ID]
    if entry["status"] != "verified":
        raise TerrainFetchError("staged DEM source is not verified")
    snapshot = deepcopy(product)
    url = _validate_product(snapshot, entry["endpoints"]["staged_download_root"])
    expected_size = snapshot.get("sizeInBytes")
    if expected_size and expected_size > max_bytes:
        raise TerrainFetchError("product size exceeds download budget")
    target = Path(out_path)
    if target.exists() or target.is_symlink():
        raise FileExistsError("destination already exists")

    http = session or requests
    with http.get(
        url,
        stream=True,
        allow_redirects=False,
        headers={"Accept-Encoding": "identity"},
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        if response.status_code != requests.codes.ok:
            raise TerrainFetchError("download requires a complete HTTP response")
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise TerrainFetchError("unexpected download content encoding")
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                content_length = int(content_length)
            except (ValueError, TypeError) as exc:
                raise TerrainFetchError("invalid download content length") from exc
            if content_length < 0:
                raise TerrainFetchError("invalid download content length")
            if content_length > max_bytes:
                raise TerrainFetchError("content length exceeds download budget")

        target.parent.mkdir(parents=True, exist_ok=True)
        digest = sha256()
        count = 0
        prefix = b""
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".dem-") as staged:
            # Use the standard-library copy buffer size; it is an I/O allocation
            # choice, independent of the explicit caller byte budget.
            for chunk in response.iter_content(chunk_size=shutil.COPY_BUFSIZE):
                count += len(chunk)
                if count > max_bytes:
                    raise TerrainFetchError("stream exceeds download budget")
                prefix = (prefix + chunk)[: len(_TIFF_SIGNATURES[0])]
                digest.update(chunk)
                staged.write(chunk)
            if prefix not in _TIFF_SIGNATURES:
                raise TerrainFetchError("download did not return a TIFF signature")
            if content_length is not None and count != content_length:
                raise TerrainFetchError("received bytes differ from content length")
            if expected_size and count != expected_size:
                raise TerrainFetchError("received bytes differ from product size")
            staged.flush()
            # link() publishes a complete file atomically and fails if target
            # already exists, including when another writer won the race.
            os.link(staged.name, target)

    return DemTileDownload(
        path=target,
        size_bytes=count,
        sha256=digest.hexdigest(),
        product=snapshot,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
