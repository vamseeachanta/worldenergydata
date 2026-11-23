# Plan Review r5: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Source/Provenance

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Reviewer:** Codex subagent Curie
**Verdict:** MAJOR

## Findings

1. **MAJOR - Direct `CoresOilConversionAudit(...)` construction could still
   bypass source/provenance validation.**

   The plan moved source-class, citation, API math, and representative-basis
   checks into the registry loader, while `CoresCrudeDensityFactor` remained a
   plain frozen dataclass and `CoresOilConversionAudit.__post_init__` only
   checked accepted membership, non-null `bbl_per_tonne`, duplicate keys, and
   default-key consistency. A caller could manually construct an
   `accepted_for_conversion=True` factor with `source_class="secondary_article"`
   or an arbitrary `bbl_per_tonne`, then pass it through `_accepted_entries`.

## r4 Source Finding Status

- Public mutable conversion map was fixed.
- Source-class/risk wording was fixed.
- Present sidecars with `missing_fields` were fixed.
- Ayoluengo evidence-only handling was fixed.
- All-or-blocked closeout was fixed.
- Raw-float injection was not fully fixed because direct audit construction
  could still carry unvalidated accepted factors.

## Patch Response

- `CoresCrudeDensityFactor.__post_init__` now calls shared
  `validate_crude_density_factor(...)`.
- The registry loader now uses the same validation helper as direct dataclass
  construction.
- `CoresOilConversionAudit.__post_init__` now revalidates every factor in
  `used_factors` and `_accepted_entries`.
- The TDD list now includes direct construction rejection for
  `source_class="secondary_article"` with `accepted_for_conversion=True`, and
  audit rejection for accepted secondary-source/non-representative ranged
  factors.
