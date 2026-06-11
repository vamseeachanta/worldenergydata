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
   A drift-guard test asserts `config/bsee.yml`,
   `BSEEWebScraper.URLS`, and `url_registry.py` agree.
3. **Archives contain no `.csv`.** Each zip holds a leading directory
   entry plus quoted-CSV **`.txt`** members with CRLF endings (e.g.
   `PlatStrucRawData/mv_platstruc_structures.txt`). Extraction skips
   directory entries, selects the primary member by configured glob
   (fallback: largest member), and tolerates latin-1 bytes in operator
   names.
4. **Healthy responses** use `Content-Type:
   application/x-zip-compressed` and carry `Last-Modified` (files are
   regenerated daily). The optional live smoke test
   (`BSEE_LIVE_SMOKE=1`) HEAD-checks every catalog URL.

## Failure classification (issue #460 interface)

`DatasetFailure` carries `FailureClass.DETERMINISTIC` (stale-URL HTML,
empty body, archive without data members, zero-row parse) vs
`FailureClass.TRANSIENT` (timeouts, connection errors, corrupt
payload). When *all* datasets fail deterministically, the job's
`error_msg` is prefixed `[deterministic]` so the scheduler retry layer
can skip backoff.

## Deliberately out of scope

- **#49 KeyError `'Total Depth Date'`** lives in the analysis path
  (`src/worldenergydata/bsee/analysis/well_api12.py:511`,
  `get_api12_analysis`), not the refresh path reworked here. Left for
  a dedicated rework of the directional-survey/well-path module.
- Writing *all* archive members (not just the primary table) to
  Parquet, and lease-area (`lab`) / serial-register datasets in the
  scheduler job — the catalog structure supports adding them as new
  `scheduler_datasets` entries.
