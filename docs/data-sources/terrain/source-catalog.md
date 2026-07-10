# Terrain & Bathymetry Public Source Catalog

Issue [#930](https://github.com/vamseeachanta/worldenergydata/issues/930)
(epic [#929](https://github.com/vamseeachanta/worldenergydata/issues/929),
workstream A1). Machine-readable twin:
[`src/worldenergydata/field_development/terrain_sources.yml`](../../../src/worldenergydata/field_development/terrain_sources.yml)
(loaded and validated by `worldenergydata.field_development.terrain`).

Consumers: the field-development layout/screening epic (digitalmodel#1507) and
the onshore tracer (digitalmodel#1508 — needs the USGS 3DEP DEM path first).

Every source below was verified live on **2026-07-10** (curl HEAD or a tiny
sample download against the real endpoint — not documentation pages).

## Verified sources

| Source | Provider | Access | Format | Resolution | Coverage | License |
|---|---|---|---|---|---|---|
| USGS 3DEP seamless DEM (dynamic image service) | USGS | ArcGIS ImageServer `exportImage` (bbox → clipped raster) | GeoTIFF | best-available seamless (1/3 arc-sec ~10 m baseline; 1 m where lidar published) | Onshore US | US public domain |
| USGS 3DEP staged tiles + TNM Access API | USGS | TNM products API + static S3 tiles | GeoTIFF | 1/3 arc-sec, 1°x1° tiles (~490 MB each) | Onshore US | US public domain |
| GEBCO 2024 global grid | GEBCO / BODC | Static download (release-pinned URL) | netCDF | 15 arc-sec (~450 m) | Global | Public domain (attribution requested) |
| NOAA NCEI Coastal Relief Model | NOAA NCEI | THREDDS (HTTPServer / OpenDAP / WCS / WMS) | netCDF | 3 arc-sec (~90 m) per coastal volume | US coastal zone incl. GoM | US public domain |
| BOEM northern GoM deepwater bathymetry | BOEM | Static download (west/east GeoTIFF zips) | GeoTIFF | 40 x 40 ft (~12.2 m) | Northern GoM deepwater | US public domain |

## Verification evidence (2026-07-10)

- **USGS 3DEP dynamic service** — `exportImage` with
  `bbox=-95.40,29.70,-95.30,29.80&bboxSR=4326&size=64,64&format=tiff&pixelType=F32&f=image`
  returned HTTP 200 with a valid 64x64 float32 GeoTIFF (66,342 bytes).
  Service metadata (`?f=json`) reports 3DEP DEM data published as of
  2026-06-23.
- **USGS 3DEP staged tiles** — TNM products API returned HTTP 200 JSON
  (4 products for the test bbox); HEAD of tile `USGS_13_n30w096.tif` returned
  HTTP 200, `image/tiff`, 487,781,914 bytes, Last-Modified 2026-06-24.
- **GEBCO 2024** — HEAD of the BODC zip endpoint returned HTTP 200,
  `application/zip`, `gebco_2024.zip`, 4,267,373,073 bytes. (A `gebco_2025`
  path returned 404 on the verification date — 2024 is the latest release at
  this endpoint; bump the release-pinned URL on new annual grids.)
- **NOAA NCEI CRM** — THREDDS catalog XML returned HTTP 200 (HTTPServer /
  OpenDAP / WCS / WMS services); a byte-range request on `crm_vol3.nc`
  (Florida & eastern GoM) returned HTTP 206,
  `Content-Range: bytes 0-0/570529124`, `application/x-netcdf`.
- **BOEM GoM bathymetry** — HEAD of
  `BOEM_Bathymetry_West_meters_tiff.zip` returned HTTP 200, 513,392,333 bytes;
  `BOEM_Bathymetry_East_meters_tiff.zip` HTTP 200, 509,191,783 bytes (both
  Last-Modified 2024-09-25).

## Fetch helper

```python
from worldenergydata.field_development.terrain import fetch_dem

# Clipped onshore-US DEM (WGS84 bbox) -> small GeoTIFF, no bulk tile download
path = fetch_dem((-95.40, 29.70, -95.30, 29.80), size=(256, 256))
```

Endpoints are config-externalized in `terrain_sources.yml`; `fetch_dem`
refuses unverified sources, sniffs the GeoTIFF magic (the ArcGIS service
reports errors as HTTP-200 JSON), and defaults its output to the system temp
directory. **Rasters are fetch-on-demand only — never commit them to git**
(staged tiles ~490 MB, GEBCO ~4.3 GB, CRM volumes ~570 MB, BOEM halves
~510 MB).

Tests: `tests/modules/field_development/test_terrain.py` (offline by default;
the live smoke test is opt-in via `WED_LIVE_NETWORK_TESTS=1` and the
`network` marker).
