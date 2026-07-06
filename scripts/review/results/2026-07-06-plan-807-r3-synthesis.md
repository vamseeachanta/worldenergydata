# Plan Review r3 Synthesis: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Round:** r3
**Result before patch:** MAJOR
**Result after patch:** Ready for focused r4 review

## Blocking Findings

- Source/provenance review found the audit wrapper still exposed raw conversion
  floats without a provenance invariant.
- Source/provenance review found the report did not explicitly surface
  present-sidecar missing fields.
- Source/provenance review found source-class rules left a secondary-source
  loophole.
- Implementation/downstream review found the scheduler config file was in scope
  but the real config-loading test was omitted from targeted pytest gates.

## Applied Changes

- Replaced audit float maps with backed `CoresCrudeDensityFactor` entries and a
  `bbl_per_tonne_for_field(...)` accessor.
- Added audit validation and TDD coverage for unbacked conversion entries.
- Added missing-fields report limitation and TDD coverage.
- Enumerated source classes and made secondary/industry articles evidence-only.
- Added scheduler config test coverage and included it in targeted pytest.

## Next Review Focus

r4 should verify that:

- conversion factors cannot be injected as raw floats at public parser or audit
  boundaries;
- source classes cannot promote secondary/industry articles into conversion
  factors;
- present sidecars with missing fields are visible in report limitations; and
- targeted tests/gates cover scheduler config as well as scheduler job wiring.
