# Adversarial Re-Review Request: Issue #336 (revised compact)

You are an independent adversarial reviewer. Findings only. Do not praise or restate.

Target
- Repo: vamseeachanta/worldenergydata
- Issue #336: currency normalization and comparability policy for annual disclosures
- Stage: revised draft plan review before any plan-review move

What was revised to address prior review findings:
- fixed deterministic v1 policy in-plan: static in-repo FX table, normalized USD, base year 2020, 3% annual escalation/de-escalation; corrected repo-grounding to real current tests: test_cost_predictor.py, test_proxy_comparison.py, test_calibration_schema.py; preserve magnitude_scale and as_reported_metric_name explicitly; kept #336 bounded to normalization only; no linkage work (#335) and no analytics/views (#338); named concrete new files: disclosure_normalization.py and fx_policy_v1.py

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

An additive annual-disclosure normalization/comparability contract that preserves original amount/currency/unit/magnitude-scale and `as_reported_metric_name` fields unchanged, emits separate normalized comparable money fields when policy prerequisites are satisfied, and leaves the existing sanctioned-project dataset and current predictor/proxy-calibration behavior unchanged.

---

## Scope Boundaries

### In scope now
- Define normalization policy for annual disclosure monetary rows
- Freeze a deterministic v1 policy now: normalized currency = USD, normalized base year = 2020, fixed annual escalation/de-escalation rate = 3%, FX source = static versioned local table committed in-repo
- Preserve original as-reported values alongside normalized comparable values
- Define minimum metadata for comparability: currency, amount, magnitude scale, fiscal year, normalization method/version
- Add deterministic utility behavior for normalization and comparability; do not add consumer-facing analytics views here
- Add focused tests proving reproducible normalization and explicit non-comparable outcomes

### Explicitly out of scope for this issue
- Changing meaning of `CostDataPoint.cost_usd_mm`
- Rewriting sanctioned public dataset into mixed sanction/disclosure store
- Broad automated FX ingestion or live rate pipelines
- Dashboards, benchmark products, or consumer-facing derived views (belongs to #338)
- Linkage-model redesign or unmatched/ambiguous-row semantics (belongs to #335)

---

## Pseudocode

```text
function normalize_disclosure_money(record, fx_table, base_year=2020, escalation_rate=0.03):
    preserve raw amount/currency/unit/magnitude_scale/as_reported_metric_name unchanged
    if missing amount or currency or magnitude_scale or fiscal_year:
        return explicit not_comparable result with normalized fields None
    if currency not in fx_table or fiscal_year not in fx_table[currency]:
        return explicit not_comparable result with normalized fields None
    usd_nominal = convert reported amount using static in-repo FX table for fiscal year
    usd_base_year = adjust to base year using fixed 3% annual escalation/de-escalation
    return record + normalized_amount, normalized_currency='USD', normalized_base_year=2020, normalization_method='fx_then_base_year_adjustment_v1', comparability_status='comparable'

function load_normalized_annual_disclosures(raw_records, fx_table):
    return [normalize_disclosure_money(r, fx_table) for r in raw_records]
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/disclosure_normalization.py` | additive normalization/comparability utility for annual disclosure rows |
| Create | `src/worldenergydata/cost/data_collection/fx_policy_v1.py` | static versioned in-repo FX/base-year policy inputs for v1 |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export normalization/comparability surface |
| Verify only | `src/worldenergydata/cost/data_collection/public_dataset.py` | sanctioned as-reported dataset remains unchanged |
| Verify only | `src/worldenergydata/cost/calibration/cost_predictor.py` | keep existing predictor behavior unchanged; use only as precedent |
| Create | `tests/unit/cost/test_disclosure_normalization.py` | normalization/comparability tests for annual disclosure rows |
| Verify only | `tests/unit/cost/test_cost_predictor.py` | predictor behavior unchanged |
| Verify only | `tests/unit/cost/test_proxy_comparison.py` | downstream calibration behavior unchanged |
| Verify only | `tests/unit/cost/test_calibration_schema.py` | sanction-schema behavior unchanged |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_as_reported_values_are_preserved_after_normalization` | raw amount/currency/unit/scale/metric-name fields are untouched | comparable disclosure row | raw preserved |
| `test_normalized_value_is_stored_in_separate_fields` | additive comparable layer only | comparable disclosure row | normalized fields populated separately |
| `test_same_input_produces_same_normalized_output` | deterministic behavior | repeated same row | same normalized output |
| `test_normalization_method_metadata_is_recorded` | comparable output is auditable | comparable row | method/base year/version present |
| `test_missing_currency_marks_record_not_comparable` | incomplete row stays valid but unnormalized | row missing currency | not comparable |
| `test_missing_fiscal_year_marks_record_not_comparable` | no silent year assumptions | row missing fiscal_year | not comparable |
| `test_unsupported_currency_marks_record_not_comparable` | missing FX mapping fails safely | row with unsupported currency | not comparable |
| `test_unsupported_fiscal_year_marks_record_not_comparable` | unsupported FX year fails safely | row with uncovered year | not comparable |
| `test_missing_scale_marks_record_not_comparable` | scale is mandatory for comparability | row missing magnitude_scale | not comparable |
| `test_scale_is_applied_before_normalization` | million/billion scale handled explicitly | scaled row | expected normalized amount |
| `test_same_currency_rows_use_no_fx_but_still_record_method` | same-currency normalization stays deterministic | USD row | comparable result with method metadata |
| `test_cross_currency_rows_can_be_compared_when_policy_inputs_exist` | policy can compare currencies deterministically | two rows different currencies | comparable normalized outputs |
| `test_existing_public_dataset_loader_behavior_is_unchanged` | sanctioned dataset unaffected | current loader | unchanged |
| `test_cost_predictor_behavior_is_unchanged` | predictor remains untouched | existing predictor path | unchanged |
| `test_proxy_comparison_behavior_is_unchanged` | downstream calibration path remains untouched | proxy comparison path | unchanged |

---

## Acceptance Criteria

- [ ] Normalization is additive, not destructive of as-reported values
- [ ] Every normalized record preserves original amount/currency/unit/magnitude-scale and `as_reported_metric_name` fields
- [ ] Comparable outputs use separate named normalized fields and include method/version metadata
- [ ] Deterministic v1 policy is fixed in the plan: static in-repo FX table, USD normalized currency, 2020 base year, 3% annual escalation/de-escalation
- [ ] Missing or unsupported policy inputs produce explicit non-comparable rows rather than silent coercion
- [ ] Existing sanctioned dataset tests still pass without weakened assertions
- [ ] Existing predictor and proxy-comparison behavior remain unchanged

---

## Risks and Open Questions

- #336 depends on #334 disclosure schema/loader being present first.
- The v1 normalization policy is fixed for planning purposes to avoid TDD ambiguity: static in-repo FX table, normalized USD outputs, 2020 base year, 3% annual escalation/de-escalation.
- Future work may replace this with a stronger versioned policy, but this issue should not reopen that decision.
- Must avoid drifting into linkage semantics (#335) or consumer-facing analytics/views (#338).

---

## Complexity: T2

**T2** — bounded schema/policy/test work if implemented as an additive normalization layer isolated from existing sanction calibration and downstream analytics surfaces.
