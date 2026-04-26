# Terminal 1 — Issue #349 Capability Inventory + Module Readiness Matrix

You are running unattended in `/mnt/local-analysis/workspace-hub/worldenergydata`.

GitHub issue: #349 https://github.com/vamseeachanta/worldenergydata/issues/349

## Mission
Build a repo-grounded capability inventory and module readiness matrix for `worldenergydata` so future agents can understand what the repo can actually do versus what README/MODULE_INDEX/docs claim.

## Mode and boundaries
- Planning/audit/reporting only.
- Do NOT implement code changes.
- Do NOT run unbounded data downloads.
- Do NOT edit GitHub labels, issue body, or unrelated files.
- Do NOT ask the user any questions.
- Use `uv run` for Python commands where applicable.

## Allowed write paths
Write only:
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`

You may also post one concise final GitHub comment to issue #349.

## Forbidden paths
Do NOT write to:
- `src/**`
- `tests/**`
- `data/**`
- `docs/plans/**`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.*`
- `docs/reports/2026-04-26-worldenergydata-scheduler-*`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.*`
- `.planning/**`

## Evidence sources to inspect
- `README.md`
- `MODULE_INDEX.md`
- `module-manifest.yaml`
- `data/catalog.yaml`
- `src/worldenergydata/**`
- `tests/**`
- `docs/**`
- `examples/**`
- `notebooks/**`
- `config/**`
- `src/worldenergydata/scheduler/**`
- open GitHub issues, especially #266-#273, #313, #327, #328, #334, #343, #344, #336, #342, #151, #153, #124, #128.

## Required analysis
For every module named in `MODULE_INDEX.md` and every top-level production module under `src/worldenergydata/`, classify:
- package/source exists: yes/no, with path evidence
- public CLI/API entrypoint exists: yes/no/unclear, with path evidence
- tests exist and are likely collectable: yes/no/blocked, with path evidence
- data catalog coverage exists: yes/no/sample-only/empty, with path evidence
- scheduler coverage exists: yes/no/gap/blocked, with path evidence
- docs/examples exist: yes/no/stale, with path evidence
- related open issues/blockers
- readiness lane: implementation-ready, planning-needed, data-missing, docs-stale, blocked/test-infra-risk

## Required output: Markdown
Write `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` with sections:
1. Executive summary
2. Methodology and commands used
3. Source-of-truth comparison: README vs MODULE_INDEX vs source tree vs data catalog
4. Readiness matrix table
5. Stale/overbroad claims and proposed corrections
6. High-value follow-up issues to create or revisit
7. Risks/unknowns
8. Recommended next overnight batch lanes

## Required output: YAML
Write `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml` with a list of module records containing keys:
- module
- source_paths
- cli_entrypoints
- tests
- data_catalog
- scheduler
- docs_examples
- related_issues
- readiness_lane
- evidence_notes

## Final GitHub comment
Post a concise final comment to #349 including:
- artifact paths
- top 5 capability gaps
- top 5 modules ready for deeper planning/execution
- any follow-up issue candidates

## Verification before stopping
Run:
- `test -s docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
- `test -s docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`
- `git status --short -- docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`

Do not commit. Leave artifacts for orchestrator review.
