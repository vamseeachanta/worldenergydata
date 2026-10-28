# Staged DEM downloads

The existing `fetch_dem` helper exports a clipped dynamic DEM; `find_dem_tiles`
discovers a bounded TNM product page. `download_dem_tile` now retrieves a
selected staged GeoTIFF with explicit resource limits and a provenance receipt.
A successful transfer does not establish suitability for engineering use.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-21 | Added bounded staged retrieval and an offline example to complete the selected-product access path. |

## Inputs and method

Import `download_dem_tile` from
`worldenergydata.field_development.terrain_tiles`. Supply a product item from
`find_dem_tiles`, an output path, a positive integer `max_bytes` and a finite,
positive `timeout` in seconds. These limits are caller choices. The timeout
applies to connection and read inactivity, rather than total elapsed time.

The catalog supplies the permitted staged download root. Both current and
historical products are supported: the live TNM query on 2026-10-21 returned a
historical product, so discovery does not imply the newest available tile.
Only direct HTTPS TIFF URLs under that root are accepted. Redirects, URL query
strings, fragments and encoded path components are refused. Selection remains
explicit; no bulk retrieval or hidden pagination occurs.

The helper streams to a temporary file on the destination filesystem. It sums
chunk lengths, rejects a transfer exceeding `max_bytes`, and compares the final
count with positive `sizeInBytes` metadata and any HTTP `Content-Length`.
Missing or zero product size is treated as unknown; the stream budget still
applies. TIFF and BigTIFF byte-order signatures are checked. A hard link
publishes the completed file atomically without replacing an existing file;
the filesystem must support hard links. Failures remove only the staging file.

`DemTileDownload.to_manifest()` retains the selected product metadata, actual
byte count, SHA-256 digest and UTC retrieval time. Its file locator is a basename;
the caller chooses where to save the JSON receipt. The receipt preserves source
publication dates separately from retrieval time. It is a transport record,
not an elevation qualification certificate.

## Offline worked example

Run from the repository root with an unused output directory outside the
repository; the script creates that directory. Dependencies are `requests`,
`PyYAML` and `pydantic` (the package import requires `pydantic`).

```sh
PYTHONPATH=src python examples/terrain_dem_download.py "$OUTPUT_DIR"
```

Inputs are one synthetic product, a seven-byte budget and a synthetic TIFF
signature stub `b"II*\x00abc"`. The independent calculation is four signature
bytes plus three payload bytes, giving seven bytes. Equality with the budget
is accepted. The script writes `tile.tif` and `tile.manifest.json`, with
`size_bytes: 7`, the digest of those literal bytes, the unmodified product
metadata and `qualification: NOT_EVALUATED`. It makes no network requests.
The stub is deliberately not a valid elevation raster. Reuse of an existing
tile or manifest path raises an error rather than replacing it.

## Live use

For a small clip, retain the existing dynamic path:

```python
from worldenergydata.field_development.terrain import fetch_dem

# Synthetic rectangle and output dimensions; these are caller inputs.
clip = fetch_dem((-95.4, 29.7, -95.3, 29.8), output_dir / "clip.tif", size=(32, 32))
```

For staged access, inspect the discovery metadata before selecting a product.
The page retains TNM `total`, `items`, dates and spatial metadata. Advance the
explicit `offset` by the number of returned items when another page is needed;
a page is not evidence of complete coverage.

```python
import json

from worldenergydata.field_development.terrain import find_dem_tiles
from worldenergydata.field_development.terrain_tiles import download_dem_tile

# bbox, selected_index, byte_budget, timeout_seconds and output_dir are inputs.
page = find_dem_tiles(bbox, max_items=page_size)
product = page["items"][selected_index]
receipt = download_dem_tile(
    product,
    output_dir / "selected.tif",
    max_bytes=byte_budget,
    timeout=timeout_seconds,
)
manifest = receipt.to_manifest()
with (output_dir / "selected.manifest.json").open("x", encoding="utf-8") as stream:
    json.dump(manifest, stream, indent=2)
```

Rasters and receipts belong outside Git. Staged downloads can be large; the
caller must choose disk and byte budgets. A SHA-256 digest identifies downloaded
bytes but provides no independent authenticity check without a trusted expected
digest. A mutable source URL can change between discovery and retrieval.

## Sources and qualification limits

- [USGS TNM Access API v1 documentation](https://tnmaccess.nationalmap.gov/api/v1/docs),
  accessed 2026-10-21: Products parameters and ProductsResponse fields
  `sourceId`, `format`, `downloadURL`, `sizeInBytes`, dates and spatial metadata.
- [USGS staged product root](https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current/)
  is catalogued in `terrain_sources.yml`. The TNM Products response was opened
  on 2026-10-21 to confirm the historical URL form; no full staged tile was
  downloaded for validation.
- [Esri Export Image reference](https://developers.arcgis.com/rest/services-reference/enterprise/export-image/),
  accessed 2026-10-21: the existing dynamic `bbox`, `size` and
  `adjustAspectRatio` request contract.
- [Requests timeout documentation](https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts),
  accessed 2026-10-21: timeout is an inactivity limit, not a total download limit.
- [libtiff TIFF definitions](https://raw.githubusercontent.com/libsdl-org/libtiff/master/libtiff/tiff.h),
  accessed 2026-10-21: `TIFF_VERSION_CLASSIC`, `TIFF_VERSION_BIG`,
  `TIFF_LITTLEENDIAN` and `TIFF_BIGENDIAN` define the transport signatures.

No terrain equations, resolution conversions or engineering acceptance limits
are introduced. TIFF structure, georeferencing, horizontal CRS, vertical datum,
units, NoData, coverage, source accuracy and intended-use acceptance remain
`NOT_EVALUATED`. Bulk campaigns, resumable transfers, mosaicking, reprojection
and elevation qualification remain later slices.
