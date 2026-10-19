"""BOEM half selection, explicit downloads, and independently calculated grids."""

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from worldenergydata.field_development import boem_bathymetry as boem
from worldenergydata.field_development.terrain import TerrainFetchError

# Synthetic request coordinates, not a claim of BOEM coverage or resolution.
BBOX = (0.0, 0.0, 2.0, 2.0)


def entry(half: str, content: bytes = b"fixture") -> dict[str, Any]:
    """Synthetic records use measured byte length and independently hashed bytes."""
    url = f"https://example.org/{half}.zip"
    return {
        "source_id": "boem_gom_bathymetry",
        "endpoint": f"{half}_meters_geotiff_zip",
        "filename": f"{half}.zip",
        "source_url": url,
        "final_url": url,
        "final_host": "example.org",
        "allowed_hosts": ["example.org"],
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        # Successful HEAD status follows the existing bathymetry test fixture.
        "head": {"status": 200},
        "units": "m",
        "vertical_convention": "elevation_positive_up",
        "convention_evidence": {"status": "inspected"},
    }


def manifest(tmp_path: Path, entries: list[dict[str, Any]]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"files": entries}), encoding="utf-8")
    return path


@pytest.mark.parametrize("half", ["east", "west"])
def test_select_half_from_bundled_manifest(half: str) -> None:
    """Expected endpoints are terrain_sources.yml: boem_gom_bathymetry.endpoints."""
    selected = boem.boem_manifest_entry(half)
    assert selected["source_id"] == "boem_gom_bathymetry"
    assert selected["endpoint"] == f"{half}_meters_geotiff_zip"
    assert selected["filename"] == f"BOEM_Bathymetry_{half.title()}_meters_tiff.zip"


@pytest.mark.parametrize("half", ["north", "EAST", "", "../east"])
def test_invalid_half(half: str) -> None:
    with pytest.raises(ValueError, match="half"):
        boem.boem_manifest_entry(half)


@pytest.mark.parametrize("records", [[], [entry("east"), entry("east")]])
def test_missing_or_duplicate_half(tmp_path: Path, records: list[dict]) -> None:
    with pytest.raises(TerrainFetchError, match="exactly one"):
        boem.boem_manifest_entry("east", manifest_path=manifest(tmp_path, records))


def test_unrelated_source_cannot_satisfy_selection(tmp_path: Path) -> None:
    other = entry("east")
    other["source_id"] = "other"
    with pytest.raises(TerrainFetchError, match="exactly one"):
        boem.boem_manifest_entry("east", manifest_path=manifest(tmp_path, [other]))


@pytest.mark.parametrize("name", ["../east.zip", "/east.zip", "..", "", r"a\east.zip"])
def test_unsafe_filename(tmp_path: Path, name: str) -> None:
    selected = entry("east")
    selected["filename"] = name
    with pytest.raises(TerrainFetchError, match="basename"):
        boem.boem_manifest_entry("east", manifest_path=manifest(tmp_path, [selected]))


def forbid_download(*args: Any, **kwargs: Any) -> None:
    pytest.fail("unexpected network access")


def test_missing_archive_is_offline_and_leaves_root_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(boem, "fetch_bathymetry", forbid_download)
    root = tmp_path / "absent"
    with pytest.raises(TerrainFetchError, match="not cached"):
        boem.read_boem_depth_grid(
            "east",
            BBOX,
            data_root=root,
            max_cells=4,
            manifest_path=manifest(tmp_path, [entry("east")]),
        )
    assert not root.exists()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bbox": (2.0, 0.0, 0.0, 2.0)},
        {"bbox": (float("nan"), 0.0, 2.0, 2.0)},
        {"max_cells": 0},
        {"max_cells": True},
        {"max_cells": 1.5},
        {"download": "false"},
    ],
)
def test_bad_request_rejected_before_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kwargs: dict[str, Any]
) -> None:
    monkeypatch.setattr(boem, "fetch_bathymetry", forbid_download)
    options = dict(bbox=BBOX, max_cells=4, download=True)
    options.update(kwargs)
    with pytest.raises(ValueError):
        boem.read_boem_depth_grid(
            "east",
            data_root=tmp_path,
            **options,
            manifest_path=manifest(tmp_path, [entry("east")]),
        )


