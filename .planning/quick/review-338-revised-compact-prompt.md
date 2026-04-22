# Adversarial Re-Review Request: Issue #338 (revised compact)

You are an independent adversarial reviewer. Findings only. Do not praise or restate.

Target
- Repo: vamseeachanta/worldenergydata
- Issue #338: annual disclosure analytics views and consumer integration
- Stage: revised draft plan review before any plan-review move

What was revised to address prior review findings:
- grounded FDAS seam explicitly in fdas/api.py and fdas/__init__.py; deferred lower-tertiary mapping/consumption contract; lower-tertiary behavior remains unchanged in this issue; bounded cost-side benchmark behavior to rows already comparable under #336 outputs; aligned files/tests/acceptance criteria with explicit FDAS API seam and no lower-tertiary implementation changes; kept raw schema/ingestion/linkage/currency-methodology out of scope

Review questions
1. Is the revised plan now sufficiently grounded and bounded for this child issue?
2. Are files-to-change, tests, and acceptance criteria internally consistent with current repo surfaces?
3. Any remaining blockers that should prevent moving this plan to plan-review later?

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

## Exact revised plan sections under review

## Deliverable

A derived annual-disclosure analytics layer that produces a project annual cost revision view and an operator annual capex series view, plus a thin cost-side consumer hook and an explicit FDAS API seam, while preserving raw-vs-derived separation and deferring lower-tertiary field/project mapping until a separate contract exists.

---

## Scope Boundaries

### In scope now
- Derived annual analytics/view definitions built from disclosure foundation
- Thin consumer-facing integration contracts for `cost` and `fdas` only
- Explicit raw-vs-derived separation
- A documented deferral for lower-tertiary mapping until a dedicated mapping contract exists
- Tests proving cost/fdas consumers can read the derived views without changing their core semantics

### Explicitly out of scope for this issue
- Redefining raw disclosure schema from #334
- Ingestion/citation pipeline changes from #337
- Linkage-model redesign from #335
- Currency normalization/comparability redesign from #336
- Broad backfill or dashboard products
- Lower-tertiary field/project mapping design (defer to a separate contract issue)
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
    only compare against derived rows that are already same-basis/comparable under #336 outputs
    if rows are not comparable: return no benchmark payload rather than forcing a comparison

fdas integration:
    expose a disclosure analytics namespace/query object via `src/worldenergydata/fdas/api.py`
    wire lazy export in `src/worldenergydata/fdas/__init__.py` explicitly

lower_tertiary integration:
    do not implement direct consumption in this issue
    document the deferred mapping requirement and add no-op/regression protection only
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/disclosure_analytics.py` | derived annual project/operator view builders |
| Modify | `src/worldenergydata/cost/__init__.py` | expose derived disclosure view loaders for cost consumers |
| Modify | `src/worldenergydata/fdas/api.py` | add explicit FDAS disclosure analytics query/object seam |
| Modify | `src/worldenergydata/fdas/__init__.py` | expose disclosure analytics namespace via lazy export |
| Create | `tests/unit/cost/test_disclosure_analytics.py` | unit tests for derived view construction and raw-vs-derived separation |
| Modify | `tests/unit/cost/test_field_integration.py` | integration-style tests for cost-side consumer access |
| Create | `tests/unit/fdas/test_disclosure_api.py` | FDAS integration/export tests |
| Modify if needed | `tests/test_query_api.py` | package-level FDAS API/export regression if disclosure namespace is public there |
| Do not change in this issue | `src/worldenergydata/lower_tertiary/npv.py` | lower-tertiary consumption deferred until mapping contract exists |

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
| `test_cost_consumer_can_compare_predictor_output_to_latest_disclosed_capex_when_rows_are_comparable` | cost-side consumer hook works only on same-basis comparable rows | revision view + predictor input | comparison payload |
| `test_cost_consumer_refuses_mixed_basis_or_non_comparable_rows` | #338 does not steal comparability policy from #336 | non-comparable rows | no benchmark payload |
| `test_fdas_exposes_disclosure_analytics_namespace` | FDAS lazy export surface works | package import | namespace/query resolves |
| `test_fdas_query_object_returns_project_revision_view` | FDAS API seam is explicit and grounded | FDAS disclosure query object | project view |
| `test_fdas_query_object_returns_operator_capex_view` | FDAS API seam is explicit and grounded | FDAS disclosure query object | operator view |
| `test_no_lower_tertiary_behavior_changes_are_introduced` | lower-tertiary mapping is explicitly deferred | existing call path | unchanged behavior |

---

## Acceptance Criteria

- [ ] Derived layer provides a project annual cost revision view
- [ ] Derived layer provides an operator annual capex series view
- [ ] Cost-side consumer hook can use project revision view only when rows are already comparable under #336 outputs, without changing `CostDataPoint` semantics
- [ ] FDAS exposes a consumer-facing disclosure analytics surface through an explicitly grounded API/export pattern (`fdas/api.py` + `fdas/__init__.py`)
- [ ] Lower-tertiary direct consumption is explicitly deferred, and existing lower-tertiary behavior remains unchanged in this issue
- [ ] Tests prove raw-vs-derived separation and unchanged non-disclosure workflows
- [ ] #338 does not redefine raw schema, ingestion rules, linkage rules, currency methodology, or lower-tertiary mapping contracts from prior/sibling issues

---

## Risks and Open Questions

- Depends on the #334 disclosure foundation being implemented first.
- Exact import/module path for raw disclosure records is unresolved until #334 lands.
- YoY revision math is only safe when records are same-basis/comparable under #336; mixed basis must be refused rather than inferred here.
- Lower-tertiary field/project mapping is intentionally deferred because current field-oriented inputs do not provide a grounded disclosure mapping contract.
- Need to avoid expanding `CostPredictor.fit()` itself; add adapter/helper only.

---

## Complexity: T2

**T2** — bounded additive analytics and adapter work if raw foundation and prior contracts are respected; main uncertainty is dependency timing, not algorithmic breadth.
