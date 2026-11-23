# WorldEnergyData Overnight Capability/Data-Completeness Batch Prep — 2026-04-26

## Purpose
Prepare `worldenergydata` GitHub work items for long-running overnight agents focused on understanding repo capabilities, data completeness, scheduler readiness, and user-facing smoke paths.

This is a **planning/audit-first** packet. It does not authorize implementation of unapproved issue work.

## Current queue facts

- Repo: `vamseeachanta/worldenergydata`
- Open issues inspected: 70
- Existing canonical plan files: 8 under `docs/plans/`
- Existing plan-review artifacts: cost/data issues only (`plan-334` through `plan-344` family)
- Local approval markers: none found under `.planning/plan-approved/`
- Important drift: #334 has GitHub `status:plan-approved`, but no local approval marker was present during this audit; do not treat it as unattended execution-ready until approval-marker drift is reconciled.

## New overnight-ready audit issues created

| Issue | Lane | Purpose | URL |
|---|---|---|---|
| #349 | planning/audit | Capability inventory + module readiness matrix | https://github.com/vamseeachanta/worldenergydata/issues/349 |
| #350 | planning/audit | Data completeness + freshness scorecard | https://github.com/vamseeachanta/worldenergydata/issues/350 |
| #351 | planning/audit | Scheduler/source refresh runtime readiness matrix | https://github.com/vamseeachanta/worldenergydata/issues/351 |
| #352 | planning/audit | Public CLI/examples smoke matrix | https://github.com/vamseeachanta/worldenergydata/issues/352 |

## Existing issues worth revisiting after audit baseline

### Highest leverage data/source backlog

| Issue | Why revisit | URL |
|---|---|---|
| #266 | EIA scheduler job operationalization; likely source freshness blocker | https://github.com/vamseeachanta/worldenergydata/issues/266 |
| #267 | BSEE scheduler runtime download/extraction compatibility; core local-data path | https://github.com/vamseeachanta/worldenergydata/issues/267 |
| #273 | SODIR scheduler runtime endpoint contract; source endpoint/API contract risk | https://github.com/vamseeachanta/worldenergydata/issues/273 |
| #269 | SODIR/Brazil/UKCS adapters; broad regional coverage | https://github.com/vamseeachanta/worldenergydata/issues/269 |
| #268 | Metocean Open-Meteo adapter; environmental capability | https://github.com/vamseeachanta/worldenergydata/issues/268 |
| #270 | LNG terminals refresh scheduler config; known scheduler gap | https://github.com/vamseeachanta/worldenergydata/issues/270 |
| #271 | `output_dir` wiring across scheduler jobs; cross-cutting runtime correctness | https://github.com/vamseeachanta/worldenergydata/issues/271 |
| #151 | NSTA UK National Data Repository indexing | https://github.com/vamseeachanta/worldenergydata/issues/151 |
| #153 | USCG MISLE bulk dataset acquisition | https://github.com/vamseeachanta/worldenergydata/issues/153 |
| #124 | BOEM lease data ingest | https://github.com/vamseeachanta/worldenergydata/issues/124 |
| #128 | BOEM company/operator hierarchy loader | https://github.com/vamseeachanta/worldenergydata/issues/128 |

### Test/quality blockers that affect capability discovery

| Issue | Why revisit | URL |
|---|---|---|
| #313 | pytest config/import cleanup may block reliable test discovery | https://github.com/vamseeachanta/worldenergydata/issues/313 |
| #327 | `conftest.py` blocks marine safety collection | https://github.com/vamseeachanta/worldenergydata/issues/327 |
| #328 | flake8 F821 count instability; environment/race risk | https://github.com/vamseeachanta/worldenergydata/issues/328 |
| #326 | missing `ProductionAnalyzer.prepare_production_data` method | https://github.com/vamseeachanta/worldenergydata/issues/326 |
| #325 | pre-existing defects surfaced by xfail markers | https://github.com/vamseeachanta/worldenergydata/issues/325 |
| #278 | broken `modules.*` compatibility shims after consolidation | https://github.com/vamseeachanta/worldenergydata/issues/278 |

### Cost/disclosure data issue family

| Issue | Current note | URL |
|---|---|---|
| #334 | Has `status:plan-approved` but no local approval marker found; reconcile before execution | https://github.com/vamseeachanta/worldenergydata/issues/334 |
| #343 | High-value annual statement source registry + yearly coverage tracker; plan exists | https://github.com/vamseeachanta/worldenergydata/issues/343 |
| #344 | Restatement/version lineage for annual disclosure records; plan exists | https://github.com/vamseeachanta/worldenergydata/issues/344 |
| #336 | Currency normalization/comparability policy; plan exists | https://github.com/vamseeachanta/worldenergydata/issues/336 |
| #342 | Proxy comparison regression boundary; plan exists | https://github.com/vamseeachanta/worldenergydata/issues/342 |

## Evidence anchors from repo inspection

