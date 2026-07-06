# Plan Review r2 Synthesis: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Round:** r2
**Result before patch:** MAJOR
**Result after patch:** Ready for focused r3 review

## Blocking Findings

- Source/provenance review found that raw float mappings at the parser boundary
  still stripped citation provenance.
- Source/provenance review found that the plan still showed rejected Ayoluengo
  discovery/range evidence as the concrete accepted registry example.
- Implementation/downstream review found scheduler test paths and format gates
  did not cover all planned touched surfaces.
- Implementation/downstream review found a sidecar schema/prose mismatch for
  registry version/date.

## Applied Changes

- Replaced the public `density_by_field` parser/live-loader plan with
  `CoresOilConversionAudit`.
- Converted the Ayoluengo example into non-converting evidence with
  `accepted_for_conversion: false`.
- Corrected scheduler test paths to `tests/unit/scheduler/test_spain_cores_refresh.py`.
- Expanded targeted formatting gates to include Spain, scheduler, production
  adapter, and corresponding test paths.
- Added `registry_version` and `registry_date` to the exact sidecar schema.

## Next Review Focus

r3 should verify that:

- no public parser/live-loader contract still accepts raw conversion floats;
- Ayoluengo discovery/range evidence is never accepted for conversion;
- scheduler tests and format gates match repository layout; and
- sidecar schema/prose are internally consistent.
