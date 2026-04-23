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
  - draft plan exists at `docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md`
  - Codex adversarial review artifact exists:
    - `scripts/review/results/2026-04-23-plan-342-codex.md`
  - Gemini artifact recorded as unavailable:
    - `scripts/review/results/2026-04-23-plan-342-gemini.md`
  - issue comment with review/update:
    - https://github.com/vamseeachanta/worldenergydata/issues/342#issuecomment-4301355205
- Current status: revised after Codex MAJOR findings; needs fresh rerun review before `status:plan-review`

### #343 — operator annual statement source registry
- URL: https://github.com/vamseeachanta/worldenergydata/issues/343
- Title: `feat(cost): build major-operator annual statement source registry and yearly coverage tracker`
- Draft plan exists at:
  - `docs/plans/2026-04-23-issue-343-major-operator-annual-statement-source-registry-and-yearly-coverage-tracker.md`
- Planning comment posted:
  - https://github.com/vamseeachanta/worldenergydata/issues/343#issuecomment-4301223324
- Current status: review wave was started but intentionally stopped for exit preparation; no canonical review artifact saved yet

### #344 — disclosure restatement/version lineage
- URL: https://github.com/vamseeachanta/worldenergydata/issues/344
- Title: `feat(cost): add restatement/version lineage for annual disclosure records`
- Draft plan exists at:
  - `docs/plans/2026-04-23-issue-344-restatement-version-lineage-for-annual-disclosure-records.md`
- Planning comment posted:
  - https://github.com/vamseeachanta/worldenergydata/issues/344#issuecomment-4301223635
- Current status: drafted, not yet adversarially reviewed

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

1. Rerun adversarial review for the revised #342 draft and only move it to `status:plan-review` if the next review wave is clean enough.
2. Run the first full adversarial review wave for #343 and save canonical Codex/Gemini artifacts (or explicit unavailable artifact if Gemini fails again).
3. Run the first adversarial review wave for #344.
4. Add `docs/plans/README.md` via #348 so future planning waves can update a canonical local index.
5. Keep #336 in planning/revision state until the #334 foundation dependency is truly in place for implementation.

## Exit state

- `main` is clean at exit.
- No background review processes remain running.
- New future issues have been created and documented, not just discussed.
- This file is the handoff anchor for what landed, what was discovered, what remains blocked, and what the next operator should do.