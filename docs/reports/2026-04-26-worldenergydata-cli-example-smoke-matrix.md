# worldenergydata — CLI / Examples / Notebooks Smoke Matrix

- Date: 2026-04-26
- Issue: [#352](https://github.com/vamseeachanta/worldenergydata/issues/352) — Public CLI/examples smoke matrix
- Mode: smoke verification only (no code changes; no large downloads; no credentials)
- Scope: `README.md` Basic Usage, `docs/CLI.md`, `docs/COMMANDS.md`, `src/worldenergydata/cli/**`, `examples/**`, `notebooks/**`
- Author: overnight Worker D (Terminal 4)

## 1. Executive summary

1. **Bounded shell execution was unavailable in this run.** Every `Bash` invocation (including `uv run worldenergydata --help`, `python3 -c`, and `gh issue view`) was blocked by the unattended-session permission gate. Findings are therefore drawn from high-fidelity static inspection of the CLI source, README, docs, examples, notebooks, and on-disk data fixtures. Each command is classified using the same status taxonomy, with `command_run: not-executed (permission gate)` recorded as evidence so the orchestrator can re-run the matrix with execution permission and confirm the runtime classifications.
2. **Documented CLI surface is materially smaller than the actual CLI surface.** `README.md` documents three modules (`bsee`, `marine-safety`, `fdas`). `docs/CLI.md` documents the same three. `src/worldenergydata/cli/main.py` registers **fourteen** module sub-apps: `bsee`, `dashboard`, `eia`, `marine-safety`, `fdas`, `sodir`, `metocean`, `ndbc`, `texas-rrc`, `canada`, `mexico-cnh`, `landman`, `lng-terminals`, `safety-analysis`, `forecast`. This is the dominant stale-docs finding and the largest user-facing trust gap.
3. **`docs/COMMANDS.md` is unrelated to the worldenergydata CLI.** It documents legacy slash commands (`/git-sync`, `/modernize-deps`, etc.) propagated from `assetutilities`. It does not document `worldenergydata <module> <command>` and last-updated 2025-08-12. README does not link to it, but a casual reader could mis-locate it; recommend either retitling, moving, or adding a disambiguating banner.
4. **README "Basic Usage" mixes safe and unsafe commands without classification.** Of the eight commands in README §"Basic Usage" (lines 41-55), four require BSEE local data (`make data`), one performs network scraping (`marine-safety scrape uscg`), one requires database/data state (`marine-safety stats`), and only the two FDAS calculation commands are bounded and credential-free. The README does not call out which commands are safe to try unattended.
5. **Quickstart notebooks are well-engineered for safe smoke runs.** All five quickstart notebooks (`bsee`, `fdas`, `marine_safety`, `sodir`, `eia`) are import-only or fixture-only safe by design. Required CSV fixtures are present in the working tree at `data/modules/bsee/current/wells/well_data.csv` and `data/modules/marine_safety/input/{fatality,foundering,hatch}_incidents.csv`; FDAS is purely computational; SODIR and EIA wrap network calls in try/except and degrade gracefully without an API key. This is a healthy pattern that the README's CLI-level commands do not yet replicate.
6. **Examples directory has at least three forms of risk.** `examples/llm_classification_demo.py` downloads ~1.6 GB on first run (BART-large-mnli). `examples/marine_safety/batch_llm_processing.py` and `examples/marine_safety/llm_detection_example.py` import `HatchMaloperationAnalyzer` whose LLM mode is similarly heavy. `examples/validation_examples.py` imports a sibling `validator_template` that does not exist alongside it — a stale-import follow-up candidate. `examples/fdas_complete_workflow.py` uses `from src.worldenergydata.modules.fdas import …` which is the legacy import path explicitly flagged by issue [#278](https://github.com/vamseeachanta/worldenergydata/issues/278) (broken `modules.*` shims after consolidation); this example is therefore likely broken without verifying.
7. **Help-time imports are cheap; runtime imports are deferred.** Every CLI subcommand file inspected (`bsee.py`, `fdas.py`, `marine_safety.py`, `eia.py`, `dashboard.py`, `sodir.py`) wraps domain-specific imports inside the function body, so `worldenergydata <module> --help` should succeed even if a heavy dependency is missing. This makes a `--help` smoke pass cheap and high-signal — the right next runtime gate.
8. **Cross-references to the existing test/import-blocker family are direct.** Findings here connect to issues [#313](https://github.com/vamseeachanta/worldenergydata/issues/313) (pytest config/import cleanup), [#326](https://github.com/vamseeachanta/worldenergydata/issues/326) (`ProductionAnalyzer.prepare_production_data` missing), [#327](https://github.com/vamseeachanta/worldenergydata/issues/327) (conftest blocks marine safety collection), [#328](https://github.com/vamseeachanta/worldenergydata/issues/328) (flake8 F821 instability), [#325](https://github.com/vamseeachanta/worldenergydata/issues/325) (pre-existing defects under xfail), and [#278](https://github.com/vamseeachanta/worldenergydata/issues/278) (broken `modules.*` shims). The CLI runtime itself is plausibly affected by `#278` for the `bsee analyze`/`bsee report` paths because they rely on `worldenergydata.bsee.*` and `worldenergydata.bsee.reports.comprehensive.*` import trees.

## 2. Methodology and commands run

### 2.1 What I did execute (zero — gated)

The unattended-session `Bash` permission gate denied every shell invocation in this run, including:

- `uv run worldenergydata --help`
- `uv run worldenergydata info`
- `uv run python -c "from worldenergydata.cli.main import app; …"` via Typer's CLI test runner
- `python3 -c "print('hi')"` (denied — confirms blanket Bash gating, not a `uv`-specific issue)
- `gh issue view 352 --repo vamseeachanta/worldenergydata`

Each is recorded in the YAML companion with `status: not-executed-permission-gate` and `command_run` showing the exact text that was attempted, so the orchestrator can re-run with execution permission and either confirm `passing` or capture the live failure.

### 2.2 What I did do (static inspection)

- Read `README.md` (240 lines) and extracted every Basic Usage and module command.
- Read `docs/CLI.md` (462 lines) and inventoried every documented option for `bsee`, `marine-safety`, `fdas`.
- Read `docs/COMMANDS.md` (40 lines) and confirmed it is unrelated to the worldenergydata CLI.
- Read `docs/api-contracts.md` for assetutilities version contracts referenced by FDAS analysis.
- Read `src/worldenergydata/cli/main.py` (387 lines) and inventoried the 14 registered sub-apps, the `info`/`status`/`version` global commands, and the lazy-import pattern.
- Read full source of `src/worldenergydata/cli/commands/{bsee.py,fdas.py,marine_safety.py}` (head sections) and partial source of `eia.py`, `sodir.py`, `dashboard.py` to confirm subcommand structure, defaults, and which imports are deferred to runtime.
- Read all five `notebooks/quickstart_*.py` files for fixture/network/credential needs.
- Read `examples/{fdas_complete_workflow.py, validation_examples.py, llm_classification_demo.py, marine_safety_cause_visualization_demo.py}` heads and `examples/marine_safety/{batch_llm_processing.py, llm_detection_example.py, generate_cause_report.py}` heads.
- Confirmed presence of fixture CSVs under `data/modules/bsee/current/wells/` and `data/modules/marine_safety/input/`.
- Read `docs/data/LOCAL_DATA_PATTERN.md` to understand the BSEE binary data exclusion model.
- Read the companion overnight artifact `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` to align with sibling Worker A/B/C scope and the prepared list of related issues for cross-reference.

### 2.3 Classification taxonomy (for both Markdown and YAML)

- `passing` — observed exit 0 with expected output (none in this run; gated).
- `failing` — non-zero exit with captured error.
- `data-required` — needs `make data` or pre-populated `data/modules/<module>/`.
- `credential-required` — needs an API key or auth (e.g., `EIA_API_KEY`).
- `unsafe-unbounded` — performs large download or arbitrary-time scrape.
- `stale-docs` — command in docs but absent or renamed in code.
- `not-executed-permission-gate` — expected-safe command not run because Bash was gated this session; orchestrator follow-up.
- `import-only-smoke-feasible` — can be run statically with `python -c "import …"`.
- `fixture-only-run-feasible` — runs end-to-end with fixtures present in the working tree.

## 3. README command matrix

Source: `README.md` lines 18-99.

| # | Command | Source line | Classification | Why |
|---|---|---|---|---|
| 1 | `uv run worldenergydata --help` | 32 | `not-executed-permission-gate` | Help-only; safe and bounded once executable. Top-priority command for orchestrator re-run. |
| 2 | `uv run worldenergydata info` | 42 | `not-executed-permission-gate` | Pure stdout summary using a static `Table`; no imports of heavy modules. Safe. |
| 3 | `uv run worldenergydata bsee analyze --field "Jack"` | 45 | `data-required` + likely `failing` (#278) | Imports `worldenergydata.bsee.bsee.bsee` and runs `BSEEModule().router(cfg)`. Requires `data/modules/bsee/bin/**` populated by `make data`. Also at risk from broken `modules.*` shims (#278). |
| 4 | `uv run worldenergydata bsee report --type block --id 759 --format excel` | 46 | `data-required` | Imports `worldenergydata.bsee.reports.comprehensive.controller_enhanced.ReportController`; requires populated BSEE data. Help-only is safe. |
| 5 | `uv run worldenergydata marine-safety scrape uscg --start-year 2020` | 49 | `unsafe-unbounded` | USCG MISLE scrape with checkpoint resume; will run for an unbounded time and hit external HTTP endpoints. Do **not** run in unattended smoke. |
| 6 | `uv run worldenergydata marine-safety stats --source all` | 50 | `data-required` | Reads ingested incident DB; without `db init` + scraped data, it will report empty / fail in a "no data" path. |
| 7 | `uv run worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300]" --discount-rate 0.10` | 53 | `not-executed-permission-gate` (expected `passing`) | Pure NumPy/numpy-financial computation; no I/O, no network, no data files. Top-priority validation command. |
| 8 | `uv run worldenergydata fdas calculate-all --cashflows "[-5000,1000,1500,2000]"` | 54 | `not-executed-permission-gate` (expected `passing`) | Same — pure computation. |

### Module-block commands referenced later in README (lines 67-99)

| # | Command | Source line | Classification | Why |
|---|---|---|---|---|
| 9 | `worldenergydata bsee analyze --block 759` | 67 | `data-required` | Same import path as row 3. |
| 10 | `worldenergydata bsee report --type field --id "Thunder Horse" --oil-price 80` | 68 | `data-required` | Same as row 4. |
| 11 | `worldenergydata bsee data --api 608114001200` | 69 | `data-required` | Imports `worldenergydata.bsee.data.bsee_data.BSEEData`; requires populated BSEE data. |
| 12 | `worldenergydata bsee refresh --type production` | 70 | `unsafe-unbounded` | Triggers `DataRefresh.router()` — large download, network-dependent. Do not run unattended. |
| 13 | `worldenergydata marine-safety scrape uscg --start-year 2020 --end-year 2023` | 81 | `unsafe-unbounded` | Same as row 5 with explicit window. |
| 14 | `worldenergydata marine-safety db init --dev-mode` | 82 | `not-executed-permission-gate` | Has `--dry-run` per `docs/CLI.md`; `--dev-mode` writes to local SQLite; recommend running with `--dry-run` in smoke. |
| 15 | `worldenergydata marine-safety export csv --output incidents.csv` | 83 | `data-required` | Reads from DB; needs populated DB. |
| 16 | `worldenergydata marine-safety stats --verbose` | 84 | `data-required` | Same as row 6. |
| 17 | `worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300,400,500]"` | 95 | `not-executed-permission-gate` (expected `passing`) | Pure computation. |
| 18 | `worldenergydata fdas calculate-mirr --cashflows "[-5000,1000,1500,2000]" --discount-rate 0.12` | 96 | `not-executed-permission-gate` (expected `passing`) | Pure computation. |
| 19 | `worldenergydata fdas analyze --field "Thunder Horse" --discount-rate 0.10` | 97 | `data-required` | Imports `worldenergydata.fdas.analysis.cashflow.CashflowEngine`; runs without data only as a "configuration ready" step but its real value requires BSEE data. |
| 20 | `worldenergydata fdas classify 5000` | 98 | `not-executed-permission-gate` (expected `passing`) | Imports `worldenergydata.fdas.core.config.classify_dev_system_by_depth`; falls back to inline classification on `ImportError`. Safe. |

## 4. CLI module help matrix

Every module subcommand exposes `--help`. Help-time execution is cheap because each command file's heavy imports are deferred to function bodies. None of the help calls were executed this run; all are recommended for the orchestrator's re-run.

| Module sub-app | Source | Help command | Help-only safety | Notes |
|---|---|---|---|---|
| `bsee` | `cli/commands/bsee.py` | `worldenergydata bsee --help` | Safe | Subcommands: `analyze`, `report`, `data`, `refresh`, `stats` (matches `docs/CLI.md`). |
| `dashboard` | `cli/commands/dashboard.py` | `worldenergydata dashboard --help` | Safe | Single callback that starts a Plotly Dash server on `127.0.0.1:8050` if invoked without `--help`. **Undocumented in `docs/CLI.md`.** |
| `eia` | `cli/commands/eia.py` | `worldenergydata eia --help` | Safe | Subcommand: `sync` (writes JSONL). Requires `EIA_API_KEY` to do real work. **Undocumented in `docs/CLI.md`.** |
| `marine-safety` | `cli/commands/marine_safety.py` | `worldenergydata marine-safety --help` | Safe | Subgroups `scrape` (uscg/ntsb/maib), `db` (init/migrate); commands: `stats`, `export`, `analyze`, `info`. |
| `fdas` | `cli/commands/fdas.py` | `worldenergydata fdas --help` | Safe | Commands: `calculate-npv`, `calculate-mirr`, `calculate-irr`, `calculate-all`, `analyze`, `classify`, `info`. |
| `sodir` | `cli/commands/sodir.py` | `worldenergydata sodir --help` | Safe | Commands referenced in `info` table: `collect`, `analyze`, `status`. **Undocumented in `docs/CLI.md`.** |
| `metocean` | `cli/commands/metocean.py` | `worldenergydata metocean --help` | Safe | Commands per `info`: `stations`, `fetch`, `forecast`, `cache`, `db`. **Undocumented in `docs/CLI.md`.** |
| `ndbc` | `cli/commands/ndbc.py` | `worldenergydata ndbc --help` | Safe | Listed in `main.py` only; not in `info` table or `docs/CLI.md`. |
| `texas-rrc` | `cli/commands/texas_rrc.py` | `worldenergydata texas-rrc --help` | Safe | `info` row: `collect`, `analyze`, `status`, `validate-api`. **Undocumented in `docs/CLI.md`.** |
| `canada` | `cli/commands/canada.py` | `worldenergydata canada --help` | Safe | `info` row: `collect`, `analyze`, `status`, `validate-uwi`. **Undocumented in `docs/CLI.md`.** |
| `mexico-cnh` | `cli/commands/mexico_cnh.py` | `worldenergydata mexico-cnh --help` | Safe | `info` row: `scrape`, `download-open-data`, `status`, `validate-clave`. **Undocumented in `docs/CLI.md`.** |
| `landman` | `cli/commands/landman.py` | `worldenergydata landman --help` | Safe | `info` row: `search`, `lookup`, `county-info`, `providers`, `status`. **Undocumented in `docs/CLI.md`.** |
| `lng-terminals` | `cli/commands/lng_terminals.py` | `worldenergydata lng-terminals --help` | Safe | `info` row: `collect`, `process`, `export`, `report`, `pipeline`. **Undocumented in `docs/CLI.md`.** |
| `safety-analysis` | `safety_analysis/cli.py` | `worldenergydata safety-analysis --help` | Safe | `info` row: `load`, `classify`, `correlate`, `report`, `status`. **Undocumented in `docs/CLI.md`.** |
| `forecast` (production) | `cli/commands/production_forecast.py` | `worldenergydata forecast --help` | Safe | Mounted as `forecast`, not `production-forecast`; **not even in the `info` table**. |
| `version` (root) | `cli/main.py:146` | `worldenergydata version` | Safe | Prints `__version__` panel; safe. |
| `info` (root) | `cli/main.py:165` | `worldenergydata info` | Safe | Static module table; misses `dashboard`, `eia`, `ndbc`, `forecast`. |
| `status` (root) | `cli/main.py:233` | `worldenergydata status` | Safe (degrades) | Reads `data/modules/<mod>/_metadata.json`; prints "no metadata" if missing. |

## 5. Examples / notebooks matrix

### 5.1 Quickstart notebooks (`notebooks/`)

| Artifact | Status | Why | Required prereqs |
|---|---|---|---|
| `notebooks/quickstart_fdas.py` | `import-only-smoke-feasible` and `fixture-only-run-feasible` | Pure computation via `worldenergydata.fdas.api.EconomicsQuery`; no data files needed. | numpy, numpy-financial, matplotlib, pandas |
| `notebooks/quickstart_bsee.py` | `fixture-only-run-feasible` | Reads `data/modules/bsee/current/wells/well_data.csv`; that fixture is **present in the working tree**. | pandas, matplotlib + the checked-in CSV |
| `notebooks/quickstart_marine_safety.py` | `fixture-only-run-feasible` | Reads `data/modules/marine_safety/input/{fatality,foundering,hatch}_incidents.csv`; all three are **present in the working tree**. | pandas, matplotlib + the checked-in CSVs |
| `notebooks/quickstart_sodir.py` | `import-only-smoke-feasible`; live fetch is `requires-network` (degrades gracefully) | Wraps `SodirAPIClient` calls in try/except and prints a polite skip when offline. | requests (for live fetch); pandas |
| `notebooks/quickstart_eia.py` | `import-only-smoke-feasible`; live fetch is `credential-required` + `requires-network` (degrades gracefully) | Reads `os.environ.get("EIA_API_KEY")` and skips live fetch when absent. | requests + EIA_API_KEY (for live fetch); pandas |

### 5.2 Examples (`examples/`)

| Artifact | Status | Why | Risk if run blindly |
|---|---|---|---|
| `examples/fdas_complete_workflow.py` | `stale/broken-import` (very high confidence) | Imports `from src.worldenergydata.modules.fdas import …` and `from src.worldenergydata.modules.fdas.analysis import …`. The `modules.*` import path is the broken legacy shim flagged by [#278](https://github.com/vamseeachanta/worldenergydata/issues/278). The new canonical path (per CLI source and notebooks) is `worldenergydata.fdas.*` (no `modules`, no `src` prefix). | ImportError on first import. Should be rewritten or deleted. |
| `examples/validation_examples.py` | `stale/broken-import` | Imports `from validator_template import DataValidator`; no `validator_template.py` lives next to it in `examples/`. | ModuleNotFoundError. Likely orphan from earlier scaffold. |
| `examples/llm_classification_demo.py` | `unsafe-unbounded` (large download on first run) | Prints "First time: Downloads ~1.6GB" then loads `facebook/bart-large-mnli` via `transformers.pipeline`. | ~1.6 GB model download + ~minutes of CPU. Do **not** run unattended. |
| `examples/marine_safety_cause_visualization_demo.py` | `import-only-smoke-feasible` | Generates synthetic data with NumPy and renders an HTML report; no network/credentials/data files. | Should be safe; verify imports under live runtime. |
| `examples/marine_safety/batch_llm_processing.py` | `unsafe-unbounded` if LLM mode is enabled | Imports `HatchMaloperationAnalyzer`; the LLM detection branch downloads a transformer model. Smoke is OK only if run with the regex-only path. | ~1.6 GB download in LLM mode. |
| `examples/marine_safety/llm_detection_example.py` | `unsafe-unbounded` if LLM mode is enabled | Same `HatchMaloperationAnalyzer` import; same download risk. | Same as above. |
| `examples/marine_safety/generate_cause_report.py` | `import-only-smoke-feasible` | Imports `CauseAnalysisReport` and `ReportFilters`; generates synthetic incidents and writes an HTML report. | Should be safe. |
| `examples/marine_safety/reports/*.html` | n/a | Pre-generated HTML report artifacts; not executable scripts. | None. |

## 6. Known blockers mapped to existing issues

| Smoke finding | Likely-related existing issue | Why this matters for #352 |
|---|---|---|
| `bsee analyze`/`bsee report`/`bsee data` import the `worldenergydata.bsee.*` tree, which depends on the post-consolidation package layout. | [#278](https://github.com/vamseeachanta/worldenergydata/issues/278) | If the `modules.*` shim removal regressed any sibling import, the BSEE CLI runtime path may fail with `ImportError` even when help works. |
| `examples/fdas_complete_workflow.py` uses `from src.worldenergydata.modules.fdas import …`. | [#278](https://github.com/vamseeachanta/worldenergydata/issues/278) | This example is a direct user-visible artifact of that breakage. |
| `marine-safety stats` / `analyze` paths likely transit `ProductionAnalyzer` and conftest-affected code. | [#326](https://github.com/vamseeachanta/worldenergydata/issues/326), [#327](https://github.com/vamseeachanta/worldenergydata/issues/327) | If `ProductionAnalyzer.prepare_production_data` is missing or conftest-blocked, runtime smoke could fail in the same place tests do. |
| Pytest config / xfail churn affects which tests can certify the CLI surface. | [#313](https://github.com/vamseeachanta/worldenergydata/issues/313), [#325](https://github.com/vamseeachanta/worldenergydata/issues/325), [#328](https://github.com/vamseeachanta/worldenergydata/issues/328) | Without stable test discovery, a green `pytest` run does not yet vouch for the CLI commands. |
| README/CLI.md document only 3 of 14 module sub-apps. | none yet (new follow-up candidate) | Trust gap — agents reading docs will under-discover features. |
| `docs/COMMANDS.md` is unrelated to the `worldenergydata` CLI. | none yet (new follow-up candidate) | Doc collision; needs disambiguation. |
| `examples/validation_examples.py` imports a missing `validator_template`. | none yet (new follow-up candidate) | Stale/orphan example. |
| `examples/fdas_complete_workflow.py` uses `src.worldenergydata.modules.*` legacy path. | [#278](https://github.com/vamseeachanta/worldenergydata/issues/278) (existing) and a new follow-up to delete or rewrite the example. | User-visible breakage. |
| LLM examples download ~1.6 GB on first run with no docs warning at the example level. | none yet (new follow-up candidate) | Unattended-run hazard. |

## 7. New follow-up issue candidates

The following candidates are recommended; they are **not** filed by this audit. Worker D's remit is observation-only.

1. **Doc parity: cover all 14 CLI sub-apps in `docs/CLI.md` and `README.md`.** Current docs cover 3 of 14. At minimum: `dashboard`, `eia`, `sodir`, `metocean`, `ndbc`, `texas-rrc`, `canada`, `mexico-cnh`, `landman`, `lng-terminals`, `safety-analysis`, `forecast`. Add a "safety classification" column per command (safe/data-required/network/credential/unsafe) so users can self-pace.
2. **`docs/COMMANDS.md` cleanup or rename.** This file is from `assetutilities` slash-command propagation and is unrelated to the `worldenergydata` runtime CLI. Either delete, rename to `docs/SLASH_COMMANDS.md`, or add a top-of-file banner clarifying scope.
3. **`worldenergydata info` table is missing four registered modules.** `dashboard`, `eia`, `ndbc`, `forecast` are mounted in `cli/main.py` but absent from the `info()` table. Add rows so the canonical in-CLI module index matches reality.
4. **`forecast` vs `production-forecast` naming inconsistency.** Source file is `production_forecast.py`, mounted as `forecast`. Choose one and update both source/mount/help text to match user expectations.
5. **Delete or rewrite `examples/fdas_complete_workflow.py`.** Uses `src.worldenergydata.modules.fdas` — the legacy `modules.*` shim path that #278 retired. Either rewrite to `worldenergydata.fdas.*` (the path used by `notebooks/quickstart_fdas.py`) or remove the file.
6. **Delete or rebuild `examples/validation_examples.py`.** Imports `validator_template` which does not exist alongside it; orphan/dead example.
7. **Add a download-warning preamble to LLM examples.** `examples/llm_classification_demo.py`, `examples/marine_safety/batch_llm_processing.py`, `examples/marine_safety/llm_detection_example.py` all transit a ~1.6 GB BART model. Add a `--dry-run` flag or a "first-run downloads ~1.6 GB" `print` early enough that an unattended runner can bail safely.
8. **README "Basic Usage" section: tag commands by safety class.** Distinguish bounded / data-required / network commands inline so new users and unattended agents can pick the safe subset (effectively just FDAS calculations and `--help`).
9. **Smoke harness script.** Add `scripts/smoke/cli_help_matrix.sh` (or a pytest module under `tests/smoke/`) that runs all `worldenergydata <module> --help` invocations + the four pure-FDAS calculations and asserts exit 0. Wire to CI as a post-build job. This converts this Markdown matrix into an executable contract.
10. **Re-run #352 smoke matrix with execution permission.** This audit was static-only because the unattended Bash gate denied execution. Once permitted, re-run all `not-executed-permission-gate` rows and confirm `passing`/`failing` directly.

## 8. Recommended README / docs updates

1. README §"Basic Usage" should call out that `bsee analyze`, `bsee report`, `bsee data`, and `marine-safety stats` need `make data` first; this is implied at line 35-36 but not at command level.
2. README should suggest a "first try" sequence that any user can run cold without `make data`:
   - `uv run worldenergydata --help`
   - `uv run worldenergydata info`
   - `uv run worldenergydata fdas classify 5000`
   - `uv run worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300,400,500]"`
   - `uv run python notebooks/quickstart_fdas.py`
3. `docs/CLI.md` should add sections for the eleven undocumented modules (see follow-up #1 above).
4. `notebooks/README.md` is excellent; replicate its prereq/network/credential transparency in `examples/README.md` (which does not exist yet — recommend creating one).
5. `docs/api-contracts.md` notes the assetutilities git-URL install pattern; the FDAS `analyze` command depends on `AssumptionsManager` which is independent of assetutilities, but BSEE comprehensive reports may transit assetutilities. Worth a one-line note in `docs/CLI.md` on `bsee report`.
6. Add a one-sentence statement in `README.md` near `make data` about the fixture-only path (BSEE wells CSV + marine_safety incidents CSV) so users understand which subsets work pre-`make data`.

---

## Verification footer

- This Markdown report is generated by Worker D for issue [#352](https://github.com/vamseeachanta/worldenergydata/issues/352).
- Companion machine-readable record: `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml`.
- Sibling overnight artifacts: `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` (planning packet), and the in-flight Worker A/B/C reports for #349/#350/#351.
- This run did **not** modify `src/`, `tests/`, `data/`, `docs/plans/`, `.planning/`, or any other forbidden path.

## Prepared GitHub comment (for orchestrator to post on #352)

Posting was attempted via `gh issue comment 352 --repo vamseeachanta/worldenergydata` and **denied by the same Bash permission gate** that blocked the smoke commands. The intended comment body is captured below verbatim so the orchestrator (or a re-run with permission) can post it.

```markdown
## Worker D — CLI/Examples Smoke Matrix complete (planning/audit only)

Artifacts (untracked, not committed):
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml`

### Execution status
**No shell commands executed.** Every `Bash` invocation in this unattended session was denied by the permission gate (`uv run worldenergydata --help`, `worldenergydata info`, `python3 -c`, `gh issue view`). All findings are from high-fidelity static inspection and recorded as `not-executed-permission-gate` so the orchestrator can re-run with execution permission.

### Top findings
1. **Doc/CLI parity gap.** `docs/CLI.md` documents 3 module sub-apps; `src/worldenergydata/cli/main.py` registers **14**. Missing from CLI.md: `dashboard`, `eia`, `sodir`, `metocean`, `ndbc`, `texas-rrc`, `canada`, `mexico-cnh`, `landman`, `lng-terminals`, `safety-analysis`, `forecast`. The CLI's own `info()` table also omits 4 (`dashboard`, `eia`, `ndbc`, `forecast`).
2. **`docs/COMMANDS.md` is unrelated** to the worldenergydata CLI — it documents legacy assetutilities slash commands. Recommend rename or banner.
3. **`examples/fdas_complete_workflow.py` uses the broken `src.worldenergydata.modules.fdas` legacy path** retired by [#278](https://github.com/vamseeachanta/worldenergydata/issues/278). Likely fails on import.
4. **`examples/validation_examples.py` imports a missing `validator_template`** module — orphan example.
5. **Three LLM examples download ~1.6 GB on first run** (`examples/llm_classification_demo.py`, `examples/marine_safety/batch_llm_processing.py`, `examples/marine_safety/llm_detection_example.py`). No download warning at script level.
6. **All 5 quickstart notebooks are smoke-safe**: FDAS is pure compute; BSEE and marine-safety fixtures are present in-tree (`data/modules/bsee/current/wells/well_data.csv`, `data/modules/marine_safety/input/*.csv`); SODIR and EIA wrap network calls in try/except and degrade without keys.

### Commands recommended as priority on re-run with execution permission
- `uv run worldenergydata --help`, `worldenergydata info`, `worldenergydata version`, `worldenergydata status`
- All 14 module `--help` invocations
- `worldenergydata fdas classify 5000`
- `worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300,400,500]"`
- `worldenergydata fdas calculate-mirr --cashflows "[-5000,1000,1500,2000]" --discount-rate 0.12`
- `worldenergydata fdas calculate-all --cashflows "[-5000,1000,1500,2000]"`
- `worldenergydata marine-safety db init --dev-mode --dry-run`

### Commands classified as data-required (need `make data` first)
`bsee analyze`, `bsee report`, `bsee data`, `marine-safety stats`, `marine-safety export`, `fdas analyze` (full path).

### Commands classified as credential-required
`eia sync` (needs `EIA_API_KEY`).

### Commands classified as unsafe-unbounded
`marine-safety scrape uscg|ntsb|maib`, `bsee refresh`, the LLM examples above, `dashboard` (starts a server when invoked without `--help`).

### Related existing issues
- [#278](https://github.com/vamseeachanta/worldenergydata/issues/278) — broken `modules.*` shim path (impacts BSEE CLI runtime + `examples/fdas_complete_workflow.py`)
- [#326](https://github.com/vamseeachanta/worldenergydata/issues/326) — missing `ProductionAnalyzer.prepare_production_data` (impacts marine-safety analysis path)
- [#327](https://github.com/vamseeachanta/worldenergydata/issues/327) — conftest blocks marine-safety collection (impacts marine-safety stats/export smoke)
- [#313](https://github.com/vamseeachanta/worldenergydata/issues/313), [#325](https://github.com/vamseeachanta/worldenergydata/issues/325), [#328](https://github.com/vamseeachanta/worldenergydata/issues/328) — pytest/lint stability blockers
- [#266](https://github.com/vamseeachanta/worldenergydata/issues/266) (EIA), [#267](https://github.com/vamseeachanta/worldenergydata/issues/267) (BSEE), [#268](https://github.com/vamseeachanta/worldenergydata/issues/268) (metocean), [#269](https://github.com/vamseeachanta/worldenergydata/issues/269) (SODIR/Brazil/UKCS), [#270](https://github.com/vamseeachanta/worldenergydata/issues/270) (LNG), [#271](https://github.com/vamseeachanta/worldenergydata/issues/271) (output_dir wiring), [#273](https://github.com/vamseeachanta/worldenergydata/issues/273) (SODIR runtime) — scheduler/source paths surfaced by `--help` undocumentation

### New follow-up issue candidates (not filed)
1. Doc parity: cover all 14 CLI sub-apps in `docs/CLI.md` and `README.md` with safety classifications.
2. `docs/COMMANDS.md` cleanup or rename.
3. Update `worldenergydata info` table to include `dashboard`, `eia`, `ndbc`, `forecast`.
4. `forecast` vs `production-forecast` naming reconciliation.
5. Delete or rewrite `examples/fdas_complete_workflow.py` for the new `worldenergydata.fdas.*` path.
6. Delete or rebuild `examples/validation_examples.py`.
7. Add download-warning preamble to LLM examples.
8. Tag README "Basic Usage" commands by safety class; suggest a "first try cold" sequence.
9. Add `scripts/smoke/cli_help_matrix.sh` + CI hook to make this matrix executable.
10. Re-run #352 smoke matrix with execution permission to upgrade `not-executed-permission-gate` rows to `passing`/`failing`.

Artifacts left for orchestrator review; no commits and no source changes.
```
