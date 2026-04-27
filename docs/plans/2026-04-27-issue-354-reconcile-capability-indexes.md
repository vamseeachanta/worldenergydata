# Issue #354 Plan — Reconcile module manifest, indexes, catalog, and CLI info

> **Status:** plan-review — revised after adversarial MAJOR review
> **Complexity:** T3 documentation/governance cleanup
> **Date:** 2026-04-27
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/354
> **Related audit:** `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
> **Review artifacts:** `docs/reports/2026-04-27-plan-354-adversarial-review.md`, `docs/reports/2026-04-27-plan-354-355-rereview.md`

## Problem Statement

The repository has multiple competing capability contracts:

- `README.md` advertises only 3 headline modules (`bsee`, `marine-safety`, `fdas`).
- `MODULE_INDEX.md` and `module-manifest.yaml` advertise 27 modules, mostly as `stable`.
- `data/catalog.yaml` reports 12 modules / 44 datasets / ~10.5 MB, including empty datasets for `hse`, `oil_price`, `pipeline_safety`, and `wind`.
- `src/worldenergydata/` contains ~40 top-level packages/directories, including substantial off-manifest capabilities such as `cost`, `dashboard`, `decommissioning`, `drilling_pressure_management`, `economics`, `eia`, `reservoir`, `west_africa`, and others.
- `src/worldenergydata/cli/main.py` registers 15 sub-apps, but `info()` omits `dashboard`, `eia`, `ndbc`, and `forecast`.
- Scheduler claims disagree: `MODULE_INDEX.md` lists `texas_rrc` as scheduler-wired, while `config/scheduler/scheduler_config.yml` wires `lng_terminals_refresh` and does not wire `texas_rrc`/`mexico_cnh`.

This drift makes the repo hard for users and agents to reason about. Agents reading the manifest can over-trust sample/stub data; users reading README under-discover live features; scheduler/source-refresh work can target stale claims.

## Goals

1. Establish one explicit capability taxonomy across README, `MODULE_INDEX.md`, `module-manifest.yaml`, `data/catalog.yaml`, CLI `info()`, and scheduler notes.
2. Reconcile obvious stale claims without pretending every package is production-ready.
3. Make incomplete/stub/sample-only data visible and filterable.
4. Preserve backward-compatible discovery for existing users while making source-of-truth precedence explicit.
5. Add bounded verification that detects future drift without running data refreshes.

## Non-Goals / Boundaries

- Do **not** run full data refreshes or source downloads.
- Do **not** implement missing scheduler jobs for `texas_rrc`/`mexico_cnh`; this plan only corrects or clearly labels claims.
- Do **not** promote off-manifest packages to `stable` by default; classify them as `experimental`, `internal`, `stub`, or `back-compat` unless evidence supports more.
- Do **not** delete modules or data directories in this issue.
- Do **not** resolve CLI docs/examples cleanup from #355 beyond shared taxonomy references.

## Resource Intelligence

Primary evidence:

- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
- `README.md`
- `MODULE_INDEX.md`
- `module-manifest.yaml`
- `data/catalog.yaml`
- `src/worldenergydata/cli/main.py`
- `config/scheduler/scheduler_config.yml`

High-signal deltas from audit:

| Surface | Current claim | Evidence-backed correction |
|---|---|---|
| README | 3 module narrative | Link to full capability index and list all registered CLI sub-apps at a high level. |
| `MODULE_INDEX.md` | 27 indexed modules | Add source-tree/off-manifest appendix or expand manifest with explicit status tiers. |
| Manifest | 27 modules, most stable | Add data/readiness fields; downgrade or flag data-empty modules. |
| Catalog | 12 modules, 44 datasets | Preserve as data inventory, not capability inventory; add stub/sample semantics if maintained. |
| CLI `info()` | 11 rows | Add missing registered sub-apps: `dashboard`, `eia`, `ndbc`, `forecast`. |
| Scheduler table | `texas_rrc` wired, `lng_terminals` gap | Replace with actual `scheduler_config.yml`: `lng_terminals_refresh` wired; `texas_rrc`/`mexico_cnh` config/source exists but no scheduler job. |

## Frozen Design Decisions From Adversarial Review

1. **Curated registry contract:** `module-manifest.yaml` is the curated capability registry. It may include stable/beta/experimental/stub/back-compat records, but it is the contract that `MODULE_INDEX.md` summarizes.
2. **Data inventory contract:** `data/catalog.yaml` is a checked-in data inventory only. It must not be used as proof that a module is production-ready.
3. **Source-tree discovery contract:** top-level source packages are discovery input. Each source-tree entry must be represented in the manifest, the MODULE_INDEX appendix, or an explicit ignore/internal allowlist.
4. **Scheduler authority:** `config/scheduler/scheduler_config.yml` is the runtime authority for what is scheduler-wired. Manifest/index scheduler claims must match it.
5. **CLI public surface:** `src/worldenergydata/cli/main.py` is the public CLI registry authority. `worldenergydata info` should list every registered sub-app, but full command docs are handled by #355.
6. **`eia` vs `eia_us`:** treat `eia` as the CLI front door/alias for the curated `eia_us` capability in this issue. Do not create a second public capability unless a future issue deliberately splits them.
7. **Off-manifest policy:** source entries are classified into exactly one bucket: curated manifest capability, MODULE_INDEX appendix capability, internal infra file, empty namespace, or back-compat shim. Unclassified entries fail validation.

## Catalog Status Derivation Rules

Use deterministic module-level values:

- `full`: checked-in datasets are substantive enough to support documented local workflows.
- `sample`: checked-in datasets exist but are explicitly sample/fragments; BSEE's many 100-row CSVs and small marine-safety samples must not be sold as full source coverage.
- `empty`: catalog module exists with `datasets: []`.
- `runtime_fetched`: normal data path is live fetch/scheduler/API and checked-in data is absent by design.
- `reference_data`: catalog-only static reference data such as pipe schedules or component specs.
- `not_applicable`: infrastructure/analysis modules with no data inventory.
- `unknown`: temporary only; implementation should minimize and justify each use.

If a module has mixed datasets, choose the least-overstating status (`sample` beats `full`) and add notes for substantive exceptions.

## Proposed Implementation Phases

### Phase 0 — Baseline snapshot and contract decision

- Generate a small machine-readable comparison report from the live tree:
  - manifest IDs,
  - catalog module IDs,
  - top-level source packages,
  - CLI sub-app registry names,
  - scheduler job names.
- Implement the frozen contract above; do not reopen source-of-truth decisions during execution.
- Keep the generated comparison as a bounded report artifact if useful, but do not rely on one-off manual counting.

### Phase 1 — Manifest/schema cleanup

Update `module-manifest.yaml` with explicit classification fields. Minimum viable fields:

```yaml
status: stable|beta|experimental|stub|internal|back_compat
public_cli: true|false
in_scheduler: true|false
catalog_status: full|sample|empty|runtime_fetched|reference_data|not_applicable|unknown
capability_source: manifest|source_tree|catalog_only|back_compat
```

Specific corrections:

- `lng_terminals.in_scheduler: true` because `scheduler_config.yml` contains `lng_terminals_refresh`.
- `texas_rrc.in_scheduler: false` unless a job adapter is created separately in a future issue.
- `mexico_cnh.in_scheduler: false` unless a job adapter is created separately in a future issue.
- Preserve `eia_us` as the manifest capability and document CLI `eia` as its front door/alias.
- Add clear `catalog_status: empty` or downgrade/flag `hse` and `pipeline_safety` if no checked-in datasets exist.
- Add appendix rows, not stable manifest promotions, for catalog-only modules unless clearly capability-backed: `pipeline`, `subsea`, `oil_price`, `wind`.
- Add appendix rows for live off-manifest packages by default; promote to manifest only if tests/docs/data justify it.
- Explicitly classify `_compat.py`, `engine.py`, `modules/`, empty namespace directories, and shim packages so they do not churn the validator.

### Phase 2 — Regenerate/rewrite `MODULE_INDEX.md`

- Update `MODULE_INDEX.md` as the public projection of the reconciled manifest plus explicit appendices; if no generator exists yet, manual edits must follow the same generated-section structure and validator invariants.
- Replace the stale scheduler table:
  - wired: `bsee`, `sodir`, `ukcs`, `brazil_anp`, `eia_us`, `metocean`, `lng_terminals`.
  - config/source present but not scheduler-wired: `texas_rrc`, `mexico_cnh`, `canada`.
- Add an "Off-manifest / experimental source packages" appendix if those packages are not promoted into the manifest.
- Add a "Data readiness caveats" section covering samples, runtime-fetched datasets, empty catalog entries, and catalog-only reference data.

### Phase 3 — README and CLI `info()` parity

- Update README:
  - keep the top-level narrative concise,
  - add a full module discovery link to `MODULE_INDEX.md`,
  - update project structure to the flat `src/worldenergydata/<module>` layout,
  - avoid claiming all modules have full data.
- Update `src/worldenergydata/cli/main.py` `info()` table to include every registered sub-app:
  - add `dashboard`, `eia`, `ndbc`, `forecast`.
- Ensure CLI `info()` wording aligns with #355's safety classification and docs cleanup but does not duplicate full docs.

### Phase 4 — Bounded drift checks

Add tests or scripts that do **not** import heavyweight runtime modules or execute refreshes:

- Parse `module-manifest.yaml`, `data/catalog.yaml`, `config/scheduler/scheduler_config.yml`.
- Parse CLI registry with AST/static parsing as the default. Runtime import is optional after #353 lands and must not be required for this issue.
- Assert:
  - scheduler table rows match `scheduler_config.yml`,
  - `info()` contains all registered sub-app names,
  - `eia` is documented as the CLI alias/front door for `eia_us`,
  - `module-manifest.yaml.total_modules` equals the actual number of manifest module records,
  - `MODULE_INDEX.md` total/count claims match the manifest and explicitly state appendix counts,
  - every manifest record has the new schema fields,
  - every empty/sample/runtime-fetched catalog module has an explicit status/caveat,
  - every source package is classified or intentionally ignored via explicit allowlist.

## Files Likely to Change

| Path | Expected change |
|---|---|
| `module-manifest.yaml` | Add readiness fields and correct scheduler/data-status claims. |
| `MODULE_INDEX.md` | Reconcile module count, scheduler table, and data-readiness caveats. |
| `README.md` | Update module discovery, project structure, and caveat language. |
| `src/worldenergydata/cli/main.py` | Add missing `info()` rows only; no runtime behavior changes beyond display text. |
| `tests/unit/...` or `tests/smoke/...` | Add bounded drift checks. |
| Optional script under `scripts/` | Generate/validate capability matrix from live files. |

## Test Plan

Preferred tests are deterministic and non-networked:

1. `test_cli_info_lists_registered_subapps`
   - Compare registered sub-app names to the displayed/static info rows.
   - If CLI import is blocked by #353, use AST/static parsing until #353 is fixed.
2. `test_scheduler_index_matches_scheduler_config`
   - Parse `MODULE_INDEX.md` scheduler section and `config/scheduler/scheduler_config.yml`.
   - Assert wired module/job list matches or documented exceptions exist.
3. `test_manifest_catalog_status_is_explicit`
   - Every manifest module has explicit `catalog_status` or equivalent.
   - Empty catalog modules are not silently labelled fully data-ready.
4. `test_off_manifest_packages_are_classified`
   - Live top-level packages not in manifest are listed in a known appendix/allowlist.
5. `test_module_index_count_claims_are_truthful`
   - Count claims in `MODULE_INDEX.md` match generated/declared manifest totals and appendix totals.
6. `test_eia_cli_alias_maps_to_eia_us_capability`
   - CLI `eia` is documented as the public command for manifest `eia_us`, or any future split is explicit.
7. `test_manifest_schema_complete`
   - Every manifest record has `public_cli`, `in_scheduler`, `catalog_status`, and `capability_source`.

## Acceptance Criteria

- [ ] README no longer implies only 3 repo capabilities; it links to/briefly lists full current discovery surface.
- [ ] Project structure in README reflects flat package layout, not stale `modules/<name>` layout as the primary structure.
- [ ] `MODULE_INDEX.md` scheduler table matches `config/scheduler/scheduler_config.yml` or documents explicit gaps.
- [ ] `module-manifest.yaml` distinguishes code maturity, CLI exposure, scheduler wiring, and data availability.
- [ ] `worldenergydata info` includes all currently registered sub-apps.
- [ ] Empty/sample/runtime-fetched data states are visible and not hidden behind `stable` capability labels.
- [ ] Bounded tests/scripts detect future source-of-truth drift without network calls or data refreshes.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Over-classifying experimental packages as stable | Default off-manifest packages to `experimental`/`internal` until backed by tests/docs/data. |
| #353 import timeout makes CLI introspection flaky | Use AST/static parsing in tests first; upgrade to runtime smoke after #353. |
| Manual index edits drift again | Add a validator or generator and test it. |
| Catalog-only reference data gets mistaken for code modules | Use `capability_source: catalog_only` / `reference_data` classification. |
| Scope creep into scheduler/data refresh implementation | Keep scheduler job creation and data downloads out of this issue. |

## Approval Notes

This plan is documentation/governance plus bounded verification. It is safe for overnight implementation after adversarial plan review and user approval because it avoids refreshes, destructive data edits, and broad runtime execution.
