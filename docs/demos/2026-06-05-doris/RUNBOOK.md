# Doris Group AI-Initiative Demo — Consolidated Runbook

**Demo:** 1-hour Teams call, **Fri 2026-06-05** · **Audience:** Mo Dessoukey, Doris Group
(offshore/subsea operator + engineering) · **Goal:** gauge the value and how it fits their systems.
**Tracking:** workspace-hub#2859.

This runbook turns the two per-repo readiness assessments into one rehearsed, ordered live
demo. It leads with GREEN (verified-runnable) capability, keeps every step to a single
copy-pasteable command with its expected artifact and a one-line talking point, and holds
AMBER/roadmap items to the end.

Readiness sources (read for per-domain detail):
- `worldenergydata/docs/demos/2026-06-05-doris/worldenergydata-readiness.md` (10 GREEN / 9 AMBER / 0 RED — SODIR RED fixed, see §Changes)
- `digitalmodel/docs/demos/2026-06-05-doris/digitalmodel-readiness.md` (17 GREEN / 5 AMBER / 0 RED)

All steps **smoke-verified end-to-end on this machine on 2026-05-28** (observed values below).

---

## 0. Pre-flight (do once, before the call)

Two repos, two virtualenvs. This machine runs codex-under-Claude; `uv run` may fail because
`~/.cache/uv` is read-only — prefer the repo `.venv/bin/python` shown below (or
`UV_CACHE_DIR=/tmp/uv-cache uv run ...`).

```bash
# worldenergydata env preamble (prefix every WED step with this)
cd /mnt/local-analysis/worldenergydata
export WED='PYTHONPATH=src:../assetutilities/src MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg'
# digitalmodel env preamble
cd /mnt/local-analysis/digitalmodel
export DM='PYTHONPATH=src'
```

Pre-flight checklist:
- [ ] Network reachable (metocean + SODIR pull live; both have cached fallbacks).
- [ ] `worldenergydata/.venv` and `digitalmodel/.venv` present.
- [ ] BSEE well CSV present: `worldenergydata/data/modules/bsee/current/wells/well_data.csv`.
- [ ] Open the two HTML artifacts in a browser tab in advance (lower_tertiary portfolio; subsea cross-section).
- [ ] Dry-run §1–§2 leads once; they are the parts most worth being crisp on.

---

## 1. Data & economics story (worldenergydata) — LEAD HERE

Run from `/mnt/local-analysis/worldenergydata`. Prefix each command with `env $WED`.

| # | Domain | Command | Expected artifact / observed | Talking point |
|---|--------|---------|------------------------------|---------------|
| 1.1 | **bsee** — GoM production | `env $WED .venv/bin/python notebooks/quickstart_bsee.py` | Loads **57,281** GoM well records (19 cols) + 100-row production sample; renders water-depth/operator/spud-year plots | "We start from the real Gulf of Mexico well inventory — operators, water depth, spud activity — not a toy dataset." |
| 1.2 | **metocean** — design conditions (live) | `env $WED .venv/bin/python - <<'PY'`<br>`from worldenergydata.metocean.clients.open_meteo_client import OpenMeteoClient`<br>`c=OpenMeteoClient(); r=c.fetch_forecast(28.5,-88.5,forecast_days=1)`<br>`print(r.records_count, r.source.value, r.data[0].wave_height_m, r.data[0].current_speed_ms)`<br>`PY` | **24** hourly records for GoM (28.5,-88.5); first row ~**0.98 m** wave, **1.0 m/s** current. No API key. | "Live, no-key metocean — wave/wind/current for any coordinate, the design-condition input subsea engineering starts from." |
| 1.3 | **fdas** — economics | `env $WED .venv/bin/python notebooks/quickstart_fdas.py` | NPV @10% **$10.8M**, IRR **10.32%**, MIRR **73.88%**, payback **9.0 yr**, + sensitivity & cashflow waterfall | "Decision support: NPV/IRR/MIRR/payback and sensitivity — the economics layer over the field data." |
| 1.4 | **lower_tertiary** — 10-field portfolio | `env $WED .venv/bin/python -m worldenergydata lower-tertiary portfolio-economics --output-csv docs/demos/2026-06-05-doris/artifacts/lower_tertiary_portfolio.csv --output-html docs/demos/2026-06-05-doris/artifacts/lower_tertiary_portfolio.html` | **10** GoM Lower Tertiary fields (Anchor, Big Foot, …), total cum capex **$55,500M**; writes CSV + HTML into the repo | "Portfolio economics across a real 10-field GoM deepwater play — capex, NPV per field, price sensitivity." Open the HTML. |
| 1.5 | **vessel_fleet** — construction/riser assets | `env $WED .venv/bin/python - <<'PY'`<br>`import pandas as pd`<br>`print(pd.read_csv('data/modules/vessel_fleet/curated/construction_vessels.csv').iloc[:,0].head().to_list())`<br>`PY` | **17** construction vessels (Sleipnir, Thialf, Balder, Aegir, Pioneering Spirit), **36** riser components | "Pivot from reservoir economics to execution: the heavy-lift / construction fleet and riser equipment for installation planning." |
| 1.6 | **vessel_hull_models** — hull geometry | `env $WED .venv/bin/python - <<'PY'`<br>`from pathlib import Path; from worldenergydata.vessel_hull_models.geometry.obj_parser import OBJParser`<br>`print(OBJParser().parse(Path('data/modules/vessel_hull_models/hulls/sea_cypress.obj')).get_stats())`<br>`PY` | `sea_cypress.obj`: **13,536** vertices, **17,720** faces, ~22.9 × 4.3 × 8.6 m | "We carry vessel geometry too — hull meshes feed seakeeping / hydrodynamics in the engineering side." |
| 1.7 | **sodir** — Norway (NCS), live | `env $WED .venv/bin/python notebooks/quickstart_sodir.py` | **142** NCS fields; top operators **Equinor 61, Aker BP 36**; **300** field-year production rows (1977–2026). Live SODIR factpages CSV + committed snapshot fallback. | "Same model, Norwegian shelf — live SODIR field operators and production. Directly relevant to a Norway-rooted operator." |

