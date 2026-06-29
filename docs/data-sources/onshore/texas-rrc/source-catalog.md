# Texas RRC Source Catalog

This catalog defines the first onshore pilot for `worldenergydata`: Texas RRC
field-development data stored under `/mnt/ace`. Official Texas RRC datasets are
the durable source of record. PatchOps and RRC EWA web-form queries are
validation and query-prototyping surfaces.

## Lifecycle Coverage

| Source family | Coverage | Refresh | Format | Status |
| --- | --- | --- | --- | --- |
| `production_pdq` | Lease, field, district, operator, oil, gas, condensate, water, production month, well count | Last Saturday each month | ZIP/CSV | Available |
| `wellbore_query` | API, district, lease, county, field, operator, permit, schedule, well type, status | Beginning of month | ZIP/ASCII | Available |
| `drilling_permits` | Permit master/trailer, API, field, lease, depth, location, permit type | Nightly | ASCII | Available |
| `completion_data` | Completion and recompletion forms, district-organized completion data | Nightly | ZIP/ASCII/PDF | Partial |
| `directional_surveys` | Directional survey applications | Daily | ZIP/PDF | Partial |
| `well_gis_layers` | Well GIS layers by county | Twice weekly | Shapefile | Available |
| `pipeline_gis_layers` | Pipeline GIS layers by county | Twice weekly | Shapefile | Available |
| `field_lease_operator` | Field, lease, operator, P-4, docket, and organization context | Source-specific | Mixed | Partial |
| `rrc_ewa_lease_query_validation` | API-to-lease lookup and specific lease production query validation | Service-managed | Web form/CSV | Validation only |
| `patchops_rrc_validation` | RRC well, production, and pipeline query validation | Service-managed | MCP/PostGIS tools | Validation only |

## Partial-Source Caveats

Raw refresh uses official Texas RRC download links only. Entries with
`download_strategy: official_godrive_file` or `download_strategy: direct_http`
are eligible for `worldenergydata texas-rrc refresh`; validation-only,
index-required, and `official_godrive_directory` entries are skipped by default.
Directory entries are still official RRC sources, but need fanout/pagination
handling before they can be safely refreshed as a bulk operation.

Completion data is partial for lifecycle reconstruction because structured data
does not capture every detail available in W-2/G-1 forms. Some lifecycle
evidence remains in forms or imaged files and will need a separate document
extraction step if the project needs full form fidelity.

Directional surveys are partial because Texas RRC publishes directional survey
applications as daily zipped PDF images. The public bulk surface does not provide
clean station-level MD, inclination, and azimuth tables without PDF extraction.

Field, lease, and operator context is partial because those identifiers appear
across multiple RRC products. The normalized layer must preserve original keys
and source names so later joins remain auditable.

PatchOps maps to the same domains as the official catalog for validation:
`wellbore_query`, `production_pdq`, and `pipeline_gis_layers`. It must not become
the only durable data source for the public repository.

The RRC EWA lease query endpoints are official web-form surfaces that are useful
for validating API-to-lease joins and specific lease production output against
the bulk PDQ and Wellbore Query downloads. The historical `derrickturk/rrc-scraper`
repository documents that flow, but it has no asserted SPDX license in GitHub
metadata, so it is reference-only; implementation must use the official endpoint
behavior and not copy scraper code.
