# Plan for #1038: bidirectional asset-to-project cost-map program

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1038
> **Lane:** Claude orchestration; Codex child execution
> **Review artifacts:** `scripts/review/results/2026-07-16-plan-1038-1044-claude.md` | `scripts/review/results/2026-07-16-plan-1038-1044-codex.md` | `scripts/review/results/2026-07-16-plan-1038-1044-gemini.md`

## Resource Intelligence Summary

- The program will extend the four curated tables in `data/modules/cost/curated/`: 80 sanctioned projects (67 with disclosed USD CAPEX), 110 awards across 29 projects, 19 project cost statements across 11 projects, and 49 revision-trail points across 21 projects at the planning baseline.
- `timeseries.reconciliation` will already distinguish capex-comparable award bases, coverage, partner-net checks, award stage anchors, and sanction-to-outturn evidence. `timeseries.back_allocation` will already expose six lifecycle stages and architecture-specific, banded priors.
- `CostObservation` will already enforce sourced/fitted/allocated/assumed/TODO provenance and native-currency semantics. The new work will preserve, not weaken, those contracts.
- The frozen FDAS references will be `lease_assumptions.xlsx`, `financial_project_summary.xlsx`, and `drilling_and_completion_days.xlsx` under `docs/modules/bsee/analysis/production/FDAS_V30/`.
- Big Foot will provide a useful tracer bullet because the live corpus will contain a $4,000MM sanction total, a $5,100MM outturn point, one $45MM point award, one excluded $200MM midstream award, major award-coverage gaps, and 3,033 observed drilling/completion days.
- No external engineering standard will govern the accounting model. The authoritative inputs will be cited disclosures, the accepted pilot contract, the repository provenance rules, and explicit empirical validation. Stakeholder circulation will remain paused under #1017.
- Generated coverage metadata will replace hand-maintained counts in decision surfaces because the current curated Markdown summaries will lag the live CSVs.

## Artifact Map

| Artifact | Path |
|---|---|
| Program plan | `docs/plans/2026-07-16-issue-1038-cost-map-program.md` |
| Human review packet | `docs/reports/2026-07-16-issues-1038-1044-cost-map-plan.html` |
| Shared domain contract | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py` |
| Existing observation contract | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/schema.py` |
| Existing reconciliation | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/reconciliation.py` |
| Existing allocation priors | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/back_allocation.py` |
| Contract tests | `tests/unit/cost/test_cost_map_schema.py` |
| Child plans | `docs/plans/2026-07-16-issue-1039-*.md` through `2026-07-16-issue-1044-*.md` |

## Deliverable

The epic will establish one versioned accounting contract and a gated execution sequence for requirements, award linkage, bidirectional synthesis, dated traces, correlated estimation, and FDAS reconciliation. It will not itself authorize child implementation.

## Shared Contract to Freeze

- Canonical keys will identify project, phase, asset/work package, award, source event, and model vintage without rewriting source labels.
- Amounts will carry `currency`, `price_basis`, `basis_year`, `ownership_basis`, `scope_basis`, `capex_basis`, lower/upper values, and provenance.
- Value bases will preserve the full existing vocabulary: `point`, `range`, `band`, `backlog`, `not_public`, `lease_contract`, `combined`, and `midstream`.
- Evidence status will distinguish `disclosed`, `award_derived`, `allocated`, `modeled`, `assumed`, `todo`, and `not_public`.
- Linkage status will distinguish `linked`, `partial`, `bundled`, `overlap`, `unlinked`, and `ambiguous`; `not_public` will remain an orthogonal value basis, not a linkage outcome.
- Stable `project_id`, `award_id`, `requirement_id`, and `event_id` fields will preserve many-to-many lineage without using mutable display labels as keys.
- Arithmetic will fail closed on currency, price-basis, ownership, scope, phase, and capex-basis incompatibility.
- A bundled award will be represented once and linked many-to-many; it will never be copied into multiple additive rows.
- Every reconciliation will expose included, excluded, overlapping, unallocated, residual, and unreconciled amounts.

## Planned Execution Sequence

1. #1039 will prove the complete contract on Big Foot and will stop for owner taxonomy/accounting approval.
2. #1040 will scale required assets and award linkage across the empirical portfolio.
3. #1041 and #1042 will consume the approved linkage surface and may proceed in parallel.
4. #1043 will train only after synthesis and historical feature availability are defined.
5. #1044 will compare the completed outputs to frozen FDAS workbooks and generate the integrated decision surface.
6. #1017 will remain outside the execution graph until the owner separately authorizes circulation.

## TDD Test List

| Test | Expected result |
|---|---|
| incompatible currencies enter additive arithmetic | fail closed |
| gross and partner-net values enter one subtotal | fail closed |
| bundled award links to multiple assets | one monetary contribution only |
| linked `not_public` award is evaluated | linked scope finding with no invented value |
| allocated/modeled value is serialized | never labeled disclosed |
| range is aggregated | lower and upper bounds remain ordered |
| every child consumes the same enum vocabulary | schema contract passes |
| empirical coverage is reported | exact live counts and exclusions are emitted |

## Acceptance Criteria

- [ ] One shared schema will govern all six children and will be approved through the Big Foot pilot.
- [ ] Each child will have its own reviewed plan and separate explicit user approval before implementation.
- [ ] Dependency gates will prevent training or reconciliation from preceding their input contracts.
- [ ] Program outputs will preserve native currency, range, basis, provenance, and unavailable findings.
- [ ] Portfolio coverage claims will be recomputed from the live files.
- [ ] Generated HTML will be the human-facing default; machine-readable outputs will remain reproducible.
- [ ] Every implemented child will receive T3 adversarial artifact/code review and an issue summary before close.
- [ ] No email, external send, workbook overwrite, or self-merge will occur.

## Risks and Decisions Reserved for the Owner

- The owner will approve the pilot taxonomy before #1040 scales it.
- Sparse valued awards may constrain asset-level validation; absence will be reported, not filled.
- The estimator may prove non-viable for some cohorts; `non_estimable` will remain a valid deliverable.
- Workbook values will remain assumptions until independently sourced; reconciliation will not promote them to disclosure evidence.

## Complexity: T3

This will be a systemic, cross-layer program with coupled data contracts, calculations, model validation, workbooks, and generated reports. Three-provider adversarial review will apply at both plan and implementation stages.
