# Plan Review: Issue #669 - Texas RRC GoDrive directory refresh

**Plan:** `docs/plans/2026-06-30-issue-669-texas-rrc-godrive-directory-refresh.md`
**Reviewer:** Codex inline adversarial review
**Date:** 2026-06-30
**Verdict:** MINOR - ready for user approval after preserving listed constraints

## Findings

### 1. Pagination must be specified, not discovered during implementation

The riskiest part of the plan is the JSF/PrimeFaces directory pagination
contract. A vague "scrape all pages" instruction would likely produce a brittle
implementation or one that silently refreshes only the first 250 rows.

Resolution in plan: the plan includes the verified POST fields for
`fileTable` pagination and requires transport tests to assert the payload.

### 2. Directory downloads cannot reuse the single-file first-page parser

The existing `download_godrive_file_to()` opens the landing page and finds one
named file on that page. It will fail for files that are only visible on later
directory pages. A directory implementation that only reuses that function
would pass for some GIS files and fail for completion/date-window selections.

Resolution in plan: the plan requires a separate
`download_godrive_directory_file_to()` path that navigates to `entry.page_first`
before posting the entry command id.

### 3. Partial success must not look like a valid snapshot

For GIS datasets, a complete snapshot requires many files. Writing each file
directly into the final raw directory would make a failed batch
indistinguishable from a valid partial snapshot unless every consumer inspects
the manifest.

Resolution in plan: the plan requires batch staging and only promotes files
after every selected file succeeds. Failed batches remove staging and write an
error manifest.

### 4. Completion and directional defaults must avoid accidental bulk downloads

The observed official listings contain 1965 completion files and 2128
directional survey files. Defaulting those sources to "all files" would create
large, slow, and probably unintended refreshes.

Resolution in plan: the plan defaults completion and directional survey sources
to latest filename-date selection and requires explicit date-window options for
broader refreshes.

## Residual Risks

- The RRC GoDrive UI can change its JSF field names. The plan mitigates this
  with focused parser/payload tests and a live dry-run smoke, but future source
  drift can still require a transport patch.
- `wellFED.zip` does not fit the numeric county-code pattern. The plan keeps
  GIS selection prefix-based instead of numeric-only to avoid dropping it.
- Live no-download smoke tests depend on external RRC availability and should
  remain outside required unit tests.

## Required Constraints For Implementation

- Do not use PatchOps, EWA, GitHub scrapers, or copied third-party code as raw
  refresh sources.
- Do not put raw refresh output under the git worktree.
- Do not mark the issue approved from this review; user approval is still
  required before implementation.
