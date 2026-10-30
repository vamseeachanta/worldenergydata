# Bathymetry fetch and grid queries

Refs [936](https://github.com/vamseeachanta/worldenergydata/issues/936),
[934](https://github.com/vamseeachanta/worldenergydata/issues/934).

The terrain catalog remains the source authority. `bathymetry_manifest.json`
records the requested and final URLs, allowed redirect hosts, expected sizes,
source versions, licence provenance, and file inspection evidence. Bathymetry
files are retained externally and are never shipped with the package.

BOEM east and west are GeoTIFF ZIP archives. Both have been fetched and hashed;
the manifest pins the actual bytes and UTC retrieval dates. Their inspected
seabed samples are negative elevations. Band units and descriptions are absent;
the metre basis is the published metres distribution and source catalog. Both
rasters use NAD27 Transverse Mercator with horizontal cells of 40 US survey feet,
float32 values and nodata 0. Validated deepwater clips return 2,403.958 m at
92 degrees west, 26 degrees north (west), and 2,853.842 m at 87 degrees west,
28 degrees north (east), within the screening criterion of 1,000–6,000 m.
A coverage gap is not a valid deepwater sample. The east record's point value
and screening depth differ by 0.305 m; their cells of origin are not recorded.
Reconciliation is pending the next curation run.

The GEBCO 2024 requested ZIP endpoint redirects to the ice-surface-elevation
variant `GEBCO_2024_CF.nc`, an uncompressed netCDF file, served at
7,466,018,396 bytes. The issue's 4,267,373,073 bytes describes the earlier ZIP
rather than the current distribution. GEBCO has not yet been fetched; curation is pending. A null hash and assumed
conventions deny reuse until completion and inspection.
Rights remain catalog/issue provenance; no new licence qualification is claimed.

Set `WORLDENERGYDATA_BATHYMETRY_ROOT` to an external data directory, or provide
`data_root` explicitly. No default root is assumed. Fetch one file at a time:

```python
from worldenergydata.field_development.bathymetry import fetch_bathymetry

archive = fetch_bathymetry(
    "boem_gom_bathymetry", "BOEM_Bathymetry_West_meters_tiff.zip",
    curate=True,
)
```

Each HTTP hop uses HTTPS and a record-specific host allow-list. Automatic
redirects are disabled; at most three hops are followed. A destination outside
the list is refused before a request is sent. The final URL and host must match
the manifest on HEAD and GET, and are recorded in the local observation.
Live HEAD and transfer lengths are checked against `size_bytes`; the issue's
size is retained as provenance only and is never a runtime gate.

Curation writes an observation beside the file, containing its measured size,
SHA-256 and retrieval time. Only a reviewed pinned digest permits reuse.
Cached-file use and `read_depth_grid` refuse missing digests or corrupt files.
Failed transfers retain `.part` and resume metadata. Resume requires a strong
matching ETag and validated Content-Range; an ignored Range restarts transfer.
There is at most one transport retry, after a three-second injectable pause.
HTTP refusals and validation failures are never retried.

```python
from worldenergydata.field_development.bathymetry import load_manifest
from worldenergydata.field_development.bathymetry_grid import (
    read_depth_grid, depth_profile,
)

entry = next(e for e in load_manifest() if e["filename"] == archive.name)
grid = read_depth_grid(archive, entry, (-92.0, 26.0, -91.9, 26.1))
profile_m = depth_profile(grid, (-91.99, 26.01), (-91.91, 26.09), samples=20)
```

GeoTIFF reading requires optional `rasterio`; netCDF reading requires optional
`netCDF4`. Neither is a project dependency. Tiny generated ZIP/GeoTIFF and
netCDF integration tests exercise clips, axes, nodata and sign conversion;
each skips cleanly when its optional package is absent. The direct netCDF
reader opens the verified file read-only, reads coordinate axes and the bounded
index window, and leaves no temporary or derived file. Readers share no
extraction path. `max_cells` defaults to one million.

Each read still hashes the entire source file before opening it. Verified BOEM
clips took approximately 8.1 s (west) and 13.3 s (east), including this hash and
ZIP reader work; these are observed timings, not a benchmark guarantee. The
GEBCO verification cost remains unmeasured while its transfer is incomplete.
No verification cache or digest bypass is introduced.

GeoTIFF CRS is transformed to WGS84 with nearest-cell sampling. Inspected
`elevation_positive_up` values below zero become positive depths;
`depth_positive_down` values are already depths. Land and nodata become NaN.
Unknown units, unknown signs, and conventions supported only by assumptions
are refused. Profiles sample nearest cells on a straight lon/lat line; ties
choose the first axis cell. Antimeridian boxes and coordinates outside the grid
centre extent are refused. Screening checks do not establish engineering
suitability; source qualification and independent review remain required.

[935](https://github.com/vamseeachanta/worldenergydata/issues/935) (NOAA coastal
relief) remains a follow-up and is unchanged.

The reader dependency decision remains outside this fix-up scope.

For explicit east/west selection and offline-first bounded reads, see
[BOEM bathymetry consumer access](boem-bathymetry.md).
