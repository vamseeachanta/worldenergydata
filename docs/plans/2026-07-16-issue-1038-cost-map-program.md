# Plan for #1038: bidirectional asset-to-project cost-map program

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1038
> **Client:** N/A
> **Lane:** lane:claude
> **Review artifacts:** R1 Codex MAJOR: `scripts/review/results/2026-07-16-plan-1038-1044-codex-r1.md`; final Claude/Codex/Gemini artifacts PENDING

## Resource Intelligence Summary

- The program will extend the four curated tables in `data/modules/cost/curated/`: 80 sanctioned projects (67 with disclosed USD CAPEX), 110 awards across 29 projects, 19 project cost statements across 11 projects, and 49 revision-trail points across 21 projects at the planning baseline.
- Current `timeseries.reconciliation` distinguishes capex-comparable award bases, coverage, partner-net checks, award stage anchors, and sanction-to-outturn evidence. Current `timeseries.back_allocation` exposes six lifecycle stages and architecture-specific, banded priors.
- Current `CostObservation` enforces sourced/fitted/allocated/assumed/TODO provenance and native-currency semantics. The new work will preserve, not weaken, those contracts.
- The frozen FDAS references will be `lease_assumptions.xlsx`, `financial_project_summary.xlsx`, and `drilling_and_completion_days.xlsx` under `docs/modules/bsee/analysis/production/FDAS_V30/`.
- Big Foot provides a useful tracer bullet because the live corpus contains a $4,000MM sanction total, a $5,100MM outturn point, one $45MM point award, one excluded $200MM midstream award, major award-coverage gaps, and 3,033 observed drilling/completion days.
- No external engineering standard will govern the accounting model. The authoritative inputs will be cited disclosures, the accepted pilot contract, the repository provenance rules, and explicit empirical validation. Stakeholder circulation will remain paused under #1017.
- Generated coverage metadata will replace hand-maintained counts in decision surfaces because the current curated Markdown summaries will lag the live CSVs.

## Artifact Map

