# WorldEnergyData Scheduler — Overnight Command Pack — 2026-04-26

**Issue:** [#351](https://github.com/vamseeachanta/worldenergydata/issues/351).
**Companion:** `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`.
**Working directory for every command below:** `/mnt/local-analysis/workspace-hub/worldenergydata`.

## Risk legend

| Tag | Meaning | Allowed in this overnight envelope? |
|---|---|---|
| `[no-op]` | Reads only — help text, status print, file inspection. No network, no disk write. | YES — always safe |
| `[dry-run]` | Existing `--dry-run` / plan-only mode of an in-repo script. No network downloads, no destructive writes. | YES — always safe |
| `[endpoint-probe]` | Single HEAD or small bounded GET against a documented public endpoint. No auth needed. ≤10 KB response. | YES — bounded by rule |
| `[bounded-sample]` | Real fetch but scoped to one small dataset / one location / one record. ≤10 MB total. | YES if probe in same source class succeeded |
| `[full-refresh]` | Full source refresh; documented runtime, public endpoint, no auth. May be tens of MB. | **Candidate only — orchestrator decision** |
| `[blocked-cred]` | Code complete but missing required credential (env var or secret). | **Do not run** until credential provisioned |
| `[blocked-runtime]` | Needs additional host capability (Selenium, large RAM, geckodriver). | **Do not run** in default overnight host |
| `[blocked-impl]` | Repo-side implementation missing (stub returns `skipped`). | **Do not run** — would be a no-op masquerading as work |

> **Hard rule for this orchestrator pass:** only `[no-op]`, `[dry-run]`, `[endpoint-probe]`, and `[bounded-sample]` may execute without further approval. `[full-refresh]` requires the orchestrator to greenlight per-source after seeing probe output.

---

## Section A — Run-now safe (no further approval)

### A.1 Help / usage / version probes — `[no-op]`

```bash
uv run python -m worldenergydata.scheduler
```
Expected: usage text printed, exits 0. No network, no writes.

```bash
uv run python scripts/refresh_bsee_all.py --help
```
Expected: argparse help text, exits 0.

```bash
uv run python -c "from worldenergydata.scheduler.cli import ALL_JOBS; [print(j.name) for j in ALL_JOBS]"
```
Expected: 7 names — `bsee_refresh`, `sodir_refresh`, `eia_us_refresh`, `brazil_anp_refresh`, `ukcs_refresh`, `metocean_refresh`, `lng_terminals_refresh`.

### A.2 Scheduler status read — `[no-op]`

```bash
uv run python -m worldenergydata.scheduler status --config config/scheduler/scheduler_config.yml
```
Expected: JSON dict with `jobs.<name>.{last_run, last_result, next_run}` for all 7 jobs plus `staleness`/`alerts` keys. Reads `logs/scheduler/status.json` if present; tolerates absence. No network.

### A.3 Config validation — `[no-op]`

```bash
uv run python -c "from worldenergydata.scheduler.config import load_config, validate_config; c = load_config('config/scheduler/scheduler_config.yml'); validate_config(c); print('OK', len(c.jobs), 'jobs', sum(1 for j in c.jobs if j.get('enabled', True)), 'enabled')"
```
Expected: `OK 7 jobs 7 enabled`.

### A.4 BSEE refresh dry-run — `[dry-run]`

```bash
uv run python scripts/refresh_bsee_all.py --dry-run
```
Expected: log lines like `[<bin_dir>] DRY-RUN: would download <url> → <N> stubs to replace`. No network downloads — only filesystem stub-detection. Final summary lists Skipped=N where N = total specs.

```bash
make data-dry
```
Equivalent to the above via the Makefile.

### A.5 Endpoint HEAD probes — `[endpoint-probe]`

> Each probe is one HTTP request, no auth, response inspected for status and `Content-Length` only. **Do not pipe response bodies anywhere except stdout/log.**

```bash
# BSEE — 4 zip endpoints (public, no auth)
uv run python -c "import requests; [print(u, requests.head(u, timeout=15, allow_redirects=True).status_code, requests.head(u, timeout=15, allow_redirects=True).headers.get('Content-Length','?')) for u in ['https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip','https://www.data.bsee.gov/Pipeline/Files/PipePermRawData.zip','https://www.data.bsee.gov/Platform/Files/PermStrucRawData.zip','https://www.data.bsee.gov/Pipeline/Files/PipeLocAllRawData.zip']]"
```
Expected: HTTP 200 + Content-Length in MB range for each.

```bash
# SODIR factmaps — single bounded GET (table=1001 = blocks; small payload)
uv run python -c "import requests; r = requests.get('https://factmaps.sodir.no/api/rest/services/DataService/data', params={'table':'1001','format':'json'}, timeout=30); print(r.status_code, len(r.content), 'bytes', list(r.json().keys())[:5] if r.headers.get('Content-Type','').startswith('application/json') else 'non-json')"
```
Expected: `200 <bytes> ['data', ...]` (or whatever the factmaps envelope is). Records #273 envelope shape live for the readiness report follow-up.

```bash
# EIA v2 root catalog — no key needed for the discovery endpoint
uv run python -c "import requests; r = requests.get('https://api.eia.gov/v2/', timeout=30); print(r.status_code, r.headers.get('Content-Type','?'), len(r.content))"
```
Expected: 200 + JSON. Confirms upstream reachable independent of `EIA_API_KEY`.

```bash
# Open-Meteo Marine — single GOM coord, ≤1 KB response
uv run python -c "import requests; r = requests.get('https://marine-api.open-meteo.com/v1/marine', params={'latitude':28.5,'longitude':-88.5,'hourly':'wave_height','forecast_days':1}, timeout=30); print(r.status_code, len(r.content))"
```
Expected: 200 + small JSON. Validates #268 upstream contract before wiring PR.

```bash
# GIE ALSI (LNG) — public, no auth, single HEAD
uv run python -c "import requests; r = requests.head('https://alsi.gie.eu/api', timeout=15, allow_redirects=True); print(r.status_code)"
```
Expected: 200/301/302. Validates #270 source-side reachability.

### A.6 Bounded sample fetch — `[bounded-sample]`

> Run only **after** A.5 BSEE HEAD probes returned 200 for the chosen URL. Single small dataset, ≤6 MB payload, single worker.

```bash
uv run python scripts/refresh_bsee_all.py --dir platstruc --workers 1
```
Expected: ≤30s runtime; replaces LFS stubs in `data/modules/bsee/bin/platstruc/` with real pickled DataFrames. Idempotent — re-run is a no-op once real data is in place. Output path is gitignored (BSEE binaries excluded per `CLAUDE.md` rules).

---

## Section B — Full refresh candidates (orchestrator decision required)

> Do **not** run without explicit go-ahead from the orchestrator. Each runs against a real public endpoint with no destructive side effects beyond writing the configured `output_dir`.

### B.1 SODIR full refresh — `[full-refresh]`

```bash
uv run python -m worldenergydata.scheduler run-job sodir_refresh --config config/scheduler/scheduler_config.yml
```
Touches: `https://factmaps.sodir.no` (3 GETs).
Writes: `data/modules/sodir/sodir_blocks.parquet`, `sodir_wellbores.parquet`, `sodir_fields.parquet`, `_metadata.json`.
Expected runtime: <30s.
Pre-condition: A.5 SODIR probe returned HTTP 200 + non-empty `data`.
Risk: low — public, rate-limited, small payload, partial-failure tolerant.

### B.2 BSEE scheduler-scope refresh — `[full-refresh]`

```bash
uv run python -m worldenergydata.scheduler run-job bsee_refresh --config config/scheduler/scheduler_config.yml
```
Touches: 4 BSEE zip URLs (`platform`, `pipeline_permit`, `pipeline_location`, `deepwater_structure`).
Writes: `data/modules/bsee/bsee_*.parquet` + `_metadata.json`.
Expected runtime: 2–5 minutes.
Pre-condition: A.5 BSEE HEAD probes returned 200 for all 4 URLs.
Risk: low-medium — BSEE has been intermittently slow; retry/backoff already in place.

### B.3 BSEE full LFS-stub replacement — `[full-refresh]`

```bash
uv run python scripts/refresh_bsee_all.py --workers 4
```
Touches: 129 BSEE bin specs across many URLs, including OGOR-A yearly files.
Writes: `data/modules/bsee/bin/<dir>/*.bin` (pickled DataFrames). Skips already-real bins.
Expected runtime: ~8 minutes (per `Makefile` `data:` comment).
Pre-condition: BSEE HEAD probes from A.5 succeeded.
Risk: medium — much larger volume than B.2; OGOR-A files individually 100 MB+. Disk usage ~300 MB.

### B.4 BSEE full refresh, skip OGOR-A (faster) — `[full-refresh]`

```bash
uv run python scripts/refresh_bsee_all.py --workers 4 --skip-ogor
```
Same as B.3 minus the OGOR-A yearly production files. Use when bandwidth is limited.

---

## Section C — Blocked: missing credentials / runtime — `[blocked-cred]` / `[blocked-runtime]`

### C.1 EIA refresh — `[blocked-cred]`

```bash
# DO NOT RUN until EIA_API_KEY is in env
uv run python -m worldenergydata.scheduler run-job eia_us_refresh --config config/scheduler/scheduler_config.yml
```
Blocker: `EIA_API_KEY` env var not provisioned in the overnight host. Without it `EIAFeedClient` will fail. Resolution: provision key (free tier from `https://www.eia.gov/opendata/register.php`), then promote to `[full-refresh]`.

### C.2 Mexico CNH SIH dashboard — `[blocked-runtime]`

```bash
# DO NOT RUN — requires Selenium + Chrome + ChromeDriver
# Path: src/worldenergydata/mexico_cnh/<scrapers>
```
Blocker: `config/mexico_cnh.yml` declares `requires_selenium: true`. The headless Chrome stack is not part of this overnight host. Open-data CSV path via `https://datos.gob.mx` is API-driven and would be the cleaner first wire-up for a future scheduler entry — but no scheduler entry exists today.

---

## Section D — Blocked: stub jobs — `[blocked-impl]`

> Each of the four jobs below currently returns `JobResult(status="skipped")` deterministically. Running them produces a misleading green "skipped" row in `logs/scheduler/status.json`, suggesting the scheduler ran when it did not. **Do not run.** Treat these as implementation work, not overnight execution.

```bash
# DO NOT RUN — stub returns skipped
uv run python -m worldenergydata.scheduler run-job metocean_refresh
# DO NOT RUN — stub returns skipped
uv run python -m worldenergydata.scheduler run-job brazil_anp_refresh
# DO NOT RUN — stub returns skipped
uv run python -m worldenergydata.scheduler run-job ukcs_refresh
# DO NOT RUN — stub returns skipped
uv run python -m worldenergydata.scheduler run-job lng_terminals_refresh
```

Issue mapping:
- `metocean_refresh` → [#268](https://github.com/vamseeachanta/worldenergydata/issues/268). `OpenMeteoClient` is implemented; wire it.
- `brazil_anp_refresh` → [#269](https://github.com/vamseeachanta/worldenergydata/issues/269). Endpoint contract not yet established.
- `ukcs_refresh` → [#269](https://github.com/vamseeachanta/worldenergydata/issues/269) / [#151](https://github.com/vamseeachanta/worldenergydata/issues/151). NSTA endpoints not yet established.
- `lng_terminals_refresh` → [#270](https://github.com/vamseeachanta/worldenergydata/issues/270). Wire to FERC/GIE/GIIGNL clients.

---

## Section E — Expected output paths

| Step | Path | Purpose |
|---|---|---|
| A.2 | `logs/scheduler/status.json` (read-only here) | Existing scheduler status snapshot |
| A.4 / A.6 / B.3 / B.4 | `data/modules/bsee/bin/<dir>/*.bin` | BSEE LFS-stub replacements (gitignored) |
| B.1 | `data/modules/sodir/sodir_{blocks,wellbores,fields}.parquet`, `_metadata.json` | SODIR refresh output |
| B.2 | `data/modules/bsee/bsee_{platform_structures,pipeline_permits,pipeline_locations,deepwater_structures}.parquet`, `_metadata.json` | BSEE scheduler-scope refresh output |
| C.1 (when unblocked) | `data/modules/eia/eia_{petroleum_weekly,gas_storage_weekly}.{jsonl,parquet}`, `eia_ingestion_state.json`, `_metadata.json` | EIA incremental ingest |

> The `data/modules/**` tree is gitignored per `worldenergydata/CLAUDE.md` ("BSEE binary (~300MB) not in git — run `make data`"). Generated artifacts persist on disk for downstream consumers but never enter git.

---

## Section F — Rollback / cleanup notes

- **Probes (A.1 – A.5)** — no cleanup needed; nothing was written.
- **A.6 / B.2 / B.3 / B.4 (BSEE)** — to roll back to LFS-stub state: `git lfs pull` will repopulate stubs; or `rm -rf data/modules/bsee/bin/<dir>` and re-run `git checkout -- data/modules/bsee/bin/<dir>` to restore stubs from LFS index. Operator should consider real data more durable than stubs and avoid rolling back without reason.
- **B.1 (SODIR)** — to roll back: `rm data/modules/sodir/sodir_*.parquet data/modules/sodir/_metadata.json`. The factmaps API will reproduce the same data on rerun.
- **C.1 (EIA)** — incremental: state lives in `data/modules/eia/eia_ingestion_state.json`. To force a from-scratch re-ingest after a partial run, `rm -f data/modules/eia/eia_*.{jsonl,parquet,_metadata.json}` *and* `rm data/modules/eia/eia_ingestion_state.json`. Otherwise the next run picks up where the previous left off.
- **Logs** — `logs/scheduler/status.json` is overwritten on each `run-job`. Prior content is not preserved; if needed, snapshot before rerunning.
- **No git modifications** — none of the commands above commit, stage, or modify tracked files. The only repo-level artifact is the two reports under `docs/reports/` produced by the audit author.

---

## Section G — Quick reference table

| Step | Command | Risk | Exec? |
|---|---|---|---|
| A.1a | `uv run python -m worldenergydata.scheduler` | `[no-op]` | YES |
| A.1b | `uv run python scripts/refresh_bsee_all.py --help` | `[no-op]` | YES |
| A.2 | `uv run python -m worldenergydata.scheduler status` | `[no-op]` | YES |
| A.3 | `uv run python -c "...load_config..."` | `[no-op]` | YES |
| A.4a | `uv run python scripts/refresh_bsee_all.py --dry-run` | `[dry-run]` | YES |
| A.4b | `make data-dry` | `[dry-run]` | YES |
| A.5a | BSEE 4× HEAD probes | `[endpoint-probe]` | YES |
| A.5b | SODIR factmaps single GET | `[endpoint-probe]` | YES |
| A.5c | EIA v2 root GET | `[endpoint-probe]` | YES |
| A.5d | Open-Meteo marine single GET | `[endpoint-probe]` | YES |
| A.5e | GIE ALSI HEAD | `[endpoint-probe]` | YES |
| A.6 | `refresh_bsee_all.py --dir platstruc --workers 1` | `[bounded-sample]` | YES |
| B.1 | `run-job sodir_refresh` | `[full-refresh]` | **decision** |
| B.2 | `run-job bsee_refresh` | `[full-refresh]` | **decision** |
| B.3 | `refresh_bsee_all.py --workers 4` | `[full-refresh]` | **decision** |
| B.4 | `refresh_bsee_all.py --workers 4 --skip-ogor` | `[full-refresh]` | **decision** |
| C.1 | `run-job eia_us_refresh` | `[blocked-cred]` | NO |
| C.2 | Mexico CNH Selenium | `[blocked-runtime]` | NO |
| D.x | `run-job {metocean,brazil_anp,ukcs,lng_terminals}_refresh` | `[blocked-impl]` | NO |

---

*Generated 2026-04-26 under issue [#351](https://github.com/vamseeachanta/worldenergydata/issues/351). All commands above were authored from static evidence — none were executed in this audit pass. The harness used by this session gated `uv run` invocations and `gh` reads, so live probe output is not yet captured. Orchestrator: please re-run Section A end-to-end before deciding on Section B.*
