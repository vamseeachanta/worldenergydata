"""Offline GEBCO reader contracts, using explicit synthetic hand calculations.

Source conventions: GEBCO Compilation Group (2024), GEBCO_2024 Grid,
"CF-compliant NetCDF format" and "Grid, vertical and horizontal datum":
https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid
Coordinate rules: CF Conventions 1.6 (2011), sections 1.2, 4.1, 4.2 and 5:
https://cfconventions.org/Data/cf-conventions/cf-conventions-1.6/build/cf-conventions.html
All fixture coordinates, elevations and resource budgets are chosen test inputs,
not measured GEBCO data or engineering acceptance limits.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from worldenergydata.field_development.bathymetry import file_sha256
from worldenergydata.field_development.bathymetry_grid import (
    _depth,
    _read_netcdf,
    read_depth_grid,
)
from worldenergydata.field_development.terrain import TerrainFetchError


class Variable:
    """Minimal netCDF variable with a log of actual array reads."""

    def __init__(self, values: Any, dimensions: tuple[str, ...], units: str):
        self.values = np.ma.asarray(values)
        self.shape = self.values.shape
        self.dimensions = dimensions
        self.units = units
        self.reads: list[Any] = []

    def __getitem__(self, key: Any) -> Any:
        self.reads.append(key)
        return self.values[key]


@pytest.fixture
def dataset(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Chosen 3 by 3 grid; rows are latitudes, columns are longitudes."""
    variables = {
        "lon": Variable([0, 1, 2], ("lon",), "degrees_east"),
        "lat": Variable([0, 1, 2], ("lat",), "degrees_north"),
        "elevation": Variable(
            [[-10, -20, -30], [-40, 0, 5], [-70, -80, -90]], ("lat", "lon"), "m"
        ),
    }
    state = SimpleNamespace(variables=variables, closed=False)

    class Dataset:
        def __init__(self, path: Path, mode: str):
            assert mode == "r"
            self.variables = variables

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: object) -> None:
            state.closed = True

    monkeypatch.setitem(sys.modules, "netCDF4", SimpleNamespace(Dataset=Dataset))
    return state


def test_inclusive_clip_and_land(dataset: Any, tmp_path: Path) -> None:
    """Hand calculation: x,y in [1,2] select rows/columns 1,2.

    Their elevations [[0,5],[-80,-90]] become [[0,NaN],[80,90]]:
    GEBCO (2024), CF-compliant NetCDF format, defines negative bathymetry;
    land exclusion and retaining sea-level zero are the reader's contract.
    """
    grid = _read_netcdf(tmp_path / "grid.nc", (1, 1, 2, 2), 4, "elevation_positive_up")
    np.testing.assert_array_equal(grid.longitude, [1, 2])
    np.testing.assert_array_equal(grid.latitude, [1, 2])
    np.testing.assert_allclose(grid.depth_m, [[0, np.nan], [80, 90]], equal_nan=True)
    assert dataset.variables["elevation"].reads == [(slice(1, 3), slice(1, 3))]
    assert dataset.closed


@pytest.mark.parametrize("name", ["lon", "lat", "elevation"])
def test_missing_variable_fails_before_elevations(
    dataset: Any, tmp_path: Path, name: str
) -> None:
    elevation = dataset.variables["elevation"]
    del dataset.variables[name]
    with pytest.raises(TerrainFetchError, match="required.*variables"):
        _read_netcdf(tmp_path / "grid.nc", (0, 0, 1, 1), 4, "elevation_positive_up")
    assert not elevation.reads
    assert dataset.closed


@pytest.mark.parametrize(
    "name,attribute,value",
    [
        ("lon", "dimensions", ("other",)),
        ("lat", "dimensions", ("other",)),
        ("lon", "units", "radians"),
        ("lat", "units", "radians"),
        ("elevation", "units", None),
        ("elevation", "dimensions", ("lon", "lat")),
        ("elevation", "shape", (2, 3)),
    ],
)
def test_bad_schema_fails_before_elevations(
    dataset: Any, tmp_path: Path, name: str, attribute: str, value: Any
) -> None:
    setattr(dataset.variables[name], attribute, value)
    with pytest.raises(TerrainFetchError, match="netCDF|elevation"):
        _read_netcdf(tmp_path / "grid.nc", (0, 0, 1, 1), 4, "elevation_positive_up")
    assert not dataset.variables["elevation"].reads
    assert dataset.closed


