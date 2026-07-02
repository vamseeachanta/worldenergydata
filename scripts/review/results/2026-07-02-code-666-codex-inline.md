# Code Review: Issue #666 - Texas RRC onshore field atlas reports

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/666
**Review stage:** code/artifact
**Reviewer:** Codex inline
**Date:** 2026-07-02
**Verdict:** APPROVE after fixes

## Scope Reviewed

- `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/`
- `src/worldenergydata/cli/commands/texas_rrc.py`
- `tests/unit/texas_rrc/test_field_atlas_report_*.py`
- `docs/data-sources/onshore/texas-rrc/field-atlas-reports.md`
- Published artifacts under `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/`

## Findings

### Fixed: Directory promotion could delete existing reports before replacement

The first implementation removed the target report directory before replacing it
with the staging directory. If the final rename failed after removal, the
previous published report set would have been lost. The writer now renames the
existing target to a timestamped backup, promotes staging, removes the backup
only after successful promotion, and restores the backup on failure when
possible.

Regression coverage:
`tests/unit/texas_rrc/test_field_atlas_report_io.py::test_rewrite_removes_stale_field_pages`

### Fixed: Index metric counted `not_available` as infrastructure coverage

The first index metric counted every row with an
`infrastructure_access_class`, including the fallback `not_available` class.
The renderer now counts only fields with an actual infrastructure access row,
which matches the published value of 61,518 out of 67,082 fields.

Regression coverage:
`tests/unit/texas_rrc/test_field_atlas_report_html.py::test_index_counts_only_fields_with_infrastructure_rows`

## Residual Risks

- The full report publication writes 67,082 HTML files. This is accepted by the
  issue scope, but operators should expect a non-trivial file count under
  `/mnt/ace`.
- Some source rows lack district values; those reports use `unknown` in the
  page filename while preserving the source field number and caveat trail.

## Verification Evidence

- Red test evidence: focused tests initially failed with
  `ModuleNotFoundError: No module named 'worldenergydata.texas_rrc.reports'`.
- Focused #666 tests: `14 passed`.
- Texas RRC unit suite: `505 passed in 166.96s`.
- Dry run against `/mnt/ace`: 67,082 summary rows, 67,082 field pages, no source
  gaps.
- Full publish: 67,082 field HTML pages; manifest row/page count 67,082; no
  source gaps.
- Parquet summary read through project environment: 67,082 rows.
- HTML self-containment sample: no `http://`, `https://`, or `<script src=`.
- Black check: pass.
- isort check: pass.
- `git diff --check`: pass.
- Workspace-hub legal diff scan:
  `bash scripts/legal/legal-sanity-scan.sh --repo=../wt-wed-669 --diff-only`
  passed.
