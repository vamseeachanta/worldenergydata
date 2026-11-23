# Plan Review: Issue #745 - Colorado ECMC wellhead pressures

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/745
**Plan:** `docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md`
**Mode:** Codex inline adversarial review
**Date:** 2026-07-03

## Review Stance

Default posture was non-approve: assume the plan could over-claim Colorado
coverage, contaminate the gas screen with water pressure, mis-handle tubing or
casing pressures as measured BHP, or compute gradients from ambiguous joins.

## Findings

No blocking findings remain.

## Checks Performed

- Direct-source URLs are official ECMC URLs and were live-probed before plan
  drafting.
- The plan scopes v1 to 2025 annual production plus rolling monthly production
  while preserving a configurable annual-years path, so it does not falsely
  promise full 1999-present historical coverage in the first implementation.
- The wells shapefile schema was inspected from the official ZIP and contains
  `Field_Name`, `Max_TVD`, `Max_MD`, `Facil_Id`, and API fields needed for the
  v1 screen join.
- The plan excludes water-pressure fields from curated gas-screen observations
  and keeps them in normalized/quality accounting only.
- The plan keeps all Colorado production-report pressure values as
  wellhead/casing/tubing screening observations, not measured BHP.
- The plan requires unique well/depth joins and positive reference depth before
  computing screen-ready gradients.
- TDD, live `/mnt/ace` refresh, screen integration, docs, legal scan, and
  CI-equivalent formatting checks are included before PR closeout.

## Residual Risks

- ECMC production backfill volume is large; v1 intentionally proves one annual
  file plus rolling monthly first.
- `GasPressureCasing` is operationally useful but less interpretable than
  tubing pressure; implementation must preserve `pressure_kind` and avoid
  near-vacuum claims for casing/tubing pressures.
- Field names come from the current wells shapefile and may not perfectly match
  historical producing formation codes; docs must frame Colorado field ranking
  as a late-life screen, not a definitive field-development architecture model.

## Verdict

APPROVE FOR USER REVIEW. Do not implement until the user explicitly approves
the issue plan and the issue is labeled `status:plan-approved`.
