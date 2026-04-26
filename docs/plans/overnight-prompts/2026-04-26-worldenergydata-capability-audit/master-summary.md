# WorldEnergyData Overnight Capability/Data Completeness Audit Prompt Pack — 2026-04-26

## Mode
Claude-only, planning/audit/reporting wave. No implementation, no unbounded downloads, no destructive operations.

## Repo
`/mnt/local-analysis/workspace-hub/worldenergydata`

## Issue-to-terminal mapping

| Terminal | Issue | Workstream | Prompt file | Primary output |
|---:|---:|---|---|---|
| T1 | #349 | Capability inventory + module readiness matrix | `terminal-1-issue-349-capability-matrix.md` | `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` |
| T2 | #350 | Data completeness + freshness scorecard | `terminal-2-issue-350-data-completeness.md` | `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` |
| T3 | #351 | Scheduler/source refresh runtime readiness | `terminal-3-issue-351-scheduler-readiness.md` | `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` |
| T4 | #352 | CLI/examples smoke matrix | `terminal-4-issue-352-cli-smoke.md` | `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` |

## Contention map

- T1 writes only:
  - `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
  - `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`
- T2 writes only:
  - `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
  - `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`
- T3 writes only:
  - `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`
  - `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md`
- T4 writes only:
  - `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
  - `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml`

All workers may post GitHub issue comments to their own issue only. No worker should edit labels, issue bodies, code, tests, shared indexes, or the batch handoff file.

## Launch pattern

Use Claude Code non-interactive mode from repo root. Example:

```bash
cd /mnt/local-analysis/workspace-hub/worldenergydata
mkdir -p logs/overnight/2026-04-26-worldenergydata-capability-audit
PROMPT=$(< docs/plans/overnight-prompts/2026-04-26-worldenergydata-capability-audit/terminal-1-issue-349-capability-matrix.md)
claude -p --permission-mode acceptEdits --no-session-persistence --output-format text --max-budget-usd 20 "$PROMPT" </dev/null \
  > logs/overnight/2026-04-26-worldenergydata-capability-audit/terminal-1-issue-349.log 2>&1 &
```

## Morning deliverables

By morning, expect:

1. Four report artifacts under `docs/reports/`.
2. Four machine-readable matrices/command packs.
3. One final issue comment per issue #349-#352.
4. A prioritized follow-up list for future implementation/data-refresh plans.
5. Clear classification of safe vs unsafe long-running data refresh commands.

## Hard stop

This pack does **not** authorize implementation or code changes. If a worker discovers a fix, it should document it as a follow-up issue candidate or recommended plan target.
