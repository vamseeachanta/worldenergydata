"""Offline regressions for bounded reads and missing bathymetry values."""

import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from test_bathymetry import record

from worldenergydata.field_development import bathymetry_grid


@pytest.mark.parametrize(
    "max_cells",
    [True, False, np.bool_(True), 0, -1, 1.5, 2.0, np.nan, np.inf, -np.inf, "4", None],
)
def test_invalid_cell_budget_refused_before_file_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, max_cells: Any
) -> None:
    """A count must be a positive integer, not a boolean or floating bound.

    These are synthetic API cases, not geographic acceptance limits. NaN and
    infinity otherwise make the window-size comparison fail to impose a bound.
    """

    def unexpected_verification(*args: Any) -> None:
        pytest.fail("invalid cell budget reached archive verification")

    monkeypatch.setattr(bathymetry_grid, "verify_file", unexpected_verification)
    entry = {
        "units": "m",
        "vertical_convention": "elevation_positive_up",
        "convention_evidence": {"status": "inspected"},
    }
    with pytest.raises(ValueError, match="max_cells"):
        bathymetry_grid.read_depth_grid(
            tmp_path / "absent.zip", entry, (0, 0, 1, 1), max_cells=max_cells
        )


@pytest.mark.parametrize(
    "convention,expected",
    [
        ("elevation_positive_up", [20, np.nan, 0, np.nan, np.nan, np.nan, np.nan]),
        ("depth_positive_down", [np.nan, 5, 0, np.nan, np.nan, np.nan, np.nan]),
    ],
)
def test_nonfinite_source_values_remain_missing_in_profiles(
    convention: str, expected: list[float]
) -> None:
    """Hand calculation for a synthetic row [-20, 5, 0, NaN, -inf, inf, masked].

    Positive-up depth is -elevation: -(-20) = 20; +5 is land.
    Positive-down depth keeps +5 and rejects -20. Zero remains zero in both.
    NaN, either infinity and the masked -7 have no finite depth; all become NaN.
    A profile through each exact centre must reproduce this row without filling.
    Finiteness basis: NumPy 2.3 isfinite reference, Notes and Examples (2025):
    https://numpy.org/doc/2.3/reference/generated/numpy.isfinite.html
    Sign basis: bathymetry_manifest.json, BOEM convention_evidence; the reverse
    convention is an explicit synthetic input, not inferred source metadata.
    """
    source = np.ma.array(
        [[-20, 5, 0, np.nan, -np.inf, np.inf, -7]],
        mask=[[False, False, False, False, False, False, True]],
    )
    grid = bathymetry_grid.DepthGrid(
        np.arange(7, dtype=float),
        np.array([0.0]),
        bathymetry_grid._depth(source, convention),
    )
    np.testing.assert_allclose(grid.depth_m, [expected], equal_nan=True)
    profile = bathymetry_grid.depth_profile(grid, (0, 0), (6, 0), samples=7)
    np.testing.assert_allclose(profile, expected, equal_nan=True)


@pytest.fixture
def boem_style_archive(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    """Synthetic sign/nodata fixture, not a representation of source resolution.

    The negative-elevation convention, missing band units and zero nodata follow
    bathymetry_manifest.json, BOEM convention_evidence. The chosen depths and
    degree-sized cells are synthetic inputs, unrelated to measured source data.
    Rasterio 'Nodata Masks', 'Numpy masked arrays' (accessed 2026-10-19):
    https://rasterio.readthedocs.io/en/stable/topics/masks.html
    """
    rasterio = pytest.importorskip("rasterio")
    from affine import Affine

    path = tmp_path / "synthetic.tif"
    values = np.array([[-20, 0, 5], [-30, -np.inf, np.nan]], dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=3,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        nodata=0,
        transform=Affine(1, 0, 0, 0, -1, 2),
    ) as raster:
        raster.write(values, 1)
    archive = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.write(path, arcname="grid/synthetic.tif")
    entry = record(archive.read_bytes())
    entry.update(
        units="m",
        vertical_convention="elevation_positive_up",
        convention_evidence={"status": "inspected"},
    )
    return archive, entry


@pytest.mark.parametrize("max_cells", [6, np.int64(6)])
def test_boem_style_clip_at_exact_cell_budget(
    boem_style_archive: tuple[Path, dict[str, Any]], max_cells: int
) -> None:
    """Hand calculation: 2 rows * 3 columns = 6 cells, so a budget of 6 fits.

    With unit cells and top-left corner (0, 2), centres are x = col + 0.5
    and y = 2 - (row + 0.5): x=[0.5,1.5,2.5], y=[1.5,0.5].
    Affine centre rule: Rasterio 'Transforms', 'Using Affine transformation
    matrix' (accessed 2026-10-19):
    https://rasterio.readthedocs.io/en/stable/topics/transforms.html
    Negating -20 and -30 gives 20 and 30; +5 is land, zero is declared nodata,
    and infinity/NaN are missing. No interpolation may replace a missing cell.
    """
    archive, entry = boem_style_archive
    grid = bathymetry_grid.read_depth_grid(
        archive, entry, (0, 0, 3, 2), max_cells=max_cells
    )
    np.testing.assert_array_equal(grid.longitude, [0.5, 1.5, 2.5])
    np.testing.assert_array_equal(grid.latitude, [1.5, 0.5])
    np.testing.assert_allclose(
        grid.depth_m, [[20, np.nan, np.nan], [30, np.nan, np.nan]], equal_nan=True
    )
    # Exact centres of the top row select [20, missing, missing] independently.
    profile = bathymetry_grid.depth_profile(grid, (0.5, 1.5), (2.5, 1.5), samples=3)
    np.testing.assert_allclose(profile, [20, np.nan, np.nan], equal_nan=True)


def test_boem_style_clip_over_budget_refused_before_pixel_read(
    boem_style_archive: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hand calculation: the same 2 * 3 = 6 cells exceed a budget of 5."""
    from rasterio.vrt import WarpedVRT

    from worldenergydata.field_development.terrain import TerrainFetchError

    class ReadGuard(WarpedVRT):
        def read(self, *args: Any, **kwargs: Any) -> Any:
            pytest.fail("over-budget clip reached pixel read")

    monkeypatch.setattr("rasterio.vrt.WarpedVRT", ReadGuard)
    archive, entry = boem_style_archive
    with pytest.raises(TerrainFetchError, match="max_cells"):
        bathymetry_grid.read_depth_grid(archive, entry, (0, 0, 3, 2), max_cells=5)
