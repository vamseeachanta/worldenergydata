# worldenergydata-australia

Australia source package for offshore field-development screening.

The initial #721 slice is **FieldConcept / screening-only**: Australia has no
national open per-field *offshore production* database, so this member ingests
the strong AU asset — field metadata (per-field water depth, spud date) from
**DataVic Open Data** (Resources Victoria) and **NOPTA** (Commonwealth offshore
titles/wells), both **CC-BY-4.0** — and runs the field-development concept
screening (`recommend()`) on it. Production economics are explicitly deferred
(no volumes), and the chain output is labelled `production_available=False` so
the zeroed cashflow is never mistaken for a screening result.

## Offline bathymetry point enrichment

`metadata.ga_bathymetry.normalize_bathymetry_point(point)` accepts an explicitly
extracted `ga_ausbathytopo250m_2023` point. Required evidence comprises
`height_depth` (number or null), `unit="m"`, `vertical_datum="MSL"`, the extraction
query's `latitude` and `longitude`, `spatial_reference={"wkid": 4326}`,
`source_sha256` (lowercase hexadecimal SHA-256 of the retained source bytes), and
`retrieved_at_utc` (a timestamp with timezone). The product identifier is required
in `product`. This interface records caller-supplied evidence; it does not verify
the digest against source bytes or establish freshness.

The [GA/DEA 2023 specifications, band and product-information tables](https://knowledge.dea.ga.gov.au/data/external-data/ga-ausbathytopo-250m/)
define the metre/MSL basis, NoData sentinel and WGS84 reference system. Depth is
the negative of submerged elevation relative to MSL. Missing, NoData, shoreline
and land samples return `NOT_EVALUATED` with a reason and null depth. Invalid
units, datum, coordinates or provenance raise `ValueError`.

`enrich_well_from_bathymetry(well, point)` returns a copy and requires the exact
same query coordinates and WGS84 datum. Qualified existing well depths take
priority. NOPTA GDA94 coordinates require a separately established transformation;
relabeling them WGS84 is not a transformation. No nearest-point matching,
interpolation or automatic field linkage is performed.

Pass the returned well through `australia_field_to_concept(..., wells=[well])`
with an explicit matching field name and representative well identifier. The
field fallback is used when depth is unavailable; measured field depths take
priority over grid estimates. Enrichment metadata retains extraction provenance,
and FieldConcept `data_source` records the bathymetry origin, product and claimed
digest. Coordinates retain their original datum in metadata; FieldConcept has no
coordinate fields. A grid estimate is never labelled as a measured water depth.

This adapter is for screening only. No live point extraction, survey accuracy,
vertical uncertainty, current-product coverage or wider field coverage is
established. The product is the documented 2023 edition; it is not implicitly
upgraded to newer editions. No source rows or grids are redistributed. Live
retrieval, digest readback, coordinate transformation and curated field linkage
remain later slices. The earlier NOPTA service licence boundary remains as
recorded in `data/nopta_wells_note.md`.