@pytest.mark.parametrize("name", ["lon", "lat"])
@pytest.mark.parametrize(
    "values",
    [
        np.ma.array([0, 1, 2], mask=[False, True, False]),
        [0, np.nan, 2],
        [0, 0, 2],
        [0, 2, 1],
        ["west", "centre", "east"],
    ],
)
def test_bad_coordinates_fail_before_elevations(
    dataset: Any, tmp_path: Path, name: str, values: Any
) -> None:
    """CF 1.6 sections 1.2 and 5 prohibit missing/nonmonotonic coordinates."""
    dataset.variables[name].values = np.ma.asarray(values)
    with pytest.raises(TerrainFetchError, match="netCDF.*coordinate"):
        _read_netcdf(tmp_path / "grid.nc", (0, 0, 1, 1), 4, "elevation_positive_up")
    assert not dataset.variables["elevation"].reads
    assert dataset.closed


@pytest.mark.parametrize("bbox", [(0, 0, 2, 2), (5, 5, 6, 6)])
def test_budget_or_empty_clip_does_not_read_elevations(
    dataset: Any, tmp_path: Path, bbox: tuple[float, ...]
) -> None:
    """Hand count: inclusive [0,2] selects 3*3=9 cells, above chosen budget 4.

    The other box contains no fixture coordinates. Neither may read values.
    """
    with pytest.raises((TerrainFetchError, ValueError), match="max_cells|outside"):
        _read_netcdf(tmp_path / "grid.nc", bbox, 4, "elevation_positive_up")
    assert not dataset.variables["elevation"].reads
    assert dataset.closed


@pytest.mark.parametrize("budget", [True, False, 0, -1, 1.5, np.nan, np.inf])
def test_invalid_budget_rejected_before_file_access(
    tmp_path: Path, budget: Any
) -> None:
    """A cell count is a caller-selected positive integer, never a boolean."""
    with pytest.raises(ValueError, match="max_cells.*positive integer"):
        read_depth_grid(tmp_path / "absent.nc", {}, (0, 0, 1, 1), max_cells=budget)


@pytest.mark.parametrize("convention", ["elevation_positive_up", "depth_positive_down"])
def test_nonfinite_elevations_become_missing(convention: str) -> None:
    """Hand result: all signed infinities and NaN represent no finite depth.

    Missing data policy follows CF 1.6 section 2.5.1; no interpolation is used.
    """
    assert np.isnan(_depth([np.inf, -np.inf, np.nan], convention)).all()


@pytest.mark.parametrize("reverse_lon", [False, True])
@pytest.mark.parametrize("reverse_lat", [False, True])
def test_real_netcdf_axis_order_and_missing_depths(
    tmp_path: Path, reverse_lon: bool, reverse_lat: bool
) -> None:
    """Hand calculation on a chosen integer grid, not a global-grid sample.

    Coordinates 0,1,2 and bbox (1,0,2,1) select elevations [[-20,5],
    [0,missing]]. GEBCO (2024) negative elevation gives depth [[20,NaN],
    [0,NaN]]. Reversing either source axis reverses its output axis/values.
    Missing-data masking is CF 1.6 section 2.5.1. The chosen fill value -9999
    is a fixture sentinel, not a claimed GEBCO fill value.
    """
    netcdf = pytest.importorskip("netCDF4")
    path = tmp_path / "tiny.nc"
    lon_order = slice(None, None, -1 if reverse_lon else 1)
    lat_order = slice(None, None, -1 if reverse_lat else 1)
    values = np.array([[-10, -20, 5], [-40, 0, -9999], [-70, -80, -90]])
    with netcdf.Dataset(path, "w") as source:
        source.createDimension("lat", 3)
        source.createDimension("lon", 3)
        lon = source.createVariable("lon", "f8", ("lon",))
        lat = source.createVariable("lat", "f8", ("lat",))
        lon.units, lat.units = "degrees_east", "degrees_north"
        lon[:], lat[:] = np.array([0, 1, 2])[lon_order], np.array([0, 1, 2])[lat_order]
        elevation = source.createVariable(
            "elevation", "i2", ("lat", "lon"), fill_value=-9999
        )
        elevation.units = "m"
        elevation[:] = values[lat_order, lon_order]
    digest = file_sha256(path)
    entry = {
        "source_id": "gebco_global_bathymetry",
        "size_bytes": path.stat().st_size,
        "head": {"status": 200},  # Synthetic verification record; no network.
        "sha256": digest,
        "units": "m",
        "vertical_convention": "elevation_positive_up",
        "convention_evidence": {"status": "inspected"},
    }
    before = set(tmp_path.iterdir())
    grid = read_depth_grid(path, entry, (1, 0, 2, 1), max_cells=4)
    np.testing.assert_array_equal(grid.longitude, np.array([1, 2])[lon_order])
    np.testing.assert_array_equal(grid.latitude, np.array([0, 1])[lat_order])
    np.testing.assert_allclose(
        grid.depth_m,
        np.array([[20, np.nan], [0, np.nan]])[lat_order, lon_order],
        equal_nan=True,
    )
    assert set(tmp_path.iterdir()) == before
    assert file_sha256(path) == digest
