# Code Review: Issue #751 Colorado ECMC Form 5A Ingest

Issue: https://github.com/vamseeachanta/worldenergydata/issues/751
Reviewer: Codex inline
Date: 2026-07-04
Scope: implementation branch `feature/colorado-ecmc-form5a-ingest-751`

## Verdict

APPROVE after inline fix.

## Review Notes

Multi-agent dispatch was not used because the available subagent tool requires
explicit user authorization for subagents/delegation. This review was performed
inline against the code diff, tests, tracked config, docs, and live `/mnt/ace`
run evidence.

## Findings

### Important - Default Config Was Capped But Not Runnable

The first implementation of `build_facility_detail_source_list` raised whenever
the full raw WELLS source-list length exceeded `max_requests` unless
`allow_full_source_list` was true. That made the tracked conservative config
(`max_requests: 5`, `allow_full_source_list: false`) unable to run any capped
live fetch.

Resolution:

- Changed the guard to block only full-population runs unless
  `allow_full_source_list` is true.
- Updated tests to assert capped runs are allowed and full-list runs fail
  closed.
- Verified the tracked config now runs as a 5-page live direct-source crawl.

## Verification

- Focused suite: `59 passed`
- Ruff check: pass
- Ruff format check: pass
- `git diff --check`: pass
- `scripts/legal/legal-sanity-scan.sh`: pass
- Live direct-source run with tracked config:
  - WELLS rows: 124,332
  - FacilityDetail request rows: 5
  - fetched pages: 5
  - parsed Initial Test Data rows: 49
  - usable candidate pressure rows: 11
  - screen-promotable rows: 0
  - promotion: `candidate_only`
