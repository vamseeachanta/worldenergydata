# Cost disclosure execution wave — future issues and exit handoff

Date: 2026-04-23
Repo: `vamseeachanta/worldenergydata`
Wave: approved cost execution packet `2026-04-22-approved-cost-wave`

## Completed execution branches

- `issue-335-exec`
  - PR: https://github.com/vamseeachanta/worldenergydata/pull/new/issue-335-exec
  - Issue: https://github.com/vamseeachanta/worldenergydata/issues/335
- `issue-338-exec`
  - PR: https://github.com/vamseeachanta/worldenergydata/pull/new/issue-338-exec
  - Issue: https://github.com/vamseeachanta/worldenergydata/issues/338
- `issue-337-exec`
  - PR: https://github.com/vamseeachanta/worldenergydata/pull/new/issue-337-exec
  - Issue: https://github.com/vamseeachanta/worldenergydata/issues/337

## Validated results

### #335
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_linkage.py -v`
- Closeout comment: https://github.com/vamseeachanta/worldenergydata/issues/335#issuecomment-4300768508

### #338
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_disclosure_analytics.py tests/unit/fdas/test_disclosure_api.py tests/test_query_api.py --no-cov -v`
- Closeout comment: https://github.com/vamseeachanta/worldenergydata/issues/338#issuecomment-4300765931

### #337
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_disclosure_ingest_contract.py -v`
- Passed: `PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/unit/cost/test_calibration_schema.py -v`
- Closeout comment: https://github.com/vamseeachanta/worldenergydata/issues/337#issuecomment-4300829035

## Known blocker carried forward

The planned sanction-layer regression boundary that included `tests/unit/cost/test_proxy_comparison.py` is currently broken on `main` independent of the disclosure-wave diffs.

Observed failure:
- `ModuleNotFoundError: No module named 'worldenergydata.cost.calibration.proxy_comparison'`

Grounding:
- test exists: `tests/unit/cost/test_proxy_comparison.py`
- referenced module path is absent: `src/worldenergydata/cost/calibration/proxy_comparison.py`

## Future GitHub issues created from this wave

### #342 — broken regression boundary
- URL: https://github.com/vamseeachanta/worldenergydata/issues/342
- Title: `bug(cost): restore broken proxy comparison regression boundary`
- Reason: fixes the pre-existing missing-module failure so future disclosure compatibility checks can run without false negatives.

### #343 — operator annual statement source registry
- URL: https://github.com/vamseeachanta/worldenergydata/issues/343
- Title: `feat(cost): build major-operator annual statement source registry and yearly coverage tracker`
- Reason: operationalizes the next scaling step for annual disclosure gathering by tracking major operators, online annual-statement sources, and year coverage over time.

### #344 — disclosure restatement/version lineage
- URL: https://github.com/vamseeachanta/worldenergydata/issues/344
- Title: `feat(cost): add restatement/version lineage for annual disclosure records`
- Reason: year-over-year statement tracking will eventually require explicit handling of amended filings, revised annual reports, and superseded disclosure rows.

## Recommended next order

1. Review and merge the implementation branches for #335, #338, and #337.
2. Plan and execute #342 to restore the broken regression boundary.
3. Plan and execute #343 to establish durable annual-statement source coverage for major operators.
4. Execute #336 for normalization/comparability once source coverage and ingestion paths are stable enough to justify it.
5. Plan #344 when original-vs-revised disclosure lineage becomes material in the dataset.

## Exit state

- Main checkout remained clean while execution work happened in isolated worktrees.
- Follow-up issues needed for the next wave have been created, not just drafted.
- This file is the docs-side handoff anchor for the completed execution wave.
