"""Offline bathymetry qualification and hand-checkable synthetic grids."""

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pytest

from worldenergydata.field_development.bathymetry import (
    fetch_bathymetry,
    verify_file,
)
from worldenergydata.field_development.bathymetry_grid import (
    DepthGrid,
    clip_to_bbox,
    depth_profile,
)
from worldenergydata.field_development.terrain import TerrainFetchError


def record(content: bytes = b"fixture") -> dict[str, Any]:
    return {
        "filename": "fixture.zip",
        "source_id": "boem_gom_bathymetry",
        "source_url": "https://example.org/grid.zip",
        "size_bytes": len(content),
        "issue_reported_size_bytes": len(content),
        "allowed_hosts": ["example.org"],
        "final_url": "https://example.org/grid.zip",
        "final_host": "example.org",
        "sha256": hashlib.sha256(content).hexdigest(),
        "head": {"status": 200, "size_bytes": len(content)},
    }


def test_verified_file_and_corruption(tmp_path: Path) -> None:
    path = tmp_path / "fixture.zip"
    path.write_bytes(b"fixture")
    verify_file(path, record())
    path.write_bytes(b"corrupt")
    with pytest.raises(TerrainFetchError, match="SHA-256"):
        verify_file(path, record())


def test_unknown_digest_refused(tmp_path: Path) -> None:
    entry = record()
    entry["sha256"] = None
    with pytest.raises(TerrainFetchError, match="not yet fetched"):
        verify_file(tmp_path / "fixture.zip", entry)


def test_profile_and_clip_hand_checkable() -> None:
    grid = DepthGrid(
        np.array([0.0, 1.0, 2.0]),
        np.array([0.0, 1.0, 2.0]),
        np.array([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0], [70.0, 80.0, np.nan]]),
    )
    profile = depth_profile(grid, (0.0, 0.0), (2.0, 2.0), samples=3)
    np.testing.assert_allclose(profile, [10.0, 50.0, np.nan], equal_nan=True)
    clipped = clip_to_bbox(grid, (0.0, 0.0, 1.0, 1.0))
    np.testing.assert_array_equal(clipped.depth_m, [[10.0, 20.0], [40.0, 50.0]])
    with pytest.raises(ValueError, match="outside"):
        depth_profile(grid, (-1.0, 0.0), (1.0, 1.0))


class Response:
    def __init__(
        self,
        status: int = 200,
        content: bytes = b"fixture",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status
        self.content = content
        self.headers = headers or {"Content-Length": str(len(content)), "ETag": '"v1"'}

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        yield self.content


class Session:
    def __init__(self, response: Response | None) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def head(self, url: str, **kwargs: Any) -> Response:
        return Response()

    def get(self, url: str, **kwargs: Any) -> Response:
        self.calls.append(kwargs)
        assert self.response is not None
        return self.response


def manifest(tmp_path: Path, entry: dict[str, Any]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"files": [entry]}))
    return path


def test_fetch_and_cached_verification(tmp_path: Path) -> None:
    session = Session(Response())
    path = fetch_bathymetry(
        "boem_gom_bathymetry",
        "fixture.zip",
        tmp_path,
        manifest_path=manifest(tmp_path, record()),
        session=session,
    )
    assert path.read_bytes() == b"fixture"
    fetch_bathymetry(
        "boem_gom_bathymetry",
        "fixture.zip",
        tmp_path,
        manifest_path=tmp_path / "manifest.json",
        session=session,
    )
    assert len(session.calls) == 1


def test_refusal_is_not_retried(tmp_path: Path) -> None:
    session = Session(Response(status=403))
    with pytest.raises(TerrainFetchError, match="refused"):
        fetch_bathymetry(
            "boem_gom_bathymetry",
            "fixture.zip",
            tmp_path,
            manifest_path=manifest(tmp_path, record()),
            session=session,
        )
    assert len(session.calls) == 1


def test_validated_resume(tmp_path: Path) -> None:
    (tmp_path / "fixture.zip.part").write_bytes(b"fix")
    (tmp_path / "fixture.zip.resume.json").write_text(json.dumps({"etag": '"v1"'}))
    session = Session(
        Response(
            206,
            b"ture",
            {"Content-Range": "bytes 3-6/7", "Content-Length": "4", "ETag": '"v1"'},
        )
    )
    path = fetch_bathymetry(
        "boem_gom_bathymetry",
        "fixture.zip",
        tmp_path,
        manifest_path=manifest(tmp_path, record()),
        session=session,
    )
    assert path.read_bytes() == b"fixture"
    assert session.calls[0]["headers"]["Range"] == "bytes=3-"


def test_bad_resume_refused(tmp_path: Path) -> None:
    (tmp_path / "fixture.zip.part").write_bytes(b"fix")
    (tmp_path / "fixture.zip.resume.json").write_text(json.dumps({"etag": '"v1"'}))
    session = Session(Response(206, b"ture", {"Content-Range": "bytes 0-3/7"}))
    with pytest.raises(TerrainFetchError, match="range"):
        fetch_bathymetry(
            "boem_gom_bathymetry",
            "fixture.zip",
            tmp_path,
            manifest_path=manifest(tmp_path, record()),
            session=session,
        )