- `README.md` advertises BSEE, marine safety, and FDAS workflows plus local BSEE data requirement.
- `MODULE_INDEX.md` claims 27 modules and flags scheduler gaps for `canada`, `hse`, `marine_safety`, `pipeline_safety`, and `lng_terminals`.
- `src/worldenergydata/` has far more live module folders than the README highlights, including `brazil_anp`, `canada`, `eia_us`, `hse`, `lng_terminals`, `metocean`, `mexico_cnh`, `pipeline_safety`, `sodir`, `texas_rrc`, `ukcs`, `vessel_fleet`, `vessel_hull_models`, `west_africa`, etc.
- `data/catalog.yaml` reports 12 modules / 44 datasets / ~10.5 MB, while `MODULE_INDEX.md` advertises 27 modules; this mismatch is the main data-completeness audit target.
- Several catalog modules are empty or likely incomplete: `hse`, `oil_price`, `pipeline_safety`, `wind` have zero catalog datasets; `marine_safety` catalog row counts look sample-sized.

## Recommended overnight batch topology

Use four planning/audit workers only. Do not run implementation or unbounded downloads unless a worker's issue body explicitly classifies the command as safe.

### Worker A — Capability Matrix (#349)

```text
Repo: /mnt/local-analysis/workspace-hub/worldenergydata
Issue: #349 https://github.com/vamseeachanta/worldenergydata/issues/349
Mode: planning/audit only; docs/reports output only; no implementation.

Goal: Build the capability inventory and module readiness matrix requested in #349.

Required outputs:
- docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md
- docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml
- Suggested follow-up issue list with duplicate-search evidence.

Evidence sources: README.md, MODULE_INDEX.md, module-manifest.yaml, data/catalog.yaml, src/worldenergydata/**, tests/**, docs/**, examples/**, notebooks/**, scheduler configs.

Rules:
- Use explicit file-path evidence for every module claim.
- Classify modules into implementation-ready, planning-needed, data-missing, docs-stale, blocked/test-risk.
- Do not change code.
- Post a concise progress/final comment to #349 with artifact paths and top blockers.
```

### Worker B — Data Completeness Scorecard (#350)

```text
Repo: /mnt/local-analysis/workspace-hub/worldenergydata
Issue: #350 https://github.com/vamseeachanta/worldenergydata/issues/350
Mode: planning/audit only; bounded metadata inspection; no unbounded downloads.

Goal: Build the data completeness/freshness scorecard requested in #350.

Required outputs:
- docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md
- docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.csv or .yaml
- Prioritized list of safe overnight data-refresh candidates with commands, expected paths, and risk tags.

Rules:
- Reconcile MODULE_INDEX.md vs data/catalog.yaml module mismatches.
- Call out empty/sample-only/stale modules with row-count and timestamp evidence.
- Rank BSEE, EIA, SODIR, UKCS/NSTA, Brazil ANP, Mexico CNH, Canada, Texas RRC, BOEM lease/company, marine safety, HSE, metocean.
- Do not perform large downloads by default.
- Post concise final comment to #350.
```

### Worker C — Scheduler Runtime Readiness (#351)

```text
Repo: /mnt/local-analysis/workspace-hub/worldenergydata
Issue: #351 https://github.com/vamseeachanta/worldenergydata/issues/351
Mode: planning/audit and dry-run classification only.

Goal: Audit scheduler/runtime refresh readiness and prepare a safe command pack.

Required outputs:
- docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md
- docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md
- Per-issue next-lane classification for #266, #267, #268, #269, #270, #271, #273.

Rules:
- Explicitly separate repo-code defects from host/API/credential/runtime blockers.
- Every command in the command pack must be tagged no-op audit, endpoint probe, bounded sample, full refresh, or blocked.
- Do not run full refreshes unless already proven bounded and safe.
- Post concise final comment to #351 and linked issue comments only if confidence is high.
```

### Worker D — CLI/Examples Smoke Matrix (#352)

```text
Repo: /mnt/local-analysis/workspace-hub/worldenergydata
Issue: #352 https://github.com/vamseeachanta/worldenergydata/issues/352
Mode: smoke verification only; no implementation.

Goal: Verify public CLI/examples/notebook pathways and classify README/docs commands.

Required outputs:
- docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md
- docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml or .csv
- Follow-up issue candidates for broken/stale public examples.

Rules:
- Prefer bounded commands: `uv run worldenergydata --help`, `uv run worldenergydata info`, module `--help`, and pure FDAS calculation examples.
- Avoid commands that download large BSEE or external datasets unless run in dry-run/sample mode.
- Link results to known issues #313, #327, #328, #326, #325, #278 where appropriate.
- Post concise final comment to #352.
```

## Execution guardrails

1. These four new issues are **not** implementation-approved; they are planning/audit work items.
2. Do not treat #334 as unattended execution-ready until `status:plan-approved` is backed by `.planning/plan-approved/334.md` or the approval-state drift is otherwise reconciled.
3. If an overnight worker discovers a fixable bug, create/link a follow-up issue or draft a plan; do not silently patch code.
4. For long data-refresh commands, first write the command pack and classify boundedness; execute only commands explicitly marked safe.
5. All final outputs should be durable repo artifacts under `docs/reports/` and GitHub issue comments with links.
