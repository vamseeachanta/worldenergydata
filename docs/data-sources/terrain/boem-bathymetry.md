# BOEM bathymetry consumer access

Select a published east or west metre GeoTIFF and read a bounded depth grid
through `worldenergydata.field_development.boem_bathymetry`. Access defaults to
verified local archives. A missing archive is downloaded only with an explicit
`download=True` request.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-19 | Document half selection and explicit downloads for bounded consumer reads. |

## Source basis

The [BOEM public bathymetry page](https://www.boem.gov/oil-gas-energy/mapping-and-data/map-gallery/northern-goa-deepwater-bathymetry-grid-3d-seismic),
sections **The Bathymetry Grid** and **Downloads**, describes the eastern and
western halves and supplies separate metre GeoTIFF archives. The page was
accessed on 2026-10-19 and returned HTTP 200 after the catalog URL redirected.
Endpoint names come from `terrain_sources.yml`; sizes, hashes, units and inspected
vertical conventions remain in `bathymetry_manifest.json`. This interface adds
no engineering coefficient, accuracy criterion or inferred boundary between
halves. It delegates reprojection, cell-centre clipping and sign conversion to
the existing reader described in [Bathymetry fetch and grid queries](bathymetry-fetch.md).

## Usage

Supply `external_data_directory` as a `pathlib.Path`, `area_of_interest` as a
WGS84 `(west, south, east, north)` bounding box in degrees, and `cell_budget` as
a positive integer maximum number of raster cells. The budget is a caller
resource constraint; it is required and has no engineering acceptance meaning.

```python
from worldenergydata.field_development.boem_bathymetry import (
    boem_manifest_entry,
    read_boem_depth_grid,
)

entry = boem_manifest_entry("west")
grid = read_boem_depth_grid(
    "west",
    area_of_interest,
    data_root=external_data_directory,
    max_cells=cell_budget,
)
```

`boem_manifest_entry` reads metadata without accessing the network. It rejects
missing or duplicate half records and unsafe archive filenames. Only the BOEM
metre GeoTIFF endpoints are selected; feet and hillshade products are excluded.

To fetch a missing half, pass `download=True` to the same call. The existing
serial, resumable fetcher validates pinned bytes before the reader opens them.
Only the selected half is requested. Cached files are hashed on every read;
corrupt files are retained and refused even when downloading is enabled. An
unknown digest cannot authorize a download or cached read through this API;
explicit curation remains available through the lower-level fetcher. Invalid
bounding boxes, budgets, download flags and unqualified units/sign evidence are
rejected before a download starts. Offline requests create no data directory.

The returned `DepthGrid` contains WGS84 cell-centre axes and positive-down depths
in metres. Land and nodata become NaN. Optional `rasterio` is required. The API
neither selects coverage automatically nor combines east and west; use the
published coverage map to select a half. A bounding box outside that half is
refused by the reader. Crossing the split requires separate reads and a future
mosaic policy. Engineering suitability remains unevaluated.

## Test basis and limits

`test_boem_bathymetry.py` checks both half records in the bundled manifest,
selection failures, request validation, offline behavior, unknown digests and
corrupt caches. A generated GeoTIFF exercises both halves through the real
reader and the real fetcher with simulated HTTP responses. Its docstring derives
cell centres and depths by hand, including zero nodata and positive land
values. It checks the exact cell budget boundary without numerical tolerances.
These synthetic coordinates and elevations are fixtures, not BOEM observations.
Live archives are not downloaded or requalified by these tests.
