# worldenergydata Capability Inventory and Module Readiness Matrix

- **Issue:** [#349](https://github.com/vamseeachanta/worldenergydata/issues/349)
- **Date:** 2026-04-26
- **Mode:** planning/audit only — no code changes
- **Scope:** repo-grounded capability vs. claims audit
- **Companion artifact:** `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`

## 1. Executive summary

The repo's documented capability surface is materially smaller than what is actually shipped, and what is shipped is materially less complete than the manifest implies. Three simultaneous drifts are at work:

1. **Under-claim drift (README → reality).** `README.md` headlines only `bsee`, `marine-safety`, and `fdas`, but `cli/main.py` registers 15 sub-apps and `src/worldenergydata/` contains ~40 module directories.
2. **Over-claim drift (MODULE_INDEX/manifest → reality).** `MODULE_INDEX.md` and `module-manifest.yaml` advertise **27 modules at `stable`**, but
   - `data/catalog.yaml` only knows **12 modules / 44 datasets / 10.5 MB**, of which **4 (`hse`, `oil_price`, `pipeline_safety`, `wind`) have empty `datasets:` lists** and most BSEE CSVs are 100-row sample fragments;
   - several `stable`-tagged modules (`brazil_anp`, `ukcs`, `hse`, `pipeline_safety`, `lower_tertiary`, `vessel_fleet`, `vessel_hull_models`, `well_production_dashboard`, `eia_us`) have **no Typer CLI sub-app registered** in `cli/main.py`;
   - the manifest's `in_scheduler` flags conflict with `config/scheduler/scheduler_config.yml` for `lng_terminals` (manifest says `false`, scheduler-config has it enabled), and the manifest implies `texas_rrc`/`mexico_cnh` are scheduled even though `scheduler_config.yml` does not list them.
3. **Off-manifest drift (src tree → MODULE_INDEX).** ~16 source packages exist that the manifest does not enumerate (`baker_hughes`, `cost`, `dashboard`, `decommissioning`, `drilling`, `drilling_pressure_management`, `economics`, `eia`, `marine`, `modules`, `reservoir`, `subsea`, `well_bore_design`, `well_planning`, `west_africa`, `engine.py`/`_compat.py`). Several have substantial test coverage in `tests/unit/<name>/`, so they are not scratch directories — they are unindexed first-class capabilities.

Net effect: an agent using `MODULE_INDEX.md` as a contract will silently miss live capability (off-manifest packages), recommend untrustworthy data (sample-row catalog entries flagged `stable`), or attempt unscheduled modules as if scheduled. Each of these drifts is independently fixable but should be treated as a single index reconciliation lane before downstream automation lanes proceed.

The four highest-leverage capability gaps are: (a) `MODULE_INDEX.md` reconciliation (27 vs 40+ vs 12), (b) catalog-empty modules tagged `stable` (`hse`, `pipeline_safety`), (c) CLI sub-app coverage gaps for nine `stable` manifest modules, (d) scheduler-flag drift on three modules. Top execution-ready modules are `bsee`, `metocean`, `marine_safety`, `safety_analysis`, `lng_terminals`, `fdas`, and `well_production_dashboard` (each has substantial source + tests + at least one usable surface).

## 2. Methodology and commands used

Evidence collection was bounded to filesystem inspection plus pre-known issue context from the orchestrator brief. No subprocess execution of `pytest`, scrapers, or the CLI itself was performed — that is the scope of #352 (`cli-example-smoke-matrix`).

Sources consulted:

- `README.md` (claims surface) — 240 lines.
- `MODULE_INDEX.md` (agent-facing inventory) — 161 lines, claims 27 modules.
- `module-manifest.yaml` (machine inventory, generated 2026-02-20) — 27 module records.
- `data/catalog.yaml` (filesystem reflection, generated 2026-04-16) — 12 modules / 44 datasets / 10.5 MB.
- `pyproject.toml` (entrypoint + deps) — `worldenergydata = "worldenergydata.cli.main:app"`.
- `src/worldenergydata/cli/main.py` and `cli/commands/__init__.py` — Typer sub-app registry.
- `src/worldenergydata/scheduler/jobs/` — job script files.
- `config/scheduler/scheduler_config.yml` — runtime job enable list.
- `src/worldenergydata/<module>/` — package contents per module.
- `tests/unit/<module>/` — per-module test counts (via `find ... test_*.py`).
- `data/modules/<module>/` — physical data inventory.
- `examples/`, `notebooks/`, `docs/modules/`, `docs/CLI.md` — discovery surfaces.
- Orchestrator brief: `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` — pre-classified issue list (#266–#273, #313, #325–#328, #334, #336, #342–#344, #151, #153, #124, #128, #278).

Commands actually run (representative):

- `ls -la src/worldenergydata/` and `ls src/worldenergydata/<pkg>/` — package contents.
- `find tests/unit/<pkg> -name "test_*.py" -type f -printf "%h\n" | sort | uniq -c | sort -rn` — per-test-dir file counts.
- `find tests -maxdepth 4 -name "test_*.py" -type f | wc -l` — global test file count: **522 `test_*.py` files**.
- `Read` of `MODULE_INDEX.md`, `module-manifest.yaml`, `data/catalog.yaml`, `config/scheduler/scheduler_config.yml`, `pyproject.toml`, `src/worldenergydata/cli/main.py`, `src/worldenergydata/__init__.py`, `tests/conftest.py`.

Out of scope here (delegated to sibling lanes): live data freshness, runtime scheduler dry-runs, CLI smoke verification, full pytest collection.

## 3. Source-of-truth comparison

`★ Insight ─────────────────────────────────────`
This repo has four sources of truth (README, MODULE_INDEX, manifest, catalog) and a fifth implicit one (the live src tree). When four indexes disagree, the actionable rule is: trust the source tree first, the catalog second (it is filesystem-derived), then manifest, then MODULE_INDEX, and treat README as marketing copy. The audit's job is to reduce that count, not just report the deltas.
`─────────────────────────────────────────────────`

### Headline counts

| Surface | Module count | Last touched | Notes |
|---|---|---|---|
| `README.md` | 3 (`bsee`, `marine-safety`, `fdas`) | 2026-02-11 | Heavy under-claim; "Modules" section describes only the BSEE/marine/FDAS triad. |
| `MODULE_INDEX.md` | 27 (18 data + 7 infrastructure + 2 analysis/viz) | 2026-02-20 | Agent-facing canon; matches `module-manifest.yaml` structurally. |
| `module-manifest.yaml` | 27 | 2026-02-20 | All 27 tagged `stable` except `lng_terminals` (`beta`) and `analysis` (`stub`). |
| `data/catalog.yaml` | 12 modules / 44 datasets / 10.5 MB | 2026-04-16 | Reflects filesystem only; 4 modules have empty `datasets:`. |
| `src/worldenergydata/` | ~40 directories (incl. 5+ empty) | rolling | 16+ packages off-manifest. |
| `cli/main.py` registrations | 15 sub-apps + 4 root cmds | 2026-04-16 | Some `stable`-tagged manifest modules have no CLI surface. |
| `scheduler/jobs/` files | 7 (`bsee`, `brazil_anp`, `eia_us`, `lng_terminals`, `metocean`, `sodir`, `ukcs`) | 2026-04-16 | All listed in `scheduler_config.yml` as `enabled: true`. |
| `tests/unit/<mod>/` directories | 41 module subdirs, 522 `test_*.py` total | rolling | Coverage exists for many off-manifest modules. |

### Drift A — manifest ↔ source tree

**On manifest, missing from `src/worldenergydata/`:** none observed at top level (manifest `analysis` corresponds to `src/worldenergydata/analysis/`, which is empty per its `stub` status).

**In `src/worldenergydata/`, missing from manifest** (16 packages):

| Source path | Has tests? | Apparent kind | Comment |
|---|---|---|---|
| `src/worldenergydata/baker_hughes/` | (no `tests/unit/baker_hughes` but `tests/test_baker_hughes_loader.py` exists) | data source | Loader present; no manifest record. |
| `src/worldenergydata/cost/` | 8 tests in `tests/unit/cost/` | analysis | `cost_calibration.py`, `cost_model.py`, `data_completeness.py`. |
| `src/worldenergydata/dashboard/` | 2 tests in `tests/unit/dashboard/` | viz | Plotly Dash app (`app.py`, `data_loader.py`); registered in CLI. |
| `src/worldenergydata/decommissioning/` | 5 tests | analysis | `late_life.py`, regulations data + model. |
| `src/worldenergydata/drilling/` | (empty dir) | placeholder | Reserve namespace; no `__init__.py` even. |
| `src/worldenergydata/drilling_pressure_management/` | 3 tests | analysis | `fleet_mpd.py`, `mpd_systems.py`, `mpd_configurations.py`. |
| `src/worldenergydata/economics/` | 2 tests | analysis | `carbon.py`, `dcf.py`. |
| `src/worldenergydata/eia/` | 1 test in `tests/unit/eia/` | data source | `client.py`, `ingestion.py`, `ingestion_runner.py`. **Distinct from `eia_us/`.** |
| `src/worldenergydata/marine/` | (no module-level test dir) | viz/util | `vessel_gis.py` only. |
| `src/worldenergydata/modules/` | shim | back-compat | `bsee/`, `hse/`, `marine_safety/`, `well_production_dashboard/` shim subdirs only. |
| `src/worldenergydata/reservoir/` | (no `tests/unit/reservoir/` listed) | analysis | `resource_estimation.py` + `models/`. Has root-level `tests/reservoir/`. |
| `src/worldenergydata/subsea/` | (empty src dir; data exists in `data/modules/subsea/`) | placeholder | Catalog has 2 datasets but no source code. |
| `src/worldenergydata/well_bore_design/` | 3 tests | analysis | `decision_framework.py`, `hydraulics.py`, `schemas.py`. |
| `src/worldenergydata/well_planning/` | 4 tests | analysis | `batch_economics/`, `models/`. |
| `src/worldenergydata/west_africa/` | 7 tests | data source | `analysis/`, `eiti/`, `nigeria/`, `disclosure_analytics.py`. Tied to disclosure issues #334/#343/#344. |
| `src/worldenergydata/engine.py`, `_compat.py` | n/a | infra | Top-level orchestration + import shim; manifest comments acknowledge these. |

### Drift B — manifest ↔ data catalog

`module-manifest.yaml` lists 27 modules; `data/catalog.yaml` lists 12. The set difference:

- **In manifest but absent from `data/catalog.yaml`:** `sodir`, `ukcs`, `brazil_anp`, `mexico_cnh`, `canada`, `texas_rrc`, `eia_us`, `lower_tertiary`, `safety_analysis`, `metocean`, `well_production_dashboard`, `landman`, plus all infrastructure packages. Several of these populate data only at runtime via the scheduler (`sodir`, `eia_us`, etc.), so absence is expected for some — but `MODULE_INDEX.md` advertises them as `stable`, which a downstream agent will read as "data ready."
- **In `data/catalog.yaml` but absent from manifest:** `pipeline` (43 rows of API 5L pipe schedule reference data), `subsea` (14+14 rows of mooring components / rigid jumper specs), `oil_price` (empty datasets), `wind` (empty datasets). The catalog tracks reference data the manifest does not enumerate.

### Drift C — manifest ↔ scheduler runtime

| Module | Manifest `in_scheduler` | `scheduler/jobs/` file? | `scheduler_config.yml` enabled? | Verdict |
|---|---|---|---|---|
| `bsee` | true | yes | yes | consistent |
| `sodir` | true | yes | yes | consistent |
| `ukcs` | true | yes | yes | consistent |
| `brazil_anp` | true | yes | yes | consistent |
| `eia_us` | true | yes | yes | consistent |
| `metocean` | true | yes | yes | consistent |
| `lng_terminals` | **false** | **yes** (`lng_terminals_refresh.py`) | **yes (weekly)** | **drift — manifest stale** |
| `texas_rrc` | true (claimed via `config/texas_rrc.yml`) | no | no | drift — manifest implies wired but no runtime entry |
| `mexico_cnh` | true (claimed via `config/mexico_cnh.yml`) | no | no | drift — manifest implies wired but no runtime entry |
| `canada` | false | no | no | consistent (config exists, no job) |
| `hse`, `marine_safety`, `pipeline_safety` | false | no | no | consistent — explicit gaps |

### Drift D — README ↔ CLI registry

`README.md` documents three modules; `cli/main.py` registers 15 sub-apps:
`bsee`, `dashboard`, `eia`, `marine-safety`, `fdas`, `sodir`, `metocean`, `ndbc`, `texas-rrc`, `canada`, `mexico-cnh`, `landman`, `lng-terminals`, `safety-analysis`, `forecast` (production_forecast). Plus root commands: `version`, `info`, `status`, `--help`. The README does not mention any of `sodir`, `eia`, `metocean`, `texas-rrc`, `canada`, `mexico-cnh`, `landman`, `lng-terminals`, `safety-analysis`, `forecast`, `ndbc`, `dashboard`.

### Drift E — manifest `stable` ↔ CLI sub-app coverage

Manifest modules tagged `stable` with **no** Typer CLI sub-app registered in `cli/main.py`:

- `brazil_anp` — has source `src/worldenergydata/brazil_anp/` with `analysis`, `data`, `production`; only programmatic use.
- `ukcs` — has `analysis`, `data`, `production`, `wells`; programmatic only.
- `eia_us` — has `client`, `data`, `analysis`, `production`, `international`; CLI registered for sibling `eia` module instead.
- `hse` — has full `importers/` (10 files), `acquirers/`, `database/`; programmatic only.
- `pipeline_safety` — has `importers/`, `database/`, `workflow.py`; programmatic only.
- `vessel_fleet` — has `loaders/`, `models/`, `parsers/`, full pipeline; programmatic only.
- `vessel_hull_models` — has `acquisition/`, `geometry/`, `cli.py` file present but not registered in `cli/main.py`.
- `well_production_dashboard` — has `cli.py` file present but not registered in `cli/main.py`; has `api.py`, `api_enhanced.py`.
- `lower_tertiary` — has `latest_runner.py`, `npv.py`, `production_classifier.py`; programmatic only.

## 4. Readiness matrix

Lane legend:
- **execution-ready** — source + tests + CLI/API surface + at least sample data; can plan implementation work.
- **planning-needed** — source exists with one of {tests, CLI, data, docs} clearly missing; needs a discrete plan before code work.
- **data-missing** — code present, catalog/data layer empty or not exercised.
- **docs-stale** — claim surface (README/MODULE_INDEX) materially diverges from code.
- **blocked/test-infra-risk** — explicit known blocker via tracked issues (#313/#327/#328/#326/#325/#278) or import drift.
- **stub** — directory empty or shim-only by design.

| Module | Source | CLI | Tests | Catalog/data | Scheduler | Docs/examples | Lane |
|---|---|---|---|---|---|---|---|
| `bsee` | `src/worldenergydata/bsee/` (extensive subpkgs) | yes (`cli/commands/bsee.py`, 28 KB) | 100 | 19 datasets in `data/modules/bsee/` (most 100-row samples; `well_data.csv` 57k rows; `Paleowells.csv` 6362 rows) | yes (`bsee_refresh.py`, weekly) | `notebooks/quickstart_bsee.py`; `docs/modules/bsee/` | execution-ready (caveat: most catalog rows are samples, not full BSEE) |
| `sodir` | full (`api_client.py`, `cache.py`, `processors/`, `production/`, `npv_norway.py`) | yes (registered) | 26 | none in `data/catalog.yaml` (runtime-fetched) | yes (daily) | `notebooks/quickstart_sodir.py`; `tests/sodir-integration` | execution-ready |
| `ukcs` | `analysis`, `data`, `production`, `wells` | **no** | 6 | none | yes (monthly) | sparse | planning-needed (CLI gap; #269 referenced) |
| `brazil_anp` | `analysis`, `data`, `production` | **no** | 5 | none | yes (monthly) | sparse | planning-needed (CLI gap) |
| `mexico_cnh` | full (`scrapers/`, `processors/`, `validators.py`, `mexico_cnh.py`) | yes | 5 | none | **manifest drift** (claims yes; not in scheduler_config) | partial | docs-stale + planning-needed |
| `canada` | full (`aer/`, `bcer/`, `common/`, `production/`, `emerging_basins/`) | yes | 12 | none | no (config only) | partial | execution-ready for collection; scheduler gap |
| `texas_rrc` | full (`api_client.py`, `processors/`, `validators.py`) | yes | 10 | none | **manifest drift** (claims yes; not in scheduler_config) | partial | docs-stale |
| `eia_us` | `client`, `data`, `production`, `international`, `analysis` | **no (different `eia` registered)** | 7 | none | yes (monthly) | partial | docs-stale + planning-needed (name collision with `eia/`) |
| `eia` (off-manifest) | `client.py`, `ingestion.py`, `ingestion_runner.py` | yes | 1 | none | no | minimal | planning-needed (clarify vs `eia_us`) |
| `lower_tertiary` | `latest_runner.py`, `npv.py`, `production_classifier.py`, `v30_*` | **no** | 10 | none in catalog (uses BSEE-derived enhanced data via `fdas`) | no | partial | planning-needed (CLI gap; data dependency on `fdas`/`bsee`) |
| `hse` | `acquirers/`, `database/`, `importers/` (10 files) | **no** (only via `safety-analysis`) | 17 | **empty** in `data/catalog.yaml` (`datasets: []`) | no | partial | data-missing + planning-needed |
| `pipeline_safety` | `database/`, `importers/`, `workflow.py` | **no** | 3 | **empty** in catalog | no | examples present | data-missing + planning-needed |
| `marine_safety` | full (`scrapers/` for USCG/NTSB/ATSB+ATSB pipeline 8 files, `acquirers/`, `analysis/`, `database/`, `processors/`, `reports/`, `cli.py` + 7 cli_*.py modules) | yes | 51 | catalog has 14 datasets but mostly small JSON manifests + 20–30-row sample CSVs | no (manifest acknowledges Phase-2 gap) | extensive (`examples/marine_safety/`, `notebooks/quickstart_marine_safety.py`, `docs/marine-safety-data-sources-comprehensive.md`) | execution-ready (caveat: scheduler gap, #153 USCG MISLE blocker) |
| `safety_analysis` | full (`adapters/`, `analysis/`, `core/`, `nlp/`, `risk_index/`, `taxonomy/`, `cli.py`) | yes | 38 | none | no | partial | execution-ready |
| `fdas` | `core/`, `analysis/`, `adapters/`, `data/`, `reports/`, `api.py` | yes | 13 | 1 dataset (`well_data_enhanced.csv`, 57k rows, derived from `bsee`) | no (consumes `bsee` output) | `notebooks/quickstart_fdas.py`, `examples/fdas_complete_workflow.py` | execution-ready |
| `metocean` | full (`clients/`, `cache/`, `database/`, `extrapolation/`, `processors/`, `statistics/`, `unified/`, `well_datasets/`, `cli.py` + 6 cli_*.py modules, `ndbc_analysis.py`) | yes (`metocean` + sibling `ndbc`) | 34 | none in catalog (fetched live) | yes (daily) | partial | execution-ready |
| `lng_terminals` | full (`collectors/`, `loaders/`, `processors/`, `exporters/`, `models/`, `query.py`, `cli.py`) | yes | 26 | 227-row seed in `data/modules/lng_terminals/curated/terminals_seed.csv` | yes (manifest drift: claims `false`) | partial | execution-ready (manifest reconciliation needed) |
| `vessel_fleet` | full (`collectors/`, `loaders/`, `parsers/`, `dedup/`, `quality/`, `schemas/`, `storage/`, `bridge/`) | **no** | 34 | catalog has 7 datasets (incl. 2210-row `drilling_rigs.csv`) | no | partial | execution-ready (CLI gap is the only blocker) |
| `vessel_hull_models` | full (`acquisition/`, `geometry/`, `rig_hulls/`, `visualization/`, `cli.py`) | **no (file present, not registered)** | 9 | 1 dataset (5-row `sample_rigs.csv`) | no | partial | planning-needed (wire CLI; expand from sample) |
| `well_production_dashboard` | extensive (24 files: `api.py`, `api_enhanced.py`, `cli.py`, multiple `views_*` and `components_*`) | **no (file present, not registered)** | 11 | none (consumes `bsee`) | no | partial | planning-needed (wire CLI) |
| `landman` | `landman.py`, `models.py`, `providers/`, `validators.py` | yes | 8 | none | no | partial | execution-ready |
| `production` (unified) | `unified/`, `forecast/` | yes (`forecast` only) | 7 | none | no | minimal | planning-needed |
| `common` | `catalog.py`, `config.py`, `data_resolver.py`, `units.py`, `legacy/`, `validation/` | n/a | 17 | n/a | n/a | partial | execution-ready (infra) |
| `validation` | `base.py`, `rules.py`, `schema.py`, `schemas.py`, `validators.py` | n/a | 6 | n/a | n/a | partial | execution-ready (infra) |
| `scheduler` | `scheduler.py`, `cli.py`, `monitor.py`, `staleness.py`, `alerting.py`, `parquet_output.py`, `status_enricher.py`, `jobs/` (7 jobs) | yes (own `cli.py`) | 14 | n/a | self | minimal | execution-ready (deeper readiness in #351) |
| `reporting` | `export.py`, `templates/`, `utils/`, `examples/` | n/a | 3 | n/a | n/a | partial | execution-ready (infra) |
| `analysis` | empty (per manifest `stub`) | n/a | 0 | n/a | n/a | n/a | stub |
| `testing` | (empty src, but `worldenergydata.testing` referenced by `tests/conftest.py:31`) | n/a | n/a | n/a | n/a | minimal | data-missing in src; conftest depends on it (import risk) |
| `pipeline` (catalog only) | none | n/a | n/a | 1 dataset (43 rows API 5L) | n/a | minimal | docs-stale (catalog-only; not in manifest) |
| `subsea` (catalog + empty src) | empty `src/.../subsea/` | n/a | n/a | 2 datasets (14 rows each: mooring components, rigid jumpers) | n/a | minimal | docs-stale (orphan data) |
| `oil_price`, `wind` (catalog only, empty) | none | n/a | n/a | empty `datasets:` | n/a | n/a | data-missing (orphan stubs) |
| `baker_hughes` (off-manifest) | yes (full subpackage) | no | `tests/test_baker_hughes_loader.py` | n/a | n/a | minimal | planning-needed (manifest gap) |
| `cost` (off-manifest) | `cost_calibration.py`, `cost_model.py`, `data_completeness.py`, `calibration/`, `data_collection/`, `disclosure_analytics.py` | no | 8 | n/a | n/a | minimal | planning-needed; ties to disclosure issues #334/#343/#344 |
| `dashboard` (off-manifest) | `app.py`, `data_loader.py` | yes (registered as `dashboard`) | 2 | n/a | n/a | minimal | planning-needed (manifest gap) |
| `decommissioning` (off-manifest) | `late_life.py`, `_regulations_data.py`, `_regulations_model.py`, `regulations.py` | no | 5 | n/a | n/a | minimal | planning-needed |
| `drilling_pressure_management` (off-manifest) | `fleet_mpd.py`, `mpd_configurations.py`, `mpd_systems.py` | no | 3 | n/a | n/a | minimal | planning-needed |
| `economics` (off-manifest) | `carbon.py`, `dcf.py` | no | 2 | n/a | n/a | minimal | planning-needed |
| `marine` (off-manifest) | `vessel_gis.py` | no | 0 (no module dir) | n/a | n/a | n/a | planning-needed (clarify vs `marine_safety`) |
| `well_planning` (off-manifest) | `batch_economics/`, `models/` | no | 4 | n/a | n/a | minimal | planning-needed |
| `well_bore_design` (off-manifest) | `decision_framework.py`, `hydraulics.py`, `schemas.py` | no | 3 | n/a | n/a | minimal | planning-needed |
| `west_africa` (off-manifest) | `analysis/`, `eiti/`, `nigeria/`, `disclosure_analytics.py`, `loader.py`, `report.py` | no | 7 | n/a | n/a | minimal | planning-needed; tied to disclosure issues #334/#343/#344 |
| `reservoir` (off-manifest) | `resource_estimation.py`, `models/` | no | (separate `tests/reservoir/`) | n/a | n/a | minimal | planning-needed |
| `drilling` (off-manifest) | empty dir | n/a | n/a | n/a | n/a | n/a | stub |
| `base_configs` (off-manifest) | empty dir | n/a | n/a | n/a | n/a | n/a | stub |
| `modules` (off-manifest compat) | `bsee/`, `hse/`, `marine_safety/`, `well_production_dashboard/` shims | n/a | n/a | n/a | n/a | n/a | back-compat shim (#278 blocker referenced) |
| `engine.py`, `_compat.py` (top-level files) | yes | n/a | n/a | n/a | n/a | minimal | execution-ready (infra) |

Status of known test-infra blockers (orchestrator brief):

- `#313` pytest config/import cleanup, `#327` conftest blocking marine_safety collection — affect any "tests exist" claim for collection-level reliability. Per-module test counts above reflect file presence on disk, not pytest collection success.
- `#326` missing `ProductionAnalyzer.prepare_production_data` — local risk in `bsee` analysis path.
- `#325` xfail-surfaced pre-existing defects — distributed.
- `#278` `modules.*` compat shim breakage — observable via `src/worldenergydata/modules/` skeleton.

## 5. Stale or overbroad claims and proposed corrections

| Surface | Claim | Reality | Proposed correction |
|---|---|---|---|
| `MODULE_INDEX.md:4` | "Total modules indexed: 27" | ~40 src packages; 12 in catalog | Either expand index to all live src packages with explicit `experimental`/`internal` tags, or add a "Not indexed (off-manifest)" appendix listing the 16 packages above. |
| `module-manifest.yaml:54,167,272` | `lng_terminals.in_scheduler: false`; `texas_rrc` and `mexico_cnh` implied scheduled | `scheduler_config.yml` enables `lng_terminals_refresh` weekly; does NOT list `texas_rrc_refresh` or `mexico_cnh_refresh` | Flip `lng_terminals.in_scheduler` to `true`; reword `texas_rrc`/`mexico_cnh` notes to clarify "config present, no scheduler job" — or add the missing job files. |
| `module-manifest.yaml:77, 145` | `hse` and `pipeline_safety` `status: stable` | `data/catalog.yaml` has `datasets: []` for both | Downgrade to `beta` or add an `data_status: empty` field; document that `make data` is required. |
| `MODULE_INDEX.md:147` | "Modules wired into the WRK-076 automated refresh scheduler" lists 7 incl. `texas_rrc` | `scheduler_config.yml` lists 7 jobs but **`texas_rrc` is not among them**; `lng_terminals` is. | Replace the `texas_rrc` row with `lng_terminals`, and add a "config-only, no job adapter" section for `canada`, `texas_rrc`, `mexico_cnh`. |
| `README.md:57–99` | Modules section names only `bsee`, `marine-safety`, `fdas` | 15 sub-apps registered, 27+ modules in manifest | Add a "Full module list" reference link to `MODULE_INDEX.md` and a one-line summary of each registered CLI sub-app. |
| `README.md:101–133` | Project Structure shows `modules/bsee/`, `modules/marine_safety/`, `modules/fdas/` only | The flat namespace migration (WRK-096) moved everything to `worldenergydata.<name>` | Update to reflect flat package layout; remove obsolete `modules/<name>/data/...` tree. |
| `data/catalog.yaml:701–705, 1120–1124, 1176–1180, 2052–2056` | Modules `hse`, `oil_price`, `pipeline_safety`, `wind` listed with empty `datasets:` | No data files; only a "run 'make data'" stub note | Either remove these from catalog until data lands, or add a `status: stub` flag so consumers can filter. |
| `data/catalog.yaml:1125–1180, 1181–1281, 2052–2056, 1120–1124` | Modules `pipeline`, `subsea`, `oil_price`, `wind` are not in `module-manifest.yaml` | Reference data + empty stubs | Add manifest records (probably under "Reference data" section) or move them out of the catalog into `data/reference/`. |
| `MODULE_INDEX.md:122–134` | Agent Quick Reference uses `from worldenergydata.<X>` paths | Per `__init__.py`, the package warns on `worldenergydata.modules.X` imports via `_compat.py` | Verify each Quick Reference snippet imports the canonical path; add a "deprecated patterns" section so agents avoid the `modules.X` shim (#278). |

## 6. High-value follow-up issues to create or revisit

The orchestrator brief enumerates the existing issue queue. New audit-derived candidates (verify against the open list before filing to avoid duplicates with #266–#273, #313, #325–#328, #334, #336, #342–#344, #151/#153, #124/#128, #278):

1. **Index reconciliation parent issue** — single tracking issue covering MODULE_INDEX.md ↔ source tree ↔ catalog.yaml ↔ scheduler_config drift. Likely supersedes spot fixes.
2. **Manifest scheduler-flag fix** — small mechanical PR: flip `lng_terminals.in_scheduler` to `true`; clarify `texas_rrc`/`mexico_cnh` rows. Low risk, high signal.
3. **Off-manifest packages classification** — for each of the 16 off-manifest src packages, classify as: `add to manifest`, `move under existing manifest module`, `mark experimental`, or `delete`. `west_africa`, `cost`, `economics` are likely candidates for promotion (they tie to disclosure issues #334/#343/#344). `drilling/`, `base_configs/`, `subsea/` (empty) are likely candidates for deletion or documented stubs.
4. **CLI sub-app coverage backlog** — register sub-apps for `brazil_anp`, `ukcs`, `eia_us`, `hse`, `pipeline_safety`, `vessel_fleet`, `vessel_hull_models` (file exists but unregistered), `well_production_dashboard` (file exists but unregistered), `lower_tertiary`. Some of these will need first-time CLI authoring.
5. **`eia` vs `eia_us` name collision** — documented decision: which is canonical, what to do with the other. Affects #266 (EIA scheduler operationalization).
6. **`testing` subpackage import contract** — `tests/conftest.py:31` imports `from worldenergydata.testing.performance`, but `src/worldenergydata/testing/` is currently empty per `ls`. Either confirm the module is installed-but-not-on-disk via a path resolution detail, or lift the missing `performance.py` module. Pairs with #313/#327.
7. **Catalog stub flagging** — add `status: stub` or remove empty-dataset modules (`hse`, `oil_price`, `pipeline_safety`, `wind`) from `data/catalog.yaml`; tracker for `make data` outcomes.
8. **README rewrite for full module surface** — promote the 15 registered CLI sub-apps; link MODULE_INDEX.

## 7. Risks and unknowns

- **Test collection success ≠ test file presence.** The 522 `test_*.py` count is on-disk only. With `#313`/`#327` open, real pytest collection may fail for `marine_safety` and adjacent modules. The smoke matrix (#352) is the right venue to confirm. Treat per-module test counts as upper bounds, not guarantees.
- **`tests/conftest.py:31` imports `worldenergydata.testing.performance`.** A blank `ls src/worldenergydata/testing/` raises a real risk that conftest fails at collection time. This may already be an installed-package vs. on-disk dichotomy (e.g., the package is registered but the file is in a different layout), but it's worth verifying as part of #313.
- **Catalog freshness vs. live data.** `data/catalog.yaml` was generated 2026-04-16; many BSEE files have `last_modified: 2025-07-31`. Sample-row CSVs (`row_count: 100`) suggest the BSEE bulk CSVs were checked in as samples and never replaced by `make data`. This is the explicit subject of #350 — capability matrix is not the place to score it.
- **Manifest authority.** `module-manifest.yaml` was regenerated 2026-02-20 (per its own header). Two months of source-tree change have happened since. Either treat the manifest as "as of Feb 2026" and add a regeneration job, or fold its purpose into a tool that derives from the live tree.
- **#278 compat-shim breakage.** `src/worldenergydata/modules/` exists as a back-compat namespace. The orchestrator brief flags it as broken. Any agent following `MODULE_INDEX.md:78` or older docs will hit deprecation warnings or import failures. Confirm import paths in Section 5 before publishing the matrix to downstream agents.
- **Orphan source modules without manifest entries.** `cost`, `economics`, `west_africa`, `decommissioning`, `well_planning`, `well_bore_design`, `drilling_pressure_management`, `reservoir`, `baker_hughes` are all live with tests but invisible to manifest-querying agents. Risk: well-meaning agents declare these "not implemented" and either rebuild or skip them.
- **No `gh` issue listing was performed in this audit.** The orchestrator brief enumerated the relevant open issues; this report does not independently confirm their open/closed state. Recommended: at the start of each downstream lane, run `gh issue list --state open --limit 200` and reconcile.

## 8. Recommended next overnight batch lanes

In priority order (lowest risk, highest signal first):

1. **Lane `#349-followup-A` — manifest scheduler-flag fix** (mechanical, ≤30 min). Flip `lng_terminals.in_scheduler`; clarify `texas_rrc`/`mexico_cnh` notes. No code change. PR-only.
2. **Lane `#349-followup-B` — off-manifest classification** (planning, 1–2 h). Per off-manifest package, propose: promote / move / experimental / delete. Output: an audit table referenced by a parent reconciliation issue. No code change.
3. **Lane `#349-followup-C` — `testing` subpackage import contract** (planning + smoke, ≤1 h). Confirm whether `tests/conftest.py:31` import resolves at collection time; if not, scope the smallest fix into #313's ambit.
4. **Lane `#349-followup-D` — README rewrite** (docs, 1 h). Promote the 15 registered CLI sub-apps; link MODULE_INDEX. No code change.
5. **Lane `#349-followup-E` — CLI registration backlog** (planning, 1 h). Per missing-CLI module above, propose register-only PR or "needs CLI authoring" follow-up. Several already have `cli.py` files (`vessel_hull_models`, `well_production_dashboard`) and only need a one-line add to `cli/main.py`.
6. **Lane `#349-followup-F` — catalog stub flag** (mechanical, ≤30 min). Either remove empty-dataset modules from `data/catalog.yaml` or add `status: stub`. Coordinates with #350 data-completeness scorecard.

Hand off to sibling lanes (already scoped by orchestrator):

- Data completeness deep dive → **#350** (sibling matrix scoped to dataset rows/freshness).
- Scheduler runtime dry-run → **#351** (sibling matrix scoped to job behaviour).
- CLI/example smoke verification → **#352** (sibling matrix scoped to runnability of the help text claims here).

`★ Insight ─────────────────────────────────────`
The repo is healthier than its docs suggest and frailer than its manifest suggests. The fastest reviewer-facing signal is that 522 test files, ~40 src packages, and 15 CLI sub-apps are not the same shape as "27 modules, 3 in the README." The next agent's first job should be index reconciliation, not feature work — drift compounds, and every downstream lane will hit it eventually.
`─────────────────────────────────────────────────`
