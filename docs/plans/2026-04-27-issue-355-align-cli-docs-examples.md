# Issue #355 Plan — Align public CLI docs/examples with smoke matrix

> **Status:** plan-review — revised after adversarial MAJOR review
> **Complexity:** T2/T3 docs + bounded smoke cleanup
> **Date:** 2026-04-27
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/355
> **Related audit:** `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
> **Review artifacts:** `docs/reports/2026-04-27-plan-355-adversarial-review.md`, `docs/reports/2026-04-27-plan-354-355-rereview.md`

## Problem Statement

The public CLI and example documentation does not match the runtime surface:

- `docs/CLI.md` and README document only `bsee`, `marine-safety`, and `fdas`.
- `src/worldenergydata/cli/main.py` registers 15 sub-apps: `bsee`, `dashboard`, `eia`, `marine-safety`, `fdas`, `sodir`, `metocean`, `ndbc`, `texas-rrc`, `canada`, `mexico-cnh`, `landman`, `lng-terminals`, `safety-analysis`, and `forecast`.
- `docs/COMMANDS.md` is unrelated to the worldenergydata CLI; it documents legacy propagated slash commands from `assetutilities`.
- README Basic Usage mixes safe commands, data-required commands, and unsafe/unbounded scraping commands without labels.
- `examples/fdas_complete_workflow.py` uses stale `src.worldenergydata.modules.fdas` imports related to #278.
- `examples/validation_examples.py` imports a missing `validator_template`.
- Several LLM examples can download ~1.6 GB on first run without sufficiently early script-level guardrails.

This makes it unsafe for agents or users to run examples blindly and causes under-discovery of working CLI surfaces.

## Goals

1. Make public CLI docs match the registered command surface.
2. Classify commands/examples by run safety: bounded, data-required, credential-required, network-required, server-starting, unsafe-unbounded, or stale/broken.
3. Repair or explicitly quarantine stale examples.
4. Add a bounded smoke contract for help-only and pure-compute paths.
5. Avoid unbounded downloads, scraping, and data refreshes.

## Non-Goals / Boundaries

- Do **not** run `bsee refresh`, `marine-safety scrape`, dashboard server starts, LLM downloads, or full data refreshes.
- Do **not** solve all runtime defects in dependent modules (#278/#326/#327/#313/#325/#328); link to them and gate docs accordingly.
- Do **not** add credentials or require external API keys.
- Do **not** rewrite every example into a production tutorial; the first pass is parity, safety labels, and smokeability.
- Keep CLI capability taxonomy aligned with #354 rather than inventing a second taxonomy.

## Resource Intelligence

Primary evidence:

- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
- `README.md`
- `docs/CLI.md`
- `docs/COMMANDS.md`
- `src/worldenergydata/cli/main.py`
- `examples/`
- `notebooks/quickstart_*.py`

Critical findings from the audit:

| Finding | Evidence | Plan response |
|---|---|---|
| Docs cover 3 of 15 CLI sub-apps | `docs/CLI.md`, `cli/main.py` | Add docs sections or at least summary rows for all registered sub-apps. |
| `worldenergydata info` omits 4 sub-apps | `cli/main.py` rows vs registrations | Coordinate with #354 or include small fix if approved. |
| README commands are not safety-labelled | README Basic Usage | Add safety labels and a cold-start safe sequence. |
| `docs/COMMANDS.md` is unrelated | file header says custom slash commands / assetutilities | Add a banner clarifying it is not runtime CLI docs; no rename/delete in this issue. |
| FDAS complete workflow has stale imports | `examples/fdas_complete_workflow.py` | Rewrite to canonical `worldenergydata.fdas.*` paths or quarantine with warning. |
| validation example imports missing file | `examples/validation_examples.py` | Delete, rebuild, or mark broken pending source. |
| LLM examples download ~1.6 GB | audit + example text | Add early warnings and opt-in flags/dry-run behavior. |

## Frozen Design Decisions From Adversarial Review

1. **CLI registry source:** parse `src/worldenergydata/cli/main.py` for `app.add_typer(..., name=...)`; do not use hand-maintained CLI allowlists except as test fixtures derived from source.
2. **#354 boundary:** #354 owns capability taxonomy and `worldenergydata info` implementation. #355 may reference `info()` drift, but should not change `cli/main.py` unless #354 is approved/merged first or the change is explicitly coordinated.
3. **`docs/COMMANDS.md` decision:** keep the file in place and add a top banner clarifying it is custom slash-command documentation, not runtime `worldenergydata` CLI documentation. Do not delete/rename in this issue.
4. **Example decision:** create `examples/README.md` as the authoritative examples safety matrix. Mark stale examples as `stale/broken` unless a trivial, test-backed rewrite is available.
5. **Notebook scope:** notebooks are out of implementation scope except for documentation cross-reference to the already-audited quickstarts. Do not modify notebooks in this issue.
6. **LLM guardrail decision:** target exactly `examples/llm_classification_demo.py`, `examples/marine_safety/batch_llm_processing.py`, and `examples/marine_safety/llm_detection_example.py`. Add an early opt-in guard before model-loading paths, using `WORLDENERGYDATA_RUN_LLM_EXAMPLES=1` or an equivalent explicit CLI flag.
7. **Smoke vehicle:** add static pytest/docs tests first. Runtime smoke is optional and must be marked pending #353 if `uv`/CLI startup is still blocked.

## Proposed Implementation Phases

### Phase 0 — Establish safety taxonomy

Use one table across README, `docs/CLI.md`, and examples:

- `bounded-safe`: local help/info/version/pure computation; no writes beyond explicit output path.
- `fixture-only`: runs using checked-in small fixtures.
- `data-required`: requires `make data` or populated `data/modules`.
- `credential-required`: requires API key/auth.
- `network-required`: bounded external call.
- `server-starting`: starts a local server/process if invoked without `--help`.
- `unsafe-unbounded`: long scrape/large download/unbounded refresh.
- `stale/broken`: known import/path/documentation break.

### Phase 1 — README first-run safety cleanup

- Add a "safe first commands" block:
  - `worldenergydata --help`
  - `worldenergydata info`
  - `worldenergydata version`
  - FDAS pure calculations/classification.
- Label existing README Basic Usage commands individually.
- Mark `bsee analyze/report/data` as data-required.
- Mark `bsee refresh` and `marine-safety scrape` as unsafe/unbounded unless users provide deliberate bounded options.
- Keep `make data` caveat but make it command-level, not only global.

### Phase 2 — Expand `docs/CLI.md` to current runtime surface

- Ensure all registered sub-apps have at least a section with:
  - purpose,
  - help command,
  - safety classification,
  - data/network/credential prerequisites,
  - examples limited to safe or clearly labelled commands.
- Existing detailed sections for `bsee`, `marine-safety`, and `fdas` should gain safety labels rather than being rewritten from scratch.
- Add missing sections for `dashboard`, `eia`, `sodir`, `metocean`, `ndbc`, `texas-rrc`, `canada`, `mexico-cnh`, `landman`, `lng-terminals`, `safety-analysis`, and `forecast`.
- If command detail is uncertain, document `worldenergydata <module> --help` as the authoritative runtime help and mark examples as pending live smoke.

### Phase 3 — Resolve `docs/COMMANDS.md` collision

Add a top-of-file banner: "This document describes custom slash commands / agent-ops commands, not the `worldenergydata` runtime CLI. For runtime CLI usage see `docs/CLI.md`." Do not rename or delete the file in this issue.

### Phase 4 — Examples cleanup

- Add `examples/README.md` with safety matrix for all examples.
- `examples/fdas_complete_workflow.py`: mark/quarantine as `stale/broken` in `examples/README.md` with link to #278; only rewrite imports if a focused smoke test proves the canonical API works.
- `examples/validation_examples.py`: mark/quarantine as `stale/broken` in `examples/README.md`; rebuild is a future issue unless a minimal real `worldenergydata.validation` replacement is obvious and test-backed.
- LLM examples: add early warning/opt-in guard before model-loading paths in exactly these files: `examples/llm_classification_demo.py`, `examples/marine_safety/batch_llm_processing.py`, `examples/marine_safety/llm_detection_example.py`; document approximate first-run download size.
- Ensure generated example outputs are written under a temp/output path and not repo root unless documented.

### Phase 5 — Bounded smoke contract

Add static pytest/docs tests as the required smoke contract. Optional runtime smoke may be added only as skipped/pending #353 until CLI startup is reliable:

- Help-only commands for every registered sub-app:
  - `worldenergydata --help`
  - `worldenergydata <module> --help`
- Root safe commands for future runtime smoke only:
  - `worldenergydata version`
  - `worldenergydata info`
  - exclude `worldenergydata status` from required runtime smoke until its no-data behavior is confirmed after #353.
- Pure FDAS commands:
  - `fdas classify`
  - `fdas calculate-npv`
  - `fdas calculate-mirr`
  - `fdas calculate-all`
- Example import-only/fixture-only commands where confirmed safe.

The smoke contract must explicitly skip or assert-skip unsafe/data/credential commands.

## Files Likely to Change

| Path | Expected change |
|---|---|
| `README.md` | Add safety classifications and safe first-run sequence. |
| `docs/CLI.md` | Expand coverage to every registered sub-app and add safety/prereq labels. |
| `docs/COMMANDS.md` | Add banner disambiguating custom slash commands from runtime CLI; no rename/delete. |
| `examples/README.md` | New safety matrix for examples. |
| `examples/fdas_complete_workflow.py` | Optional trivial rewrite only if smoke-backed; otherwise classify stale in `examples/README.md`. |
| `examples/validation_examples.py` | Classify stale in `examples/README.md`; rebuild only if minimal and test-backed. |
| LLM example scripts | Add exact early opt-in guard before model loading. |
| `tests/...` | Static pytest/docs tests for docs parity and safety classification. |

## Test Plan

1. `test_cli_docs_registered_subapps_are_documented`
   - Parse CLI registered names from `src/worldenergydata/cli/main.py` via AST/static parsing.
   - Assert `docs/CLI.md` contains a structured row/section for each sub-app with safety class and prerequisite fields, not just a string mention.
2. `test_readme_basic_usage_has_safety_labels`
   - Assert README includes the safety taxonomy, exact cold-start safe commands, and labels for `bsee refresh`, `marine-safety scrape`, BSEE data-required commands, and marine-safety data-required commands.
3. `test_docs_commands_is_disambiguated`
   - Assert `docs/COMMANDS.md` has the exact required banner explaining it is not runtime CLI docs.
4. `test_examples_readme_classifies_all_python_examples`
   - Every `examples/**/*.py` appears in `examples/README.md` with a safety class and prerequisites; notebooks are not required here.
5. `test_llm_examples_require_explicit_opt_in`
   - Static test that the three target LLM examples check `WORLDENERGYDATA_RUN_LLM_EXAMPLES` or equivalent before model pipeline execution.
6. `test_stale_examples_are_not_presented_as_safe`
   - FDAS/validation examples are rewritten or explicitly marked stale/quarantined.
7. Optional smoke execution after #353:
   - all help-only commands exit 0 within a bounded timeout,
   - pure FDAS commands exit 0,
   - unsafe/data/credential commands are skipped with explicit reason.

## Acceptance Criteria

- [ ] `docs/CLI.md` covers every currently registered CLI sub-app at least at summary/prereq level.
- [ ] README contains a cold-start safe path and marks data-required/unbounded commands.
- [ ] `docs/COMMANDS.md` can no longer be mistaken for runtime CLI docs.
- [ ] `examples/README.md` classifies every Python example by safety and prerequisites.
- [ ] Stale/broken examples are repaired or clearly quarantined; they are not advertised as safe runnable examples.
- [ ] LLM examples require explicit opt-in or provide an early bail-out before large model download.
- [ ] Static pytest/docs smoke contract exists and avoids network, credentials, unbounded scrapes, server starts, and large downloads.
- [ ] Runtime smoke commands, if added, are skipped/pending #353 and exclude `status` until no-data behavior is confirmed.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| #353 `uv run` timeout blocks live smoke | Use direct `.venv` or static tests first; mark uv-mode smoke pending #353. |
| CLI docs become verbose/noisy | Use summary tables + links to `--help`; document details only where stable. |
| Example rewrites uncover deeper API breaks | Quarantine with issue links instead of broad refactors. |
| LLM import triggers download during tests | Static tests and opt-in flags; never instantiate transformer pipeline in smoke. |
| Overlap with #354 | #354 owns capability taxonomy; #355 owns user-facing CLI/example docs and smoke safety. |

## Approval Notes

This plan is safe for overnight execution after review/approval if the worker stays within docs, examples safety guardrails, and bounded static/smoke tests. It should not execute refreshes, scrapers, servers, external APIs, or LLM downloads.
