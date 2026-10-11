"""Offline bathymetry qualification and hand-checkable synthetic grids."""

import hashlib
import json

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


def record(content=b"fixture"):
    return {
        "filename": "fixture.zip",
        "source_id": "boem_gom_bathymetry",
        "source_url": "https://example.org/grid.zip",
        "size_bytes": len(content),
        "issue_size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "head": {"status": 200, "size_bytes": len(content)},
    }


def test_verified_file_and_corruption(tmp_path):
    path = tmp_path / "fixture.zip"
    path.write_bytes(b"fixture")
    verify_file(path, record())
    path.write_bytes(b"corrupt")
    with pytest.raises(TerrainFetchError, match="SHA-256"):
        verify_file(path, record())


def test_unknown_digest_refused(tmp_path):
    entry = record()
    entry["sha256"] = None
    with pytest.raises(TerrainFetchError, match="not yet fetched"):
        verify_file(tmp_path / "fixture.zip", entry)


def test_profile_and_clip_hand_checkable():
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
    def __init__(self, status=200, content=b"fixture", headers=None):
        self.status_code = status
        self.content = content
        self.headers = headers or {"Content-Length": str(len(content)), "ETag": '"v1"'}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_content(self, chunk_size):
        yield self.content


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def head(self, *args, **kwargs):
        return Response()

    def get(self, *args, **kwargs):
        self.calls.append(kwargs)
        return self.response


def manifest(tmp_path, entry):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"files": [entry]}))
    return path


def test_fetch_and_cached_verification(tmp_path):
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


def test_refusal_is_not_retried(tmp_path):
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


def test_validated_resume(tmp_path):
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


def test_bad_resume_refused(tmp_path):
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


def test_size_drift_blocks_before_network(tmp_path):
    entry = record()
    entry["size_bytes"] += 1
    session = Session(Response())
    with pytest.raises(TerrainFetchError, match="differs from issue"):
        fetch_bathymetry(
            "boem_gom_bathymetry",
            "fixture.zip",
            tmp_path,
            manifest_path=manifest(tmp_path, entry),
            session=session,
        )
    assert not session.calls


def test_range_ignored_restarts(tmp_path):
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


def test_curation_does_not_grant_reuse(tmp_path):
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


def test_sign_land_and_nodata():
    from worldenergydata.field_development.bathymetry_grid import _depth

    np.testing.assert_allclose(
        _depth(np.ma.array([-20.0, 5.0, -1.0], mask=[False, False, True])),
        [20.0, np.nan, np.nan],
        equal_nan=True,
    )


def test_archive_traversal_refused(tmp_path):
    import zipfile

    from worldenergydata.field_development.bathymetry_grid import _member

    path = tmp_path / "archive.zip"
    with zipfile.ZipFile(path, "w") as zipped:
        zipped.writestr("../grid.tif", b"fixture")
    with pytest.raises(TerrainFetchError, match="unsafe"):
        _member(path, ".tif", None)


def test_netcdf_reads_only_bbox(tmp_path, monkeypatch):
    import sys
    import types
    import zipfile

    from worldenergydata.field_development.bathymetry_grid import _read_netcdf

    reads = []

    class Variable:
        dimensions = ("lat", "lon")
        units = "m"

        def __getitem__(self, key):
            reads.append(key)
            return np.array([[-50.0, -60.0], [-80.0, -90.0]])

    class Coordinate:
        def __init__(self, units):
            self.units = units

        def __getitem__(self, key):
            return np.array([0.0, 1.0, 2.0])

    class Dataset:
        def __init__(self, path):
            self.variables = {
                "lon": Coordinate("degrees_east"),
                "lat": Coordinate("degrees_north"),
                "elevation": Variable(),
            }

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setitem(sys.modules, "netCDF4", types.SimpleNamespace(Dataset=Dataset))
    path = tmp_path / "grid.zip"
    with zipfile.ZipFile(path, "w") as zipped:
        zipped.writestr("grid.nc", b"synthetic reader transport")
    grid = _read_netcdf(path, "grid.nc", (1.0, 1.0, 2.0, 2.0), 4)
    assert reads == [(slice(1, 3), slice(1, 3))]
    np.testing.assert_array_equal(grid.depth_m, [[50.0, 60.0], [80.0, 90.0]])
    with pytest.raises(TerrainFetchError, match="max_cells"):
        _read_netcdf(path, "grid.nc", (0.0, 0.0, 2.0, 2.0), 4)


def test_fractional_window_covers_qualifying_centres():
    from types import SimpleNamespace

    from worldenergydata.field_development.bathymetry_grid import _cover_window

    window = SimpleNamespace(col_off=0.9, row_off=0.9, width=0.7, height=0.7)
    assert _cover_window(window) == (0, 0, 2, 2)


def test_malformed_axis_refused_before_values():
    from worldenergydata.field_development.bathymetry_grid import _validate_axis

    with pytest.raises(ValueError, match="monotonic"):
        _validate_axis(np.array([0.0, 100.0, 1.0]), 180)


def test_unknown_source_conventions_refused():
    from worldenergydata.field_development.bathymetry_grid import _qualify_conventions

    with pytest.raises(TerrainFetchError, match="conventions"):
        _qualify_conventions(
            {"units": "ft", "vertical_convention": "depth_positive_down"}
        )
    _qualify_conventions({"units": "m", "vertical_convention": "elevation_positive_up"})
