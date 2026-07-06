# Plan Review r3: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Source/Provenance

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Reviewer:** Codex subagent Feynman
**Verdict:** MAJOR

## Findings

1. **MAJOR - Provenance could still be bypassed through
   `CoresOilConversionAudit.factors_by_field`.**

   The public `density_by_field` API was removed, but the proposed audit
   dataclass still exposed `factors_by_field: dict[str, float]`. The parser
   used that float map directly, and a planned parser test constructed an audit
   whose float map contained `{"ayoluengo": 6.95}`. The plan needed an explicit
   invariant/test that every field conversion entry is derived from an accepted
   `CoresCrudeDensityFactor` in `used_factors`.

2. **MAJOR - Report handling did not explicitly surface `missing_fields` when a
   sidecar exists.**

   The sidecar schema supported `coverage_status: "missing"` and
   `missing_fields`, but report limitations only enumerated all-cited,
   defaulted, or no-sidecar states. The plan needed a visible
   `oil_tonnes_to_bbl_has_missing_fields` limitation and a test for a
   present-but-missing sidecar.

3. **MINOR - Secondary-source acceptance remained slightly ambiguous.**

   The prose restricted conversion-driving factors to regulator/operator/
   filing/assay/technical literature, but still left a possible secondary-source
   loophole. The registry needed explicit allowed `source_class` values and a
   rule that secondary/industry articles are evidence-only unless replaced by an
   underlying conversion-eligible source.

## r2 Source Finding Status

- Ayoluengo evidence handling was fixed before r3.
- Public `density_by_field` was removed before r3, but the audit wrapper still
  needed a provenance invariant.

## Patch Response

- `CoresOilConversionAudit.factors_by_field` now maps to
  `CoresCrudeDensityFactor` objects instead of raw floats.
- The plan now requires `CoresOilConversionAudit` to be built only by
  `build_oil_conversion_audit(...)`, with every conversion factor backed by an
  accepted cited factor or an explicit defaulted-field entry.
- The parser now uses `oil_conversion_audit.bbl_per_tonne_for_field(...)`
  instead of reading a float map directly.
- The TDD list now includes a test rejecting unbacked audit conversion entries.
- Report states now include `oil_tonnes_to_bbl_has_missing_fields`, with a
  present-sidecar missing-fields test.
- Source-class validation now enumerates allowed source classes and makes
  `industry_technical_article` and `secondary_article` evidence-only.
