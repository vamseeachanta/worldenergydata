# BSEE Source Catalog — Closed-Thread Knowledge → Code

This page maps the BSEE data-ingest domain knowledge accumulated in
closed issues #9, #11, #12, and #49 to its current, tested home in
code. It exists so the knowledge survives as adapters and tests rather
than as issue prose. Part of epic #423; the runtime fixes address #267.

## Where the knowledge lives now

| Closed-thread knowledge | Source thread | Code home |
|---|---|---|
| `https://www.data.bsee.gov/Main/RawData.aspx` is the authoritative index of all bulk zip downloads | #9, #12 | `config/bsee.yml` (`portal.raw_data_index`); full per-dataset registry in `src/worldenergydata/bsee/data/refresh/url_registry.py` |
| Scheduler dataset catalog (URLs, primary tables, timeouts) externalized as reviewable config | #9 | `config/bsee.yml` (`scheduler_datasets`), loaded by `src/worldenergydata/scheduler/jobs/bsee_refresh.py:load_dataset_catalog` with built-in fallback |
| Scraping-method hierarchy: plain request/POST first, Selenium background, Selenium foreground last | #11 | Bulk path uses plain requests only (`src/worldenergydata/bsee/data/scrapers/bsee_web.py`); hierarchy documented in `config/bsee.yml` and `payload.py` module docstring |
| Downloaded data goes stale easily; prefer re-download over cached archives (refresh cadence) | #9 | Scheduler `bsee_refresh` weekly job (`config/scheduler/scheduler_config.yml`); BSEE regenerates files daily ~09:45 UTC (live-verified 2026-06-10) |
| Read zips live from URL into memory without temp extraction (for files ~10 MB) | #12 | `BSEEWebScraper.download_zip_to_memory` + `worldenergydata.bsee.data.refresh.payload.extract_primary_table` |
| Platform-structure / pipeline-segment / lease-area datasets enumerated | #12 | `url_registry.py` (`platstruc`, `pipeloc`, `lab` = LeaseAreaBlock, `serialreg`, `leaseowner`, ...); scheduler subset in `config/bsee.yml` |
| Well/borehole by-API12 query workflow (download → load → query; online query preferred) | #9 | `src/worldenergydata/bsee/analysis/well_api12.py` and `bsee/data/sources/` (pre-existing; not reworked here) |

## Runtime contract gotchas (issue #267, live-verified 2026-06-10)

These are encoded as code + tests in
`src/worldenergydata/bsee/data/refresh/payload.py` and
`tests/unit/bsee/test_bsee_payload.py` /
`tests/unit/scheduler/test_bsee_adapter.py`:

1. **Stale URLs return HTTP 200 + HTML, not 404.** When BSEE moves a
   file, the old URL serves a ~28 KB HTML page with status 200.
   `classify_payload()` checks zip magic / HTML markers before any
   `zipfile` call, and the refresh job classifies the failure
   `deterministic` (issue #460) instead of crashing with
   `BadZipFile`.
2. **Two URLs had moved** (the #267 root cause):
   - `deepwater_structure`: `/Platform/Files/PermStrucRawData.zip` →
     `/Other/Files/PermStrucRawData.zip`
   - `pipeline_location`: `PipeLocAllRawData.zip` →
     `PipeLocRawData.zip`
   Drift guards: one test asserts `config/bsee.yml`,
   `BSEEWebScraper.URLS`, and `url_registry.py` agree on every
   scheduler dataset URL; a second scans the whole `bsee` + `scheduler`
   source trees (and `config/bsee.yml`) so the two known-stale URL
   strings cannot be reintroduced anywhere in live code (docs/tests
   may still mention them as history).
3. **Archives contain no `.csv`.** Each zip holds a leading directory
   entry plus quoted-CSV **`.txt`** members with CRLF endings (e.g.
   `PlatStrucRawData/mv_platstruc_structures.txt`). Extraction skips
   directory entries and selects the primary member by configured
   glob, **fail-closed**: when patterns are configured and none match
   (member rename / pattern typo), extraction raises instead of
   silently writing the largest member. The largest-member fallback
   applies only when no patterns are configured. Latin-1 bytes in
   operator names are tolerated.
4. **Healthy responses** use `Content-Type:
   application/x-zip-compressed` and carry `Last-Modified` (files are
   regenerated daily). The optional live smoke test
   (`BSEE_LIVE_SMOKE=1`) HEAD-checks every catalog URL.

## Failure classification (issue #460 interface)

`DatasetFailure` carries `FailureClass.DETERMINISTIC` (stale-URL HTML,
empty body, archive without data members, unmatched member patterns,
zero-row parse) vs `FailureClass.TRANSIENT` (timeouts, connection
errors, corrupt payload, unrecognized non-HTML bodies). The retry
contract is wired structurally, not by string convention:

- Transient per-dataset failures are retried in-job (bounded,
  `TRANSIENT_DATASET_ATTEMPTS = 2`).
- `JobResult.retryable` (default `True`) tells
  `RetryManager.run_with_retry()` whether re-running the job can help;
  the manager returns immediately -- no backoff sleep -- on a
  non-retryable result (covered by scheduler-level tests).
- All datasets failing deterministically → `status="failure"`,
  `retryable=False`, `error_msg` prefixed `[deterministic]` (the
  prefix is kept for operators/logs; the scheduler acts on the field).
- Partial refresh with only deterministic failures → `status="success"`
  with an explicit `[partial:deterministic]` message (retry cannot fix
  a stale URL; written datasets count).
- Partial refresh with any transient failure remaining →
  `status="failure"`, `retryable=True`, so the scheduler retry layer
  re-runs the job rather than masking a stale dataset as success.

## Deliberately out of scope

- **#49 KeyError `'Total Depth Date'`** lives in the analysis path
  (`src/worldenergydata/bsee/analysis/well_api12.py:511`,
  `get_api12_analysis`), not the refresh path reworked here. Left for
  a dedicated rework of the directional-survey/well-path module.
- Writing *all* archive members (not just the primary table) to
  Parquet, and lease-area (`lab`) / serial-register datasets in the
  scheduler job — the catalog structure supports adding them as new
  `scheduler_datasets` entries.

## BOEM FieldReserves program (#847)

| Dataset | Upstream | Code home |
|---|---|---|
| `fieldreserves_tables` | `https://www.data.boem.gov/FieldReserves/Files/2023%20Tables%20xlsx%20Public.zip` (annual, vintage-pinned — bump per `data/modules/offshore_assets/curated/LT_RESERVES_DISCOVERY.md`) | `url_registry.py` → `scripts/refresh_bsee_all.py` (.xlsx members → one bin per sheet) |
| `fieldreserves_master` | `https://www.data.boem.gov/FieldReserves/Files/mastdatadelimit.zip` (Field Name Master List: area/block/`FIELD_NAME_CODE`/lease; headerless delimited) | `url_registry.py` → `scripts/refresh_bsee_all.py` |
| `deepqual` (cadence upgrade) | `https://www.data.bsee.gov/Other/Files/DeepQualRawData.zip` | now also on the weekly scheduler (`config/bsee.yml`), consumed by `FieldNameResolver` + `build_lt_reserves_discovery.py` |

Curated consumer: `data/modules/offshore_assets/curated/lt_reserves_discovery.csv` (+ discrepancies CSV). Future family sources: #855.
