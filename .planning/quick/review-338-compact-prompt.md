# Adversarial Plan Review Request: Issue #338

You are an independent adversarial reviewer. Findings only. Do not praise or restate.

Target
- Repo: vamseeachanta/worldenergydata
- Issue #338: annual disclosure analytics views and consumer integration
- Stage: draft canonical plan review before any approval-stage move

Review questions
1. Is the plan correctly grounded in the current repo surfaces named in the plan?
2. Is scope properly bounded for this child issue, without stealing work from sibling issues?
3. Are the files-to-change, tests, and acceptance criteria internally consistent?
4. Are there any hidden blockers, missing tests, or likely failure modes that should block plan-review?

Required output
- Verdict: APPROVE | MINOR | MAJOR
- Retrieval adequacy: adequate | insufficient
- Strengths
- Findings by severity: critical, high, medium, low
- Missing tests
- Scope creep concerns
- Weakest assumption
- Most likely implementation failure mode
- Most likely test gap
- Future issues suggested
- Review confidence

## Exact plan sections under review

## Deliverable

A derived annual-disclosure analytics layer that produces a project annual cost revision view and an operator annual capex series view, plus thin consumer-facing integration hooks for `cost`, `fdas`, and `lower_tertiary`, while preserving raw-vs-derived separation and leaving raw schema/ingestion/currency-methodology work to prior issues.

---

## Scope Boundaries

### In scope now
- Derived annual analytics/view definitions built from disclosure foundation
- Thin consumer-facing integration contracts for `cost`, `fdas`, and `lower_tertiary`
- Tests proving downstream consumers can read the derived views
- Explicit raw-vs-derived separation

### Explicitly out of scope for this issue
- Redefining raw disclosure schema from #334
- Ingestion/citation pipeline changes from #337
- Linkage-model redesign from #335
- Currency normalization/comparability redesign from #336
- Broad backfill or dashboard products
- Replacing existing `CostPredictor`, FDAS financial core, or lower tertiary economics logic wholesale

---

## Pseudocode

```text
function load_project_cost_revision_view(raw_disclosure_records):
    project_rows = project-scope disclosure rows that are linkable under #334/#335 contract
    group by operator + project_name
    sort by fiscal_year
    emit derived rows with reported capex, provenance, yoy delta, yoy pct where valid

function load_operator_annual_capex_view(raw_disclosure_records):
    operator_rows = operator-scope disclosure rows
    group by operator
    sort by fiscal_year
    emit derived rows with reported capex, provenance, yoy delta, yoy pct where valid

function build_cost_disclosure_benchmark(project_revision_view, predictor_input):
    keep predictor contract unchanged
    compare predictor output against latest matching disclosed project capex

fdas integration:
    expose a disclosure analytics namespace/query object via existing lazy export pattern

lower_tertiary integration:
    allow optional annual disclosure view input to enrich summaries without changing default behavior
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/disclosure_analytics.py` | derived annual project/operator view builders |
| Modify | `src/worldenergydata/cost/__init__.py` | expose derived disclosure view loaders for cost consumers |
| Modify | `src/worldenergydata/fdas/__init__.py` | expose disclosure analytics namespace via lazy export |
| Modify | `src/worldenergydata/lower_tertiary/npv.py` | optional disclosure-view consumption hook without changing default behavior |
| Create | `tests/unit/cost/test_disclosure_analytics.py` | unit tests for derived view construction and raw-vs-derived separation |
| Modify/Create | `tests/unit/cost/test_field_integration.py` | integration-style tests for cost-side consumer access |
| Create | `tests/unit/fdas/test_disclosure_api.py` | FDAS integration/export tests |
| Create | `tests/unit/lower_tertiary/test_disclosure_integration.py` | lower tertiary optional-consumption tests |
| Modify if needed | `tests/test_query_api.py` | package-level API/export regression |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_project_scope_records_produce_project_revision_view` | project rows create revision view | project disclosure rows | derived revision rows |
| `test_operator_scope_records_produce_operator_capex_view` | operator rows create operator capex view | operator disclosure rows | derived operator series |
| `test_operator_rows_never_appear_in_linkable_project_view` | scope separation preserved | mixed rows | operator rows excluded from project view |
| `test_derived_rows_preserve_provenance_fields` | provenance survives derivation | raw disclosure rows | derived rows with provenance |
| `test_yoy_delta_only_computed_with_valid_prior_year` | no fake series math | sparse rows | delta only when valid |
| `test_raw_records_are_not_mutated_by_view_generation` | raw-vs-derived separation | raw dataset | unchanged raw rows |
| `test_cost_consumer_can_compare_predictor_output_to_latest_disclosed_capex` | cost-side consumer hook works | revision view + predictor input | comparison payload |
| `test_fdas_exposes_disclosure_analytics_namespace` | FDAS lazy export surface works | package import | namespace/query resolves |
| `test_lower_tertiary_summary_unchanged_without_disclosure_view` | default behavior preserved | existing call path | unchanged summary |
| `test_lower_tertiary_can_optionally_consume_disclosure_view` | optional enrichment works | disclosure view + matching field/project | enriched summary |

---

## Acceptance Criteria

- [ ] Derived layer provides a project annual cost revision view
- [ ] Derived layer provides an operator annual capex series view
- [ ] Cost-side consumer hook can use project revision view without changing `CostDataPoint` semantics
- [ ] FDAS exposes a consumer-facing disclosure analytics surface through its public API/export pattern
- [ ] Lower tertiary can optionally consume derived disclosure view data without breaking existing call paths
- [ ] Tests prove raw-vs-derived separation and unchanged non-disclosure workflows
- [ ] #338 does not redefine raw schema, ingestion rules, linkage rules, or currency methodology from prior issues

---

## Risks and Open Questions

- Depends on the #334 disclosure foundation being implemented first.
- Exact import/module path for raw disclosure records is unresolved until #334 lands.
- YoY revision math is only safe when records are same-basis/as-reported; mixed basis must stay out of scope unless normalized upstream.
- Lower tertiary field/project mapping may require a minimal explicit rule rather than assumptions.
- Need to avoid expanding `CostPredictor.fit()` itself; add adapter/helper only.

---

## Complexity: T2

**T2** — bounded additive analytics and adapter work if raw foundation and prior contracts are respected; main uncertainty is dependency timing, not algorithmic breadth.
