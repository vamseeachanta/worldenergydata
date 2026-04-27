# WorldEnergyData Scheduler / Source Refresh Runtime Readiness — 2026-04-26

**Issue:** [#351](https://github.com/vamseeachanta/worldenergydata/issues/351) — Scheduler/source refresh runtime readiness matrix
**Mode:** planning/audit only — no code changes, no full refreshes, no labels touched.
**Companion artifact:** `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md`

---

## 1. Executive summary

- The scheduler **process surface is healthy**: a single CLI (`python -m worldenergydata.scheduler …`), one YAML config (`config/scheduler/scheduler_config.yml`), and a uniform `AbstractJob` adapter contract.
- Of the **7 jobs registered**, **only 3 perform real data fetches** (`bsee_refresh`, `sodir_refresh`, `eia_us_refresh`). The remaining 4 (`brazil_anp_refresh`, `ukcs_refresh`, `metocean_refresh`, `lng_terminals_refresh`) are **Tier-2 stubs that return `status="skipped"` deterministically** while still being marked `enabled: true` in the YAML — they consume scheduler ticks and write `_metadata.json` paths but do not touch any source.
- **`metocean_refresh` is the most leveraged stub**: the underlying `OpenMeteoClient` (and NDBC/COOPS/MetNorway/ERDDAP siblings) is **already implemented** in `src/worldenergydata/metocean/clients/`. The gap is wiring, not source contract.
- **`output_dir` wiring is consistent for the three real jobs** — each respects `config["output_dir"]` and falls back to `get_module_data_safe(<module>)`. The four stubs read `output_dir` but never write to it. No defects observed in the wiring pattern itself.
- **Scheduler-health monitor (`docs/reports/scheduler-health-2026-W16.md`) tracks five different names** (`eia_weekly`, `bsee_incidents`, `sodir`, `anp`, `ukcs`) — none of which match the `_refresh` registrations in `cli.py:ALL_JOBS`. This is a **naming-drift defect** that masks all jobs as "❌ manifest missing". Worth a follow-up issue.
- **Runtime blockers** (host/credentials) are isolated: EIA needs `EIA_API_KEY`, Mexico CNH would need Chrome+Selenium, BSEE OGOR-A files need long timeouts. None of these are repo-code defects.
- Live `python` / `uv run` probes were **not executed** — the harness gates these and this session is unattended. All findings below are from static evidence.

**Bottom line for the orchestrator:** the safe overnight envelope is **3 dry-runs + 4 endpoint HEAD probes + 1 bounded SODIR factmaps GET + the existing `make data-dry` BSEE refresh plan dump**. Anything else either modifies state, requires credentials, or relies on a stub that returns no data.

---

## 2. Methodology and safe commands used

### 2.1 Evidence sources inspected (static reads only)

| Surface | Files |
|---|---|
| Scheduler runtime | `src/worldenergydata/scheduler/{cli,scheduler,config,__main__}.py` |
| Scheduler base + jobs | `src/worldenergydata/scheduler/jobs/{base,bsee_refresh,sodir_refresh,eia_us_refresh,metocean_refresh,brazil_anp_refresh,ukcs_refresh,lng_terminals_refresh}.py` |
| Scheduler YAML | `config/scheduler/scheduler_config.yml` |
| Per-source configs | `config/{sodir,canada,texas_rrc,mexico_cnh,landman,lng_terminals}.yml` |
| BSEE adapters | `src/worldenergydata/bsee/data/scrapers/bsee_web.py`, `src/worldenergydata/bsee/data/refresh/url_registry.py` (referenced) |
| BSEE refresh script | `scripts/refresh_bsee_all.py` (Makefile `make data` / `make data-dry`) |
| SODIR adapters | `src/worldenergydata/sodir/{api_client,endpoints,errors}.py` |
| EIA adapters | `src/worldenergydata/eia/{client,ingestion,ingestion_runner}.py` |
| Metocean adapters | `src/worldenergydata/metocean/clients/{open_meteo,ndbc,coops,met_norway,erddap}_client.py` |
| Module map | `MODULE_INDEX.md`, `module-manifest.yaml` |
| Existing health snapshot | `docs/reports/scheduler-health-2026-W16.md` |
| Mission spec | `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` |

### 2.2 Live commands attempted

| Command | Outcome |
|---|---|
| `uv run python -m worldenergydata.scheduler` (no args, prints usage) | **Blocked — harness permission gate** |
| `gh issue view 351` | **Blocked — harness permission gate** |

The session ran unattended without permission approvals available, so all further classifications below are derived from source-code evidence and existing artifacts. The command pack in the companion document encodes what would have been run.

### 2.3 Bounded probe envelope (defined, not executed)

- HEAD requests against documented public endpoints (BSEE zips, SODIR factmaps, EIA v2 API root, Open-Meteo marine API, GIE ALSI) — non-mutating, allowed by mission.
- `--dry-run` / `--help` invocations of the scheduler CLI and `scripts/refresh_bsee_all.py`.
- Single-record SODIR factmaps GET (table `1001` blocks) bounded at <10 KB response.

All command text lives in the companion command pack with `[risk]` tags.

---

## 3. Scheduler inventory

### 3.1 Process surface

- **Entry points:** `python -m worldenergydata.scheduler [start|stop|status|run-job <name>] [--config PATH]`. Defined in `src/worldenergydata/scheduler/cli.py:107-168`. No `console_scripts` console entry; only the module form is supported.
- **Loop:** `DataScheduler.start()` is a blocking `schedule.run_pending()` polling loop with `tick_interval=1.0`s — `src/worldenergydata/scheduler/scheduler.py:212-231`. There is no daemonization, no pidfile, no signal-driven `stop`. `cmd_stop` is documented as a no-op stub.
- **Config:** `config/scheduler/scheduler_config.yml` is the sole canonical config file. `SchedulerConfig.validate_config` enforces `interval ∈ {daily, weekly, monthly}` only; sub-daily intervals are unsupported.
- **State persistence:** in-memory `_job_state` dict only (`scheduler.py:36-37`). Reboot loses last-run history. Status JSON is written by `StatusReporter` to `logs/scheduler/status.json`.
- **Retry:** `RetryManager` with `max_retries=3`, `backoff_seconds=60` (per YAML). Wraps each `job.run()` invocation.
- **Alerting:** SMTP-based via `AlertSender`; `smtp_host` is `null` in YAML, so alerting is effectively dormant unless env-injected.
- **Webhook:** `monitoring.webhook_url` is `null`; status POSTs are dormant.
- **Status enrichment:** `enrich_status()` in `status_enricher.py` is invoked for `cmd_status` — adds staleness + alerts keys around the bare `jobs` dict.

### 3.2 Registered jobs (from `cli.py:ALL_JOBS`)

| Order | Job name | Adapter class | Module | Has real fetch? |
|---|---|---|---|---|
| 1 | `bsee_refresh` | `BseeRefreshJob` | `bsee` | **YES** |
| 2 | `sodir_refresh` | `SodirRefreshJob` | `sodir` | **YES** |
| 3 | `eia_us_refresh` | `EiaUsRefreshJob` | `eia` | **YES** (needs API key) |
| 4 | `brazil_anp_refresh` | `BrazilAnpRefreshJob` | `brazil_anp` | NO — stub |
| 5 | `ukcs_refresh` | `UkcsRefreshJob` | `ukcs` | NO — stub |
| 6 | `metocean_refresh` | `MetoceanRefreshJob` | `metocean` | NO — stub (despite live clients existing) |
| 7 | `lng_terminals_refresh` | `LngTerminalsRefreshJob` | `lng_terminals` | NO — stub |

### 3.3 Gap: jobs configured in YAML but unwired in code

None — every YAML entry maps to a registered class. However, **5 source modules have first-class configs but no scheduler job at all**: `canada` (`config/canada.yml`), `mexico_cnh` (`config/mexico_cnh.yml`), `texas_rrc` (`config/texas_rrc.yml`), `landman` (`config/landman.yml`), and the safety/regulatory triplet `marine_safety` / `hse` / `pipeline_safety` (no per-source YAML, but live module dirs).

`MODULE_INDEX.md` already flags this gap explicitly (lines 159-160).

### 3.4 Gap: scheduler-health monitor name drift (latent defect)

`docs/reports/scheduler-health-2026-W16.md` reports against five names — `eia_weekly`, `bsee_incidents`, `sodir`, `anp`, `ukcs` — that **none of which match** `cli.py:ALL_JOBS` registrations (`*_refresh`). The current health output ("❌ manifest missing" for all five) is therefore a misclassification. Either the health script (`scripts/cron/scheduler-health.sh`) or the manifest it consumes needs reconciling with `ALL_JOBS`. Recommended follow-up issue.

---

## 4. Source-by-source readiness matrix

Legend for `Safe overnight action`:
- **no-op audit** — file-only inspection, already done in this report
- **endpoint probe** — HEAD or single bounded GET against a documented endpoint
- **dry-run** — invoke the existing `--dry-run` / `--help` of the script
- **bounded sample** — single small dataset fetch (≤1 file, ≤10 MB)
- **full refresh candidate** — already supported and proven safe; the orchestrator may schedule
- **implementation needed** — repo-side wiring missing
- **credential-blocked** — code OK but environment lacks secrets
- **runtime-blocked** — needs additional host capability (browser, geckodriver, large RAM)

### 4.1 Modules wired into the scheduler

#### `bsee_refresh` — real, runs against bsee.gov

- **Job config**: `config/scheduler/scheduler_config.yml:7-11`. Weekly @ 02:00, `output_dir: data/modules/bsee`.
- **Endpoint contract**: 4 zip URLs hard-coded in `BSEEWebScraper.URLS` (`bsee_web.py:24-33`) — `platform`, `pipeline_permit`, `pipeline_location`, `deepwater_structure`. URLs end at `www.data.bsee.gov/{Platform,Pipeline}/Files/*RawData.zip`. No prior 404 evidence in repo. Public, unauthenticated.
- **Output**: 4 `.parquet` files in `data/modules/bsee/`. Partial-failure tolerant — `bsee_refresh.py:74-99` keeps successful datasets even if some fail.
- **Credentials**: none.
- **Dry-run**: `make data-dry` → `python3 scripts/refresh_bsee_all.py --dry-run` (a different, more comprehensive 129-bin LFS-stub replacer; not the scheduler job, but useful for inventory).
- **Risk**: zip downloads can be 50–100+ MB; the scheduler timeouts in `BSEEWebScraper.TIMEOUTS` are 600–2400s — adequate for this scope, but production/war datasets (NOT in scheduler scope) need 2400s.
- **Safe overnight action**: **endpoint probe** (HEAD on each of the 4 URLs); **full refresh candidate** for the 4 in-scope datasets; **dry-run** for the broader 129-bin path.
- **Runtime vs repo split**: zero repo-side defects observed; runtime risk is network/timeouts only.
- **Related issue**: [#267](https://github.com/vamseeachanta/worldenergydata/issues/267).

#### `sodir_refresh` — real, runs against factmaps.sodir.no

- **Job config**: `scheduler_config.yml:14-18`. Daily @ 03:00.
- **Endpoint contract**: `SODIR_ENDPOINTS` in `src/worldenergydata/sodir/endpoints.py:10-110`. Migrated May 2025 from `factpages.sodir.no` → `factmaps.sodir.no`. Pattern: `GET /api/rest/services/DataService/data?table=<id>&format=json`. Scheduler job uses `blocks(1001)`, `wellbores(5000)`, `fields(7100)` — fields enriched with `format=json` automatically by `SodirAPIClient._make_request` (`api_client.py:316-318`).
- **Output**: `sodir_blocks.parquet`, `sodir_wellbores.parquet`, `sodir_fields.parquet` in `data/modules/sodir/`.
- **Credentials**: none. Rate-limit is 10 rps, 24-h cache TTL.
- **Risk**: SODIR's new factmaps endpoint occasionally returns wrapped envelopes vs raw arrays — `sodir_refresh.py:71-72` does `response.get("data", [])`, so a schema change to e.g. `{"items": [...]}` would silently produce zero records, returning success-but-empty.
- **Safe overnight action**: **endpoint probe** (single GET against `?table=1001&format=json`, expect HTTP 200 + non-empty `data`); **full refresh candidate** (small payloads, <10 MB total).
- **Runtime vs repo split**: zero repo-side defects observed; the only risk is upstream schema drift, which is a runtime contract issue.
- **Related issue**: [#273](https://github.com/vamseeachanta/worldenergydata/issues/273) directly; [#269](https://github.com/vamseeachanta/worldenergydata/issues/269) for combined NCS/UKCS/Brazil rollup.

#### `eia_us_refresh` — real, requires `EIA_API_KEY`

- **Job config**: `scheduler_config.yml:20-26`. Monthly day=5 @ 04:00.
- **Endpoint contract**: `EIAFeedClient` (in `src/worldenergydata/eia/client.py`) — fetches `petroleum_weekly` and `gas_storage_weekly` via the EIA v2 API. State stored in `eia_ingestion_state.json` next to outputs.
- **Output**: `eia_*.jsonl` (incremental append) + `eia_*.parquet` snapshot in `data/modules/eia/`.
- **Credentials**: `EIA_API_KEY` env var or `config["api_key"]`. Without it `EIAFeedClient` likely fails.
- **Safe overnight action**: **dry-run** (will instantiate state file and exit on missing key, harmless); **endpoint probe** against `https://api.eia.gov/v2/` root (returns metadata, no records).
- **Runtime vs repo split**: code path is implemented; **runtime blocker** is `EIA_API_KEY` provisioning.
- **Related issue**: [#266](https://github.com/vamseeachanta/worldenergydata/issues/266).

#### `metocean_refresh` — STUB (despite live OpenMeteoClient)

- **Job code**: `metocean_refresh.py:33-54` returns `JobResult(status="skipped")` — explicitly a Tier-2 placeholder.
- **Real adapter exists**: `src/worldenergydata/metocean/clients/open_meteo_client.py` exposes `OPEN_METEO_MARINE_BASE_URL = "https://marine-api.open-meteo.com"` and a typed `OpenMeteoForecast` dataclass. Sibling clients: `NDBCClient`, `COOPSClient`, `MetNorwayClient`, `ERDDAPClient`. None are imported by the scheduler job.
- **Job config**: `scheduler_config.yml:28-35`. Daily @ 01:00. **Two locations are listed** (`GOM`, `NCS`) in YAML — the stub never reads them.
- **Output**: `data/modules/metocean/` — directory created but never written.
- **Credentials**: Open-Meteo Marine API requires no auth. NDBC/COOPS none. MetNorway requires User-Agent identification.
- **Safe overnight action**: **endpoint probe** against `https://marine-api.open-meteo.com/v1/marine` (no key, public); **implementation needed** to wire the stub to `OpenMeteoClient.fetch_marine()`.
- **Runtime vs repo split**: pure repo-side gap — wiring exists in client, missing in job adapter. **High-leverage** because the upstream API has no auth and is the cheapest of the 4 stubs to operationalize.
- **Related issue**: [#268](https://github.com/vamseeachanta/worldenergydata/issues/268).

#### `brazil_anp_refresh` — STUB

- **Job code**: `brazil_anp_refresh.py` returns `skipped`. TODO comment names ANP public data portal as the target source.
- **No supporting client** found under `src/worldenergydata/brazil_anp/` (not inspected line-by-line; module dir exists).
- **Safe overnight action**: **implementation needed**. Possible **endpoint probe** against `https://app.anp.gov.br` (Portal-only HTML — likely needs scraping rather than API).
- **Runtime vs repo split**: pure repo-side gap; no proven endpoint contract yet.
- **Related issue**: [#269](https://github.com/vamseeachanta/worldenergydata/issues/269).

#### `ukcs_refresh` — STUB

- **Job code**: returns `skipped`. TODO names NSTA (North Sea Transition Authority) endpoints.
- **Safe overnight action**: **implementation needed**. The companion issue [#151](https://github.com/vamseeachanta/worldenergydata/issues/151) covers the larger UK NDR ingestion.
- **Runtime vs repo split**: pure repo-side gap.
- **Related issues**: [#269](https://github.com/vamseeachanta/worldenergydata/issues/269), [#151](https://github.com/vamseeachanta/worldenergydata/issues/151).

#### `lng_terminals_refresh` — STUB (rich config but no fetch)

- **Job code**: returns `skipped`.
- **Config evidence**: `config/lng_terminals.yml` is fully populated with FERC, GIE/ALSI, GIIGNL, and seed sources, complete with rate limits and cache TTLs — but the scheduler job ignores all of it.
- **Safe overnight action**: **endpoint probe** against `https://alsi.gie.eu/api` (public, no auth) and `https://www.ferc.gov` (HEAD only); **implementation needed**.
- **Runtime vs repo split**: repo-side gap; one of the cleanest stubs to fill in because the config layer is already designed.
- **Related issue**: [#270](https://github.com/vamseeachanta/worldenergydata/issues/270).

### 4.2 Modules with config/code but no scheduler job

| Module | Config file | Has client? | Scheduler entry | Probe-safe? | Action |
|---|---|---|---|---|---|
| `canada` | `config/canada.yml` | live (AER, BCER) | none | yes (HEAD `https://www.aer.ca`, `https://www.bc-er.ca`) | **scheduler wiring needed** |
| `mexico_cnh` | `config/mexico_cnh.yml` | live (Selenium) | none | partial — open data API HEAD ok, SIH dashboard requires Chrome | **runtime-blocked + scheduler wiring** |
| `texas_rrc` | `config/texas_rrc.yml` | live | none | yes (HEAD `https://mft.rrc.texas.gov`) | **scheduler wiring needed** |
| `landman` | `config/landman.yml` | live | none | yes (state GIS HEAD probes) | **scheduler wiring needed** |
| `marine_safety` | none | live (USCG/MAIB/NTSB/TSB importers) | none | depends on vendor — many not API-driven | **scheduler scope decision needed** |
| `hse` | none | live (BSEE incident scrapers under `hse/scrapers/`) | none | yes (BSEE HSE feeds) | **scheduler wiring needed** |
| `pipeline_safety` | none | live (PHMSA importers) | none | yes (HEAD PHMSA portal) | **scheduler wiring needed** |
| `eia_us` (alt module) | n/a | live, separate from `eia` | none | shares `EIA_API_KEY` | **clarify naming vs `eia_us_refresh`** |

> Note: `MODULE_INDEX.md:159-160` already documents these gaps (`canada`, `hse`, `marine_safety`, `pipeline_safety`, `lng_terminals`).

---

## 5. Issue #266–#273 next-lane classification

| Issue | Title (short) | Audit verdict | Next lane | Confidence |
|---|---|---|---|---|
| [#266](https://github.com/vamseeachanta/worldenergydata/issues/266) | EIA scheduler operationalization | **Code complete; runtime blocker** = `EIA_API_KEY`. State JSON pattern, JSONL ingest, Parquet snapshotting all implemented. | **runtime/credentials** — provision API key in env, then schedule full refresh. No code change needed. | high |
| [#267](https://github.com/vamseeachanta/worldenergydata/issues/267) | BSEE runtime download/extraction | **Code complete** for 4 datasets (platform / pipeline_permit / pipeline_location / deepwater_structure). Scheduler scope is narrower than `scripts/refresh_bsee_all.py` (4 vs 129 bins). | **runtime / network** — schedule a scoped refresh first; revisit script unification only if double-pipeline becomes a maintenance burden. | high |
| [#268](https://github.com/vamseeachanta/worldenergydata/issues/268) | Metocean Open-Meteo adapter | **Stub job; live `OpenMeteoClient` exists.** Highest-leverage stub — auth-free, public API. | **repo-remediation** — small wiring PR: replace stub body with `OpenMeteoClient.fetch_marine()` calls per `locations` from YAML. | high |
| [#269](https://github.com/vamseeachanta/worldenergydata/issues/269) | SODIR / Brazil ANP / UKCS adapters | SODIR is **complete**; Brazil ANP and UKCS are **stubs without proven endpoint contracts**. Misleading to bundle the three under one issue. | **decompose** — close out SODIR portion (#273 is the live ticket), open separate scoped issues for Brazil ANP scraping and UKCS/NSTA endpoints (overlap with #151). | medium-high |
| [#270](https://github.com/vamseeachanta/worldenergydata/issues/270) | LNG terminals scheduler config | Config is rich; job is stub. | **repo-remediation** — wire stub to `lng_terminals` module (FERC/GIE seed sources). Orchestrator should not run a full refresh until the wiring lands. | high |
| [#271](https://github.com/vamseeachanta/worldenergydata/issues/271) | output_dir wiring across jobs | **Pattern is consistent** across the 3 real jobs. Stubs accept config but never use it (irrelevant until they're implemented). | **status-quo / spot-fix on stubs at implementation time** — no cross-cutting refactor needed; consider folding into the per-stub implementation issues. | medium-high (could be reduced/closed) |
| [#273](https://github.com/vamseeachanta/worldenergydata/issues/273) | SODIR runtime endpoint contract | factmaps endpoint pattern (`/api/rest/services/DataService/data?table=<id>`) is correctly encoded in `endpoints.py` and `api_client.py`. **Latent risk**: response unwrap assumes `{"data": [...]}` envelope; schema drift would silently zero out. | **runtime probe + add envelope guard** — overnight: HEAD/GET probe; follow-up: harden `sodir_refresh.py:71` against alternative envelope keys. | high |

---

## 6. Runtime vs repo-remediation blockers

### 6.1 Repo-remediation (code/config changes)

| Blocker | Where | Severity | Issue |
|---|---|---|---|
| Stub jobs produce false `enabled: true` telemetry | 4 `_refresh.py` jobs | High — masks "skipped" as scheduled | #268 / #269 (BR, UK) / #270 |
| Metocean wiring trivially possible | `metocean_refresh.py` | High leverage | #268 |
| Brazil ANP endpoint contract unknown | `brazil_anp_refresh.py` | Medium — needs research | #269 |
| UKCS endpoint contract unknown | `ukcs_refresh.py` | Medium — overlaps #151 | #269 / #151 |
| LNG terminals stub ignores rich config | `lng_terminals_refresh.py` | Medium | #270 |
| Health monitor names ≠ `ALL_JOBS` registrations | `scripts/cron/scheduler-health.sh` (referenced by `scheduler-health-2026-W16.md`) | Medium — false negatives in health reports | **new** (no existing issue) |
| 5 source modules lack scheduler wiring | `canada`, `mexico_cnh`, `texas_rrc`, `landman`, `hse`, `marine_safety`, `pipeline_safety` | Medium-Low — depends on cadence priority | **new** (or extend MODULE_INDEX gap note) |
| SODIR envelope assumption | `sodir_refresh.py:71-72` | Low — defensive hardening | extension of #273 |

### 6.2 Runtime / environment / credentials

| Blocker | Where | Severity | Mitigation |
|---|---|---|---|
| `EIA_API_KEY` not provisioned | `eia_us_refresh` | High — blocks #266 | Provision key in env; document expected location in `.env.example` |
| Mexico CNH SIH dashboard requires Selenium | `mexico_cnh` | High — blocks scheduler wiring | Containerize Chrome+Selenium, or fall back to `datos.gob.mx` open-data CSV path |
| BSEE network reliability | `bsee_refresh` + `scripts/refresh_bsee_all.py` | Medium — already mitigated by retry+backoff | Schedule overnight; monitor `logs/scheduler/status.json` |
| SMTP alerting dormant | `scheduler_config.yml` `monitoring.smtp_*` | Low — failures still log | Provision `.env` SMTP if alerting is desired |
| Webhook dormant | `scheduler_config.yml` `monitoring.webhook_url` | Low | Optional |

### 6.3 No-blocker / already-safe

- SODIR factmaps API: public, rate-limited at 10 rps, no key required. Probe and full refresh both safe.
- Open-Meteo Marine API: public, no key, daily quota generous.
- BSEE zip endpoints: public, no key, well-instrumented timeouts.

---

## 7. Safe overnight execution sequence

Recommended ordering (each step is also detailed, with exact commands, in the companion command pack):

1. **No-op audit (this report).** Already complete — no execution needed.
2. **Help/usage probes (`[risk: no-op]`)** — one-shot text output, no network.
   - `uv run python -m worldenergydata.scheduler` (prints usage)
   - `uv run python scripts/refresh_bsee_all.py --help`
3. **Scheduler status read (`[risk: no-op]`)** — instantiates `DataScheduler`, reads YAML, reads `logs/scheduler/status.json` if present, no network.
   - `uv run python -m worldenergydata.scheduler status`
4. **Endpoint HEAD probes (`[risk: endpoint probe]`)** — non-mutating, single request each.
   - BSEE: 4 HEAD requests against `URLS` in `bsee_web.py`.
   - SODIR: 1 GET `https://factmaps.sodir.no/api/rest/services/DataService/data?table=1001&format=json` (small payload).
   - EIA: 1 GET `https://api.eia.gov/v2/` (metadata root, no key needed for catalog).
   - Open-Meteo: 1 GET marine forecast for one location, ≤1 KB.
   - GIE ALSI: 1 HEAD `https://alsi.gie.eu/api`.
5. **Dry-run plan dumps (`[risk: dry-run]`)** — no downloads, lists what *would* run.
   - `uv run python scripts/refresh_bsee_all.py --dry-run`
   - `make data-dry`
6. **Bounded BSEE single-dataset refresh (`[risk: bounded sample]`)** — one scoped dataset to validate end-to-end pipeline before broader runs.
   - `uv run python scripts/refresh_bsee_all.py --dir platstruc --workers 1`
   - Output: ~5 MB of replaced bins under `data/modules/bsee/bin/platstruc/`.
7. **(Conditional) full SODIR refresh (`[risk: full refresh candidate]`)** — only if endpoint probe in step 4 returned non-empty `data` arrays. Total payload <10 MB.
   - `uv run python -m worldenergydata.scheduler run-job sodir_refresh`
8. **(Blocked) EIA refresh** — do NOT run unless `EIA_API_KEY` is in env. The job will fail-fast otherwise.
9. **(Skip) all 4 stub jobs** — running them is a no-op and pollutes telemetry. Do not invoke `run-job metocean_refresh` etc.

Step 6 or 7 can be promoted to "approved for execution" once the orchestrator confirms the relevant probe in step 4 passed.

---

## 8. Follow-up issue candidates / revisited issues

### 8.1 New issues to file (after orchestrator review)

1. **Health monitor name reconciliation.** `scripts/cron/scheduler-health.sh` reports against `eia_weekly` / `bsee_incidents` / `sodir` / `anp` / `ukcs`, but `cli.py:ALL_JOBS` registers `*_refresh` names. Result: chronic "❌ manifest missing" false negatives in `docs/reports/scheduler-health-2026-*.md`. Fix one side or write a translation manifest.
2. **Stub-job telemetry confusion.** While stubs are still in place, mark `enabled: false` in `scheduler_config.yml` to avoid "scheduled-but-skipping" health flapping. Alternative: have stubs return a distinct status string (e.g. `"unimplemented"`) that the health monitor surfaces differently from genuine `"skipped"`.
3. **SODIR envelope hardening.** Extend [#273](https://github.com/vamseeachanta/worldenergydata/issues/273): add a defensive fallback in `sodir_refresh.py:71` for alternative envelope keys (`items`, `result`, `records`, top-level array).

### 8.2 Issues to revisit after this baseline

- **#266** — promote to "ready, awaiting credential provisioning" rather than "needs implementation".
- **#268** — reframe as a small, mechanical wiring PR; move out of "research" into "ready-to-implement".
- **#269** — split into per-region sub-issues; close the SODIR strand once #273 hardens.
- **#270** — flag as "config rich, wiring missing" so reviewers know the scope is small.
- **#271** — consider closing as "no cross-cutting work needed; address per stub at implementation time".
- **#273** — add envelope-hardening as scope (see 8.1.3) so a single PR covers contract verification + defensive parsing.

### 8.3 Adjacent issues this audit touched

- [#151](https://github.com/vamseeachanta/worldenergydata/issues/151) — UK NSTA NDR ingestion overlaps `ukcs_refresh` stub.
- [#153](https://github.com/vamseeachanta/worldenergydata/issues/153) — USCG MISLE bulk acquisition overlaps `marine_safety` (no scheduler entry yet).
- [#124](https://github.com/vamseeachanta/worldenergydata/issues/124), [#128](https://github.com/vamseeachanta/worldenergydata/issues/128) — BOEM lease/operator data; not currently a scheduler module — would be a new wiring lane.

---

*Generated 2026-04-26 under issue [#351](https://github.com/vamseeachanta/worldenergydata/issues/351). No code modified, no labels touched, no full refreshes executed. See companion command pack for executable / blocked / candidate commands.*

---

## Appendix A — Proposed final comment for #351 (orchestrator to post)

The mission permits one concise final GitHub comment on [#351](https://github.com/vamseeachanta/worldenergydata/issues/351). The harness running this audit gated `gh` in unattended mode, so the comment was not posted in-session. The body below is ready to paste verbatim:

```markdown
## Scheduler/source refresh runtime readiness — audit landed

**Artifacts (no code changed, no labels touched):**
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`
- `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md`

**Headline:** of 7 jobs registered in `scheduler/cli.py:ALL_JOBS`, only **3 perform real fetches** (`bsee_refresh`, `sodir_refresh`, `eia_us_refresh`); the other 4 are deterministic Tier-2 stubs returning `status="skipped"` while still marked `enabled: true` in `scheduler_config.yml`. `output_dir` wiring is consistent across the 3 real jobs (#271 likely closeable). Health monitor (`scheduler-health-2026-W16.md`) tracks names that don't match `ALL_JOBS` registrations — latent false-negative source not currently tied to an issue.

### Per-issue next-lane classification

| Issue | Verdict | Next lane |
|---|---|---|
| #266 EIA scheduler | code complete | runtime/credentials — provision `EIA_API_KEY` |
| #267 BSEE runtime | code complete (4 datasets in scope) | runtime/network — schedule scoped refresh |
| #268 metocean Open-Meteo | stub job; **`OpenMeteoClient` already implemented** | repo-remediation — small wiring PR |
| #269 SODIR/Brazil/UKCS bundle | SODIR done, ANP+UKCS are stubs without endpoint contracts | decompose into per-region issues |
| #270 LNG terminals | rich config, stub job | repo-remediation — wire to FERC/GIE clients |
| #271 output_dir wiring | pattern consistent in real jobs; stubs accept-but-ignore | likely closeable; spot-fix at stub-implementation time |
| #273 SODIR endpoint contract | factmaps endpoint correctly encoded; latent envelope-unwrap risk | runtime probe + envelope-hardening follow-up |

### Safe overnight envelope (executable without further approval)

- `[no-op]` scheduler help / status / config-validate
- `[dry-run]` `make data-dry`, `refresh_bsee_all.py --dry-run`
- `[endpoint-probe]` HEAD on 4 BSEE zips; bounded GET on SODIR factmaps `?table=1001`; GET on EIA v2 root, Open-Meteo marine single coord, GIE ALSI HEAD
- `[bounded-sample]` `refresh_bsee_all.py --dir platstruc --workers 1`

### Full-refresh candidates — orchestrator decision required

`run-job sodir_refresh`; `run-job bsee_refresh`; `refresh_bsee_all.py [--skip-ogor]`. All gated on the corresponding probe in Section A.5 of the command pack returning HTTP 200.

### Blocked

- `[blocked-cred]` `eia_us_refresh` — no `EIA_API_KEY` in env.
- `[blocked-runtime]` Mexico CNH SIH — needs Selenium+Chrome.
- `[blocked-impl]` `metocean_refresh`, `brazil_anp_refresh`, `ukcs_refresh`, `lng_terminals_refresh` — running them only pollutes telemetry.

### Caveat on this run

`uv run` and `gh` invocations were gated by the harness in this unattended session, so **no live probe output was captured**. All findings are from static evidence (source code, configs, existing reports). Orchestrator should re-run Section A end-to-end and update the SODIR envelope-shape note in the readiness report before greenlighting Section B.

### New follow-ups suggested

1. Health-monitor name reconciliation (no existing issue) — `scripts/cron/scheduler-health.sh` reports against `eia_weekly`/`bsee_incidents`/`sodir`/`anp`/`ukcs` while `ALL_JOBS` uses `*_refresh`.
2. Mark `enabled: false` for stub jobs (or distinct `unimplemented` status) so health doesn't flap on deterministic skips.
3. SODIR envelope-hardening as a scope extension on #273.
```

To post (single command, run from repo root):
```bash
gh issue comment 351 --body-file - <<'EOF'
<paste the markdown block above, without the surrounding backtick fence>
EOF
```
