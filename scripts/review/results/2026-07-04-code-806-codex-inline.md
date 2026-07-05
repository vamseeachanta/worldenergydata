# Code Review: Issue [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) Spain CORES live refresh

**Range:** `44f2141971c1c87ee0c71776eaedbfdd74bc28ba..d0fb7d9c0cfd2921086565ea9ad79f6331e58c28`
**Reviewer:** Codex inline/local fallback
**Date:** 2026-07-04
**Posture:** adversarial defect-hunting; default is non-APPROVE unless implementation evidence is sufficient.

## Reviewer Availability

Attempted independent Codex CLI review first:

- `codex exec review --base origin/main ...` ran for several minutes without writing an artifact and was terminated.
- `codex exec ...` with a custom adversarial prompt hit the known CLI stdin path (`Reading additional input from stdin...`) and was terminated.

This artifact records the main-session read-only adversarial review fallback. The implementation was already committed and pushed before this artifact was created.

## Scope Reviewed

Reviewed implementation against the approved [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) plan:

- official CORES statistics-page discovery and workbook URL validation;
- direct XLSX download and caller-supplied cache root behavior;
- atomic raw-cache writes and SHA-256/HTTP metadata;
- explicit `Production` worksheet parsing;
- normalized oil/gas/all CSV generation under `/mnt/ace` during execution;
- committed Ayoluengo metadata refresh;
- `SpainCoresAdapter` compatibility;
- tests, lint/format, legal scan, and line-count guardrail.

## Critical

None found.

## Important

None found.

## Minor

None blocking.

## Verification Notes

- Source discovery validates both workbook filenames from the official CORES statistics page in `CoresWorkbookSource.discover()` (`packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:86`).
- `download_all()` validates the statistics page by default before downloading/reusing files (`packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:100`).
- Raw workbook writes use temp-file replacement and record byte count, content type, Last-Modified, SHA-256, and source URL metadata (`packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:147`, `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:250`, `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:282`).
- The live loader selects the `Production` worksheet through `CoresProductionLoader(..., sheet_name="Production")` (`packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:93`, `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:150`).
- The live loader writes `cores_oil_production.csv`, `cores_gas_production.csv`, and `cores_all_production.csv` under the caller-supplied cache root, without a library hardcode of `/mnt/ace` (`packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:106`).
- Tests cover missing workbook-link fail-closed behavior, atomic write cleanup, metadata fields, explicit `Production` worksheet reads, fixture refresh metadata, and adapter compatibility (`tests/unit/spain/test_cores_live.py:24`, `tests/unit/spain/test_cores_live.py:45`, `tests/unit/spain/test_cores_live.py:58`, `tests/unit/spain/test_cores_live.py:119`, `tests/unit/spain/test_cores_live.py:164`, `tests/unit/production/unified/test_spain_cores_adapter_loader.py:172`).

## Residual Risks

- Scheduled refresh orchestration remains intentionally deferred to [#809](https://github.com/vamseeachanta/worldenergydata/issues/809).
- Per-field oil density/API conversion remains intentionally deferred to [#807](https://github.com/vamseeachanta/worldenergydata/issues/807).
- Full CI was not run locally; scoped Spain/adapter tests, lint/format, legal scan, direct live refresh, and `/mnt/ace` cache smoke checks passed.
- CORES may change workbook layout beyond the `Start`/`Production` sheet pattern; the parser will fail closed on missing Year/Month columns through existing `CoresParseError`.

## Verification Evidence

- RED: missing `worldenergydata.spain.production.cores_live` import failed as expected before implementation.
- RED: `CoresProductionLoader(..., sheet_name="Production")` failed as expected before implementation.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/worldenergydata-spain/src:packages/worldenergydata-production/src:packages/worldenergydata-fdas/src:packages/worldenergydata-core/src .venv/bin/python -m pytest tests/unit/spain tests/unit/production/unified/test_spain_cores_adapter_loader.py --noconftest -o addopts='' -q`  
  Result: `20 passed in 43.95s`.
- `.venv/bin/python -m ruff check ...`  
  Result: `All checks passed!`.
- `.venv/bin/python -m ruff format --check ...`  
  Result: `7 files already formatted`.
- `scripts/legal/legal-sanity-scan.sh --diff-only`  
  Result: `legal-sanity-scan: PASS`.
- Live direct-source refresh wrote:
  - `/mnt/ace/worldenergydata/data/spain/cores/raw/crude-oil-production.xlsx` (`112669` bytes)
  - `/mnt/ace/worldenergydata/data/spain/cores/raw/gas-production.xlsx` (`127915` bytes)
  - `/mnt/ace/worldenergydata/data/spain/cores/normalized/cores_oil_production.csv`
  - `/mnt/ace/worldenergydata/data/spain/cores/normalized/cores_gas_production.csv`
  - `/mnt/ace/worldenergydata/data/spain/cores/normalized/cores_all_production.csv`

## Ready-to-Merge Verdict

**Ready to merge:** Yes, with documented residual scope deferrals.

**Reasoning:** The implementation satisfies the approved [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) slice, uses direct official CORES sources, avoids hardcoded `/mnt/ace` in library code, persists `/mnt/ace` operational outputs, refreshes committed metadata, and passes scoped verification. No Critical or Important defects were found in the fallback adversarial review.
