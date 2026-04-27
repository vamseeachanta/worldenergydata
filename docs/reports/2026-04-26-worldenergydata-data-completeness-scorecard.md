# worldenergydata — Data Completeness & Freshness Scorecard

- **Issue**: [#350](https://github.com/vamseeachanta/worldenergydata/issues/350)
- **Run date**: 2026-04-26
- **Mode**: Audit / read-only — no downloads, no code changes
- **Working tree**: `/mnt/local-analysis/workspace-hub/worldenergydata` @ branch `main` (clean at start)
- **Author artifact**: planning-only; orchestrator review

---

## 1. Executive Summary

The repository declares **27 modules** in `MODULE_INDEX.md` and **13 modules** in `data/catalog/source-registry.yml`, but `data/catalog.yaml` (auto-generated 2026-04-16) only enumerates **12 modules / 44 datasets / 10.5 MB** of catalog-tracked data. The on-disk landing zone `data/modules/` totals **389 MB**, dominated by **BSEE** (151 MB — most in a single 128 MB ZIP), **marine_safety** (108 MB — two SQLite DBs), and **HSE** (58 MB — one SQLite DB). All BSEE `current/` CSVs except two are 100-row sample stubs (last touched 2025-07-31), and several marine_safety raw HTML scrapes (USCG MISLE, OSHA fatalities, PHMSA pipeline/hazmat, IMO GISIS) are zero-byte or "no_results" pages — clear scrape failures or gated sources.

Headline gaps:
- **10 of 27 declared modules have no `data/modules/<name>/` directory at all** — sodir, ukcs, brazil_anp, mexico_cnh, canada, texas_rrc, eia_us, metocean, landman, lower_tertiary, safety_analysis, well_production_dashboard. Only 2 of these (sodir, ukcs, brazil_anp, eia_us, metocean) have scheduler jobs; the rest are missing both data and a scheduled refresh path.
- **Catalog drift**: `data/catalog.yaml` enumerates a 12-module subset; the 15 remaining modules in `MODULE_INDEX.md` are unreflected in the catalog generator output.
- **BSEE freshness inversion**: the largest binaries (eWellWARRawData.zip 128 MB, war_borehole_view.pkl 6 MB) refreshed 2026-02-09; CSV samples last touched 2025-07-31. The "current/" sample-CSV layer is older than the "raw" archive.
- **Marine safety SQLite DBs are 6+ months stale** (2025-10-06 / 2025-10-08).
- **Scheduler covers 7 jobs**, of which **3 jobs (sodir, ukcs, brazil_anp, metocean) refer to output dirs that do not yet exist on disk** — silent no-op risk.

Recommended posture: treat catalog as authoritative for what is currently retrievable, MODULE_INDEX.md as aspirational, and prioritize regenerating catalog after any local refresh (`scripts/generate_data_catalog.py`).

---

## 2. Methodology and Bounded Commands Used

All commands were no-op audits over local artifacts; no network calls, no full refreshes, no code changes. Commands run via Bash/Grep/Read tools:

| Command | Purpose | Tag |
|---|---|---|
| `du -sh data/modules/*` | per-module size totals | no-op audit |
| `find data/modules -maxdepth 4 -type f -printf "%s\t%p\n" \| sort -nr` | largest files | no-op audit |
| `find data/modules -maxdepth 4 -type f -printf "%T@\t%TY-%Tm-%Td\t%p\n" \| sort -n` | oldest/newest files | no-op audit |
| `cat data/modules/<m>/_metadata.json` | refresh date + record_count + file list | no-op audit |
| `cat config/scheduler/scheduler_config.yml` | scheduler job definitions | no-op audit |
| `ls src/worldenergydata/scheduler/jobs/` | implemented refresh jobs | no-op audit |
| `cat data/catalog/source-registry.yml` | declared source URLs / cadences | no-op audit |
| `grep ^  [a-z_]+:$ data/catalog.yaml` | enumerate catalog modules | no-op audit |
| `grep -c ^    - name: data/catalog.yaml` | dataset count | no-op audit |
| `grep -lr API_KEY src/worldenergydata` | credential surfaces | no-op audit |

GitHub issue lookups were attempted via `gh issue view` but blocked by sandbox permissions; the report cites issue numbers from the orchestrator brief and does not assert their current state.

---

## 3. `MODULE_INDEX.md` vs `data/catalog.yaml` vs `src/` Reconciliation

`src/worldenergydata/` contains **47 sub-packages**; `MODULE_INDEX.md` (dated 2026-02-20) declares 27. Catalog enumerates 12. Source-registry covers 14 (with `sodir_zip_data` and `lngc` not appearing in MODULE_INDEX).

| Module | In `MODULE_INDEX.md` | In `src/worldenergydata/` | In `data/catalog.yaml` | In `data/modules/` | In `source-registry.yml` |
|---|---|---|---|---|---|
| bsee | yes | yes | yes (28 datasets) | yes (151 MB) | yes |
| sodir | yes | yes | **no** | **no** | yes (as `sodir_zip_data`) |
| ukcs | yes | yes | **no** | **no** | **no** |
| brazil_anp | yes | yes | **no** | **no** | **no** |
| mexico_cnh | yes | yes | **no** | **no** | yes |
| canada | yes | yes | **no** | **no** | yes |
| texas_rrc | yes | yes | **no** | **no** | yes |
| eia_us | yes | yes (also `eia/`) | **no** | **no** (output_dir = `data/modules/eia` not `eia_us`) | **no** |
| lower_tertiary | yes | yes | **no** | **no** | **no** |
| hse | yes | yes | yes (1 SQLite) | yes (58 MB) | yes |
| pipeline_safety | yes | yes | yes | yes (25 MB) | yes |
| marine_safety | yes | yes | yes | yes (108 MB) | yes |
| safety_analysis | yes | yes | **no** | **no** | **no** |
| fdas | yes | yes | yes | yes (4.4 MB) | **no** |
| metocean | yes | yes | **no** | **no** | yes |
| lng_terminals | yes (beta) | yes | yes | yes (229 KB) | yes |
| vessel_fleet | yes | yes | yes | yes (316 KB) | **no** |
| vessel_hull_models | yes | yes | yes | yes (38 MB) | yes |
| well_production_dashboard | yes | yes | **no** | **no** | **no** |
| landman | yes | yes | **no** | **no** | yes |
| oil_price | **no** | **no** (data only) | yes | yes (89 KB) | yes |
| pipeline | **no** | **no** (data only) | yes | yes (8.5 KB) | **no** |
| subsea | **no** | yes | yes | yes (13 KB) | **no** |
| wind | **no** | **no** (data only) | yes | yes (7.1 MB) | yes |
| baker_hughes, cost, dashboard, decommissioning, drilling, drilling_pressure_management, economics, eia, marine, modules, reservoir, subsea, well_bore_design, well_planning, west_africa | **no** | yes (15 extra src packages) | **no** | **no** | **no** |

**Drift to file**: regenerate `MODULE_INDEX.md` from `module-manifest.yaml` + `src/` and decide which of the 15 extra src packages are first-class data modules vs analysis subpackages.

---

## 4. Data Completeness Scorecard Table

Lanes: **complete-enough** (production-scale, fresh), **sample-only** (stub rows only), **missing** (no data dir), **stale** (data present but cadence overdue), **credential-blocked** (source needs auth not configured), **scheduler-blocked** (no refresh job), **unknown**.

### 4.1 Production data modules

| Module | Local size | Catalog datasets | Last refresh | Lane | Notes |
|---|---|---|---|---|---|
| bsee | 151 MB | 28 datasets, 65 045 records | 2026-03-15 (per `_metadata.json`) | **sample-only** for `current/*` (100-row CSVs, 2025-07-31); production-scale for `well_data.csv` (57 281 rows), `Paleowells.csv` (6 362 rows), `eWellWARRawData.zip` (128 MB raw archive) | mixed scale; `current/` should be regenerated from raw; binary excluded from git per `CLAUDE.md` (`make data`) |
| sodir | 0 | 0 | never | **missing** | scheduler job exists (`sodir_refresh`, daily 03:00) but `data/modules/sodir/` does not exist; output_dir landing path absent |
| ukcs | 0 | 0 | never | **missing** | scheduler job exists (`ukcs_refresh`, monthly day 7); no data dir; NSTA portal often gated |
| brazil_anp | 0 | 0 | never | **missing** | scheduler job exists (`brazil_anp_refresh`, monthly day 10); no data dir; ANP site Portuguese-only |
| mexico_cnh | 0 | 0 | never | **missing / scheduler-blocked** | source-registry entry present; no scheduler job; SIH portal historically auth-gated |
| canada | 0 | 0 | never | **missing / scheduler-blocked** | source-registry covers AER/BCER/Petrinex; no scheduler job; Petrinex requires registration |
| texas_rrc | 0 | 0 | never | **missing / scheduler-blocked** | source-registry covers MFT + PDQ; no scheduler job; PDQ has rate-limiting |
| eia_us | 0 | 0 | never | **missing / credential-blocked** | scheduler job present (`eia_us_refresh`, monthly day 5) but `api_key: null` in config; output_dir mismatch (`data/modules/eia` vs module name `eia_us`) |
| lower_tertiary | 0 | 0 | per analysis | **missing** (data) / **stale** (analysis output in `reports/lower_tertiary/`) | analysis-only module; outputs live under `reports/`, not `data/modules/` |

### 4.2 Safety / regulatory modules

| Module | Local size | Catalog datasets | Last refresh | Lane | Notes |
|---|---|---|---|---|---|
| hse | 58 MB | 1 SQLite (`hse_incidents.db` 60 MB) | per file mtime ~2026-03-15 | **complete-enough** (binary present) but **catalog-thin** | SQLite blob with no row-count visibility in catalog; OSHA bulk zips not landed |
| pipeline_safety | 25 MB | catalog has section, datasets list empty in source-registry | mixed | **stale / sample-only** | raw payload present; PHMSA scrape returned zero-byte HTML for several pages |
| marine_safety | 108 MB | catalog row, 2 SQLite DBs (48 MB + 62 MB) | DBs 2025-10-06 / 2025-10-08; raw HTML 2026-03-15 | **stale** (DBs ~6 mo old) + **scrape-failed** subdomains | 11 raw pages are 0-byte or "no_results"; USCG MISLE, OSHA fatalities, PHMSA pipeline/hazmat, IMO GISIS all returned empty payloads — likely auth/JS-render blocked |
| safety_analysis | 0 | 0 | never | **missing** | analysis module; consumes other modules, no own data |

### 4.3 Economics

| Module | Local size | Catalog datasets | Last refresh | Lane | Notes |
|---|---|---|---|---|---|
| fdas | 4.4 MB | yes | per file mtime | **complete-enough** | enhanced wells CSV ~4.6 MB present; downstream of BSEE |

### 4.4 Environment / metocean

| Module | Local size | Catalog datasets | Last refresh | Lane | Notes |
|---|---|---|---|---|---|
| metocean | 0 | 0 | never | **missing** | scheduler job exists (`metocean_refresh`, daily 01:00, 2 locations); no data dir; sources are public APIs, no key required |

### 4.5 Infrastructure / asset

| Module | Local size | Catalog datasets | Last refresh | Lane | Notes |
|---|---|---|---|---|---|
| lng_terminals | 229 KB | yes | per file mtime | **sample-only** | curated `terminals_seed.csv` 32 KB; FERC/GIE/GIIGNL caches present but small |
| vessel_fleet | 316 KB | yes | per file mtime | **complete-enough (curated subset)** | `drilling_rigs.csv` 200 KB |
| vessel_hull_models | 38 MB | yes | static | **complete-enough** | OBJ files; static reference data |
| well_production_dashboard | 0 | 0 | n/a | **missing (downstream)** | UI module, consumes BSEE/SODIR/etc. |
| landman | 0 | 0 | never | **missing / scheduler-blocked** | source-registry covers BLM; no scheduler job; no data dir |

### 4.6 Other / data-only (no src module)

| Module | Local size | Catalog datasets | Last refresh | Lane | Notes |
|---|---|---|---|---|---|
| oil_price | 89 KB | yes | 2025-07-31 | **stale** (~9 mo) | only EIA `F000000__3a.xls` / `F000000__3m.xls`; "daily" cadence per registry vs static landing |
| pipeline | 8.5 KB | yes | mixed | **sample-only** | tiny |
| subsea | 13 KB | yes | mixed | **sample-only** | tiny curated subset |
| wind | 7.1 MB | yes | 2025-07-31 | **stale** (~9 mo) | USWTDB zips; static-ish source |

---

## 5. Empty, Sample-only, Stale, and Missing Datasets

### 5.1 Empty (zero-byte) or scrape-failed files

Found in `data/modules/marine_safety/raw/`:

- `osha_maritime/osha_fatalities.html` — 0 bytes (2025-10-07)
- `phmsa_hazmat/phmsa_hazmat_main.html` — 0 bytes (2025-10-07)
- `doe_pipelines/phmsa_pipeline_data.html` — 0 bytes (2025-10-07)
- `uscg_misle/misle_data_page.html` — 0 bytes (2025-10-05)
- `imo_gisis/no_results_2010..2019.html` — 11 placeholder "no_results" pages (~27 KB each, all 2026-03-15)
- `imo_gisis/page_structure_2010..2020.html` — 11 page-structure stubs (likely auth-gated GISIS)

### 5.2 Sample-only (100-row stubs)

In `data/modules/bsee/current/`:

- `completions/completion_perforations.csv` (100 rows)
- `completions/completion_properties.csv` (100 rows)
- `completions/completion_summary.csv` (100 rows)
- `geology/geology_markers.csv` (100 rows)
- `geology/hydrocarbon_bearing_interval.csv` (100 rows)
- `infrastructure/all_bsee_blocks.csv` (100 rows)
- `operations/ST_BP_and_tree_height.csv` (100 rows)
- `operations/cut_casings.csv` (100 rows)
- `operations/well_activity_bop_tests.csv` (100 rows)
- `operations/well_activity_open_hole.csv` (100 rows)
- `operations/well_activity_remarks.csv` (100 rows)
- `operations/well_activity_summary.csv` (100 rows)
- `production/production.csv` (100 rows)
- `wells/well_directional_surveys.csv` (2 rows)
- `wells/well_tubulars.csv` (100 rows)

Production-scale files at the same path: `wells/well_data.csv` (57 281 rows), `paleowells/Paleowells.csv` (6 362 rows). The mismatch suggests `current/` was hand-curated for tests and never regenerated.

### 5.3 Stale (>180 days since touch as of 2026-04-26)

| File | Last modified | Age |
|---|---|---|
| `data/modules/oil_price/F000000__3a.xls` | 2025-07-31 | ~270 days |
| `data/modules/oil_price/F000000__3m.xls` | 2025-07-31 | ~270 days |
| `data/modules/wind/uswtdb*.zip` | 2025-07-31 | ~270 days |
| `data/modules/marine_safety/database/marine_safety.db` | 2025-10-06 | ~202 days |
| `data/modules/marine_safety/marine_safety.db` | 2025-10-08 | ~200 days |
| `data/modules/marine_safety/input/*.csv` | 2025-10-23 | ~185 days |
| `data/modules/bsee/current/*.csv` (most) | 2025-07-31 | ~270 days |

### 5.4 Missing (declared but no data dir)

`sodir`, `ukcs`, `brazil_anp`, `mexico_cnh`, `canada`, `texas_rrc`, `eia_us`, `metocean`, `landman`, `lower_tertiary`, `safety_analysis`, `well_production_dashboard`.

---

## 6. Credential / API / Runtime Blockers

| Module | Blocker | Surface |
|---|---|---|
| eia_us | EIA API key (`api_key: null` in `config/scheduler/scheduler_config.yml`) | `src/worldenergydata/eia_us/client/eia_api.py`, `src/worldenergydata/eia/client.py`, `src/worldenergydata/eia/ingestion.py` reference `EIA_API_KEY` env |
| canada (Petrinex) | account registration required for AB Petrinex bulk download | `src/worldenergydata/canada/` |
| mexico_cnh (SIH) | SIH dashboard is JS-rendered; bulk export requires login | `src/worldenergydata/mexico_cnh/` |
| ukcs (NSTA Energy Pathfinder) | session-cookie auth on bulk endpoints | `src/worldenergydata/ukcs/` |
| brazil_anp | no formal blocker but Portuguese site, often rate-limited | `src/worldenergydata/brazil_anp/` |
| texas_rrc PDQ | rate limiting; user-agent + throttle required | `src/worldenergydata/texas_rrc/` |
| marine_safety (USCG MISLE) | bulk MISLE_DATA.zip 404 on direct URL since CG-INV portal redesign — evidence: `misle_data_page.html` is 0 bytes | `src/worldenergydata/marine_safety/importers/misle*` |
| marine_safety (IMO GISIS) | login-gated; "no_results_*.html" landing pages confirm scraper hit gate | `data/modules/marine_safety/raw/imo_gisis/` |
| marine_safety (PHMSA) | redirect chain returns 0-byte HTML — scraper renderer issue | `data/modules/marine_safety/raw/phmsa_*` |
| marine_safety SMTP alerts | `smtp_host` / `smtp_user` / `smtp_pass` null in scheduler config | `config/scheduler/scheduler_config.yml` lines 70-74 |
| metocean (CMEMS) | Copernicus Marine credentials required for `nrt.cmems-du.eu` | `src/worldenergydata/metocean/` |
| All scheduler webhook | `webhook_url: null` — no out-of-band failure visibility | `config/scheduler/scheduler_config.yml` line 67 |

`grep API_KEY` over `src/worldenergydata/` returned 12 hits; only **EIA** is explicitly required by the scheduler. Other Auth flows are implicit per scraper module.

---

## 7. Safe Overnight Refresh Candidates

All commands tagged. **Only `no-op audit`, `endpoint probe`, and `bounded sample` are run by an automated overnight job; everything else surfaces as a manual decision.**

| Command | Module | Tag |
|---|---|---|
| `uv run python scripts/generate_data_catalog.py` | catalog | **no-op audit** — regenerates `data/catalog.yaml` against current disk state |
| `uv run python scripts/generate_data_catalog.py --report` | catalog | **no-op audit** — produces summary report |
| `uv run python -m worldenergydata.scheduler.cli status` | scheduler | **no-op audit** — surfaces last-run + next-run per job |
| `uv run python -m worldenergydata.scheduler.staleness` | scheduler | **no-op audit** — staleness check vs config cadence |
| `uv run python -m worldenergydata.scheduler.monitor` | scheduler | **no-op audit** — health snapshot |
| `curl -sI https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip` | bsee | **endpoint probe** — confirm BSEE archive still served, capture Last-Modified |
| `curl -sI https://factmaps.sodir.no/api/rest/5000` | sodir | **endpoint probe** |
| `curl -sI https://www.data.bsee.gov/Other/Files/IncInvRawData.zip` | bsee/hse | **endpoint probe** — for IncidentStatistics + INCS too |
| `curl -sI https://api.tidesandcurrents.noaa.gov/api/prod/datums?...&format=json` | metocean | **endpoint probe** |
| `uv run python -m worldenergydata.metocean ndbc --station 42040 --hours 24` | metocean | **bounded sample** — 24-hour single-station NDBC pull |
| `uv run python -m worldenergydata.lng_terminals refresh --source giignl` | lng_terminals | **bounded sample** — small index file |
| `uv run python -m worldenergydata.scheduler.jobs.sodir_refresh --max-records 100` | sodir | **bounded sample** if flag exists; otherwise **full refresh candidate - not run** |
| `uv run python -m worldenergydata.scheduler.jobs.bsee_refresh --binary` | bsee | **full refresh candidate - not run** — 128 MB+ archive |
| `uv run python -m worldenergydata.scheduler.jobs.eia_us_refresh` | eia_us | **blocked - credentials/API required** — needs `EIA_API_KEY` |
| `uv run python -m worldenergydata.scheduler.jobs.ukcs_refresh` | ukcs | **blocked - credentials/API required** — NSTA cookie session |
| `uv run python -m worldenergydata.canada.refresh` | canada | **blocked - credentials/API required** — Petrinex registration |
| `uv run python -m worldenergydata.mexico_cnh.refresh` | mexico_cnh | **blocked - implementation needed** — JS-rendered SIH portal |
| `uv run python -m worldenergydata.texas_rrc.refresh` | texas_rrc | **blocked - implementation needed** — rate-limit safe path needed |
| `uv run python -m worldenergydata.marine_safety.importers.misle_importer` | marine_safety | **blocked - implementation needed** — MISLE portal redesign |
| `uv run python -m worldenergydata.marine_safety.scrapers.imo_gisis` | marine_safety | **blocked - credentials/API required** — IMO GISIS login |
| `uv run python -m worldenergydata.landman.refresh` | landman | **blocked - implementation needed** — no scheduler job present |
| `uv run python -m worldenergydata.safety_analysis` | safety_analysis | **no-op audit** — analysis only |

---

## 8. Follow-up Issue Candidates

The following defects fall outside the current audit's allowed-write paths and are recorded here for orchestrator triage. Issue numbers cited from orchestrator brief; current state not verified in this run.

1. **Catalog regeneration drift** — `data/catalog.yaml` is missing 15 of 27 declared modules. Owner: catalog generator (`scripts/generate_data_catalog.py`). Fix: extend generator to traverse all `data/modules/*` plus `MODULE_INDEX.md` declared modules, emit "missing" stub records for absent dirs. (Possibly tracked by #336 / #344.)
2. **Scheduler output_dir vs data dir mismatch** — `eia_us_refresh.output_dir = data/modules/eia` while module is `eia_us`; `sodir`, `ukcs`, `brazil_anp`, `metocean`, `landman` jobs declare output_dirs that don't exist on disk. (Possibly #266-#273.)
3. **BSEE current/* sample-only stale** — 12 CSVs are 100-row 2025-07-31 stubs; downstream consumers (`fdas`, `well_production_dashboard`) silently consume stub data. (Possibly #334.)
4. **Marine safety scrape failure backlog** — 4+ zero-byte HTML files and 22 IMO GISIS no-results placeholders. (Possibly #343 cluster.)
5. **EIA API key not provisioned** — scheduler job enabled but `api_key: null`. (Possibly #128 / #151.)
6. **Marine safety DB staleness >180 days** — both `marine_safety.db` files are 6 months old; no automated refresh. (Possibly #153.)
7. **Source-registry coverage gap** — `landman`, `mexico_cnh`, `canada`, `texas_rrc` declared in registry but no scheduler job. (Possibly #124.)
8. **Module-Index drift** — index dated 2026-02-20 omits 15 src packages and includes modules without data dirs. (Possibly #344.)
9. **Empty placeholder dirs** — `data/bsee/`, `data/marine_safety/` (top-level), `data/processed/`, `data/results/` are all empty 0-byte dirs and may be governance-policy stubs (`docs/DATA_RESIDENCE_POLICY.md` referenced in CLAUDE.md). (Possibly #344.)
10. **Webhook + SMTP alerting not configured** — scheduler runs blind; failures only land in `logs/scheduler/status.json`. (Possibly #266-#273 cluster.)

---

## 9. Recommended Next Steps

Ordered by leverage / safety:

1. **Regenerate catalog** (`uv run python scripts/generate_data_catalog.py --report`). Establishes the current ground truth and surfaces the 15-module drift as a diff. Safe; bounded; idempotent.
2. **Run scheduler staleness check** (`uv run python -m worldenergydata.scheduler.staleness`) and capture status.json. Compares config cadence to `_metadata.json.last_refresh`.
3. **Endpoint-probe the 7 scheduled sources** (BSEE bulk archives, SODIR REST, NSTA, ANP, EIA AEO, Open-Meteo, GIIGNL) — `curl -sI` only. Confirms upstream availability before scheduling refreshes.
4. **Provision EIA_API_KEY** — register at api.eia.gov, add to `.env` referenced by `src/worldenergydata/common/config.py`. Single-config-line unblock for `eia_us`.
5. **Schedule one bounded NDBC metocean pull** (single station, last 24 h) to validate the `metocean_refresh` path end-to-end without 7-source fanout.
6. **Open separate issues** for the 10 follow-ups above so each can be triaged independently rather than absorbed into #350.
7. **Backfill BSEE `current/*` from raw archive** — extract real rows from `eWellWARRawData.zip` instead of 100-row hand stubs. Bounded if executed file-by-file.
8. **Marine safety scrape repair** — three subdomains (USCG MISLE redirect, PHMSA renderer, IMO GISIS auth) need separate fix tickets; the symptom "0-byte HTML" is consistent across them and is not a scheduler bug.
9. **Document the empty top-level dirs** — `data/bsee/`, `data/marine_safety/`, `data/processed/`, `data/results/` either have a governance role (per `docs/DATA_RESIDENCE_POLICY.md`) or should be removed to avoid confusion.
10. **Decide on the 15 extra `src/worldenergydata/` packages** — promote to MODULE_INDEX.md as data modules, or move under `analysis/` as derived modules.

No commits made; artifacts left for orchestrator review at:

- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`
