# Intervention HSE aggregate assessment

## Summary

The Phase 1B assessment extends the conservative operator/lease/day join with
source-filtered, pooled descriptive candidates for activity mix (p5), calendar
season (p6), and vendor type (p8). Rig-age correlation (p7) is explicitly
`NOT_EVALUATED`. Every inferential pattern remains `NOT_EVALUATED`; the output
provides no p-value, effect size, rate comparison or operational recommendation.

Data as of: 2026-10-22 for the synthetic example only. No incident database was
opened or refreshed, so there are no source database modification times for this
assessment. The historical [Phase 0 inventory](../../../reports/hse/intervention-hse-patterns-2026-05-18.md)
is evidence of unresolved qualification gaps, not a current coverage audit.

> Data sources for the intended analysis: BSEE WAR, BSEE INCs and BSEE
> Accidents/Investigations. The historical audit identified incomplete offshore
> incident workbooks; longitudinal claims require an independently qualified
> full-coverage window. All operator-level candidates are pooled aggregates; no
> individual operator is named. This is engineering-analysis interpretation,
> not a regulatory finding. The synthetic example is not evidence of an HSE
> association, an incident rate or actual hurricane exposure.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-22 | Added conservative assessments and a synthetic example to expose evidence gaps before pattern claims. |
| 2 | 2026-10-24 | Preserved sparse-cell suppression alongside missing classifications to prevent reconstruction through overlapping tables. |

## Scope and method

Refs #419 and #416. The implementation is in
`packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/hse_patterns.py`.
The three implementation slices are:

1. Reuse `hse_join` normalization and inclusive window matching; reject duplicate
   incident IDs and exclude records without explicit BSEE operational-incident
   qualification. Preserve source row indices for internal auditing.
2. Compute descriptive p5, p6 and p8 candidates, apply the minimum-cell contract,
   and return explicit inference prerequisites for all four patterns, including
   p7. No statistical test or acceptance threshold is guessed.
3. Provide the runnable example, independent expected counts, input contract and
   public-review projection. Live pattern mining remains a later slice.

