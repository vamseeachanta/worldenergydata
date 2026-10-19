# NOAA coastal relief subsets

The CRM acquisition helper discovers catalog-advertised datasets and downloads
bounded native-grid subsets through WCS. Downloads remain outside Git. A returned
receipt records the source request, catalog address, byte count and SHA-256 digest;
it establishes transport provenance, not scientific suitability.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add discovery and bounded subset acquisition without full-volume downloads. |

## Source basis

- [NOAA CRM THREDDS catalog](https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.xml),
  dataset citation dated September 2010, inspected 2026-10-19: inline dataset
  paths, inherited services and the nominal three arc-second product description.
  The catalog also contains regional products; their names alone do not establish
  resolution, coverage or vertical datum.
- [NOAA volume 3 DescribeCoverage](https://www.ngdc.noaa.gov/thredds/wcs/crm/crm_vol3.nc?service=WCS&version=1.0.0&request=DescribeCoverage),
  inspected 2026-10-19: coverage `z`, request CRS `OGC:CRS84` and NetCDF3 output.
- [Unidata TDS WCS Reference](https://docs.unidata.ucar.edu/tds/current/userguide/wcs_ref.html),
  WCS 1.0.0 implementation and examples, inspected 2026-10-19: GetCoverage
  parameters, west/south/east/north bounding-box order and no interpolation.
- [NetCDF Users Guide v1.2, Appendix B](https://docs.unidata.ucar.edu/nug/current/file_format_specifications.html):
  classic and offset-format magic bytes used to reject service-error pages.

A small public GetCoverage request for volume 3 returned HTTP 200 and a NetCDF3
payload during implementation. This observation does not guarantee availability
or validate other datasets.

## Usage

Import from `worldenergydata.field_development.coastal_relief`. All resource
budgets and the output destination are explicit caller inputs. `timeout_s` is a
requests connect/read timeout, not a total download deadline. `bbox` contains
geographic degrees in west, south, east, north order. The XML parser uses
`defusedxml`, present in the existing runtime dependency graph.

```python
from worldenergydata.field_development.coastal_relief import (
    discover_crm_datasets,
    fetch_crm_subset,
)

datasets = discover_crm_datasets(
    timeout=timeout_s,
    max_bytes=catalog_byte_budget,
)
# This path is advertised in NOAA's CRM catalog, cited above.
dataset = next(d for d in datasets if d.url_path == "crm/crm_vol3.nc")
receipt = fetch_crm_subset(
    dataset,
    bbox,
    output_file,
    coverage=coverage_name,
    timeout=timeout_s,
    max_bytes=subset_byte_budget,
)
```

`coverage_name` must come from that dataset's DescribeCoverage response. Coverage
`z` was observed for volume 3; the helper does not assume it for every product.
The request selects NetCDF3 and `OGC:CRS84` without specifying interpolation or
output spacing. `build_crm_subset_url` prepares the same request without fetching.

The helper uses the existing `noaa_ncei_coastal_relief` source ID and its catalog
endpoint. `parse_crm_catalog` also accepts saved XML for offline discovery. It
supports NOAA's inline catalog layout, inherited service selection and empty-base
compound groups; it refuses ambiguous services and does not follow catalog
references or redirects. XML DTDs, entities and external references are rejected.

The byte budget applies to decoded response bytes, including when a server
compresses its response. The helper rejects HTTP errors, redirects, incomplete
uncompressed transfers, service-error pages and oversized responses. An existing
destination is preserved, and incomplete transfers do not publish an output.
Publication requires a same-directory hard link, so the output filesystem must
support hard links. Keep the returned receipt with the data; receipt persistence
is the caller's responsibility. Temporary transfer files are cleaned up.

## Verification and limits

Offline tests use synthetic catalogs and transport bytes. Expected URL fields
are written independently from the published WCS example. The byte-count example
is four magic bytes plus nine ASCII bytes, giving thirteen bytes. The independent
SHA-256 oracle is the standard library. These fixtures do not claim to be valid
scientific netCDF datasets. Resource budgets and test coordinates are synthetic
inputs, not engineering acceptance limits. No engineering equation is applied.

Elevation decoding, missing-value handling, vertical datum qualification,
conversion to water depth, regional mosaics, coordinate reprojection and spatial
accuracy are NOT_EVALUATED. The existing qualified bathymetry reader is not wired
to CRM output. Later work must inspect per-product metadata before adding that
integration. This helper does not infer engineering-ready depths from a
successful download or from a catalog entry's verified status.
