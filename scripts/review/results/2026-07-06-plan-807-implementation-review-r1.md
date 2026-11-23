# Plan Review: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Implementation/Downstream - r1

**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Reviewer:** parallel Codex explorer
**Verdict:** MAJOR

## Findings

1. **MAJOR - Scheduler/live loader behavior was not planned end-to-end.**

   The draft added live-loader density options but the scheduler job currently
   constructs `CoresLiveProductionLoader(cache_root=output_dir)` only. No
   scheduler config keys or scheduler tests were planned. Strict density gaps
   could also be treated as retryable generic failures. Required change: plan
   scheduler config propagation, sidecar creation under scheduler run, fixture
   refresh provenance, and non-retryable deterministic density failures.

2. **MAJOR - Density sidecar/report contract was underspecified and conflicted with existing cache metadata.**

   The draft proposed `normalized/cores_oil_density_factors.json` without an
   exact schema. `_metadata.json` still declares `format: csv`, while its file
   list could include JSON sidecars. Report loading did not define absent or
   malformed sidecar handling. Required change: define sidecar schema and
   validation, update metadata semantics, add `CoresReportSource` support, and
   test absent, malformed, all-cited, and defaulted cases.

3. **MAJOR - Parser API did not define how conversion provenance is produced.**

   The parser would still return only a DataFrame, while the live sidecar needs
   used/defaulted/missing field metadata generated with the same normalization
   and lookup logic. Tests also missed accented/punctuated names such as
   `Boquerón` and `Viura (1)`. Required change: define and test a shared
   field-normalization helper and conversion audit object/helper.

4. **MAJOR - Adapter/FDAS fallback divergence was not addressed.**

   The production adapter has hardcoded embedded Ayoluengo oil values for
   production-only installs. If committed fixture values change but fallback does
   not, downstream users get stale 7.33-based barrels. Required change: update
   or explicitly deprecate the embedded fallback and add default
   adapter/fallback tests after density conversion changes.

5. **MINOR - TDD list needed more exact negative coverage.**

   Required tests include default package registry loading, invalid/out-of-range
   API and bbl/tonne values, unsupported source class/confidence, accent and
   punctuation alias normalization, malformed report sidecar, and preservation of
   no-`/mnt/ace` HTML output.

## Patch Response

The plan was patched to add scheduler config/job/test scope, exact sidecar
schema, parser conversion audit design, adapter fallback scope, report sidecar
validation tests, accent/punctuation tests, malformed sidecar tests, and
metadata sidecar categorization.