For category `b`, the descriptive count is
`n(b) = sum(1 for each uniquely matched incident assigned to b)`.
This is the count definition in the [issue-416 Metric Contract](../../plans/2026-05-18-issue-416-intervention-hse-patterns.md#metric-contract)
(2026-05-18); it is not a rate. The intervention window is closed at both ends,
and identity normalization changes only case and whitespace. Prefixes,
punctuation and leading zeros remain significant. Invalid keys and ambiguous
windows are retained in diagnostics and excluded from candidate tables.
Unmatched records do not establish a non-intervention comparison cohort.

| Pattern | Descriptive candidate | Evidence still required |
| --- | --- | --- |
| p5 | PERS, PSAFE, CRANE counts for uniquely matched incidents | Validated classifier/subcategory confidence, coverage and an independently defined comparison design |
| p6 | Hurricane versus non-hurricane calendar counts | Qualified intervention-day exposure by season, coverage and a statistical design accounting for repeated observations |
| p7 | No table or statistic | Rig identity, age at incident time, rig-specific incident rates and exposure; confounding and correlation design |
| p8 | Counts pooled across operators by approved vendor type | Qualified vendor-type mapping, exposure by type, coverage and an independently defined comparison design |

The PERS/PSAFE/CRANE labels follow the issue's requested cuts and the existing
[WRK-013 taxonomy analysis](../../../reports/hse/wrk013_hse_mishap_analysis.md).
Unrecognized or missing classifications withhold all of p5 rather than silently
redefining its cohort. This helper does not run the classifier or assert its
historical confidence applies to the supplied records.

Atlantic season boundaries are June 1 through November 30, inclusive, from
[NHC Tropical Cyclone Climatology, Atlantic Hurricane Season](https://www.nhc.noaa.gov/climo/),
accessed 2026-10-22. Dates outside that interval belong to `non_hurricane`.
Calendar season alone does not measure cyclone conditions at an incident site.

## Normalized adapter input contract

The helper accepts iterables of mappings; it does not infer raw database schemas.
A qualified adapter must supply:

| Input | Required fields and meaning |
| --- | --- |
| Incident | `incident_id`: unique, nonempty, source-qualified text; `source`: exactly `BSEE`; `record_kind`: exactly `incident` |
| Incident join | `operator`, `lease_number`: textual identities; `incident_date`: explicit calendar date or ISO calendar-day string |
| Incident classification | `activity_code`: exactly `PERS`, `PSAFE` or `CRANE` for a complete p5 table |
| Intervention window | `BUS_ASC_NAME`, `BOTM_LEASE_NUM`, `WAR_START_DT`, `WAR_END_DT`: the join module's normalized window fields; windows must already be classified as intervention activity |
| Vendor mapping | `vendor_type`: `wireline`, `coil_tubing`, `lift_boat`, `snubbing`, `workover_rig`, `support_vessel` or `pumping` |

Vendor types derive from the issue-416 Metric Contract service-type row. They
are an allowlist; free text and vendor names are never copied into labels.
Every matched incident needs a qualified vendor type for a p8 table. Only
observed types are candidate cells; no vendor population or absent-type rate
is inferred. All incidents in a batch require stable IDs, including excluded
sources; repeated IDs after whitespace trimming reject the batch. ID case remains
significant. The caller must deduplicate cross-source aliases before this boundary.

`source` and `record_kind` are qualification inputs supplied by the adapter,
not proof of provenance. INC notices, other agencies and unqualified source
labels are excluded. A row's presence in the mixed-source HSE database is
insufficient to mark it as a BSEE operational incident. Locale-formatted dates,
timestamps and numeric identity values must be resolved against source evidence
before calling this helper; they are not coerced here.

## Disclosure and statistical controls

The minimum reported cell size is five incidents, from the issue-416 Operator
Aggregation Contract rule 2 (2026-05-18), strengthened to every operator-aggregate
cell by #419. A cell below the floor, including zero in the fixed p5 or p6 table,
withholds its entire table. No margins are emitted. If any candidate table is
sparse, `public_summary()` withholds every table in that release, reducing
reconstruction through overlapping cuts. Known cells are checked for sparsity
even when classifications are incomplete; both reasons are retained, and all
public tables remain withheld. Counts pool all operators; the helper never
creates per-operator buckets.

`PatternDiagnostics` contains internal source indices and unsuppressed coverage
counts. It must not be serialized as a public artifact. Use `public_summary()`
for aggregate review candidates; its status remains `REVIEW_REQUIRED`. The
projection includes only fixed labels, counts that pass the cell floor, fixed
reason codes and null statistical fields. It is not publication clearance:
external releases and combinations of releases require a separate disclosure
review and the operator deny-list scanner specified in #420.

Every result explicitly carries `statistical_sanity_not_evaluated`,
`coverage_and_source_validation_required` and
`publication_policy_review_required`. No significance cutoff, rate multiplier,
rig-age cutoff or confidence coefficient is embedded. Without qualified
exposures and statistical sanity, no pattern meets the issue-416 Metric Contract
for an inferential claim. No engineering-control recommendation is justified
by these synthetic descriptive candidates.

## Worked example: inputs, method and answer

The executable fixture is [intervention_hse_patterns.py](../../../examples/bsee/intervention_hse_patterns.py).
Run from the repository root with its package source roots available:

```bash
PYTHONPATH=src:packages/worldenergydata-bsee/src python examples/bsee/intervention_hse_patterns.py
```

Inputs are synthetic: one full-calendar-year intervention window, one approved
vendor type (`wireline`), and five distinct incidents for each of three activity
codes on each of two dates: January 1 and June 1. Identities are fictitious join
tokens; none appear in the returned public-review projection.

The independent hand calculation is:

- Each activity has `5 + 5 = 10` incidents.
- Each season has `3 * 5 = 15` incidents.
- The vendor type has `3 * 2 * 5 = 30` incidents.
- Every incident has exactly one matching window, so none is duplicated.

| Output | Answer |
| --- | --- |
| p5 | PERS: 10; PSAFE: 10; CRANE: 10 |
| p6 | hurricane: 15; non_hurricane: 15 |
| p7 | No cells; `rig_age_and_rig_exposure_required` |
| p8 | wireline: 30 |
| All inferential pattern statuses | `NOT_EVALUATED` |
| Publication status | `REVIEW_REQUIRED` |

These fixture counts exceed the disclosure floor. Replacing one activity count
with fewer than five withholds the whole p5 table; the public-review projection
then withholds all overlapping tables. The tests independently enumerate this
case, the inclusive floor, season endpoints, invalid dates/keys, ambiguity,
source exclusions, duplicate IDs, unknown labels and audit index preservation.

## Known limits and later slices

The Phase 1A pattern memo remains deferred in the committed Phase 0 findings.
The #420 operator policy/scanner is absent from this base. The current change
therefore completes conservative assessment tooling and its example, not the
full live-data acceptance criteria of #419 or the Phase 2 extraction in #418.
No live-data matched-ID sidecar, full-coverage claim or statistical significance
is supplied. Historical audit counts are not represented as current measurements.

Later slices require source-qualified DB/WAR adapters and evidenced aliases,
current coverage and modification-time auditing, classifier validation, exposure
accounting, rig-age/vendor linkage, statistical tests with effect sizes and
multiplicity treatment, and policy-scanned publication artifacts. Raw identifiers
and matched source records must remain internal. Each step must be tested before
any `NOT_EVALUATED` status is replaced with a pattern claim.
