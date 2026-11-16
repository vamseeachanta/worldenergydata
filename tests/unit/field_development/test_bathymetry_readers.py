"""Redirect security and optional readers on tiny generated source files."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tests.unit.field_development.test_bathymetry import (
    Response,
    Session,
    manifest,
    record,
)
from worldenergydata.field_development.bathymetry import fetch_bathymetry, verify_file
from worldenergydata.field_development.bathymetry_grid import (
    _depth,
    _qualify_conventions,
    read_depth_grid,
)
from worldenergydata.field_development.terrain import TerrainFetchError


class RedirectSession(Session):
    def __init__(self, responses: list[Response]) -> None:
        super().__init__(None)
        self.responses = iter(responses)
        self.urls: list[str] = []

    def request(self, url: str, **kwargs: Any) -> Response:
        assert kwargs["allow_redirects"] is False
        self.urls.append(url)
        return next(self.responses)

    head = request
    get = request


def redirect(location: str) -> Response:
    return Response(301, headers={"Location": location})


def fetch_fixture(
    tmp_path: Path, entry: dict[str, Any], session: Any, **kwargs: Any
) -> Path:
    return fetch_bathymetry(
        entry["source_id"],
        entry["filename"],
        tmp_path,
        manifest_path=manifest(tmp_path, entry),
        session=session,
        **kwargs,
    )


def test_allowed_redirect_recorded(tmp_path: Path) -> None:
    entry = record()
    entry.update(
        allowed_hosts=["example.org", "data.example.org"],
        final_url="https://data.example.org/grid.zip",
        final_host="data.example.org",
    )
    session = RedirectSession(
        [
            redirect(entry["final_url"]),
            Response(),
            redirect(entry["final_url"]),
            Response(),
        ]
    )
    target = fetch_fixture(tmp_path, entry, session)
    observation = json.loads(
        target.with_name(target.name + ".observation.json").read_text()
    )
    assert observation["final_url"] == entry["final_url"]
    assert observation["final_host"] == entry["final_host"]
    assert len(session.urls) == 4


@pytest.mark.parametrize(
    "location,reason",
    [
        ("https://unlisted.example/grid", "host"),
        ("http://example.org/grid", "HTTPS"),
    ],
)
def test_unsafe_redirect_refused_before_request(
    tmp_path: Path, location: str, reason: str
) -> None:
    entry = record()
    session = RedirectSession([redirect(location)])
    with pytest.raises(TerrainFetchError, match=reason):
        fetch_fixture(tmp_path, entry, session)
    assert session.urls == [entry["source_url"]]


def test_malformed_redirect_port_refused_before_request(tmp_path: Path) -> None:
    entry = record()
    session = RedirectSession([redirect("https://example.org:invalid/grid.zip")])
    with pytest.raises(
        TerrainFetchError, match=r"example\.org.*port is malformed"
    ) as caught:
        fetch_fixture(tmp_path, entry, session)
    assert isinstance(caught.value.__cause__, ValueError)
    assert session.urls == [entry["source_url"]]


def test_redirect_limit(tmp_path: Path) -> None:
    entry = record()
    session = RedirectSession([redirect(entry["source_url"])] * 4)
    with pytest.raises(TerrainFetchError, match="redirect limit"):
        fetch_fixture(tmp_path, entry, session)
    assert len(session.urls) == 4


def test_final_destination_must_match_manifest(tmp_path: Path) -> None:
    entry = record()
    entry["final_url"] = "https://example.org/other.zip"
    session = RedirectSession([Response()])
    with pytest.raises(TerrainFetchError, match="final destination"):
        fetch_fixture(tmp_path, entry, session)
    assert len(session.urls) == 1


def test_issue_size_is_provenance_only(tmp_path: Path) -> None:
    entry = record()
    entry["issue_reported_size_bytes"] = 1
    path = tmp_path / entry["filename"]
    path.write_bytes(b"fixture")
    verify_file(path, entry)


def test_transport_retry_pauses_once(tmp_path: Path) -> None:
    import requests

    class Interrupted(Session):
        def get(self, *args: Any, **kwargs: Any) -> Response:
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                raise requests.ConnectionError("transport interrupted")
            return Response()

    pauses: list[float] = []
    session = Interrupted(None)
    fetch_fixture(tmp_path, record(), session, pause=pauses.append)
    assert pauses == [3]
    assert len(session.calls) == 2


def test_positive_down_depth_and_plausibility() -> None:
    depths = _depth(
        np.ma.array([1500.0, -5.0, 2.0], mask=[False, False, True]),
        "depth_positive_down",
    )
    np.testing.assert_allclose(depths, [1500.0, np.nan, np.nan], equal_nan=True)
    assert 1000 < depths[0] < 6000


@pytest.mark.parametrize(
    "convention,status",
    [
        ("unknown", "inspected"),
        ("elevation_positive_up", "assumed"),
    ],
)
def test_unqualified_conventions_refused(convention: str, status: str) -> None:
    with pytest.raises(TerrainFetchError, match="conventions"):
        _qualify_conventions(
            {
                "units": "m",
                "vertical_convention": convention,
                "convention_evidence": {"status": status},
            }
        )


def qualified_record(path: Path, source: str, convention: str) -> dict[str, Any]:
    entry: dict[str, Any] = record(path.read_bytes())
    entry.update(
        source_id=source,
        units="m",
        vertical_convention=convention,
        convention_evidence={"status": "inspected"},
    )
    return entry


def test_real_tiny_geotiff(tmp_path: Path) -> None:
    import zipfile

    rasterio = pytest.importorskip("rasterio")
    from affine import Affine

    path = tmp_path / "tiny.tif"
    values = np.array([[1500, -9999, -2], [1600, 1700, 1800]], dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=3,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        nodata=-9999,
        transform=Affine(0.1, 0, -92, 0, -0.1, 27),
    ) as raster:
        raster.write(values, 1)
        raster.set_band_unit(1, "m")
    archive = tmp_path / "tiny.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.write(path, arcname="folder/tiny.tif")
    entry = qualified_record(archive, "boem_gom_bathymetry", "depth_positive_down")
    grid = read_depth_grid(archive, entry, (-92, 26.8, -91.8, 27))
    np.testing.assert_allclose(grid.longitude, [-91.95, -91.85])
    np.testing.assert_allclose(grid.latitude, [26.95, 26.85])
    np.testing.assert_allclose(
        grid.depth_m,
        np.array([[1500, np.nan], [1600, 1700]], dtype=float),
        equal_nan=True,
    )


def test_real_tiny_netcdf_preserves_directory(tmp_path: Path) -> None:
    netcdf = pytest.importorskip("netCDF4")
    path = tmp_path / "tiny.nc"
    with netcdf.Dataset(path, "w") as dataset:
        dataset.createDimension("lat", 2)
        dataset.createDimension("lon", 3)
        lon = dataset.createVariable("lon", "f8", ("lon",))
        lat = dataset.createVariable("lat", "f8", ("lat",))
        lon.units, lat.units = "degrees_east", "degrees_north"
        lon[:], lat[:] = [-92, -91, -90], [26, 27]
        elevation = dataset.createVariable(
            "elevation", "f4", ("lat", "lon"), fill_value=-9999
        )
        elevation.units = "m"
        elevation[:] = [[-1500, -9999, 5], [-1600, -1700, -1800]]
    entry = qualified_record(path, "gebco_global_bathymetry", "elevation_positive_up")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    grid = read_depth_grid(path, entry, (-92, 26, -91, 27))
    np.testing.assert_array_equal(grid.longitude, [-92, -91])
    np.testing.assert_array_equal(grid.latitude, [26, 27])
    np.testing.assert_allclose(
        grid.depth_m,
        np.array([[1500, np.nan], [1600, 1700]], dtype=float),
        equal_nan=True,
    )
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize("status", [401, 403, 429])
def test_head_refusal_does_not_retry(tmp_path: Path, status: int) -> None:
    session = RedirectSession([Response(status)])
    pauses: list[float] = []
    with pytest.raises(TerrainFetchError, match="refused"):
        fetch_fixture(tmp_path, record(), session, pause=pauses.append)
    assert len(session.urls) == 1
    assert pauses == []


def test_get_redirect_is_checked_independently(tmp_path: Path) -> None:
    session = RedirectSession([Response(), redirect("https://unlisted.example/grid")])
    with pytest.raises(TerrainFetchError, match="host"):
        fetch_fixture(tmp_path, record(), session)
    assert session.urls == [record()["source_url"]] * 2
    assert not (tmp_path / "fixture.zip.part").exists()


def test_missing_inspection_evidence_refused() -> None:
    with pytest.raises(TerrainFetchError, match="conventions"):
        _qualify_conventions(
            {"units": "m", "vertical_convention": "depth_positive_down"}
        )