def test_size_drift_blocks_before_download(tmp_path: Path) -> None:
    entry = record()
    entry["size_bytes"] += 1
    session = Session(Response())
    with pytest.raises(
        TerrainFetchError, match="current server size differs from manifest"
    ):
        fetch_bathymetry(
            "boem_gom_bathymetry",
            "fixture.zip",
            tmp_path,
            manifest_path=manifest(tmp_path, entry),
            session=session,
        )
    assert not session.calls


def test_range_ignored_restarts(tmp_path: Path) -> None:
    (tmp_path / "fixture.zip.part").write_bytes(b"fix")
    (tmp_path / "fixture.zip.resume.json").write_text(json.dumps({"etag": '"v1"'}))
    session = Session(Response())
    path = fetch_bathymetry(
        "boem_gom_bathymetry",
        "fixture.zip",
        tmp_path,
        manifest_path=manifest(tmp_path, record()),
        session=session,
    )
    assert path.read_bytes() == b"fixture"


def test_curation_does_not_grant_reuse(tmp_path: Path) -> None:
    entry = record()
    entry["sha256"] = None
    path = fetch_bathymetry(
        "boem_gom_bathymetry",
        "fixture.zip",
        tmp_path,
        manifest_path=manifest(tmp_path, entry),
        session=Session(Response()),
        curate=True,
    )
    observed = json.loads(path.with_name("fixture.zip.observation.json").read_text())
    assert observed["sha256"] == record()["sha256"]
    assert observed["readiness_status"] == "unverified"
    with pytest.raises(TerrainFetchError, match="not yet fetched"):
        verify_file(path, entry)


def test_sign_land_and_nodata() -> None:
    from worldenergydata.field_development.bathymetry_grid import _depth

    np.testing.assert_allclose(
        _depth(
            np.ma.array([-20.0, 5.0, -1.0], mask=[False, False, True]),
            "elevation_positive_up",
        ),
        [20.0, np.nan, np.nan],
        equal_nan=True,
    )


def test_archive_traversal_refused(tmp_path: Path) -> None:
    import zipfile

    from worldenergydata.field_development.bathymetry_grid import _member

    path = tmp_path / "archive.zip"
    with zipfile.ZipFile(path, "w") as zipped:
        zipped.writestr("../grid.tif", b"fixture")
    with pytest.raises(TerrainFetchError, match="unsafe"):
        _member(path, ".tif", None)


def test_netcdf_reads_only_bbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    import types

    from worldenergydata.field_development.bathymetry_grid import _read_netcdf

    reads: list[Any] = []

    class Variable:
        dimensions = ("lat", "lon")
        units = "m"
        shape = (3, 3)  # Three synthetic coordinate values on each axis below.

        def __getitem__(self, key: Any) -> Any:
            reads.append(key)
            return np.array([[-50.0, -60.0], [-80.0, -90.0]])

    class Coordinate:
        def __init__(self, units: str) -> None:
            self.units = units
            self.dimensions = ("lon",) if units == "degrees_east" else ("lat",)

        def __getitem__(self, key: Any) -> Any:
            return np.array([0.0, 1.0, 2.0])

    class Dataset:
        def __init__(self, path: Path, mode: str) -> None:
            assert mode == "r"
            self.variables = {
                "lon": Coordinate("degrees_east"),
                "lat": Coordinate("degrees_north"),
                "elevation": Variable(),
            }

        def __enter__(self) -> "Dataset":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    monkeypatch.setitem(sys.modules, "netCDF4", types.SimpleNamespace(Dataset=Dataset))
    path = tmp_path / "grid.nc"
    path.write_bytes(b"synthetic reader transport")
    before = list(tmp_path.iterdir())
    grid = _read_netcdf(path, (1.0, 1.0, 2.0, 2.0), 4, "elevation_positive_up")
    assert list(tmp_path.iterdir()) == before
    assert reads == [(slice(1, 3), slice(1, 3))]
    np.testing.assert_array_equal(grid.depth_m, [[50.0, 60.0], [80.0, 90.0]])
    with pytest.raises(TerrainFetchError, match="max_cells"):
        _read_netcdf(path, (0.0, 0.0, 2.0, 2.0), 4, "elevation_positive_up")


def test_fractional_window_covers_qualifying_centres() -> None:
    from types import SimpleNamespace

    from worldenergydata.field_development.bathymetry_grid import _cover_window

    window = SimpleNamespace(col_off=0.9, row_off=0.9, width=0.7, height=0.7)
    assert _cover_window(window) == (0, 0, 2, 2)


def test_malformed_axis_refused_before_values() -> None:
    from worldenergydata.field_development.bathymetry_grid import _validate_axis

    with pytest.raises(ValueError, match="monotonic"):
        _validate_axis(np.array([0.0, 100.0, 1.0]), 180)


def test_unknown_source_conventions_refused() -> None:
    from worldenergydata.field_development.bathymetry_grid import _qualify_conventions

    with pytest.raises(TerrainFetchError, match="conventions"):
        _qualify_conventions(
            {"units": "ft", "vertical_convention": "depth_positive_down"}
        )
    _qualify_conventions(
        {
            "units": "m",
            "vertical_convention": "elevation_positive_up",
            "convention_evidence": {"status": "inspected"},
        }
    )
