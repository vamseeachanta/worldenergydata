# Plan Review r6: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Source/Provenance

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Reviewer:** Codex subagent Avicenna
**Verdict:** MINOR

## Findings

1. **MINOR - TDD list did not explicitly cover direct
   `CoresCrudeDensityFactor(...)` rejection for non-representative ranged
   factors.**

   The plan tested direct factor construction rejection for accepted
   `secondary_article` factors, and it tested non-representative ranged factors
   through registry loading and direct audit construction. It did not explicitly
   say that direct `CoresCrudeDensityFactor(...)` construction itself rejects an
   accepted ranged/non-representative factor.

## r5 Source Finding Status

- Fixed for the plan design. Direct factor construction now routes through
  `validate_crude_density_factor(...)`, and direct audit construction revalidates
  every used/accepted factor.
- Previous safe properties remain intact: no public mutable conversion map,
  secondary/industry sources evidence-only, Ayoluengo range evidence-only,
  missing-fields sidecar/report visibility, and all-or-blocked closeout.

## Patch Response

- Test 7 now explicitly repeats direct `CoresCrudeDensityFactor(...)`
  construction with accepted non-representative
  `api_gravity_min_deg`/`api_gravity_max_deg` range evidence and no
  representative `api_gravity_deg`/`bbl_per_tonne`.