def test_unqualified_units_rejected_before_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(boem, "fetch_bathymetry", forbid_download)
    selected = entry("east")
    selected["units"] = "ft"
    with pytest.raises(TerrainFetchError, match="conventions"):
        boem.read_boem_depth_grid(
            "east",
            BBOX,
            data_root=tmp_path,
            max_cells=4,
            download=True,
            manifest_path=manifest(tmp_path, [selected]),
        )


@pytest.mark.parametrize("download", [False, True])
def test_corrupt_cache_is_refused_without_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, download: bool
) -> None:
    monkeypatch.setattr(boem, "fetch_bathymetry", forbid_download)
    archive = tmp_path / "east.zip"
    archive.write_bytes(b"corrupt")
    with pytest.raises(TerrainFetchError, match="SHA-256"):
        boem.read_boem_depth_grid(
            "east",
            BBOX,
            data_root=tmp_path,
            max_cells=4,
            download=download,
            manifest_path=manifest(tmp_path, [entry("east")]),
        )
    assert archive.read_bytes() == b"corrupt"


@pytest.mark.parametrize("half", ["east", "west"])
@pytest.mark.parametrize("download", [False, True])
def test_tiny_grid_through_consumer_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, half: str, download: bool
) -> None:
    """Independent hand calculation on a synthetic raster, not BOEM observations.

    A two-by-two grid spans x=0..2 and y=2..0 with unit spacing. Cell
    centres are x=[0.5, 1.5], y=[1.5, 0.5] by origin+(index+0.5)*step.
    Elevations [[-10, 0], [5, -20]] become depths [[10, NaN], [NaN, 20]]:
    negate negative water elevations; mask declared zero nodata and land.
    The cell budget is 2*2=4; a budget of 3 must refuse the same window.
    """
    rasterio = pytest.importorskip("rasterio")
    from affine import Affine

    tiff = tmp_path / "tiny.tif"
    with rasterio.open(
        tiff,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        nodata=0,
        transform=Affine(1, 0, 0, 0, -1, 2),
    ) as raster:
        raster.write(np.array([[-10, 0], [5, -20]], dtype="float32"), 1)
        raster.set_band_unit(1, "m")
    archive = tmp_path / "tiny.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.write(tiff, arcname="grid/tiny.tif")
    content = archive.read_bytes()
    records = [entry("east", content), entry("west", content)]
    manifest_path = manifest(tmp_path, records)
    root = tmp_path / "data"
    calls: list[str] = []

    # Exercise the real fetcher with the existing HTTP response fixture.
    # An uncached explicit download makes one HEAD and one GET request.
    from test_bathymetry import Response

    def response(url: str, **kwargs: Any) -> Response:
        calls.append(url)
        return Response(content=content)

    monkeypatch.setattr("requests.head", response)
    monkeypatch.setattr("requests.get", response)
    if not download:
        root.mkdir()
        (root / f"{half}.zip").write_bytes(content)
    grid = boem.read_boem_depth_grid(
        half,
        BBOX,
        data_root=root,
        max_cells=4,
        download=download,
        manifest_path=manifest_path,
    )
    np.testing.assert_array_equal(grid.longitude, [0.5, 1.5])
    np.testing.assert_array_equal(grid.latitude, [1.5, 0.5])
    np.testing.assert_array_equal(grid.depth_m, [[10, np.nan], [np.nan, 20]])
    assert calls == ([f"https://example.org/{half}.zip"] * 2 if download else [])
    assert not (root / f"{'west' if half == 'east' else 'east'}.zip").exists()
    monkeypatch.setattr(boem, "fetch_bathymetry", forbid_download)
    with pytest.raises(TerrainFetchError, match="max_cells"):
        boem.read_boem_depth_grid(
            half,
            BBOX,
            data_root=root,
            max_cells=3,
            download=True,
            manifest_path=manifest_path,
        )


@pytest.mark.parametrize("cached", [False, True])
def test_unknown_digest_denies_reuse_and_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cached: bool
) -> None:
    monkeypatch.setattr("requests.head", forbid_download)
    monkeypatch.setattr("requests.get", forbid_download)
    selected = entry("east")
    selected["sha256"] = None
    if cached:
        (tmp_path / "east.zip").write_bytes(b"fixture")
    with pytest.raises(TerrainFetchError, match="not yet fetched"):
        boem.read_boem_depth_grid(
            "east",
            BBOX,
            data_root=tmp_path,
            max_cells=4,
            download=True,
            manifest_path=manifest(tmp_path, [selected]),
        )
