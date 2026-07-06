# Plan Review r4 Synthesis: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Round:** r4
**Result before patch:** MAJOR
**Result after patch:** Ready for focused r5 review

## Blocking Findings

- Source/provenance review found the audit still exposed a mutable public
  conversion map.
- Source/provenance review found ambiguous source hierarchy wording in the risk
  section.
- Implementation/downstream review found repo-relative `density_registry_path`
  resolution was not specified.
- Implementation/downstream review found retry classification used an
  underspecified fake density error rather than the real live-loader gap
  exception.
- Implementation/downstream review found the embedded adapter fallback path was
  not directly tested.
- Implementation/downstream review found the scheduler YAML config lacked YAML
  validation gates.

## Applied Changes

- Replaced public conversion maps with immutable private audit entries and
  construction-time validation.
- Removed the ambiguous “industry annual survey” source hierarchy language.
- Added repo-root resolution for `density_registry_path`.
- Added exported `CoresDensityCoverageError` and real-exception scheduler
  classification tests.
- Added embedded fallback path coverage/removal test.
- Added `check-yaml` and `yamllint` gates for scheduler config.

## Next Review Focus

r5 should verify that:

- no mutable public conversion map or direct raw-float path remains;
- source-class and risk wording agree;
- scheduler config path resolution is explicit and tested;
- strict density coverage uses the real exported exception in live loader and
  scheduler retry classification; and
- embedded adapter fallback and YAML config validation are covered.
