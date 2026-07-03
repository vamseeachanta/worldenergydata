# Codex Inline Plan Review - Issue #732

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/732
**Plan:** `docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md`
**Reviewer:** Codex inline adversarial review
**Date:** 2026-07-03
**Verdict:** APPROVE WITH REQUIRED CONSTRAINTS

## Findings

1. **MAJOR - The plan must not require Texas West Panhandle/Hugoton analog recovery from the current Texas #709 packet.**

   The current direct-source Texas output contains 48 curated rows, 25 API14
   wells, and 8 fields, dominated by Eagle Ford examples. Requiring West
   Panhandle analog recovery from this specific daily packet would create a
   false blocking gate unrelated to the quality of the integration. The plan
   addresses this by preserving the Kansas Hugoton/Panoma severe-underpressure
   validation gate and adding only a Texas participation gate.

2. **MAJOR - The screen must not concatenate Texas #709 rows without an explicit schema adapter.**

   The current screen expects `well_key`, `field`, and `state`; Texas #709 emits
   `api14`, `field_name`, and no physical `state` column. Blind concatenation
   would either fail or produce misleading field groups. The plan addresses
   this with `texas_rrc_pressure_v1` normalization at the analysis boundary.

3. **MAJOR - Texas WHP observations must not be silently treated as measured virgin BHP.**

   Texas #709 rows are all `WHP_shut_in`, and #709 quality marks gradients as
   surface-pressure-over-depth screening only. The plan requires
   `require_usable_proxy=True`, preserves screening caveats, and avoids a
   measured-BHP claim in docs and summary output.

4. **MINOR - #709 source warnings can disappear unless the screen reads quality sidecars.**

   The Texas quality sidecar currently includes
   `raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z`. The plan
   adds optional `quality_path` config and requires warnings to flow into
   `screen_summary.json`.

5. **MINOR - Plan-time exact output counts must not become hardcoded tests.**

   The plan uses current counts as resource intelligence but requires tests on
   structure and participation, not fixed live counts. Live `/mnt/ace` counts
   may change if direct-source snapshots are refreshed.

## Required Constraints For Implementation

- Keep the existing Kansas Hugoton/Panoma validation gate load-bearing.
- Add a Texas participation gate that proves Texas rows are loaded and screened
  without requiring any specific Texas field tier.
- Normalize source-specific schemas before BHP estimation or field ranking.
- Propagate #709 quality warnings into the screen summary.
- Keep generated `/mnt/ace` outputs out of git.

## Review Result

The plan is approved for `status:plan-review`. Implementation remains blocked
until explicit user approval moves issue #732 to `status:plan-approved`.