> **SODIR was the only RED** in the original assessment (stale import + dead factmaps endpoint).
> It is **fixed** and now a verified GREEN — see §Changes. For a guaranteed-offline run, the
> snapshot under `data/modules/sodir/` is used automatically (`refresh=False` default); add
> `refresh=True` in the helper to pull fresh live data.

---

## 2. Engineering story (digitalmodel)

Run from `/mnt/local-analysis/digitalmodel`. Prefix each command with `env $DM`. The
test-suite commands double as live capability checks (they exercise the real modules); the
"show" rows open a pre-built artifact rather than running a solver.

| # | Domain | Command | Expected / observed | Talking point |
|---|--------|---------|---------------------|---------------|
| 2.1 | **field_development** — concept/workflow | `env $DM .venv/bin/python -m pytest -q tests/field_development/test_workflow.py` | 30 passed — tieback/FPSO/platform concept-selection workflow | "Lifecycle framing first: concept selection, tieback vs FPSO vs platform, with cost/schedule structure." |
| 2.2 | **hydrodynamics** — wave spectra + RAOs | `env $DM .venv/bin/python -m pytest -q tests/unit/hydrodynamics/test_wave_spectra_extended.py tests/unit/hydrodynamics/test_rao_analysis.py` | 59 + 69 passed | "Wave spectra and RAO analysis — the response engine for any floating or installed system." |
| 2.3 | **naval_architecture** — seakeeping | `env $DM .venv/bin/python -m pytest -q tests/naval_architecture/test_seakeeping.py` | 15 passed | "Vessel response, seakeeping, maneuvering for floating platforms and marine ops." |
| 2.4 | **orcaflex** — model library (show) | `env $DM .venv/bin/python -m pytest -q tests/orcaflex/test_model_builder.py` + open `docs/domains/orcaflex/library/` | 14 passed; library: anchors, buoys, connectors, line_types, templates, model_library | "Risers, moorings, installation — we generate OrcaFlex model libraries. Live commercial-solver runs need a licensed workstation; here we show the model-building workflow." |
| 2.5 | **structural / fatigue / CP / asset_integrity** — integrity layer | `env $DM .venv/bin/python -m pytest -q tests/structural/pipe_capacity/test_pipe_capacity_common.py tests/test_fatigue_basic.py tests/cathodic_protection/test_anode_sizing.py tests/asset_integrity/test_rsf_calculations.py` | 103 + 5 + 15 + 28 passed | "The integrity/design-code layer: pipe capacity, fatigue screening, anode sizing (DNV/ISO/API), and API 579 FFS — exactly the subsea integrity workflow." |
| 2.6 | **drilling_riser** — stack-up | `env $DM .venv/bin/python -m pytest -q tests/drilling_riser/test_stackup_doc_verified.py` | 15 passed (doc-verified test vectors) | "Riser stack-up and operability for drilling campaigns." |
| 2.7 | **solvers/openfoam** — marine CFD case-gen | `env $DM .venv/bin/python -m pytest -q tests/solvers/openfoam/test_case_builder.py tests/solvers/openfoam/test_marine_solvers.py` | 26 + 25 passed | "OpenFOAM case generation for marine current/wave CFD — framework, positioned as case-building rather than a turnkey solver scene." |
| 2.8 | **subsea** — cross-section report (show) | open `docs/subsea/cross_sections/offshore_cross_section_report.html` | Pre-built HTML cross-section report | "Subsea cross-section deliverable — show the report rather than running the broad subsea test set (see roadmap)." |

