# Plan Review r4: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Source/Provenance

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Reviewer:** Codex subagent Euclid
**Verdict:** MAJOR

## Findings

1. **MAJOR - Audit provenance could still be bypassed through a public mutable
   map.**

   The plan exposed `CoresOilConversionAudit.factors_by_field:
   dict[str, CoresCrudeDensityFactor]` in a public frozen dataclass. A frozen
   dataclass does not freeze a nested `dict`, and the public constructor
   remained available. That left a public audit-boundary bypass: mutate or
   directly construct `factors_by_field` with a raw/unaccepted value and let the
   parser key off that map.

2. **MINOR - The risk section reintroduced ambiguous source hierarchy language.**

   The validation section made `industry_technical_article` and
   `secondary_article` evidence-only, but the risk mitigation still mentioned
   “industry annual survey” after technical literature without mapping it to an
   allowed conversion-eligible class.

## r3 Source Finding Status

- Present sidecars with `missing_fields` were fixed.
- Secondary/industry source-class rules were mostly fixed but needed risk text
  cleanup.
- Ayoluengo range/discovery evidence and all-or-blocked closeout were fixed.
- The raw-float/public audit bypass remained unresolved before this patch.

## Patch Response

- `CoresOilConversionAudit` now stores immutable private tuples
  `_accepted_entries` and `_defaulted_field_keys` instead of a public conversion
  map.
- `CoresOilConversionAudit.__post_init__` now validates direct construction
  attempts as well as builder-created audits.
- The parser now uses only `bbl_per_tonne_for_field(...)` and does not inspect a
  public conversion map.
- The audit-bypass test now covers unaccepted factors, missing `bbl_per_tonne`,
  duplicate keys, and default keys not represented in `defaulted_fields`.
- The “industry annual survey” risk wording was replaced with an evidence-only
  source-lead rule unless backed by a conversion-eligible source.