| Artifact | Path |
|---|---|
| Program plan | `docs/plans/2026-07-16-issue-1038-cost-map-program.md` |
| Human review packet | `docs/reports/2026-07-16-issues-1038-1044-cost-map-plan.html` |
| Existing observation contract | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/schema.py` |
| Existing reconciliation | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/reconciliation.py` |
| Existing allocation priors | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/back_allocation.py` |
| Child plans | `docs/plans/2026-07-16-issue-1039-*.md` through `2026-07-16-issue-1044-*.md` |

## Deliverable

The epic will coordinate one versioned accounting contract and a gated execution sequence for requirements, award linkage, bidirectional synthesis, dated traces, correlated estimation, and FDAS reconciliation. It will own no implementation file; #1039 will produce the first contract manifest. The epic will not itself authorize child implementation.

## Shared Contract to Freeze

- Canonical keys will identify project, phase, asset/work package, award, source event, and model vintage without rewriting source labels.
- Amounts will carry `currency`, `price_basis`, `basis_year`, `ownership_basis`, `scope_basis`, `capex_basis`, lower/upper values, and provenance.
- Value bases will preserve the full existing vocabulary: `point`, `range`, `band`, `backlog`, `not_public`, `lease_contract`, `combined`, and `midstream`. A separate `bound_type` field will distinguish `point`, `floor`, `ceiling`, `closed_range`, and `open_range`; availability/basis and mathematical bounds will not be conflated.
- Evidence derivation will distinguish `disclosed`, `award_derived`, `allocated`, `modeled`, `assumed`, and `todo`; independent source provenance/confidence fields will retain `operator`, `regulator`, `partner`, `trade_press`, and other approved source tiers without relabeling.
- Link resolution will distinguish only `linked`, `unlinked`, and `ambiguous`; scope coverage will independently distinguish `unknown`, `none`, `partial`, and `full`; bundle topology will use a separate `bundle_group_id`/`is_bundled` field.
- Counting disposition will independently distinguish `included`, `excluded`, and `overlap`, with a closed reason vocabulary. `not_public` will remain a value basis/availability result.
- Stable `project_id`, `award_id`, `requirement_id`, and `event_id` fields will use controlled opaque identifiers (for example `prj-0001` and `awd-0001`) assigned from four versioned identity registries. They will never derive from row position or mutable content; alias, phase, and source-label corrections will preserve the identifier. IDs will be monotonically issued, tombstoned rather than reused, and covered by collision, foreign-key, merge/split migration, and `validation_group_id` checks.
- Arithmetic will fail closed on currency, price-basis, ownership, scope, phase, and capex-basis incompatibility.
- A bundled award will be represented once and linked many-to-many; it will never be copied into multiple additive rows.
- Every reconciliation will expose included, excluded, overlapping, unallocated, residual, and unreconciled amounts.
- Money arithmetic will use exact `Decimal` at retained source precision and will never convert currencies. Published point values will quantize only at serialization to 0.01 million units of their native currency using `ROUND_HALF_EVEN`; interval lows will round outward with `ROUND_FLOOR` and highs with `ROUND_CEILING`; positive allocation shares will use `ROUND_FLOOR` plus largest remainder at that same output quantum. The manifest will pin currency, source scale, output quantum, rounding mode, and boundary. For total interval `T=[Tlo,Thi]` and eligible interval `E=[Elo,Ehi]`, residual will be `[Tlo-Ehi, Thi-Elo]`; coverage will be `[Elo/Thi, Ehi/Tlo]` when denominators are positive, otherwise unavailable. Open bounds and zero-crossing residuals will remain explicit.
- Top-down uncertainty will use reviewed joint scenario share vectors whose nonnegative shares each sum to 1.0. Component envelopes will be minima/maxima across whole-project scenarios; independent marginal bands from `back_allocation.py` will not be summed. Quantized allocations will conserve each total through a deterministic largest-remainder rule, ordered by fractional remainder then stable requirement ID.

## Planned Execution Sequence

1. #1039 will prove the complete contract on Big Foot and will stop for owner taxonomy/accounting approval.
2. #1040 will scale required assets and award linkage across the empirical portfolio.
3. #1041 and #1042 will consume the approved linkage surface and may proceed in parallel.
4. #1043 will train only after synthesis and historical feature availability are defined.
5. #1044 will compare the completed outputs to frozen FDAS workbooks and generate the integrated decision surface.
6. #1017 will remain outside the execution graph until the owner separately authorizes circulation.
7. Each producing child will emit a manifest with one common required envelope: `contract_version`, schema hash, ordered input hashes, producer commit, generated-at policy, Decimal/rounding policy, and output hashes. Each consumer will name the exact upstream path/version/hash and fail closed on a missing or mismatched field.

## Pseudocode

```text
#1039 -> manifest v1 + owner approval
#1040 preflight(v1) -> manifest v2
parallel(#1041 preflight(v2), #1042 preflight(v2))
#1043 preflight(#1041, #1042) -> validated model manifest
#1044 preflight(all upstream manifests) -> read-only workbook reconciliation
if any preflight/review/legal/cleanup gate fails: stop without label advancement
```

## Attested Evidence — 2026-07-16

`wc`/CSV enumeration, workbook inspection with `openpyxl`, `sha256sum`, targeted `rg`, live `gh issue view`, and the cost-unit baseline were run at commit `090228fb`. The exact passing baseline command was `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --extra test python -m pytest tests/unit/cost/ -q --noconftest -o addopts='' --ignore tests/unit/cost/test_field_integration.py --ignore tests/unit/cost/test_proxy_comparison.py --deselect tests/unit/cost/test_disclosure_analytics.py::TestLowerTertiaryDeferralInvariant`; it returned `164 passed, 2 deselected`. These three exclusions are pre-existing and will remain named rather than being reported as a clean unrestricted suite. R1 review independently reverified the corpus counts, Big Foot rows, D&C totals, V30 total, and workbook hashes. This issue will make no runtime-failure claim, so defect reproduction is N/A.

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
- [ ] Each child will use RED → minimal GREEN → refactor cycles, will run `scripts/legal/legal-sanity-scan.sh`, will receive T3 code/artifact review, will comment its issue, and will pass the pre-completion cleanup audit before close.

## Risks and Decisions Reserved for the Owner

- The owner will approve the pilot taxonomy before #1040 scales it.
- Sparse valued awards may constrain asset-level validation; absence will be reported, not filled.
- The estimator may prove non-viable for some cohorts; `non_estimable` will remain a valid deliverable.
- Workbook values will remain assumptions until independently sourced; reconciliation will not promote them to disclosure evidence.

## Complexity: T3

This will be a systemic, cross-layer program with coupled data contracts, calculations, model validation, workbooks, and generated reports. Three-provider adversarial review will apply at both plan and implementation stages.
