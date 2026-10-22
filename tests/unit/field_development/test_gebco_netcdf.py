"""GEBCO reader contracts with hand-calculated synthetic data.

Sources: GEBCO Compilation Group (2024), GEBCO_2024 Grid, sections
"Introduction" and "CF-compliant NetCDF format":
https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid
CF Metadata Conventions 1.6 (2011), sections 1.2, 2.5.1, 4.1, 4.2 and 8.1:
https://cfconventions.org/Data/cf-conventions/cf-conventions-1.6/build/cf-conventions.html

Fixture numbers are invented inputs, not observations or acceptance limits.
"""

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from typing_extensions import Self

from worldenergydata.field_development.bathymetry_grid import (
    _read_netcdf,
    read_depth_grid,
)
from worldenergydata.field_development.terrain import TerrainFetchError


class Variable:
    def __init__(self, values: Any, dimensions: tuple[str, ...], units: str):
        self.values = np.ma.asarray(values)
        self.dimensions = dimensions
        self.units = units
        self.shape = self.values.shape
        self.reads: list[Any] = []

    def __getitem__(self, key: Any) -> Any:
        self.reads.append(key)
        return self.values[key]


@pytest.fixture
def variables(monkeypatch: pytest.MonkeyPatch) -> dict[str, Variable]:
    """Axes [0, 1, 2]; elevation rows [-1,-2,-3], [-4,-5,-6]."""
    variables = {
        "lon": Variable([0, 1, 2], ("lon",), "degrees_east"),
        "lat": Variable([0, 1], ("lat",), "degrees_north"),
        "elevation": Variable([[-1, -2, -3], [-4, -5, -6]], ("lat", "lon"), "m"),
    }

    class Dataset:
        def __init__(self, path: Path, mode: str):
            assert mode == "r"
            self.variables = variables

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    monkeypatch.setitem(sys.modules, "netCDF4", SimpleNamespace(Dataset=Dataset))
    return variables


@pytest.mark.parametrize("axis", ["lon", "lat"])
def test_masked_coordinate_refused(variables: dict[str, Variable], axis: str) -> None:
    """CF 1.6 section 1.2 forbids missing coordinate values, even in range."""
    variables[axis].values[0] = np.ma.masked
    with pytest.raises(TerrainFetchError, match="coordinate"):
        _read_netcdf(Path("unused.nc"), (0, 0, 2, 1), 6, "elevation_positive_up")
    assert variables["elevation"].reads == []


@pytest.mark.parametrize("axis", ["lon", "lat"])
def test_coordinate_dimension_refused(
    variables: dict[str, Variable], axis: str
) -> None:
    """CF 1.6 section 1.2: a coordinate shares its name with its dimension."""
    variables[axis].dimensions = ("unrelated",)
    with pytest.raises(TerrainFetchError, match="coordinate"):
        _read_netcdf(Path("unused.nc"), (0, 0, 2, 1), 6, "elevation_positive_up")
    assert variables["elevation"].reads == []


@pytest.mark.parametrize(
    "values",
    [
        [],
        [0, 0, 1],
        [0, 2, 1],
        [0, np.nan, 2],
        [0, np.inf, 2],
        [[0, 1, 2]],
        ["a", "b", "c"],
    ],
)
def test_invalid_coordinate_values_refused(
    variables: dict[str, Variable], values: Any
) -> None:
    """CF 1.6 section 1.2: finite numeric monotonic coordinate vectors.

    These invented counterexamples are empty, duplicate, unordered, nonfinite,
    two-dimensional or nonnumeric; none describes a usable coordinate axis.
    """
    variables["lon"].values = np.ma.asarray(values)
    with pytest.raises(TerrainFetchError, match="coordinate"):
        _read_netcdf(Path("unused.nc"), (0, 0, 2, 1), 6, "elevation_positive_up")
    assert variables["elevation"].reads == []


@pytest.mark.parametrize("axis,units", [("lon", "radians"), ("lat", "degrees_east")])
def test_coordinate_units_refused(
    variables: dict[str, Variable], axis: str, units: str
) -> None:
    """CF 1.6 sections 4.1/4.2 distinguish latitude and longitude units."""
    variables[axis].units = units
    with pytest.raises(TerrainFetchError, match="coordinate"):
        _read_netcdf(Path("unused.nc"), (0, 0, 2, 1), 6, "elevation_positive_up")
    assert variables["elevation"].reads == []


@pytest.mark.parametrize("missing", ["lon", "lat", "elevation"])
def test_missing_variable_refused(variables: dict[str, Variable], missing: str) -> None:
    """Only the documented GEBCO lon/lat/elevation schema is supported."""
    elevation = variables["elevation"]
    del variables[missing]
    with pytest.raises(TerrainFetchError, match="required.*variable"):
        _read_netcdf(Path("unused.nc"), (0, 0, 2, 1), 6, "elevation_positive_up")
    assert elevation.reads == []


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("units", "ft"),
        ("units", None),
        ("dimensions", ("lon", "lat")),
        ("shape", (3, 2)),
    ],
)
def test_elevation_schema_refused(
    variables: dict[str, Variable], attribute: str, value: Any
) -> None:
    """GEBCO 2024 specifies a two-dimensional metre elevation array."""
    setattr(variables["elevation"], attribute, value)
    with pytest.raises(TerrainFetchError, match="elevation"):
        _read_netcdf(Path("unused.nc"), (0, 0, 2, 1), 6, "elevation_positive_up")
    assert variables["elevation"].reads == []


