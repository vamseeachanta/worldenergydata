# worldenergydata — Buyer-Facing Capability Matrix

- **Issue:** [#364](https://github.com/vamseeachanta/worldenergydata/issues/364)
- **Last updated:** 2026-06-19
- **Source audit:** `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` (repo-grounded #349 audit)
- **Companion artifacts:** `data/capability-matrix.json` (machine-readable), GTM review `docs/reports/gtm/2026-05-04-worldenergydata-gtm-candidate-review.md`

## How to read this

Every capability is placed in exactly one of three buyer-facing tiers. The tiering is **conservative**: a capability is only **Production-Ready** when the repo ships working code *and* real (non-sample) data or a self-contained working demo, with evidence cited. Where the repo ships code but only sample-row data, an empty data catalog, or a known blocker, it is downgraded — and the reason is stated. This avoids overclaiming readiness to prospective buyers.

| Tier | Badge | Meaning for a buyer |
|------|-------|---------------------|
| **Production-Ready** | 🟢 | Working code + real data or a self-contained demo today. Can be shown/sold now. |
| **Sample-Only** | 🟡 | Code path works but data shipped is sample-row / seed / live-fetched-on-demand, or a known import/CLI blocker exists. Demo possible with caveats; not a turnkey data product yet. |
| **Roadmap** | 🔴 | Stub, empty data catalog, no wired source, or off-manifest/unindexed. Not a GTM asset today. |

> **Conservatism note vs. the issue's draft tiers.** Issue #364's initial population proposed BSEE-current, Vessel Fleet, Pipeline, and Subsea as "Tier A — Production Ready." The 2026-04-26 repo-grounded audit shows most BSEE catalog rows are 100-row *samples* (only `well_data.csv` is full at ~57k rows), Vessel Fleet has **no registered CLI**, and Pipeline/Subsea are small (14–43 row) reference seeds that are *not even in the module manifest*. They are therefore tiered more conservatively below, with the discrepancy called out.

---

## Tier 🟢 Production-Ready

Working code plus real data or a self-contained client-grade demo. Evidence cited for each.

| Capability | Tier | Evidence (file / module / report) | Buyer-facing note |
|---|---|---|---|
| FDAS field-development economics (NPV / IRR / MIRR / payback) | Production-Ready | `worldenergydata.fdas.api.EconomicsQuery`; demo `docs/reports/gtm/2026-05-04-worldenergydata-gtm-candidate-review.md` + `reports/gtm/2026-05-04-fdas-field-development-economics.html` (63 KB, 4 scenarios) | Self-contained economics engine; client-grade interactive report exists today. No external data required. |
| Production forecasting — Arps decline (hyperbolic fit, EUR, 240-month forecast) | Production-Ready | `worldenergydata.production.forecast.decline.ArpsDeclineCurve`; GTM review §1, §3 | Full fit → forecast → plot cycle works standalone (synthetic/seeded input). Pairs with FDAS for a complete economics demo. |
| Marine safety / IMO GISIS incident analytics | Production-Ready | `worldenergydata.marine_safety` (51 tests; `cli.py` registered as `marine-safety`); `reports/IMO_GISIS_Executive_Report.html` (133 KB, 13,160 records, 8 Plotly charts) | Real loaded dataset (13,160 casualties, 125 yrs) + finished interactive HTML. Strongest demo-ready data product. Caveat: USCG MISLE live feed gap (#153). |
| FDAS enhanced well dataset (GoM) | Production-Ready | `data/modules/fdas/enhanced/wells/well_data_enhanced.csv` (~57,281 wells, derived from BSEE); `worldenergydata.fdas` (13 tests, CLI registered) | One genuinely full-size shipped dataset that feeds the economics engine. Underpins the BSEE-current value prop without the BSEE import blocker. |
| Safety analysis engine (taxonomy / NLP / risk index) | Production-Ready | `worldenergydata.safety_analysis` (`adapters/`, `nlp/`, `risk_index/`, `taxonomy/`, `cli.py`; 38 tests; `safety-analysis` registered) | Mature analysis surface with CLI; consumes HSE/marine inputs. Code maturity is high; downstream HSE *data* is the gating item (see Sample-Only). |
| SODIR (Norway) production data extractor | Production-Ready | `worldenergydata.sodir` (`api_client.py`, `processors/`, `production/`, `npv_norway.py`; 26 tests; CLI registered; daily scheduler) | Wired end-to-end (live API + scheduler). Data fetched at runtime rather than shipped, but the path is operational. |
| Metocean data + statistics (NDBC / CO-OPS / Open-Meteo / extreme-value) | Production-Ready | `worldenergydata.metocean` (`clients/`, `statistics/`, `extrapolation/`, `cli.py`; 34 tests; `metocean` + `ndbc` registered; daily scheduler) | Live multi-source fetch + design-criteria statistics, scheduled. Demo runs live rather than from shipped data. |

## Tier 🟡 Sample-Only

Code path works, but shipped data is sample-row / seed / live-on-demand, or a known import/CLI blocker prevents turnkey use. Demo-able with caveats.

| Capability | Tier | Evidence (file / module / report) | Buyer-facing note |
|---|---|---|---|
| BSEE current GoM well/production data | Sample-Only | `worldenergydata.bsee` (`cli/commands/bsee.py`; 100 tests; CLI registered). Catalog: 19 datasets in `data/modules/bsee/`, **most are 100-row samples**; only `well_data.csv` (~57k) and `Paleowells.csv` (6,362) are full | Headline asset, but most CSVs shipped in git are samples — full BSEE bulk needs `make data`. Issue #364 listed this as Tier A; audit downgrades it (sample rows). Also see import-hang blocker below. |
| BSEE field-analysis module (programmatic) | Sample-Only | `worldenergydata.bsee` field analysis; GTM review §4: import hangs 30+ s when 300 MB binary absent (blocker #384) | Works with full data present but module-level import hang blocks turnkey demos. Fix tracked (#384/#359). Not "production" until the import path is lazy and the binary is wired. |
| Vessel Fleet (offshore rigs / drilling-rig registry) | Sample-Only | `worldenergydata.vessel_fleet` (full pipeline: `loaders/`, `parsers/`, `dedup/`, `quality/`; 34 tests). Catalog: 7 datasets incl. `drilling_rigs.csv` (2,210 rows). **No CLI registered** | Real 2,210-row data and a strong pipeline, but no CLI surface — programmatic only. Issue #364 listed as Tier A; downgraded here on the CLI gap. One-line fix unblocks promotion. |
| LNG terminals registry | Sample-Only | `worldenergydata.lng_terminals` (`collectors/`, `loaders/`, `exporters/`; 26 tests; CLI registered; weekly scheduler). Seed: `data/modules/lng_terminals/curated/terminals_seed.csv` (227 rows) | 227-row curated seed + working pipeline; manifest flag drift (`in_scheduler: false` vs. enabled). Demo-able; coverage is seed-scale, not exhaustive. |
| Lower Tertiary portfolio analytics (NPV / classifier) | Sample-Only | `worldenergydata.lower_tertiary` (`npv.py`, `production_classifier.py`; 10 tests). **No CLI**; depends on BSEE/FDAS data. `reports/lower_tertiary_field_summary.html` (25 KB) exists | Finished interactive HTML exists, but a live re-run depends on BSEE data and there is no CLI. Demo from existing HTML; not turnkey. |
| Pipeline reference data (API 5L pipe schedule) | Sample-Only | `data/modules/pipeline/api_5l_pipe_schedule.csv` (43 rows). Catalog-only; **not in module manifest**; no source package | Stable 43-row reference table — useful but tiny and unindexed. Reference data, not a data *product*. Issue #364 listed as Tier A; downgraded (scope + off-manifest). |
| Subsea component specs (mooring / rigid jumpers) | Sample-Only | `data/modules/subsea/` (2 datasets, ~14 rows each). Catalog-only; `src/.../subsea/` is empty; **not in manifest** | Small curated spec tables with no backing source code. Reference seeds, not a maintained pipeline. Downgraded from issue #364's Tier A. |
| HSE raw incident analytics | Sample-Only | `worldenergydata.hse` (`importers/` 10 files, `acquirers/`, `database/`; 17 tests). **`data/catalog.yaml` datasets: [] (empty)**; no CLI (only via `safety-analysis`) | Substantial importer code but the data catalog is empty — needs a bulk load. Per #364, 6.8 GB raw exists at `/mnt/ace` blocked on #359 dedup/catalog wiring. Code-ready, data-pending. |
| Canada (AER / BCER) production collection | Sample-Only | `worldenergydata.canada` (`aer/`, `bcer/`, `production/`; 12 tests; CLI registered). No scheduler job (config only); no catalog data | Collection path exists and is CLI-exposed, but unscheduled and no shipped data. Runs on demand. |
| Texas RRC / Mexico CNH production collectors | Sample-Only | `worldenergydata.texas_rrc`, `worldenergydata.mexico_cnh` (full scrapers/processors; 10 / 5 tests; CLI registered). **Manifest implies scheduled but not in `scheduler_config.yml`** | Collectors work via CLI but are not actually scheduled despite manifest claims (docs-stale). On-demand only. |

## Tier 🔴 Roadmap

Stub, empty catalog with no wired source, off-manifest/unindexed, or otherwise not a GTM asset today.

| Capability | Tier | Evidence (file / module / report) | Buyer-facing note |
|---|---|---|---|
| BSEE binary tier (2.7 GB) | Roadmap | Issue #364 init; blocked on #359 catalog wiring + decompression pipeline; binary not in git (`make data`) | Raw bulk exists off-repo but no working ingest pipeline yet. Not consumable. |
| HSE raw bulk (6.8 GB) | Roadmap | Issue #364 init; 6.8 GB at `/mnt/ace`, blocked on #359 + dedup pipeline | Same as HSE analytics' data gap, at bulk scale. Pipeline is the roadmap item. |
| Oil price series | Roadmap | `data/catalog.yaml` `oil_price` — **empty `datasets:`**; audit §4 "no source API wired"; ~244 days stale | No source wired, no data. Not GTM. |
| Wind resource data | Roadmap | `data/catalog.yaml` `wind` — **empty `datasets:`**; audit §4 "no NREL/AWS wiring"; ~244 days stale | No source wired (NREL/AWS), no data. Not GTM. |
| Pipeline safety (PHMSA) | Roadmap | `worldenergydata.pipeline_safety` (`importers/`, `workflow.py`; 3 tests). **Empty catalog**; no CLI; GTM review §3 "no standalone demo" | Importer scaffold exists but never imported real PHMSA data and no demo. Roadmap until a load lands. |
| Vessel hull models (3D rig geometry) | Roadmap | `worldenergydata.vessel_hull_models` (`geometry/`, `cli.py` present but **unregistered**; 9 tests). Data: 5-row `sample_rigs.csv` | CLI file exists but unwired; only 5 sample rows. Promising but pre-product. |
| Well production dashboard | Roadmap | `worldenergydata.well_production_dashboard` (`api.py`, `cli.py` present but **unregistered**; 11 tests). Consumes BSEE; no own data | Rich code, but no wired CLI and depends on BSEE data. Internal tool today, not a sold capability. |
| Off-manifest analysis packages (cost, economics, decommissioning, well_planning, well_bore_design, drilling_pressure_management, reservoir, west_africa, baker_hughes) | Roadmap | Audit §3 Drift A: live `src/` packages with tests but **absent from `module-manifest.yaml`**; no CLI | Real, tested code invisible to the manifest — needs classification (promote/move/experimental) before any buyer-facing claim. `west_africa`/`cost`/`economics` are the likeliest promotions. |
| Empty / stub namespaces (`drilling`, `base_configs`, `analysis`, `subsea` src, `testing`, `modules` compat shim) | Roadmap | Audit §3/§4: empty dirs or back-compat shims; `analysis` is `stub`; `modules` shim flagged broken (#278) | Reserved or deprecated namespaces. Not capabilities. |

---

## Tier counts

| Tier | Count |
|------|-------|
| 🟢 Production-Ready | 7 |
| 🟡 Sample-Only | 10 |
| 🔴 Roadmap | 9 (the off-manifest and stub rows each group several packages) |

---

## Proposed README status-badge line (not yet applied)

This issue's acceptance criteria mention per-module README badges. Rather than editing the README here, the proposed single status line to add under the project title is:

```markdown
**Capability status:** 🟢 7 production-ready · 🟡 10 sample-only · 🔴 roadmap — see [docs/gtm/capability-matrix.md](docs/gtm/capability-matrix.md)
```

Per-module badge convention (🟢 production / 🟡 sample-only / 🔴 roadmap) can then be applied to each module heading in the README Modules section, sourcing the tier from `data/capability-matrix.json` so the README and matrix stay in sync (feeds freshness scorecard #350).

## Caveats / ambiguities

- **Tier conflicts with issue #364's draft.** BSEE-current, Vessel Fleet, Pipeline, and Subsea were proposed as Tier A in the issue but are downgraded here on audit evidence (sample rows, missing CLI, tiny off-manifest reference seeds). This is deliberate conservatism; reviewers may choose to promote Vessel Fleet once a CLI is registered.
- **"Production-Ready" for SODIR/Metocean is code-path-ready, not data-shipped** — data is fetched live via scheduler, so the demo runs online rather than from a checked-in dataset.
- **Test counts are on-disk file counts**, not confirmed pytest-collection passes (#313/#327 may affect `marine_safety` collection). Treat as upper bounds.
- **Record counts** (13,160 marine; ~57k FDAS/BSEE; 2,210 rigs; 227 LNG) are from the 2026-04-26 audit / 2026-05-04 GTM review and the catalog; they should be re-confirmed against live data before external publication (#350).
