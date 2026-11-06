# GEBCO netCDF depth clips

The existing `read_depth_grid` API reads bounded cell-centre clips from a local,
verified GEBCO netCDF file. Metadata is checked before elevation values are read.
This reader validation does not qualify the bundled global source for reuse.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Document metadata validation and offline cases so unsupported files fail before elevation reads. |

## Source basis

[GEBCO Compilation Group (2024), GEBCO_2024 Grid](https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid),
sections **Introduction**, **GEBCO Grid, vertical and horizontal datum** and
**CF-compliant NetCDF format**, describes a pixel-centre registered grid with
15 arc-second intervals, 43200 rows and 86400 columns. Elevations are in metres;
negative values represent bathymetry. The published format follows CF conventions.
The reader accepts bounded subsets; it does not require global dimensions or
infer resolution from the filename.

[CF Conventions 1.6 (2011)](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.6/build/cf-conventions.html),
sections **1.2 Terminology** and **5 Coordinate Systems**, requires dimension
coordinates to be monotonic and free of missing values. Sections **4.1 Latitude
Coordinate** and **4.2 Longitude Coordinate** define geographic coordinate units.
Section **2.5.1 Missing Data** describes missing data handling. These sources
were opened successfully on 2026-10-19; no global grid was downloaded.

## Reader contract

- Required variables are `lon`, `lat` and `elevation`.
- Coordinates use their own named dimensions, `degrees_east` and `degrees_north`,
  respectively. They must be finite, unmasked, strictly monotonic geographic
  coordinates. Ascending and descending axes are supported without reordering.
- Elevation dimensions are `(lat, lon)` and its shape must match both axes.
  Units must be `m` or `meters`.
- Bounds select centres inclusively. An empty selection is refused. Only the
  selected elevation rectangle is read after metadata and cell-budget checks.
- `max_cells` is a caller-selected positive integer resource budget. Booleans,
  fractional values and nonfinite values are refused before file access.
- For inspected positive-up elevations, depth equals negative elevation at or
  below sea level. Positive land elevations, masked samples and nonfinite
  values become NaN. Sea-level zero is retained. No interpolation is performed.

The existing manifest verification still checks file size and SHA-256 before
opening the file. A null digest or assumed convention still refuses reuse.
Reading all coordinate values and hashing the full file are still required;
only elevation-array access is bounded. See [fetch and grid queries](bathymetry-fetch.md)
for the fetch API and external data-root configuration.

## Offline evidence

`tests/unit/field_development/test_gebco_grid.py` uses tiny synthetic arrays and
states the expected cell selection and depth conversion by hand in docstrings.
Read spies establish that invalid metadata, an empty box or an exceeded cell
budget triggers no elevation reads. Real optional-netCDF tests exercise all
ascending/descending axis combinations, integer elevations, land, sea-level zero
and fill-value masking. They check file digest and directory contents after
reading. Fixture values are chosen inputs, not measured global-grid samples or
engineering acceptance criteria. The existing bathymetry tests also exercise
fetch integrity checks and GeoTIFF compatibility.

## Limits and later slices

Global download, release reconciliation, digest pinning, local source inspection,
resolution qualification and a real geographic sample remain pending. The
bundled GEBCO manifest and source catalog are unchanged. These tests establish
reader behavior on synthetic data, not global-source accuracy or engineering
suitability. Antimeridian-spanning clips remain unsupported. The ice-surface
variant does not establish seabed depths beneath ice.
