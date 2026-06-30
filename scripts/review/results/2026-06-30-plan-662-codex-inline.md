# Plan Review: Issue #662 - Texas RRC well lifecycle spine

**Plan:** `docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md`
**Reviewer:** Codex inline adversarial review
**Date:** 2026-06-30
**Verdict:** MINOR - ready for user approval after preserving listed constraints

## Findings

### 1. Raw source parsing can become an accidental rewrite of the entire RRC schema

The issue needs a lifecycle spine, not a complete Texas RRC source warehouse.
The highest risk is over-expanding into every field in the official manuals and
stalling implementation before a useful API14 table exists.

Resolution in plan: the plan limits the first contract to the lifecycle columns
needed by downstream field development and preserves source-specific originals
only where traceability needs them.

### 2. API14 must be the only join key exposed downstream

Texas RRC sources can expose API10, API12, API14, permit numbers, lease IDs, and
field IDs. Joining on lease or permit first would duplicate wells and make later
production attribution unreliable.

Resolution in plan: Task 1 creates a canonical lifecycle key module, and Task 4
requires an outer join centered on `api14`.

### 3. Partial-source gaps must remain rows, not silent drops

Official raw snapshots will not always contain matching wellbore, permit, and
completion records for every API. Inner joins would hide exactly the lifecycle
coverage gaps that downstream analysis needs to understand.

Resolution in plan: Task 4 requires outer joins and source-presence flags, and
Task 5 requires explicit partial-source gap counts.

### 4. `/mnt/ace` writes need the same atomicity discipline as raw refresh

Curated outputs will become downstream inputs for production and field atlas
work. A failed write that leaves only the CSV or only the quality JSON would be
hard to diagnose later.

Resolution in plan: Task 6 requires staged writes and promotion only after CSV,
quality JSON, and manifest JSON are complete.

## Residual Risks

- Official Texas RRC ASCII formats may require a fixed-width parser after live
  raw artifacts are inspected. The plan mitigates this by centralizing alias
  and reader behavior in `lifecycle/sources.py`, but implementation may still
  need one source-specific parser for `drilling_permits`.
- Directional survey and imaged completion PDFs will remain source gaps until a
  separate document-extraction issue handles them.
- A local `/mnt/ace` Texas RRC payload may not exist in every development
  environment. Unit tests therefore must use fixtures and CLI dry-run against
  live `/mnt/ace` should remain an optional smoke.

## Required Constraints For Implementation

- Do not use PatchOps, EWA, LinkedIn content, GitHub scrapers, or copied
  third-party code as source-of-record inputs.
- Do not require production data for #662.
- Do not put raw, normalized, or curated Texas RRC data under the git worktree.
- Do not mark the issue approved from this review; user approval is still
  required before implementation.
