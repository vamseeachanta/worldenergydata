# Plan Review Synthesis: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) - r1

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Round:** r1
**Consensus Verdict:** MAJOR

## Consensus

Both parallel reviewers found the original draft directionally sound but not
approvable. The common defect class was that the plan allowed partial/defaulted
conversion to look operationally complete, while [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
asks for real per-field cited conversion factors.

## Required Patches Applied

- Defined [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
  closeout as all-or-blocked: every current CORES oil field needs
  an accepted cited factor, or the issue remains open with named source gaps.
- Added hard source acceptance rules and `accepted_for_conversion`.
- Rejected ranged/non-representative evidence as conversion-factor input.
- Replaced implicit fallback with explicit `allow_default_density=True`.
- Added a conversion audit helper so parser factor resolution and sidecar
  provenance share normalization and lookup behavior.
- Added exact sidecar schema and report validation rules.
- Added scheduler config propagation and non-retryable deterministic density
  failure handling.
- Added adapter fallback scope so stale 7.33-based embedded Ayoluengo values do
  not survive.
- Expanded tests for source validation, accents/punctuation, malformed sidecars,
  scheduler propagation, adapter fallback, and HTML provenance invariants.

## Next Gate

Run r2 adversarial review against the patched plan. Do not move to
`status:plan-review` or request implementation approval while unresolved MAJOR
findings remain.
