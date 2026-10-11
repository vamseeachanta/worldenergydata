# Bathymetry fetch and grid queries

Refs [936](https://github.com/vamseeachanta/worldenergydata/issues/936),
[934](https://github.com/vamseeachanta/worldenergydata/issues/934).

The terrain catalog remains the source authority. `bathymetry_manifest.json`
records three archive URLs, issue sizes, observed HEAD sizes/timestamps, units,
source versions and licence statements inherited from the catalog/issues.
No bathymetry archive is shipped. All three SHA-256 values and retrieval dates
are null: **not yet fetched**. Neither a HEAD response nor a local observation
qualifies data for engineering use.

BOEM west/east HEAD sizes match the issues. GEBCO 2024 HEAD reports
7,466,018,396 bytes against the issue's 4,267,373,073 bytes; fetching is blocked
until the release and source discrepancy is reconciled. No replacement URL or
hash is inferred. Rights are recorded from the existing catalog and issues;
no new licence qualification is claimed.

Set `WORLDENERGYDATA_BATHYMETRY_ROOT` to an external data directory, or provide
`data_root` explicitly. No default root is assumed. Fetch one archive at a time:

```python
from worldenergydata.field_development.bathymetry import fetch_bathymetry

archive = fetch_bathymetry(
    "boem_gom_bathymetry", "BOEM_Bathymetry_West_meters_tiff.zip",
    curate=True,
)
```

Curation writes an observation beside the archive, containing its actual size,
SHA-256 and retrieval time. Review that evidence and pin the actual digest/date
in the committed manifest before reuse. The normal fetch mode, cached-file use
and `read_depth_grid` refuse missing digests or corrupt files. Failed transfers
retain `.part` and resume metadata. Resuming requires a strong matching ETag and
validated Content-Range; a server ignoring Range restarts the transfer. There
is at most one transport retry. HTTP refusals are never retried.

```python
from worldenergydata.field_development.bathymetry import load_manifest
from worldenergydata.field_development.bathymetry_grid import (
    read_depth_grid, depth_profile,
)

entry = next(e for e in load_manifest() if e["filename"] == archive.name)
grid = read_depth_grid(archive, entry, (-92.0, 26.0, -91.9, 26.1))
profile_m = depth_profile(grid, (-91.99, 26.01), (-91.91, 26.09), samples=20)
```

GeoTIFF reading requires optional `rasterio`; netCDF4 reading requires optional
`netCDF4`. Neither is currently a project dependency, and neither was installed
for this job. Real-source reader integration is not established. Offline tests
use NumPy grids and a fake netCDF interface to verify bounded value slicing.
The verified netCDF ZIP is streamed to a derived file beside the archive on
every read; global elevation values are never loaded wholesale into memory.

Clips select WGS84 cell centres, limited by `max_cells` (default one million).
GeoTIFF CRS is transformed with nearest-cell sampling. Elevations below zero
become positive depths in metres; land and nodata become NaN. Profiles sample
nearest cells on a straight lon/lat line; ties choose the first axis cell.
No geodesic interpolation is performed. Antimeridian boxes and coordinates
outside the grid centre extent are refused. Results are screening inputs;
engineering acceptance requires source qualification and reader integration.

[935](https://github.com/vamseeachanta/worldenergydata/issues/935) (NOAA coastal
relief) remains a follow-up and is unchanged.