---

## 3. Safety appendix (worldenergydata) — only if time remains

| # | Domain | Command | Observed | Talking point |
|---|--------|---------|----------|---------------|
| 3.1 | **hse** | `env $WED .venv/bin/python -m pytest --noconftest -q tests/unit/hse/test_bsee_hse_db_import.py` | Local DB: **97,993** incidents, 51,487 toxic-release, 66,561 violation rows | "A real HSE incident corpus for risk/safety context." |
| 3.2 | **marine_safety** | `env $WED .venv/bin/python notebooks/quickstart_marine_safety.py` | 20 fatality / 15 foundering / 30 hatch incidents; pre-built HTML reports | "Curated marine-safety datasets + prebuilt reports." |
| 3.3 | **pipeline_safety** | `env $WED .venv/bin/python -c "import pandas as pd; print(len(pd.read_csv('data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv')))"` | **2,795** pipeline-incident rows | "Secondary pipeline-safety context." |
| 3.4 | **lng_terminals** | `env $WED .venv/bin/python -c "from worldenergydata.lng_terminals.query import LngTerminalClient, LngTerminalQuery; r=LngTerminalClient().query(LngTerminalQuery(region=['north_america'], terminal_type=['export'])); print(r.total_count, r.total_capacity_mtpa)"` | **8** NA export terminals, **121.8 MTPA** | "Infrastructure add-on: global LNG terminal query." |

---

## 4. Roadmap / hold (mention, don't run live)

These have working test/logic but are not buyer-ready live artifacts — frame as roadmap if asked.

- worldenergydata AMBER: `ukcs`, `brazil_anp`, `mexico_cnh`, `eia_us`, `safety_analysis`,
  `canada`, `texas_rrc`, `landman` (test/model logic; need cached datasets or live keys/scraping),
  and `well_production_dashboard` (CLI currently emits placeholder zeros — **not** demoed; if run,
  point output into the repo: `--output docs/demos/2026-06-05-doris/artifacts/well_dashboard.json`).
- digitalmodel AMBER: `subsea` broad VIV/pipeline tests (broken import/fixtures — use the §2.8 HTML
  instead), `marine_ops` (benchmark mismatches), `orcawave` (stale import path; needs Windows/OrcaWave),
  `nde` (optional `the_well` dep missing), `reservoir` (pandas FutureWarning-as-error).

---

## 5. Changes made for this demo (2026-05-28)

- **SODIR RED → GREEN.** Added `src/worldenergydata/sodir/factpages.py` — a self-contained
  client for SODIR's live factpages tableview CSV reports (the legacy `api_client` factmaps
  path returns HTTP 400). Rewrote `notebooks/quickstart_sodir.py` to use it (was importing a
  non-existent `SodirDatasets`, which masked the failure). Committed snapshots under
  `data/modules/sodir/` give a reproducible offline fallback. Added `tests/unit/sodir/test_factpages.py`
  (6 tests, network-free). The legacy `api_client`/`endpoints` factmaps path is left untouched
  (still used by mocked tests, `bsee` cross-regional, scheduler) and is a separate cleanup item.
- **/tmp artifacts re-pointed.** `lower_tertiary` portfolio CSV/HTML now generate into
  `docs/demos/2026-06-05-doris/artifacts/` (was `/tmp`), so they are reproducible and committed.
- **Smoke-verified** every §1 and §2 step end-to-end on this machine (observed values above):
  worldenergydata leads + SODIR + factpages tests; digitalmodel 404 tests passed across the
  prioritized greens; show-artifacts confirmed present.
