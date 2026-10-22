# GEBCO netCDF reader

The existing `read_depth_grid` API reads a bounded window from a locally
verified GEBCO netCDF file. Coordinate and elevation metadata are checked before
elevation values are read. The reader performs no network requests.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-19 | Document coordinate validation and synthetic reader tests so malformed source metadata is refused before elevation reads. |

## Source basis

[GEBCO Compilation Group (2024), GEBCO_2024 Grid](https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid),
sections **Introduction**, **GEBCO Grid, vertical and horizontal datum**, and
**CF-compliant NetCDF format**, describes pixel-centre metre elevations on a
15 arc-second geographic grid, with negative bathymetric depths and positive
topographic heights. The release uses CF Metadata Conventions 1.6.

[CF Metadata Conventions 1.6 (2011)](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.6/build/cf-conventions.html)
provides the coordinate definition in section 1.2, missing-data handling in
section 2.5.1, geographic units in sections 4.1 and 4.2, case-insensitive vertical
directions in section 4.3, and packed-data arithmetic in section 8.1.
Both sources were read on 2026-10-19. The older release-page address returned
HTTP 404; the GEBCO link above returned HTTP 200.

## Local file contract

Supply the local file, its qualified manifest entry and a geographic bounding
box to `read_depth_grid`. The manifest must carry inspected metre/sign
conventions and a pinned SHA-256 digest. The existing file verifier checks the
entire file before the reader opens it. See [fetch and grid usage](bathymetry-fetch.md).

The reader supports `lon(lon)`, `lat(lat)` and `elevation(lat, lon)`. Coordinate
units must be `degrees_east` and `degrees_north`; axes must be finite, numeric,
strictly monotonic and free of masked values. Ascending and descending axes
are accepted. Elevation dimensions and shape must match the axes, and units
must be `m` or `meters`. An optional `positive` attribute must agree with the
inspected manifest convention; its direction is case insensitive. Absent
attributes do not establish a sign convention independently of the manifest.

Cell centres on the bounding-box boundary are included. A box with no centres
is refused. `max_cells` is a caller-selected positive integer resource budget;
booleans, fractional values and nonfinite values are refused before file
access. A clip exceeding the budget is refused before elevation reads. Only
the selected contiguous elevation window is read; coordinate axes are read
in full.

The netCDF4 dependency masks missing values and unpacks data using
`z = packed * scale_factor + add_offset` (CF section 8.1). For inspected
positive-up elevations, depths are `d = -z` where `z <= 0`; positive land
elevations and missing values become NaN. This retains the existing shoreline
policy of accepting zero elevation as zero depth.

## Independent test basis

`tests/unit/field_development/test_gebco_netcdf.py` uses invented inputs with
hand calculations written in the test docstrings:

- Selecting columns at coordinates 1 and 2 in row 1 selects elevations
  -5 and -6, hence depths 5 and 6. The selected window has two cells;
  a caller budget of two accepts it and a budget of one refuses it.
- Packed values -6, -8, -10 and -12 with scale 0.5 and offset 1 yield
  elevations -2, -3, -4 and -5, hence depths 2, 3, 4 and 5. A fill value
  remains missing, and a positive land elevation becomes NaN. Reversed axes
  retain the same coordinate-to-depth associations.
- Malformed dimensions, masks, nonfinite or unordered coordinates, missing
  variables, incompatible elevation shape/units and contradictory directions
  are refused before any elevation read.

The packed-data fixture uses a real optional netCDF4 reader. File bytes and
directory contents are compared before and after reading. Existing bathymetry
tests also exercise a tiny uncompressed netCDF file and GeoTIFF archive.

## Known limits and later slices

The production GEBCO manifest remains unfetched with assumed conventions and
a null digest. Its qualification and a full-grid release/variant reconciliation
remain pending. No bulk grid or new source observation is committed. Synthetic
tests establish reader behaviour only; native release resolution, full-grid
identity and real-world depths remain unevaluated.

The reader preserves the existing geographic-box and straight lon/lat profile
restrictions. Antimeridian-spanning boxes, TID grids, reprojection and automatic
downloads are outside this change. Optional reader dependencies remain optional.
