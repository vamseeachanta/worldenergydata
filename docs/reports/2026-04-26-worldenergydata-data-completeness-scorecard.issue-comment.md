<!-- Posting blocked by sandbox permission denial on `gh issue comment 350`.
     Orchestrator: post the body below to https://github.com/vamseeachanta/worldenergydata/issues/350 -->

## Data Completeness & Freshness Scorecard — 2026-04-26

**Mode:** audit-only, no downloads, no commits. Artifacts left untracked for orchestrator review.

### Artifacts
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`

### Headline
- `MODULE_INDEX.md` declares **27** modules; `data/catalog.yaml` enumerates **12 / 44 datasets / 10.5 MB**; `src/worldenergydata/` has **47** sub-packages.
- `data/modules/` totals ~389 MB on disk: bsee (151 MB) + marine_safety (108 MB) + hse (58 MB) + vessel_hull_models (38 MB) account for >97%.
- Scheduler defines **7 jobs**; **5 of them** point at output_dirs that do not exist on disk (sodir, eia_us, metocean, brazil_anp, ukcs).

### Top 10 Data Completeness Gaps
1. **sodir / ukcs / brazil_anp / mexico_cnh / canada / texas_rrc / eia_us / metocean / landman** — declared modules with **no `data/modules/<name>/` directory**.
2. **BSEE `current/*.csv` 100-row stubs** — 12 of 16 CSVs are sample stubs from 2025-07-31; downstream fdas + dashboards consume stub data silently.
3. **Catalog drift** — 15 declared modules absent from `data/catalog.yaml`; generator (`scripts/generate_data_catalog.py`) does not enumerate full source tree.
4. **Scheduler output_dir mismatch** — `eia_us_refresh.output_dir = data/modules/eia` (module is `eia_us`); 4 other jobs land in non-existent dirs.
5. **Marine safety SQLite DBs >180 days stale** — `marine_safety.db` 2025-10-08, `database/marine_safety.db` 2025-10-06.
6. **Marine safety scrape failures** — 4 zero-byte HTML files (USCG MISLE, OSHA fatalities, PHMSA pipeline, PHMSA hazmat) + 22 IMO GISIS placeholder pages.
7. **EIA API key not provisioned** — scheduler job enabled, `api_key: null` in `config/scheduler/scheduler_config.yml`.
8. **`oil_price` and `wind` >270 days stale** — last touched 2025-07-31, no scheduler job.
9. **HSE/pipeline_safety opaque in catalog** — SQLite blobs (60 MB hse, 25 MB raw pipeline) with no row-count visibility.
10. **Empty top-level dirs** — `data/bsee/`, `data/marine_safety/`, `data/processed/`, `data/results/` are 0 bytes; intent unclear (governance stub vs cruft).

### Safe Refresh Candidates (overnight-safe)
- `uv run python scripts/generate_data_catalog.py --report` (catalog regeneration)
- `uv run python -m worldenergydata.scheduler.staleness` (cadence drift surface)
- `curl -sI` endpoint probes for the 7 scheduled sources
- Bounded NDBC pull (single station, 24h) to validate `metocean_refresh` path
- Bounded GIIGNL refresh for `lng_terminals`
- Re-download `oil_price` xls (~90 KB) and `wind` zips (~7 MB)

### Blocked / Credential-required
- **eia_us** — needs `EIA_API_KEY` env var
- **ukcs (NSTA)** — session-cookie auth on bulk endpoints
- **canada (Petrinex)** — registered account required
- **mexico_cnh (SIH)** — JS-rendered, login-gated
- **marine_safety (IMO GISIS)** — login-gated, evidence in `no_results_*.html`
- **marine_safety (USCG MISLE)** — bulk URL 404 since portal redesign
- **metocean (CMEMS)** — Copernicus Marine credentials
- **landman / texas_rrc / mexico_cnh** — implementation needed (no scheduler job or rate-limit-safe path)

Full table, follow-up issue candidates, and bounded command list in the scorecard markdown.
