# NOPTA wells enrichment boundary

The live Public/Wells FeatureServer layer 0 metadata was inspected on
2026-10-11 UTC. Endpoints and column names were taken from these listings:

- [Regulator spatial data](https://www.nopta.gov.au/maps-and-public-data/spatial-data.html)
- [Public services directory](https://gis.spatial.nopta.gov.au/gis/rest/services/Public?f=json)
- [Wells service](https://gis.spatial.nopta.gov.au/gis/rest/services/Public/Wells/FeatureServer?f=json)
- [Wells layer](https://gis.spatial.nopta.gov.au/gis/rest/services/Public/Wells/FeatureServer/0?f=json)
- [Wells item](https://portal.spatial.nopta.gov.au/portal/sharing/rest/content/items/12886c0431a842aca665a4ecd618f091?f=json)

The service and layer `copyrightText` fields are empty; item `licenseInfo` and
`accessInformation` are null. Layer licence and attribution: **not stated by the
source**. Redistribution of source well rows is not established. No real well
rows are included in this change. The fixture and its generated manifest under
`tests/unit/australia/fixtures/` are labelled synthetic, for offline software
verification only. Attribution: **Synthetic test inputs; no source well records
reproduced.**

The separate [website copyright page](https://www.nopta.gov.au/copyright.html),
retrieved on 2026-10-11 UTC, states:

> All material on this  website is licensed under a Creative Commons Attribution 4.0 International Licence,  save for content supplied by third parties, logos, any material protected by  trademark or otherwise noted in this publication, and the Commonwealth Coat of  Arms.

Its exact attribution instruction is:

> Content contained herein should be attributed as ©  Commonwealth of Australia (Department of Industry) [year], NOPTA [name of document or page containing the content].

That general website statement is not treated as confirmation of the service
item's redistribution licence. The service also describes locations as an aid
to search and discover data; coordinates are not qualified survey positions.

## Available and missing values

The inspected layer provides `OBJECTID`, `Uwi`, `WellName`, `Latitude`,
`Longitude`, `TitleNumber`, basin, rig, and date columns. Its spatial reference
is EPSG:4283 (GDA94), and `maxRecordCount` is 9000. It provides **no water-depth
column, depth unit/datum, or field-name link**. Geometry Z is never interpreted
as water depth. `KickOffDate` is not relabelled as spud date.

The normalizer preserves all returned attributes as `source_columns`. Unknown
depth, unit, datum, and field link remain null, including when coordinates exist.
The default bounded query `OBJECTID <= 5` returned zero rows during the live
exercise. Populated retrieval and wider-field coverage are not established.

Field enrichment requires an explicit representative `well_identifier` in
field metadata and an exact `field_name` link in the selected well. Depth
selection accepts nonnegative finite values only with unit `m` or `ft` and a
stated datum. The field value remains a fallback otherwise. Each depth and
coordinate selection records `measured`, `default`, or `missing` in
`value_origins`; those origins are also included in FieldConcept `data_source`.
Coordinates and their spatial reference remain in enrichment metadata because
FieldConcept has no coordinate fields. Existing metadata can be enriched and
then passed to the screening chain; no production or drilling CAPEX source is
established by this adapter.

Geoscience Australia bathymetry remains excluded: no small direct point-value
route is verified by this slice. No grids are downloaded, and the independent
bathymetry implementation is neither modified nor imported.

## Reproduction

Generate the exact committed synthetic manifest without network access:

```bash
python -m worldenergydata.australia.metadata.nopta_wells \
  --fixture tests/unit/australia/fixtures/nopta_synthetic.json \
  --output tests/unit/australia/fixtures/nopta_synthetic_manifest.json
```

For a bounded live exercise, supply previously inspected layer metadata via
`--layer` and a configured local `--output` destination. The output is local
unlicensed research evidence, not a publishable dataset. The fetcher rechecks
robots and website terms, waits at least two seconds before each request,
uses a repository-contact User-Agent, and refuses redirects. Any change to the
reviewed website terms bytes blocks queries pending a new access assessment. Each request has
a 30-second timeout and a 2 MB response limit; queries are capped at three pages
and 5 MB combined response bytes. Each page requests at most 100 records, never
more than the layer maximum. Caps and duplicate/reordered IDs fail explicitly;
no partial result is returned as complete. HTTP refusals receive no retries.
No credentials, parallel requests, cache location, or machine-specific defaults
are used.
