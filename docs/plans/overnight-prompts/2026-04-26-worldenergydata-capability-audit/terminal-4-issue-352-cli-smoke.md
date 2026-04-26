# Terminal 4 — Issue #352 CLI/Examples Smoke Matrix

You are running unattended in `/mnt/local-analysis/workspace-hub/worldenergydata`.

GitHub issue: #352 https://github.com/vamseeachanta/worldenergydata/issues/352

## Mission
Verify the user-facing CLI, examples, notebooks, and smoke-test pathways for `worldenergydata` so capability claims can be trusted by agents and users.

## Mode and boundaries
- Smoke verification/reporting only.
- Run bounded, no-download commands only.
- Do NOT run commands that perform large downloads or require credentials unless there is an explicit dry-run/help mode.
- Do NOT implement code changes.
- Do NOT edit labels, issue bodies, or unrelated files.
- Do NOT ask the user any questions.
- Use `uv run` for Python commands.

## Allowed write paths
Write only:
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml`

You may also post one concise final GitHub comment to issue #352.

## Forbidden paths
Do NOT write to:
- `src/**`
- `tests/**`
- `data/**`
- `docs/plans/**`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.*`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.*`
- `docs/reports/2026-04-26-worldenergydata-scheduler-*`
- `.planning/**`

## Evidence sources to inspect
- `README.md` Basic Usage / module usage examples
- `docs/CLI.md`
- `docs/COMMANDS.md`
- `docs/api-contracts.md`
- `src/worldenergydata/cli/**`
- `examples/**`
- `notebooks/README.md`
- quickstart notebooks under `notebooks/**`
- known issue context: #313, #315, #316, #325, #326, #327, #328, #278.

## Commands to prioritize
Run bounded commands such as:
- `uv run worldenergydata --help`
- `uv run worldenergydata info`
- module `--help` commands discoverable from CLI
- pure FDAS calculations from README if they do not require local data
- docs/example scripts only if inspection shows they are no-download or fixture-only

If a command would download BSEE/external data, require credentials, or run a full analysis over large local data, do not run it. Classify it instead.

## Required classification
For every README Basic Usage command and representative docs/CLI commands, classify:
- passing
- failing with captured error summary
- data-required
- credential-required
- unsafe/unbounded
- stale docs / command missing
- skipped because duplicate of another command

For examples/notebooks classify:
- import-only smoke feasible
- fixture-only run feasible
- requires local BSEE/data
- requires network/credentials
- stale/broken import
- not assessed, with reason

## Required output: Markdown
Write `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` with sections:
1. Executive summary
2. Methodology and commands run
3. README command matrix
4. CLI module help matrix
5. Examples/notebooks matrix
6. Known blockers mapped to existing issues
7. New follow-up issue candidates
8. Recommended README/docs updates

## Required output: YAML
Write `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml` with records containing:
- command_or_artifact
- source_file
- status
- command_run
- exit_code
- evidence_summary
- related_issue
- recommended_next_action

## Final GitHub comment
Post a concise final comment to #352 including:
- artifact paths
- commands passing
- commands broken/stale
- data-required/credential-required commands
- related existing issues and follow-up candidates

## Verification before stopping
Run:
- `test -s docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
- `test -s docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml`
- `git status --short -- docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml`

Do not commit. Leave artifacts for orchestrator review.
