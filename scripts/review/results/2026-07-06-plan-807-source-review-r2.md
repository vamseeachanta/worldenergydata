# Plan Review r2: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Source/Provenance

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Reviewer:** Codex subagent Pasteur
**Verdict:** MAJOR

## Findings

1. **MAJOR - Provenance was still stripped at the parser/loader boundary.**

   The plan introduced `CoresOilConversionAudit`, but the parser API still
   accepted raw `density_by_field: Mapping[str, float]` and returned only a
   `DataFrame`. The TDD list also passed ad hoc floats directly. That did not
   satisfy the r1 requirement that the live/default path consume validated
   factor objects or keep conversion metadata at the parser boundary.

   Required patch: make the parser/loader consume an audit/factor object or
   return `DataFrame + audit`, with raw float mappings restricted to an internal
   artifact derived from validated factors.

2. **MAJOR - Rejected Ayoluengo evidence remained as the concrete accepted
   registry example.**

   The plan correctly stated that Ayoluengo's 20-39 API range and
   discovery-test value must not become a conversion factor without a
   representative basis. However, the deliverable example still used Ayoluengo,
   `api_gravity_deg: 36.0`, AAPG as the source title, and the discovery-well
   note as though it were a conversion factor.

   Required patch: replace the example with either a neutral placeholder or an
   `accepted_for_conversion: false` evidence-only example.

## Passed Checks

- The all-or-blocked closeout rule was explicit: every current oil field needs
  an accepted cited factor or issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)
  stays open.
- The live cache coverage set was empirically verified as 12 oil fields.
- The secondary-source policy was materially tighter than r1.
- Report caveat removal was gated on complete sidecar coverage with no
  defaulted or missing fields.

## Patch Response

- The plan now requires `parse_cores_frame(..., oil_conversion_audit=...)` and
  `CoresProductionLoader(..., oil_conversion_audit=...)`; raw float mappings are
  excluded from the public parser/live-loader boundary.
- The Ayoluengo example is now explicitly evidence-only with
  `accepted_for_conversion: false`, `api_gravity_min_deg`, `api_gravity_max_deg`,
  and `bbl_per_tonne: null`.
- The TDD list now builds and passes `CoresOilConversionAudit` objects instead
  of ad hoc public `density_by_field` floats.
