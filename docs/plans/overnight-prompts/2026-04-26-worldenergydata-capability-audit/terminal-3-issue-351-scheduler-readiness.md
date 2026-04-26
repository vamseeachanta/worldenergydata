# Terminal 3 — Issue #351 Scheduler/Source Refresh Runtime Readiness

You are running unattended in `/mnt/local-analysis/workspace-hub/worldenergydata`.

GitHub issue: #351 https://github.com/vamseeachanta/worldenergydata/issues/351

## Mission
Audit the `worldenergydata` scheduler/runtime refresh pipeline and prepare a safe overnight batch plan for source refreshes, endpoint probes, and configuration fixes.

## Mode and boundaries
- Planning/audit/reporting only.
- Dry-run and help/version inspection are allowed.
- Endpoint probes are allowed only if clearly bounded and non-mutating.
- Do NOT run full refreshes or unbounded downloads.
- Do NOT implement code changes.
- Do NOT edit labels, issue bodies, or unrelated files.
- Do NOT ask the user any questions.
- Use `uv run` for Python commands where applicable.

## Allowed write paths
Write only:
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`
- `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md`

You may also post one concise final GitHub comment to issue #351.

## Forbidden paths
Do NOT write to:
- `src/**`
- `tests/**`
- `data/**`
- `config/**`
- `docs/plans/**`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.*`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.*`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.*`
- `.planning/**`

## Evidence sources to inspect
- `src/worldenergydata/scheduler/**`
- `config/*.yml`
- `scripts/*refresh*`, `scripts/*sync*`, `scripts/download_*`, `Makefile`
- `README.md`, `MODULE_INDEX.md`, docs mentioning scheduler/data refresh
- source adapters/clients for EIA, BSEE, SODIR, UKCS, Brazil ANP, Mexico CNH, Canada, Texas RRC, metocean, LNG terminals, marine safety, HSE, pipeline safety
- GitHub issues #266, #267, #268, #269, #270, #271, #273.

## Required analysis
For each scheduler/source job classify:
- job/config exists: yes/no, with evidence paths
- endpoint/client contract known vs broken/unclear
- output directory wiring status
- credentials/API requirements
- dry-run/smoke-test command availability
- expected output artifact path
- safe overnight action: no-op audit, endpoint probe, bounded sample fetch, full refresh candidate, implementation needed, credential-blocked
- related GitHub issue(s)
- runtime-vs-repo-remediation split

Specifically reconcile:
- #266 EIA scheduler job operationalization
- #267 BSEE scheduler runtime download/extraction compatibility
- #268 metocean Open-Meteo adapter
- #269 SODIR/Brazil ANP/UKCS adapters
- #270 LNG terminals scheduler config
- #271 output_dir wiring
- #273 SODIR scheduler runtime endpoint contract

## Required output: Markdown readiness report
Write `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` with sections:
1. Executive summary
2. Methodology and safe commands used
3. Scheduler inventory
4. Source-by-source readiness matrix
5. Issue #266-#273 next-lane classification
6. Runtime vs repo-remediation blockers
7. Safe overnight execution sequence
8. Follow-up issue candidates/revisited issues

## Required output: command pack
Write `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md` with:
- exact commands grouped by risk tag
- commands that are safe to run now
- commands that are full-refresh candidates but not run
- commands blocked by credentials/API/runtime uncertainty
- expected output paths
- rollback/cleanup notes for generated temp files

## Final GitHub comment
Post a concise final comment to #351 including:
- artifact paths
- per-issue next-lane classification for #266-#273
- safe commands vs blocked commands

## Verification before stopping
Run:
- `test -s docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`
- `test -s docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md`
- `git status --short -- docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md`

Do not commit. Leave artifacts for orchestrator review.
