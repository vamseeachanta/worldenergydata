# Terminal 2 — Issue #350 Data Completeness + Freshness Scorecard

You are running unattended in `/mnt/local-analysis/workspace-hub/worldenergydata`.

GitHub issue: #350 https://github.com/vamseeachanta/worldenergydata/issues/350

## Mission
Build a data completeness and freshness scorecard for `worldenergydata`, using the live data catalog, source adapters, scheduler jobs, local data tree, and source configs to identify which datasets are complete, sample-only, stale, missing, or blocked.

## Mode and boundaries
- Planning/audit/reporting only.
- Metadata inspection and bounded file-stat/row-count checks are allowed.
- Do NOT run unbounded downloads or full refreshes.
- Do NOT implement code changes.
- Do NOT edit labels, issue bodies, or unrelated files.
- Do NOT ask the user any questions.
- Use `uv run` for Python commands where applicable.

## Allowed write paths
Write only:
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`

You may also post one concise final GitHub comment to issue #350.

## Forbidden paths
Do NOT write to:
- `src/**`
- `tests/**`
- `data/**`
- `docs/plans/**`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.*`
- `docs/reports/2026-04-26-worldenergydata-scheduler-*`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.*`
- `.planning/**`

## Evidence sources to inspect
- `data/catalog.yaml`
- `data/**` directory tree, file sizes, row counts for CSV/JSON where cheap
- `MODULE_INDEX.md`
- `module-manifest.yaml`
- `config/**`
- `scripts/*refresh*`, `scripts/*sync*`, `scripts/generate_catalog.py`, `scripts/generate_data_catalog.py`
- `src/worldenergydata/**/data/**`, `src/worldenergydata/**/client/**`, `src/worldenergydata/**/collectors/**`, `src/worldenergydata/**/scrapers/**`, `src/worldenergydata/**/importers/**`
- `src/worldenergydata/scheduler/**`
- relevant open GitHub issues: #334, #336, #343, #344, #151, #153, #124, #128, #266-#273.

## Required analysis
For each expected data-source/domain module, classify:
- expected source authority / URL/API if discoverable from repo
- local presence and path(s)
- catalog presence and dataset count
- row count / size / timestamp evidence
- sample-only vs production-scale status
- freshness cadence and scheduler coverage
- credential/API key requirements
- blocker/related issue(s)
- recommended lane: complete-enough, sample-only, missing, stale, credential-blocked, scheduler-blocked, unknown

Prioritize these sources in the report:
- BSEE
- EIA
- SODIR
- UKCS/NSTA
- Brazil ANP
- Mexico CNH
- Canada
- Texas RRC
- BOEM lease/company/operator
- Marine safety / USCG MISLE / NTSB / MAIB / TSB
- HSE
- Pipeline safety
- Metocean
- LNG terminals
- Vessel fleet / vessel hull models
- FDAS / economics / cost disclosures

## Required output: Markdown
Write `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` with sections:
1. Executive summary
2. Methodology and bounded commands used
3. `MODULE_INDEX.md` vs `data/catalog.yaml` reconciliation
4. Data completeness scorecard table
5. Empty, sample-only, stale, and missing datasets
6. Credential/API/runtime blockers
7. Safe overnight refresh candidate list
8. Follow-up issue candidates/revisited issues
9. Recommended next steps

## Required output: YAML
Write `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml` with records containing:
- module
- source_authority
- local_paths
- catalog_datasets
- row_count
- size_bytes
- timestamps
- completeness_lane
- scheduler_status
- credentials_needed
- related_issues
- safe_next_action
- evidence_notes

## Safe refresh command list
For any recommended command, tag it as one of:
- no-op audit
- endpoint probe
- bounded sample
- full refresh candidate - not run
- blocked - credentials/API required
- blocked - implementation needed

Do not run commands tagged full refresh or blocked.

## Final GitHub comment
Post a concise final comment to #350 including:
- artifact paths
- top 10 data completeness gaps
- safe refresh candidates
- blocked/credential-required items

## Verification before stopping
Run:
- `test -s docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `test -s docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`
- `git status --short -- docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`

Do not commit. Leave artifacts for orchestrator review.
