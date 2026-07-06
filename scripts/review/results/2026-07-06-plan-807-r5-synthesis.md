# Plan Review r5 Synthesis: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Round:** r5
**Result before patch:** Source MAJOR, Implementation APPROVE
**Result after patch:** Ready for focused r6 source review

## Blocking Finding

- Source/provenance review found direct factor/audit construction could still
  bypass registry-loader validation.

## Applied Changes

- Added shared `validate_crude_density_factor(...)`.
- Added `CoresCrudeDensityFactor.__post_init__` validation.
- Added `CoresOilConversionAudit.__post_init__` revalidation of all used and
  accepted factors.
- Added direct-construction TDD coverage for accepted invalid secondary-source
  and non-representative ranged factors.

## Next Review Focus

r6 should verify only whether direct construction can still bypass source,
citation, representative-basis, range, or API-math validation.
