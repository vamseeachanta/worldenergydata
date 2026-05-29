# Capability Matrix — worldenergydata + digitalmodel

**Purpose:** an honest, reusable go-to-market view of what we can show a prospective offshore/subsea
client **today** vs. what is sample-grade vs. roadmap. Built for the Doris Group demo (2026-06-05,
workspace-hub#2859) but written to be prospect-agnostic.

**Cardinal rule:** never tier something Production-ready that we can't run in front of a client and
have it hold up. When evidence is ambiguous, it is classified down a tier.

## Tier definitions (unified across both repos)

A capability is classified on two axes — *does the method work* AND *is there a real, showable
artifact with no blocking dependency*:

| Tier | Definition |
|---|---|
| **Production-ready** | Method verified (tests pass or documented validation) **AND** a real showable artifact exists — real dataset, live API response, or a committed worked-example/report output — **AND** no blocking external dependency (commercial license, API key, install, scraper, manual setup). "I can run this live today and point at a real result." |
| **Sample-only** | Either the method works but only on sample/synthetic/test-fixture data (no real dataset or live source wired through), **OR** a real artifact exists but the runnable path is gated by a license/key/install/scraper not satisfiable in the demo environment. "It demonstrably computes, but the showable thing is a fixture or is gated." |
| **Roadmap** | Not currently runnable end-to-end: failing/erroring tests, broken/stale imports, missing modules, or placeholder/zero output. "Today this does not produce a trustworthy result without code work." |

## Headline

| | Production-ready | Sample-only | Roadmap | Total |
|---|---:|---:|---:|---:|
| worldenergydata | 11 | 8 | 1 | 20 |
| digitalmodel | 8 | 10 | 4 | 22 |
| **Combined** | **19** | **18** | **5** | **42** |

Lead with the 19 Production-ready capabilities. The strongest offshore/subsea-fit lead for a live
demo: **bsee** (real GoM wells) · **sodir** (live Norwegian shelf) · **metocean** (live design
conditions) · **fdas + lower_tertiary** (economics) · digitalmodel **structural / fatigue /
cathodic_protection / asset_integrity** (subsea integrity engineering) · and the **GTM demo pack**
(5 branded client-ready reports — see callout below), the single strongest visual asset.

---

## worldenergydata (energy data product)

Run env: `PYTHONPATH=src:../assetutilities/src MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python`

| Module | Tier | Capability | Data basis | Demo artifact / evidence | Caveat |
|---|---|---|---|---|---|
| bsee | Production-ready | Real Gulf of Mexico well inventory + production | real-data | 57,281 wells, 19 cols; `notebooks/quickstart_bsee.py` | — |
| sodir | Production-ready | Live Norwegian Continental Shelf fields + production | live-API | 142 NCS fields, 300 field-year rows 1977–2026; `sodir/factpages.py`, `data/modules/sodir/` snapshots | live + committed offline fallback |
| metocean | Production-ready | Live no-key GoM wave/wind/current design conditions | live-API | 24 forecast records for 28.5,-88.5; `metocean/clients/open_meteo_client.py` | — |
| lower_tertiary | Production-ready | 10-field GoM Lower Tertiary portfolio economics | real-data | $55,500M capex; `docs/demos/2026-06-05-doris/artifacts/lower_tertiary_portfolio.{csv,html}` | — |
| fdas | Production-ready | Field economics: NPV/IRR/MIRR/payback/sensitivity | real-data | computed NPV/IRR + 57 tests; `notebooks/quickstart_fdas.py`, `examples/fdas_complete_workflow.py` | — |
| hse | Production-ready | Offshore HSE incident / toxic-release / violation DB | real-data | `data/modules/hse/hse_incidents.db`: 97,993 + 51,487 + 66,561 rows | — |
| marine_safety | Production-ready | Marine fatality/foundering/hatch analysis + reports | real-data | 20/15/30 incidents; `examples/marine_safety/reports/*.html` | — |
| pipeline_safety | Production-ready | US pipeline incident dataset | real-data | `data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv`: 2,795 rows | — |
| lng_terminals | Production-ready | Global LNG terminal infrastructure query | real-data | 8 NA export terminals, 121.8 MTPA; `data/modules/lng_terminals/reports/*.html` | — |
| vessel_fleet | Production-ready | Subsea construction vessels + riser components | real-data | 17 vessels (Sleipnir/Thialf/Pioneering Spirit), 36 components; curated CSVs | — |
| vessel_hull_models | Production-ready | 3D offshore vessel hull geometry | real-data | `sea_cypress.obj`: 13,536 verts / 17,720 faces | — |
| ukcs | Sample-only | UK Continental Shelf field production/economics | synthetic-test | 46 tests pass; scheduler adapter is a Tier-2 stub (`skipped`) | no cached dataset |
| brazil_anp | Sample-only | Brazil pre-salt field production/economics | synthetic-test | 30 tests pass; scheduler adapter stub | no cached dataset |
| mexico_cnh | Sample-only | Mexico GoM production | needs-key-or-setup | 100 tests pass | live SIH needs Selenium/browser scrape |
| eia_us | Sample-only | US state/basin/Alaska production context | needs-key-or-setup | 49 tests pass | needs EIA API key; no cached demo |
| safety_analysis | Sample-only | ML risk-index scoring + classification | synthetic-test | 41 pass; synthetic probe only | no real adapter dataset |
| canada | Sample-only | Canadian well UWI parsing / regional context | synthetic-test | tests pass (180-batch) | no cached Canadian dataset |
| texas_rrc | Sample-only | Texas onshore production validators | synthetic-test | validators pass | no cached Texas dataset |
| landman | Sample-only | Land/lease management | synthetic-test | tests pass | low offshore fit; no artifact |
| well_production_dashboard | Roadmap | Well production dashboard aggregation | broken-output | CLI emits placeholder zeros; index/verification init errors; dashboard test skipped (missing modules) | not trustworthy yet |

**worldenergydata: Production-ready 11 · Sample-only 8 · Roadmap 1.**

---

## digitalmodel (engineering analysis product)

Run env: `PYTHONPATH=examples/demos/gtm:src PYTHONUNBUFFERED=1 .venv/bin/python`. Most engineering
domains are evidenced by passing test suites; a domain reaches Production-ready only when it
**also** ships a committed worked example/artifact and has no commercial-solver dependency for the
showable part.

> **★ GTM demo pack — `examples/demos/gtm/` (verified-runnable, the strongest visual asset).** Five
> branded, client-ready HTML reports that run end-to-end in seconds (demo_01 DNV freespan VIV 2.4s,
> demo_02 multi-code wall thickness ~43s, demo_03 deepwater mudmat install 1.6s, demo_04
> shallow-water pipelay 1.7s, demo_05 deepwater rigid jumper install 1.4s), plus pre-built client
> PDF packs under `examples/demos/gtm/output/`. All five verified exit 0 + report written on
> 2026-05-28. For instant live regeneration use the `--from-cache` flag (per the harness README).
> These reports are the showable artifacts behind the subsea / structural / geotechnical
> Production-ready tiers below.

| Domain | Tier | Capability | Basis | Evidence / artifact | Caveat |
|---|---|---|---|---|---|
| structural | Production-ready | Subsea pipe/member capacity with worked example | tested + example | 103 passed; `examples/structural/pipe_capacity/basic_usage.py` | — |
| fatigue | Production-ready | Fatigue screening + S-N workflow with examples | tested + example | 5 passed; `examples/domains/fatigue/advanced_examples/` | — |
| cathodic_protection | Production-ready | Anode sizing (DNV/ISO/API) with worked demo | tested + example | 15 passed; `examples/demos/demo_pipeline_cp.py` | — |
| asset_integrity | Production-ready | FFS / API 579 RSF assessment with examples | tested + example | 28 passed; `examples/asset_integrity/example_api579_*.py` | — |
| hydrodynamics | Production-ready | Wave spectra + RAO analysis with chart output | tested + example | 59+69 passed; `examples/domains/hydrodynamics/generate_hydro_charts.py` | — |
| naval_architecture | Production-ready | Seakeeping with packaged vessel library | tested + data | 15 passed; packaged vessel YAML under `naval_architecture/data/` | — |
| subsea | Production-ready | Freespan VIV + pipelay + jumper-install branded demo reports | running-demo-artifact | gtm demo_01/04/05 run + write reports (`examples/demos/gtm/output/`); also `docs/subsea/cross_sections/offshore_cross_section_report.html` | legacy `subsea.pipeline.on_bottom_stability` import still broken — the GTM demos are the showable path |
| geotechnical | Production-ready | Deepwater mudmat installation branded demo report | running-demo-artifact | gtm demo_03 runs + writes report (`examples/demos/gtm/output/demo_03_mudmat_installation_report.html`); 9 tests passed | — |
| field_development | Sample-only | Concept selection / tieback / FPSO / platform workflow | tested-only | 30 passed | tested logic; no committed worked-example artifact yet |
| drilling_riser | Sample-only | Riser stack-up and operability | tested-fixtures | 15 passed (doc-verified test vectors) | test vectors, not a showable artifact |
| orcaflex | Sample-only | Riser/mooring/installation model library | needs-licensed-solver | 14 passed; `docs/domains/orcaflex/library/`, `examples/domains/orcaflex/complete_orcaflex_workflow.py` | live solve needs OrcaFlex license |
| solvers/openfoam | Sample-only | Marine CFD case generation | framework-only | 26+25 passed | case-gen framework, not a turnkey result |
| signal_processing | Sample-only | Time-history / FFT / fatigue-input processing | tested-only | 1 passed; `examples/domains/signal_processing/` | single test; thin coverage |
| gis | Sample-only | Spatial layers for offshore assets/wells | sample-fixtures | 39 passed on sample GeoJSON/KML fixtures | fixtures, not real asset data |
| well | Sample-only | Drilling hydraulics / tubular design | tested-only | 34 passed | no worked-example artifact |
| production_engineering | Sample-only | Nodal IPR/VLP solver | tested-only | 8 passed | no worked-example artifact |
| power | Sample-only | Load-flow / microgrid / protection | tested-only | 32 passed | secondary fit; no artifact |
| ansys | Sample-only | APDL/WBJN parsing + reporting automation | tested-only | 23 passed | file-automation; no real-run artifact |
| orcawave | Roadmap | Diffraction/radiation workflow | broken-or-setup | collection fails (stale `src.mcp.orcawave` import) | needs Windows/OrcaWave + import fix |
| marine_ops | Roadmap | Marine engineering / mooring / RAO visuals | broken-or-setup | 18 passed, 2 failed (JONSWAP benchmark mismatch) | benchmark needs review |
| nde | Roadmap | Subsea acoustic inspection | broken-or-setup | optional `the_well` dependency not installed | needs data dependency |
| reservoir | Roadmap | Stratigraphic analysis | broken-or-setup | 7 passed, 1 failed (pandas FutureWarning→error) | warning-as-error fix |

**digitalmodel: Production-ready 8 · Sample-only 10 · Roadmap 4.**

---

## Verification provenance (honesty note)

- **Re-verified end-to-end this session (2026-05-28):** all worldenergydata Production-ready rows
  (live runs / real-data loads), the `sodir` fix (live SODIR fetch + 6 passing offline tests), and
  the digitalmodel Production-ready/Sample-only **test suites** (404 tests passed across the
  prioritized set). Committed artifact paths confirmed in git, not just on disk.
- **Inherited from the readiness assessments** (`docs/demos/2026-06-05-doris/*-readiness.md`):
  per-domain artifact existence for digitalmodel worked examples (the example *scripts* are
  committed and the domains' test suites pass; individual example scripts were not each re-run).
- **Correction vs. the readiness docs:** those docs marked `sodir` RED — that was fixed this
  session (now Production-ready). Adversarial reviewers working from the stale doc flagged sodir for
  demotion; overridden on verified ground truth.
- **Flagship asset — `digitalmodel/examples/demos/gtm/` (verified-runnable 2026-05-28):** a polished
  prospect-facing demo harness — 5 demos (DNV freespan VIV, multi-code wall thickness, deepwater
  mudmat install, shallow-water pipelay, rigid jumper install) + pre-built client PDF packs. **All
  five run to completion (exit 0) and write branded HTML reports** in seconds (demo_02 ~43s, the rest
  1.4–2.4s). This backs the subsea / geotechnical Production-ready upgrades.
  **Correction:** an earlier note in this file (and an earlier #2859 comment) called this harness
  "hangs locally" — that was wrong. It was a stdout block-buffering artifact: under `>` redirection
  Python fully buffers stdout, so a `timeout` SIGKILL discarded the buffer and produced an empty log
  that looked like a hang (compounded by CPU contention from a stray pytest and a wrong `PYTHONPATH`).
  Re-run unbuffered (`PYTHONUNBUFFERED=1`) with `PYTHONPATH=examples/demos/gtm:src`, it completes fine.

## How this was built

Two parallel builder agents (one per repo) synthesized the readiness docs into tiered rows; two
parallel adversarial reviewers (overclaim-hunter + cross-repo-consistency lenses) cut the optimistic
26 Production-ready down to a defensible 17 and forced the unified tier definitions above. Main
session verified the load-bearing claims (sodir, artifact paths, gtm-harness runnability) before
finalizing.
