# Adversarial Plan Review - #910 - Codex Subagent Fallback

Verdict: MAJOR

## Findings

1. **MAJOR - Quarantined roots can still be recursively touched for size before the private-root short-circuit.**
   Evidence: `docs/plans/2026-07-09-issue-910-mnt-ace-ecosystem-data-inventory.md:263-270` runs a "root-level size check" before returning the private/legacy row; `:334` allows private rows to record root-level size; `:313-315` tests child-listing/manifest limits but does not assert that `du`/size traversal is skipped for private or unknown roots. A timeboxed `du` can still traverse private directory entries. This leaves the leakage/crawl blocker partially open. Private/unknown roots should use `stat`-level metadata only or omit size unless sourced from a trusted precomputed cache, with a test proving the size walker is not called.

2. **MAJOR - The tracked HTML/JSON outputs can publish raw private/client root paths.**
   Evidence: tracked outputs are planned at `docs/plans/2026-07-09-issue-910-mnt-ace-ecosystem-data-inventory.md:195-196`; the report must record `path` at `:333`; private rows still record root path at `:334`; the plan already enumerates sensitive-looking roots such as private/client/adjacent-repo data roots at `:151-153`. The repo is public, so raw private/quarantine path names in committed HTML/JSON are a leakage channel even if child paths are omitted. Private rows need redacted stable IDs in tracked artifacts, with any raw-path mapping kept out of git.

3. **MAJOR - The legal/security scan gate is mis-targeted and would not scan this repo's generated artifacts.**
   Evidence: the plan's gate is just `/mnt/local-analysis/workspace-hub/scripts/legal/legal-sanity-scan.sh` at `docs/plans/2026-07-09-issue-910-mnt-ace-ecosystem-data-inventory.md:343`. That script sets `WORKSPACE_ROOT` from its own location at `/mnt/local-analysis/workspace-hub` in `/mnt/local-analysis/workspace-hub/scripts/legal/legal-sanity-scan.sh:16-17`; with no arguments it scans `workspace-hub`, not `/mnt/local-analysis/worldenergydata`, at `:282-285`; `--repo` also resolves under `workspace-hub` at `:263-266`. This does not gate leaked private paths/content in `worldenergydata/docs/reports`. The plan needs a scanner/test command that explicitly targets the current checkout and the generated HTML/JSON.

## Checks

- Read the revised plan, `docs/plans/README.md`, the initial Codex review, and Claude/Gemini unavailable artifacts.
- Verified #910 is open with `status:needs-plan`; no `.planning/plan-approved/910.md` exists.
- Confirmed `docs/plans/README.md:77` lists #910 as `draft`.
- Confirmed Claude and Gemini artifacts are `UNAVAILABLE` and explicitly not approval substitutes: `scripts/review/results/2026-07-09-plan-910-claude.md:3-15`, `scripts/review/results/2026-07-09-plan-910-gemini.md:3-15`.
- Verified bounded live probes only: `find /mnt/ace -maxdepth 2 -type d -name data` found 14 roots; no deep crawl performed.
- Execution/TDD gates are improved: plan approval marker/label gate at plan `:61`, RED checkpoint at `:62`, and ACs at `:328-332`.
- HTML default is satisfied, but the publication boundary is not safe until private-root redaction and a correctly targeted legal scan are added.
- No files edited. Pre-completion audit surfaced pre-existing dirty/untracked repo state and a pre-existing stash; preserved unchanged.
