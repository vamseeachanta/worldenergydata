# Cost disclosure execution wave — future issues and exit handoff

Date: 2026-04-23
Repo: `vamseeachanta/worldenergydata`
Wave: approved cost execution packet `2026-04-22-approved-cost-wave`

## Merged implementation work

The first implementation wave has been landed on `main`.

- #335 — disclosure-to-sanction linkage contract
  - PR merged: https://github.com/vamseeachanta/worldenergydata/pull/345
- #337 — disclosure ingest contract
  - PR merged: https://github.com/vamseeachanta/worldenergydata/pull/346
- #338 — disclosure analytics views and FDAS surface
  - PR merged: https://github.com/vamseeachanta/worldenergydata/pull/347

## Validation evidence from the landed wave

### #335
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_linkage.py -v`
- Closeout comment: https://github.com/vamseeachanta/worldenergydata/issues/335#issuecomment-4300768508

### #337
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_disclosure_ingest_contract.py -v`
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_calibration_schema.py -v`
- Closeout comment: https://github.com/vamseeachanta/worldenergydata/issues/337#issuecomment-4300829035

### #338
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_disclosure_analytics.py tests/unit/fdas/test_disclosure_api.py tests/test_query_api.py --no-cov -v`
- Closeout comment: https://github.com/vamseeachanta/worldenergydata/issues/338#issuecomment-4300765931

## Known blocker carried forward

The sanction-layer regression boundary around `tests/unit/cost/test_proxy_comparison.py` is still broken on `main` independent of the disclosure-wave diffs.

Observed failure
- `ModuleNotFoundError: No module named 'worldenergydata.cost.calibration.proxy_comparison'`

Grounding
- failing test exists: `tests/unit/cost/test_proxy_comparison.py`
- referenced module path is absent: `src/worldenergydata/cost/calibration/proxy_comparison.py`

## Future GitHub issues created from this work

### #342 — broken regression boundary
- URL: https://github.com/vamseeachanta/worldenergydata/issues/342
- Title: `bug(cost): restore broken proxy comparison regression boundary`
- Current planning state:
  - current draft plan: `docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md`
  - first review artifacts:
    - `scripts/review/results/2026-04-23-plan-342-codex.md`
    - `scripts/review/results/2026-04-23-plan-342-gemini.md`
  - rerun review artifacts:
    - `scripts/review/results/2026-04-23-plan-342-codex-rerun.md`
    - `scripts/review/results/2026-04-23-plan-342-gemini-rerun.md`
  - latest issue comments:
    - https://github.com/vamseeachanta/worldenergydata/issues/342#issuecomment-4301355205
    - https://github.com/vamseeachanta/worldenergydata/issues/342#issuecomment-4302933474
- Current status: revised twice after repeated MAJOR findings; still draft; needs another rerun review before `status:plan-review`

### #343 — operator annual statement source registry
- URL: https://github.com/vamseeachanta/worldenergydata/issues/343
- Title: `feat(cost): build major-operator annual statement source registry and yearly coverage tracker`
- Current planning state:
  - current draft plan: `docs/plans/2026-04-23-issue-343-major-operator-annual-statement-source-registry-and-yearly-coverage-tracker.md`
  - first review artifacts:
    - `scripts/review/results/2026-04-23-plan-343-codex.md`
    - `scripts/review/results/2026-04-23-plan-343-gemini.md`
  - rerun artifact saved:
    - `scripts/review/results/2026-04-23-plan-343-gemini-rerun.md`
  - latest issue comments:
    - https://github.com/vamseeachanta/worldenergydata/issues/343#issuecomment-4302728798
    - https://github.com/vamseeachanta/worldenergydata/issues/343#issuecomment-4303627633
- Current status: revised after first MAJOR review wave; rerun Gemini still returned MAJOR; Codex rerun did not yield a usable verdict in this session; plan remains draft and needs another revision + rerun

### #344 — disclosure restatement/version lineage
- URL: https://github.com/vamseeachanta/worldenergydata/issues/344
- Title: `feat(cost): add restatement/version lineage for annual disclosure records`
- Current planning state:
  - current draft plan: `docs/plans/2026-04-23-issue-344-restatement-version-lineage-for-annual-disclosure-records.md`
  - review artifacts:
    - `scripts/review/results/2026-04-23-plan-344-codex.md`
    - `scripts/review/results/2026-04-23-plan-344-gemini.md`
  - latest issue comment:
    - https://github.com/vamseeachanta/worldenergydata/issues/344#issuecomment-4302836484
- Current status: revised once after MAJOR findings; still draft; needs rerun review before `status:plan-review`

### #348 — planning index governance
- URL: https://github.com/vamseeachanta/worldenergydata/issues/348
- Title: `docs(planning): add canonical docs/plans README index for issue-plan tracking`
- Reason: this repo currently has `docs/plans/*.md` artifacts but no `docs/plans/README.md`, which blocks the standard planning-index workflow and makes state auditing harder

## Related planning state

### #336 — currency normalization/comparability
- Existing plan: `docs/plans/2026-04-22-issue-336-currency-normalization-and-comparability-policy-for-annual-disclosures.md`
- Existing review artifacts:
  - `scripts/review/results/2026-04-22-plan-336-codex.md`
  - `scripts/review/results/2026-04-22-plan-336-gemini.md`
- Current blocker: Codex still returned `MAJOR` because the required #334 disclosure foundation is not yet landed as the raw merged input surface assumed by the plan
- Latest state comment:
  - https://github.com/vamseeachanta/worldenergydata/issues/336#issuecomment-4301225938

## Recommended next order from this exit point

1. Revise #343 again to store per-year verified document URLs, remove or derive redundant year-bound fields, and clean up filing-channel semantics; then rerun Codex + Gemini.
2. Rerun #344 on the revised draft and only move it to `status:plan-review` if the next review wave is clean enough.
3. Rerun #342 once more on the newly tightened draft and only move it to `status:plan-review` if that review wave is clean enough.
4. Add `docs/plans/README.md` via #348 so future planning waves can update a canonical local index.
5. Keep #336 in planning/revision state until the #334 foundation dependency is truly in place for implementation.

## Exit state

- `main` is clean at exit.
- No background review processes remain running.
- New future issues have been created and documented, not just discussed.
- This file is the handoff anchor for what landed, what was discovered, what remains blocked, and what the next operator should do.
