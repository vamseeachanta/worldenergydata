# Plan: Issue #806 - Spain CORES live XLSX download lane

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/806
**Status:** completed
**Tier:** T2 (live official-source download, cache/provenance, existing parser seam)
**Client:** N/A
**Project:** worldenergydata Spain onshore/offshore production lifecycle
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will use a single-lane TDD workflow because this slice will touch
the Spain package, its committed fixture/provenance, and unified production
adapter tests. Source probes and review can run independently, but file edits
will remain serialized to avoid contaminating the just-merged Spain reference
chain.

Implementation will not begin until this plan is reviewed, pushed, moved to
`status:plan-review`, and explicitly approved by the user as
`status:plan-approved`.

### Issue and dependency status

| Issue | State | Current role |
|---|---|---|
| [#763](https://github.com/vamseeachanta/worldenergydata/issues/763) | closed, `status:done` | Spain CORES parser, fixture, adapter, and reference chain |
| [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) | open, unapproved | This live CORES XLSX download and refresh lane |
| [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) | open | Per-field crude density/API conversion refinement |
| [#808](https://github.com/vamseeachanta/worldenergydata/issues/808) | open | Gas revenue modeling |
| [#809](https://github.com/vamseeachanta/worldenergydata/issues/809) | open | Scheduled Spain CORES refresh job |
| [#810](https://github.com/vamseeachanta/worldenergydata/issues/810) | open | Spain CORES field-development HTML report |

[#806](https://github.com/vamseeachanta/worldenergydata/issues/806) will be the
next slice because [#809](https://github.com/vamseeachanta/worldenergydata/issues/809)
needs a reliable downloader/cache contract, while [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
and [#808](https://github.com/vamseeachanta/worldenergydata/issues/808) need the
live all-field product frames.

### Source contract

Implementation will use CORES as the direct source, not third-party mirrors.

| Dataset | Official source URL | CORES page start year | CORES page update | HEAD contract |
|---|---|---:|---|---|
| Indigenous Crude Oil Production | `https://www.cores.es/sites/default/files/archivos/estadisticas/crude-oil-production.xlsx` | 1966 | 12/06/2026 | HTTP 200, Excel content type, `Last-Modified: Fri, 12 Jun 2026 07:51:41 GMT` |
| Indigenous Natural Gas Production | `https://www.cores.es/sites/default/files/archivos/estadisticas/gas-production.xlsx` | 1963 | 12/06/2026 | HTTP 200, Excel content type, `Last-Modified: Fri, 12 Jun 2026 07:52:01 GMT` |

The implementation will keep the CORES statistics page as the discovery page:

```text
https://www.cores.es/en/estadisticas
```

The downloader will use the stable workbook URLs above as the first contract,
and it will parse the statistics page as a validation/discovery step so link
drift is reported explicitly instead of silently using stale URLs.

### Existing code state

The merged Spain package already provides the parser seam this issue will reuse:

- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py`
  defines `parse_cores_frame`, `CoresProductionLoader`,
  `CoresFixtureProductionLoader`, `TONNES_TO_BBL`, and `GWH_TO_MCF`.
- The parser already handles CORES wide/monthly workbooks with
  `Year | Month | <field columns> | Grand total`, drops annual `Total` rows and
  no-year rows, and converts oil tonnes to bbl and gas GWh to Mcf.
- Real CORES workbooks include a non-data `Start` sheet before the data-bearing
  `Production` sheet, so live workbook reads must select
  `sheet_name="Production"` rather than relying on pandas' default first-sheet
  behavior.
- The committed fixture loader currently reads
  `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/ayoluengo_oil_sample.csv`
  plus `_metadata.json`.
- `SpainCoresAdapter` already supports product-specific loader methods:
  `load_oil_production()` and `load_gas_production()`, merging them on
  `(field_name, year, month)`.

### Boundary decisions

- Full live workbook and normalized all-field output will be written under a
  caller-supplied `/mnt/ace` cache root during execution, not hardcoded in
  library code.
- Repo-tracked fixture output will stay small: the implementation will refresh
  the Ayoluengo oil fixture and metadata for adapter conformance, while full
  live oil/gas normalized frames will remain in `/mnt/ace`.
- The downloader will use standard-library HTTP by default unless the repo
  already exposes a shared downloader helper that fits this package boundary.
- Scheduler wiring will stay deferred to [#809](https://github.com/vamseeachanta/worldenergydata/issues/809).
- Per-field oil density/API overrides will stay deferred to [#807](https://github.com/vamseeachanta/worldenergydata/issues/807);
  this issue will preserve the documented default conversion factor.
- Gas revenue will stay deferred to [#808](https://github.com/vamseeachanta/worldenergydata/issues/808);
  this issue will still normalize gas GWh to `gas_mcf`.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review artifact | `scripts/review/results/2026-07-04-plan-806-codex-inline.md` |
| Live source/downloader module | `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py` |
| Parser facade updates, if needed | `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py` |
| Package README update | `packages/worldenergydata-spain/README.md` |
| Committed fixture metadata/sample refresh | `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/` |
| Unit tests | `tests/unit/spain/test_cores_live.py` |
| Adapter integration tests | `tests/unit/production/unified/test_spain_cores_adapter_loader.py` |

Planned execution output under `/mnt/ace`:

```text
/mnt/ace/worldenergydata/data/spain/cores/
  raw/
    crude-oil-production.xlsx
    gas-production.xlsx
  normalized/
    cores_oil_production.csv
    cores_gas_production.csv
    cores_all_production.csv
  metadata/
    cores_refresh_metadata.json
```

The implementation will accept the cache root as an argument or environment
setting so tests can use `tmp_path` and repo code will not need hardcoded
absolute paths.

## Deliverable

The implementation will add a live Spain CORES refresh lane that can:

1. Discover and validate official CORES workbook URLs from the statistics page.
2. Download oil and gas XLSX workbooks with atomic writes and SHA-256 metadata.
3. Reuse the existing `CoresProductionLoader` parser for both workbooks.
4. Read the CORES `Production` worksheet explicitly for both live workbooks.
5. Write full normalized oil/gas/all-product frames to `/mnt/ace`.
6. Refresh the committed Ayoluengo oil fixture and `_metadata.json`.
7. Expose a live loader facade with `load_oil_production()`,
   `load_gas_production()`, `load_all_production()`, and
   `load_field_production(field_name)`.
8. Keep `SpainCoresAdapter` compatible with both the existing fixture loader and
   the new live loader facade.

## Pseudocode

```python
source = CoresWorkbookSource(cache_root=ace_root / "spain" / "cores")
inventory = source.discover()
paths = source.download_all(force_refresh=False)

loader = CoresLiveProductionLoader(cache_root=source.cache_root)
oil = loader.load_oil_production()
gas = loader.load_gas_production()
all_rows = loader.load_all_production()

fixture = refresh_ayoluengo_fixture(
    oil_frame=oil,
    metadata=source.metadata(),
    output_dir=package_data_dir,
)

adapter = SpainCoresAdapter(loader=loader)
unified = adapter.fetch(ProductionQuery(regions=["spain"], fields=["Ayoluengo"]))
```

## Files to Change

- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py`
- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py`
- `packages/worldenergydata-spain/src/worldenergydata/spain/production/__init__.py`
- `packages/worldenergydata-spain/README.md`
- `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/_metadata.json`
- `packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/ayoluengo_oil_sample.csv`
- `tests/unit/spain/test_cores_live.py`
- `tests/unit/spain/test_cores_loader.py`
- `tests/unit/production/unified/test_spain_cores_adapter_loader.py`

## TDD Test List

- Source discovery:
  - a fixture copy of the CORES statistics page will resolve crude and gas XLSX
    links by dataset name and/or known URL suffix;
  - missing crude or gas links will fail closed with a clear exception;
  - workbook HEAD responses will validate Excel content type and capture
    `Last-Modified`.
- Download/cache:
  - downloads will write to a temporary file then atomically replace the cached
    workbook;
  - cached files will not be re-downloaded unless `force_refresh=True`;
  - SHA-256, byte count, source URL, and response headers will be recorded in
    metadata.
- Parse/normalize:
  - tiny oil/gas XLSX fixtures will be parsed through `CoresProductionLoader`,
    not by a duplicate parser;
  - workbook fixtures with `Start` and `Production` sheets will prove the live
    reader selects the `Production` sheet;
  - oil and gas product frames will keep separate `oil_bbl`/`gas_mcf` columns;
  - `load_all_production()` will outer-merge product frames on
    `(field_name, year, month)`.
- Fixture refresh:
  - Ayoluengo rows will be selected from live oil output and written in stable
    order;
  - `_metadata.json` will include source URLs, statistics page, CORES update
    date, HTTP last-modified, refreshed timestamp, SHA-256, row counts, and
    conversion factors.
- Adapter compatibility:
  - `SpainCoresAdapter(loader=CoresLiveProductionLoader(...))` will emit
    `STANDARD_COLUMNS` and support field filters;
  - the existing fixture-backed default adapter tests will continue to pass.

## Acceptance Criteria

- The live downloader will fetch both official CORES XLSX workbooks from direct
  source URLs and write raw artifacts under `/mnt/ace`.
- Full normalized oil, gas, and merged production CSVs will be written under
  `/mnt/ace/worldenergydata/data/spain/cores/normalized/`.
- The committed Ayoluengo fixture and metadata will be refreshable from live
  source data.
- Metadata will carry source URL, statistics page, update date, last-modified,
  SHA-256, row counts, refresh timestamp, and conversion constants.
- No library code will hardcode `/mnt/ace`; the cache root will be supplied by
  caller/config/environment.
- Focused tests will pass:
  `tests/unit/spain/test_cores_live.py`,
  `tests/unit/spain/test_cores_loader.py`, and
  `tests/unit/production/unified/test_spain_cores_adapter_loader.py`.
- Adjacent unified production checks will remain green.
- `scripts/legal/legal-sanity-scan.sh --diff-only` will pass.

## Risks

| Risk | Mitigation |
|---|---|
| CORES page link drift | Discover by dataset label and known suffix; fail closed if crude/gas links cannot be validated. |
| Workbook layout drift | Select the `Production` sheet explicitly, reuse the existing parser, and add a live-workbook smoke check that reports missing Year/Month/field columns clearly. |
| Large generated data in repo | Keep full live output under `/mnt/ace`; commit only small conformance fixture and metadata. |
| Misleading conversion precision | Preserve documented default constants and metadata; defer per-field density/API corrections to [#807](https://github.com/vamseeachanta/worldenergydata/issues/807). |
| Network flakiness | Use cache reuse by default, force-refresh opt-in, atomic writes, and metadata status. |

## Review Plan

Plan-stage review will use an adversarial Codex inline pass focused on:

- direct-source reliability and link-drift handling;
- avoiding a duplicate parser;
- `/mnt/ace` cache behavior without hardcoded absolute paths in library code;
- fixture refresh scope versus full generated data scope;
- scheduler boundary with [#809](https://github.com/vamseeachanta/worldenergydata/issues/809).

Implementation will require a separate code/artifact review before closeout.