@pytest.mark.parametrize("positive", ["down", "unknown"])
def test_contradictory_sign_refused(
    variables: dict[str, Variable], positive: str
) -> None:
    """GEBCO 2024 negative bathymetry must not be read as positive-down."""
    variables["elevation"].positive = positive
    with pytest.raises(TerrainFetchError, match="positive"):
        _read_netcdf(Path("unused.nc"), (0, 0, 2, 1), 6, "elevation_positive_up")
    assert variables["elevation"].reads == []


@pytest.mark.parametrize("positive", ["up", "UP", "Up"])
def test_positive_attribute_is_case_insensitive(
    variables: dict[str, Variable], positive: str
) -> None:
    """CF 1.6 section 4.3 allows case-insensitive positive directions.

    The synthetic elevation -1 at coordinate (0,0) gives depth -(-1) = 1.
    """
    variables["elevation"].positive = positive
    grid = _read_netcdf(Path("unused.nc"), (0, 0, 0.5, 0.5), 1, "elevation_positive_up")
    np.testing.assert_array_equal(grid.depth_m, [[1]])


def test_bounded_slice_and_cell_limit(variables: dict[str, Variable]) -> None:
    """Columns at 1 and 2 in row 1 contain -5,-6, hence depths 5,6.

    The closed box selects 1 row times 2 columns = 2 cells. A caller budget
    of 2 accepts this exact slice; a budget of 1 refuses it before reading.
    """
    grid = _read_netcdf(Path("unused.nc"), (1, 0.5, 2, 1), 2, "elevation_positive_up")
    np.testing.assert_array_equal(grid.depth_m, [[5, 6]])
    assert variables["elevation"].reads == [(slice(1, 2), slice(1, 3))]
    variables["elevation"].reads.clear()
    with pytest.raises(TerrainFetchError, match="max_cells"):
        _read_netcdf(Path("unused.nc"), (1, 0.5, 2, 1), 1, "elevation_positive_up")
    assert variables["elevation"].reads == []


@pytest.mark.parametrize(
    "budget", [True, False, 0, -1, 1.5, float("nan"), float("inf")]
)
def test_invalid_budget_refused_before_file_access(budget: Any) -> None:
    """The resource budget is a caller-selected positive integer cell count."""
    with pytest.raises(ValueError, match="max_cells"):
        read_depth_grid(Path("absent.nc"), {}, (0, 0, 2, 1), max_cells=budget)


@pytest.mark.parametrize("descending", [False, True])
def test_real_packed_netcdf(tmp_path: Path, descending: bool) -> None:
    """CF 1.6 section 8.1: unpacked = packed * scale_factor + add_offset.

    Invented packed rows [-2, -4, -6], [-8, -10, -12] with scale 0.5 and
    offset 1 give elevations [0,-1,-2], [-3,-4,-5]. Override the first two
    cells of row 0 with fill (-999) and land (packed 6 -> elevation 4).
    Thus depths are [NaN,NaN,2], [3,4,5]. Reversing both coordinates and
    data must preserve those coordinate-to-depth associations.
    """
    netcdf = pytest.importorskip("netCDF4")
    path = tmp_path / "packed.nc"
    raw = np.array([[-999, 6, -6], [-8, -10, -12]], dtype="int16")
    longitude, latitude = np.array([0, 1, 2]), np.array([0, 1])
    expected = np.array([[np.nan, np.nan, 2], [3, 4, 5]])
    if descending:
        longitude, latitude = longitude[::-1], latitude[::-1]
        raw, expected = raw[::-1, ::-1], expected[::-1, ::-1]
    with netcdf.Dataset(path, "w") as dataset:
        dataset.createDimension("lat", len(latitude))
        dataset.createDimension("lon", len(longitude))
        for name, axis, units in (
            ("lon", longitude, "degrees_east"),
            ("lat", latitude, "degrees_north"),
        ):
            variable = dataset.createVariable(name, "f8", (name,))
            variable.units = units
            variable[:] = axis
        elevation = dataset.createVariable(
            "elevation", "i2", ("lat", "lon"), fill_value=-999
        )
        elevation.units, elevation.positive = "m", "up"
        elevation.scale_factor, elevation.add_offset = 0.5, 1.0
        elevation.set_auto_maskandscale(False)
        elevation[:] = raw
    entry = {
        "source_id": "gebco_global_bathymetry",
        "units": "m",
        "vertical_convention": "elevation_positive_up",
        "convention_evidence": {"status": "inspected"},
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
        # Existing verify_file contract requires a successful source HEAD.
        "head": {"status": 200},
    }
    before = {item.name: item.read_bytes() for item in tmp_path.iterdir()}
    grid = read_depth_grid(path, entry, (0, 0, 2, 1), max_cells=6)
    np.testing.assert_array_equal(grid.longitude, longitude)
    np.testing.assert_array_equal(grid.latitude, latitude)
    np.testing.assert_allclose(grid.depth_m, expected, equal_nan=True)
    assert {item.name: item.read_bytes() for item in tmp_path.iterdir()} == before
