# Colorado ECMC Pressure-Source Discovery

Issue: [#749](https://github.com/vamseeachanta/worldenergydata/issues/749)

Follow-up ingest issue:
[#751](https://github.com/vamseeachanta/worldenergydata/issues/751)

Survey and live-scout date: 2026-07-04.

## Decision

The official ECMC FacilityDetail endpoint is a viable source for a
production-grade Form 5A / Initial Test Data pressure ingest, but it remains a
candidate-only Colorado pressure source for the underpressured screen.

The approved [#749](https://github.com/vamseeachanta/worldenergydata/issues/749)
scout proved that the public FacilityDetail HTML contains structured initial
test rows with `CASING_PRESS` and `TUBING_PRESS`. It intentionally used a
single configured API sample and did not attempt statewide iteration. A
production ingest lane under
[#751](https://github.com/vamseeachanta/worldenergydata/issues/751) now covers
source-list construction, throttling, retry/resume, coverage accounting,
multi-block parsing, identity checks, and candidate-only pressure
interpretation.

Colorado Form 5A rows therefore remain excluded from underpressured-screen
participation gates until a later reviewed rule maps a pressure kind to
`WHP_shut_in`.

## Official Source Matrix

| Source | Official URL | Role | Refresh / access | Pressure relevance |
|---|---|---|---|---|
| ECMC download catalog | https://ecmc.state.co.us/appAssets/data/downloadsExt.txt | `approved_spine` | Public catalog; direct JSON/text asset | Lists official bulk datasets and landing pages |
| ECMC data page | https://ecmc.state.co.us/data2.html | `context_only` | Public app; newer state landing page may reject non-browser access | Navigation source only |
| Production data dictionary | https://ecmc.state.co.us/documents/data/downloads/production/production_record_data_dictionary.htm | `approved_spine` | Public HTML | Defines Form 7 pressure columns used by [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) |
| Form 7 production CSVs | https://ecmc.state.co.us/documents/data/downloads/production/{YYYY}_prod_reports.csv and `monthly_prod.csv` | `approved_spine` | Annual static + monthly rolling | Carries pressure columns, but [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) live slice had zero positive pressure values |
| Wells GIS | https://ecmc.state.co.us/documents/data/downloads/gis/WELLS_SHP.ZIP | `approved_spine` | Daily static HTTPS ZIP | API, facility, field, location, MD/TVD join spine |
| Facilities GIS | https://ecmc.state.co.us/documents/data/downloads/gis/Facilities.ZIP | `context_only` | Daily static HTTPS ZIP; 169,504,664 bytes on 2026-07-04 check | Candidate facility/well crosswalk and scout seed source |
| FacilityDetail | https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api=12339345 | `candidate_pressure_observation` | Public live COGIS page by county+sequence API fragment | Exposes Form 5A-like Initial Test Data including `CASING_PRESS` and `TUBING_PRESS` |
| COA page | https://ecmc.state.co.us/cogisdb/Resources/COAs?facid=12339345 | `context_only` | Public live COGIS page by facility id | Mentions Form 5A/Form 17 obligations; not a pressure-observation table |
| Imaged document search | https://ecmc.state.co.us/cogisdb/ImagedDocToolMenu | `requires_data_request` / manual fallback | Public document-search landing page | Form attachments and Laserfiche route; not preferred for automated source of record |
| MIT/Form 21 | https://ecmc.state.co.us/documents/data/downloads/Engineering/MechIntegrityDownload.html | `excluded_integrity_pressure` | Monthly bulk MIT ZIP | Engineering integrity pressure, not reservoir or production-test pressure |
| Field inspections | https://ecmc.state.co.us/documents/data/downloads/Field/FieldDownload.html | `context_only` | Monthly bulk field-inspection export | Compliance/operations context only |
| ECMC download guide | https://ecmc.state.co.us/documents/data/downloads/ECMC_Download_Guidance_v2_ada.pdf | `context_only` | Public PDF | Confirms SQL-backed form data/attachments exist and supports data-request framing |

## Live Scout Evidence

The approved scout used:

```text
config/colorado_ecmc_source_discovery.yml
```

and wrote:

```text
/mnt/ace/worldenergydata/data/modules/colorado_ecmc/source_discovery/
  raw/facility_detail/12339345.html
  raw/facility_detail/manifest.json
  parsed/facility_detail_initial_tests.parquet
  parsed/facility_detail_initial_tests.json
  reports/colorado_ecmc_pressure_source_discovery.json
```

Live result:

| Metric | Value |
|---|---:|
| FacilityDetail request count | 1 |
| API fragment | `12339345` |
| HTTP status | 200 |
| Raw HTML size | 50,740 bytes |
| Parsed initial-test rows | 11 |
| Candidate pressure rows | 2 |
| Candidate pressure kinds | `WHP_casing_initial_test`, `WHP_flowing_tubing_initial_test` |
| Report decision | `facility_detail_candidate_for_follow_up` |
| Screen status | `source_discovery_not_screen_ready` |

The sampled page is for API `05-123-39345`, facility `436953`, Wattenberg
field, NIOBRARA formation (`NBRR`). The parsed initial-test pressure rows are:

| Test type | Measure | Candidate kind |
|---|---:|---|
| `CASING_PRESS` | 1700 | `WHP_casing_initial_test` |
| `TUBING_PRESS` | 1300 | `WHP_flowing_tubing_initial_test` |

Other initial-test rows (`BBLS_H2O`, `BBLS_OIL`, `BTU_GAS`, `MCF_GAS`,
calculated rates, and gravity) are retained as rates/properties, not pressure
observations.

## Interpretation Boundary

The discovery parser classifies pressure-like values before any screen use:

| Lane | Classification | Screen use |
|---|---|---|
| FacilityDetail Initial Test Data `CASING_PRESS` | Candidate pressure observation | Candidate-only in [#751](https://github.com/vamseeachanta/worldenergydata/issues/751); not screen-promotable until a later shut-in interpretation rule |
| FacilityDetail Initial Test Data `TUBING_PRESS` | Candidate pressure observation | Candidate-only in [#751](https://github.com/vamseeachanta/worldenergydata/issues/751); flowing-pressure evidence is not screen-promotable |
| FacilityDetail treatment pressure | Excluded engineering pressure | Never screen evidence without a later explicit contract change |
| MIT/Form 21 pressures | Excluded integrity pressure | Never screen evidence without a later explicit contract change |
| Form 17/bradenhead pressures | Excluded annulus/compliance pressure | Never screen evidence without a later explicit contract change |
| Form 7 production pressure columns | Implemented spine source | Empty in [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) 2025+monthly live slice |

## Production Ingest Lane (#751)

The production lane is configured by:

```text
config/colorado_ecmc_facility_detail_ingest.yml
```

The default configuration is capped (`max_requests: 5`) and writes heavy
outputs under:

```text
/mnt/ace/worldenergydata/data/modules/colorado_ecmc/facility_detail_ingest/
  source_lists/
  raw/facility_detail/html/
  raw/facility_detail/status/
  parsed/
  curated/pressure/
  reports/
```

Refresh cadence:

- WELLS source list spine: daily official GIS ZIP.
- FacilityDetail/Form 5A pages: live COGIS pages; use a polite, capped,
  resumable crawl, not a blind daily statewide refresh.
- Form 7 production pressure columns: monthly/annual bulk lane from
  [#745](https://github.com/vamseeachanta/worldenergydata/issues/745), not the
  Form 5A source of record.

The curated Form 5A table preserves reported psig and converted psia, selected
reference depth, raw HTML lineage, and `era=completion_initial_test`.
`TUBING_PRESS` is tagged `flowing_tubing_initial_test`; `CASING_PRESS` is
tagged `initial_test_casing_pressure_unverified`. Both are candidate-only and
not screen-promotable in [#751](https://github.com/vamseeachanta/worldenergydata/issues/751).

Default capped run evidence from 2026-07-04:

| Metric | Value |
|---|---:|
| Source WELLS rows | 124,332 |
| FacilityDetail request rows | 5 |
| Fetched pages | 5 |
| Parsed initial-test rows | 49 |
| Usable candidate pressure rows | 11 |
| Screen-promotable rows | 0 |
| Promotion status | `candidate_only` |

Runtime note: local Miniforge `python3` environments may lack parquet support.
Use `/usr/bin/python3` or the repo CI environment for commands that write
parquet outputs.

## Follow-Up Requirements

Any future statewide run or screen activation should keep these controls:

- use an approved source list from the wells/facilities spine;
- carry a hard throttle and retry/backoff policy;
- write raw HTML and manifests under `/mnt/ace`;
- support resume after interruption;
- count coverage by API/facility and parse status;
- fail closed on parser drift;
- keep MIT/Form 21, treatment pressure, and Form 17/bradenhead lanes excluded;
- update the underpressured-screen contract only after pressure kind, gauge
  handling, depth reference, field join, and quality sidecars are reviewed.
