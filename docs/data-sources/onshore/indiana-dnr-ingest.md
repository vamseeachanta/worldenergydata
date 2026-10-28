# Indiana operator well-record ingestion

## Summary

The Indiana DNR ingest produces a permit-level operator inventory from the
official GIS service, with completion records, image catalogue references and
coverage counts. API numbers require a separately sourced crosswalk; they are
never constructed from permit numbers. The supplied example is entirely synthetic.
No bulk collection or PDMS access was performed for this implementation.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Add ingestion, source observations and a reproducible example to expose permit and API coverage separately. |

## Sources and access observations

Public pages and metadata were inspected on 2026-10-20 UTC. Responses, request
addresses, timestamps and HTTP statuses were retained outside the repository.
No source records or raw extracts are redistributed here.

| Source | Observation | Access decision |
| --- | --- | --- |
| [Official OilAndGasWells service](https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer?f=pjson) | HTTP 200. Query-enabled service; description and copyright text empty. | Prefer REST over viewer scraping. Published query capability does not establish reuse permission. Bulk collection requires an explicit recorded permission in the shared fetcher. |
| [Well layer](https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer/0?f=pjson) | HTTP 200. Operator, permit, IGS identifiers, lease, status, scans and geometry. No API or spud-date field. | Select operator names locally from an authorised snapshot. |
| [Completion table](https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer/1?f=pjson) | HTTP 200. IGS-keyed completion types, raw date strings, driller and logger depths. No formation-top or completion-zone fields. | Preserve every completion and raw date; do not assign depth units absent evidence. |
| [Image catalogue](https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer/2?f=pjson) | HTTP 200. Permit-keyed filenames, descriptions and URLs. | Catalogue only; no PDF downloads, OCR or interpretation. |
| [Completion join table](https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer/3?f=pjson) | HTTP 200. Occurrence intervals and remarks exist, without a structured tops schema. | Not ingested; do not reinterpret remarks as formation tops. |
| [PDMS](https://igws.indiana.edu/pdms/) | HTTP 404 after redirect. Basic/Premium boundaries and terms could not be read. | No PDMS automation, scraping, subscription access or bulk requests. Manual Basic-tier crosswalks require attributable evidence and permitted access. |
| [DNR well-records page](https://www.in.gov/dnr/oil-and-gas/permits-and-forms/permits/well-records-search) | HTTP 200. Links to a current Experience viewer. | Prefer the REST route. A direct backing-service relationship is not established. |
| [Current viewer catalogue](https://www.arcgis.com/sharing/rest/content/items/3c355ac677984daf99c1453bb6477831?f=pjson) | HTTP 200. Item is accessible; licence information is empty. The older viewer item named in the issue returns an ArcGIS error despite HTTP 200. | Viewer bulk terms remain unverified. No HTML scraping or viewer automation. |
| [Current statistics page](https://www.in.gov/dnr/oil-and-gas/oil-and-gas-activity/oil-and-gas-statistics) | HTTP 200; links production charts. The older statistics address in the issue returns HTTP 404. | Production is outside this inventory; charts cannot establish well-level production. |
| [Annual Production Report, State Form 56442](https://forms.in.gov/Download.aspx?id=13638) | HTTP 200 PDF. Part II names a lease or production unit, lists permits and reports monthly oil and gas totals. | Confirms lease-level reporting; the form does not supply production per well. |

The service metadata above publishes `maxRecordCount = 2000` for the selected
tables. This is a page-size ceiling, not a request-rate allowance. Read current
metadata before configuring a collection. The implementation takes page size,
request budgets, pacing and retry limits as inputs; it adds no guessed rate.

## Method and output

The package is `worldenergydata.modules.state_regulators.indiana_dnr`, alongside
the existing state-regulator ingests. It reuses `state_regulators.fetch` for
terms checks, header-aware delays, throttling, persisted budgets and digest-checked
content caching.

1. Collect official well, completion and image tables in object-id order, using
   `objectid > last_seen` after the first page. Inspect each table's schema and
   page ceiling before querying. A required query-page budget bounds the run.
   Deterministic URLs let an interrupted run reuse completed pages. A new data
   vintage requires a separate cache directory. Collection is sequential, not
   a transactional snapshot; capture start/end times and page provenance remain
   attached. ArcGIS errors, nonprogressing pages and unexpected schemas fail
   explicitly rather than yielding an empty inventory.
2. Normalise names to uppercase; make `&` and `AND` equivalent; remove punctuation
   and repeated whitespace; remove trailing legal suffixes. Compare exact stems,
   without substring or fuzzy matching. This follows the matching policy recorded
   in issue #1129's research dated 2026-10-12. Report every original spelling.
   A matching stem is a candidate grouping, not proof of legal entity identity.
3. Join completions on the survey IGS key and image references on the numeric
   permit key, following the relationships published by the well layer. Leading
   zeroes are ignored only for joining; original identifiers stay in output.
   Duplicate identities and conflicting crosswalk permit keys are rejected.
4. Optionally join a manual `supplements` list by IGS identifier **and** permit
   number. Each entry must include a nonempty `source_record` object. Supplemental
   API numbers remain supplied strings, without format conversion or fabrication.
   Supplement provenance is retained separately from regulator provenance.

Every well carries `api_number`, `permit_no`, `operator_of_record`, `lease_name`,
`county`, `location`, `well_status`, `total_depth`, `completion_zones`,
`formation_tops`, `spud_date`, `completion_dates` and `source_record`. Raw completion
attributes remain under `completions`; depth entries preserve driller/logger
values per completion with unknown units. Dates are source strings, not silently
parsed or converted. Geometry retains its declared spatial reference; UTM and
township/range attributes are also retained without coordinate conversion.

`operator_of_record` is the service's operator field, not an independently
verified current permittee or a contract operator. `contract_operator` is null
unless explicitly supplied with evidence. Current-status codes, scan status and
Class II values are preserved without interpreting them as idle status, liability
or a plugging obligation. Such conclusions remain `NOT_EVALUATED`.

Missing scalar attributes are null; missing collections are empty. Per-well
`not_evaluated` lists identify unsupported attributes. Coverage distinguishes
missing tables, missing API numbers, completion coverage and image references.
Counts describe the supplied snapshot only; they do not establish statewide
completeness, freshness or the number of imaged-only documents. Image catalogue
presence indicates potential records to inspect, not their contents.

Indiana production is reported per lease or production unit in State Form 56442,
Part II, linked above.
No production figures are ingested, and no well-level production claim is
supported. `production_granularity` remains `NOT_EVALUATED` because no filings
are included; statewide charts cannot be assigned to wells.

## Worked example: inputs, method and answer

Input: [synthetic snapshot](../../../examples/indiana_dnr/synthetic_snapshot.json).
All entities, API-like identifiers, depths, dates, geometry and records in this
file are invented test data, not public well observations.

```bash
PYTHONPATH=src python -m worldenergydata.modules.state_regulators.indiana_dnr \
  --snapshot examples/indiana_dnr/synthetic_snapshot.json \
  --operator 'S&S' --output "$TMPDIR/indiana-inventory.json"
```

The three input wells belong to `S & S LLC`, `S and S, Inc.` and `OTHER LLC`.
Normalisation gives `S AND S`, `S AND S` and `OTHER`. The answer therefore contains
two wells, preserving their original operator names and permits `0007` and
`0008`. One has a sourced synthetic API crosswalk and a completion, and the
other has neither. Both image references join to the first permit. The driller
depth `1200` is copied from its completion with units unknown. No depth equation,
engineering coefficient or acceptance threshold is used.

Expected coverage, independently counted from the input:

| Quantity | Expected count |
| --- | --- |
| Input wells | 3 |
| Matched wells | 2 |
| With API number | 1 |
| Without API number | 1 |
| With completions | 1 |
| With image catalogue | 1 |

## Collection configuration and dry run

Run `python -m worldenergydata.modules.state_regulators.indiana_dnr.collection
--config CONFIG --output OUTPUT --dry-run` to plan without network requests.
The JSON configuration supplies `row_counts` with keys `wells`, `completions`,
`images`, plus `page_size` and the source's `max_record_count`.

The baseline query count per table is `floor(row_count / page_size) + 1`,
including a possible empty terminal probe. Add a metadata request per table.
This is a counting identity, not an engineering equation; shorter pages,
changed counts and retries can increase the requests. Query semantics follow
the [ArcGIS REST query reference](https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/),
opened 2026-10-20.

Actual collection uses the same command without `--dry-run`. It also requires
`max_query_pages`, a `fetch` object matching the shared `FetchConfig` fields
(including an explicit cache directory and identifying User-Agent), and a
`terms` list of `TermsCheck` records: `origin`, `terms_url`, `checked_at` in UTC,
and explicit `bulk_allowed`. Do not assert permission merely because the
service responds. Current source observations do not establish bulk permission.
Keep configurations, caches and extracts outside version control. The resulting
snapshot is the offline inventory command's input.

## Validation and remaining work

Tests use the synthetic worked example and independent request counting. They
exercise name variants, unmatched names, identifier preservation, multiple
completions, missing fields, ambiguous or malformed crosswalks, catalogue joins,
the CLI, page ordering, caps, interruption/resume and the shared terms gate.

The three implemented slices are offline inventory, guarded acquisition, and
coverage/provenance plus the worked example. Later data-dependent work requires
verified source permission, a permitted API crosswalk and PDMS formation/top
evidence. Status-code interpretation, depth units, image interpretation and
production ingestion remain unevaluated; none is silently inferred.
