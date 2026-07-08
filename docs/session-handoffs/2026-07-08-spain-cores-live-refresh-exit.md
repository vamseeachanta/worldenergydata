# Spain CORES Live Refresh Exit Handoff - 2026-07-08

## Active Task

Continue the worldenergydata onshore/international field-development work after the Spain CORES scheduler and density-output closeout. The requested checkpoint was to run the live Spain CORES refresh against the direct source and write operational output under:

`/mnt/ace/worldenergydata/data/spain/cores`

## Current State

- Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) is closed with `status:done`.
- PR [#896](https://github.com/vamseeachanta/worldenergydata/pull/896) merged at `a289a38c010b671c2d09d829c8082811dc58911d`.
- Issue [#809](https://github.com/vamseeachanta/worldenergydata/issues/809) remains closed with `status:done`; the live-refresh checkpoint is documented in [this post-close comment](https://github.com/vamseeachanta/worldenergydata/issues/809#issuecomment-4909504159).
- Checkout used for this handoff: `/mnt/local-analysis/wt-wed-807-source-gaps`.
- Handoff branch: `docs/spain-cores-live-refresh-exit`.

## Completed This Session

1. Closed the final [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) density-output follow-up:
   - Missing density source coverage now emits `oil_tonnes_to_bbl_blocked_by_missing_density_source: Albatros`.
   - Default-density output now emits `oil_tonnes_to_bbl_assumes_default_factor: Albatros=7.33`.
   - Mixed missing/defaulted audits preserve both blocker and assumption markers.
   - Non-finite default factors are rejected before rendering.

2. Ran the direct-source Spain CORES live refresh checkpoint:
   - Strict density mode reached the direct source path and failed closed with `CORES refresh failed: missing density factors for: Albatros`.
   - Operational mode with explicit `allow_default_density=true` succeeded and wrote `/mnt/ace/worldenergydata/data/spain/cores`.

3. Verified refreshed `/mnt/ace` outputs:
   - `_metadata.json`: `source_url=https://www.cores.es/en/estadisticas`, `format=csv`, `record_count=4375`, `last_refresh=2026-07-07T22:09:55.022578+00:00`.
   - `manifest.json`: `job_name=spain_cores_refresh`, `status=success`, `records_updated=4375`, `last_success_ts=2026-07-07T22:09:55.022812+00:00`.
   - `metadata/cores_refresh_metadata.json`: direct workbook URLs, HTTP `200`, SHA-256 hashes, byte counts, last-modified values.
   - `normalized/cores_all_production.csv`: 4,375 rows, 20 fields.
   - `normalized/cores_oil_production.csv`: 2,865 rows, 12 fields.
   - `normalized/cores_gas_production.csv`: 1,520 rows, 9 fields.
   - `normalized/cores_oil_density_factors.json`: `coverage_status=defaulted`, `defaulted_fields=["Albatros"]`, `default_bbl_per_tonne=7.33`.

4. Ran downstream smoke:
   - `scripts/spain/build_cores_field_development_report.py --cache-root /mnt/ace/worldenergydata/data/spain/cores` succeeded.
   - Report consumed 20 fields, evaluated `Ayoluengo`, and surfaced:
     - `oil_tonnes_to_bbl_has_defaulted_fields: Albatros`
     - `oil_tonnes_to_bbl_assumes_default_factor: Albatros=7.33`

## Verification Evidence

- Local [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) verification before PR [#896](https://github.com/vamseeachanta/worldenergydata/pull/896):
  - `tests/unit/spain/test_cores_field_development_density.py`: 19 passed.
  - Adjacent Spain/scheduler subset: 96 passed.
  - Local PR-gate-equivalent selector targets: 578 passed, 2 skipped.
  - `black --check`, `isort --check-only`, `git diff --check`, legal scan, and Bandit passed.
  - GitHub checks all passed before merge.
- Live refresh verification:
  - Strict density run failed non-retryably on Albatros only.
  - Operational run succeeded with 4,375 records.
  - Field-development report smoke succeeded from the `/mnt/ace` cache.

## Open Work / Recommended Next Checkpoint

Recommended next action: use the refreshed `/mnt/ace` Spain CORES cache in the next production/field-development analysis slice rather than re-running [#809](https://github.com/vamseeachanta/worldenergydata/issues/809).

Likely candidates:

- [#831](https://github.com/vamseeachanta/worldenergydata/issues/831) is open and `status:plan-approved`; it refreshes field-benchmark artifacts and already calls out Spain as the only real region in the stale benchmark. Confirm lane ownership before taking it up because it is labeled `lane:claude`.
- [#808](https://github.com/vamseeachanta/worldenergydata/issues/808) remains open for Spain CORES gas revenue modeling, but it is not plan-approved in the observed state and should go through Issue -> Plan -> approval before implementation.
- [#713](https://github.com/vamseeachanta/worldenergydata/issues/713) remains the broader international source-to-field-development epic.

Do not redo [#809](https://github.com/vamseeachanta/worldenergydata/issues/809). The live refresh checkpoint is complete unless the next session needs a fresh timestamped rerun.

## Suggested Skills

- `superpowers:using-superpowers`
- `github:github` for issue/PR orientation
- `superpowers:test-driven-development` for any code change
- `superpowers:requesting-code-review` before merge
- `handoff` when preparing another session exit

## Cleanup / Residue

- In-repo runtime residue from tests and live verification was removed: `.venv`, `.pytest_cache`, `.test_performance.db`, and temporary `/tmp/spain-cores-live-report.*` files.
- The checkout was clean before this handoff file was added.
- Preserved pre-existing residue:
  - `stash@{0}: On main: wed stale pre-reorg dirty tree (recoverable) 2026-06-26`
  - local squash-source branch `feature/spain-807-albatros-output-assumption` with remote gone; safe delete refused after squash merge, so it was preserved.
  - `/mnt/local-analysis/.cleanup-trash/20260616-095709`
  - unrelated `/mnt/local-analysis` sibling worktrees.

