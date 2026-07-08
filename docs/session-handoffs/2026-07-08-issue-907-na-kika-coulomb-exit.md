# Session Handoff: Issue #907 Na Kika / Coulomb Transaction Package

Date: 2026-07-08T22:39:49Z
Repo: `worldenergydata`
Branch: `feat/wf-api-3286-worldenergydata-adopt`
Issue: https://github.com/vamseeachanta/worldenergydata/issues/907

## Current State

- Created GitHub issue #907 for the Shell/Talos/Ridgewood Na Kika / Coulomb transaction insight package.
- Drafted the issue plan at `docs/plans/2026-07-08-issue-907-na-kika-coulomb-transaction-package.md`.
- `docs/plans/README.md` already contains the #907 plan index row and is not currently dirty.
- Posted issue status comment: https://github.com/vamseeachanta/worldenergydata/issues/907#issuecomment-4918414774
- Issue labels remain `status:needs-plan`; do not implement yet.

## Plan Scope

The draft plan proposes a regenerable transaction package with:

- Structured transaction facts and source sidecar.
- Transaction HTML and machine-readable metrics.
- Standalone lifecycle HTML and lifecycle JSON.
- Economics-readiness JSON reporting BSEE production input status.
- Tests for Ridgewood buyer-leg handling, Shell/Talos consideration-basis separation, source claim provenance, BP preferential-right scenarios, Herschel minimum lifecycle coverage, and host-vs-field concept separation.

## Review State

- Codex r1 review: `MAJOR`; found missing Ridgewood modeling, weak consideration-basis tests, and narrow provenance.
- Codex subagent review: `MAJOR`; found under-specified lifecycle/economics artifacts, weak source-sidecar schema, missing golden metrics, and weak Herschel coverage.
- Codex follow-up review: `MINOR`; no remaining MAJOR content defects after patches.
- Claude review: `UNAVAILABLE`; noninteractive CLI returned `Not logged in · Please run /login`.
- Gemini review: `UNAVAILABLE`; noninteractive CLI required manual authorization and exited 41.

Review artifacts exist locally under `scripts/review/results/2026-07-08-plan-907-*.md`. That directory is ignored by `.gitignore`, so force-add the issue-specific review artifacts if they need to be preserved in Git.

## Blocker

T2 cross-provider review is incomplete. A real second-provider plan review is still required before moving #907 from `status:needs-plan` to `status:plan-review`.

## Recommended Next Checkpoint

1. Authenticate or route a second-provider review through Claude or Gemini.
2. If the second-provider review returns no MAJOR findings, update the plan review summary.
3. Commit/push the plan, handoff, and any chosen review artifacts using explicit pathspecs.
4. Move issue #907 to `status:plan-review`.
5. Wait for explicit user approval before implementation.

## Suggested Skills

- `coordination/issue-planning-mode` for the remaining plan-review gate.
- `coordination/pre-completion-cleanup-audit` before final closeout.
- `field-dev-code-recon` when implementation starts, because the task ties public field-development sources to local `worldenergydata` artifacts.

## Dirty/Residue Notes

Expected task residue:

- `docs/plans/2026-07-08-issue-907-na-kika-coulomb-transaction-package.md`
- `docs/session-handoffs/2026-07-08-issue-907-na-kika-coulomb-exit.md`
- ignored local review artifacts under `scripts/review/results/2026-07-08-plan-907-*.md`

Pre-existing/unrelated residue observed and not touched:

- `reports/capabilities/`
- `reports/lower_tertiary/lifecycle/`
- `scripts/lower_tertiary/build_lifecycle_posters.py`
- stash `stash@{0}: On main: wed stale pre-reorg dirty tree (recoverable) 2026-06-26`
- `/mnt/local-analysis/.cleanup-trash/20260616-095709`
