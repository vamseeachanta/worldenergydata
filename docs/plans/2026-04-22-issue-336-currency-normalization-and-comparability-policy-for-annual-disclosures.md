# Plan for #336: currency normalization and comparability policy for annual disclosures

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-22
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/336
> **Review artifacts:** scripts/review/results/2026-04-22-plan-336-codex.md | scripts/review/results/2026-04-22-plan-336-gemini.md

---

## Policy revision — 2026-11-06

The annual-disclosure policy will require a caller-supplied escalation rate and
its evidence, rather than adopt the original fixed 3.0% rate as a default. No
qualified empirical escalation series is supplied with this module. A missing
rate or source will therefore produce an explicit non-comparable result, even
for same-year amounts. The 3.0% scenario will remain an explicitly labelled
assumption in examples and tests. USD outputs, the default 2020 base year and
static versioned FX inputs will remain in scope; the existing predictor's fixed
rate will remain unchanged. This revision will supersede the original fixed-rate
requirement in the scope, pseudocode, acceptance criteria and risks below.

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/cost/data_collection/public_dataset.py` preserves as-reported cost data and does not normalize annual disclosure rows.
- `src/worldenergydata/cost/data_collection/calibration_schema.py` uses a single normalized money field for sanction-era points, not annual disclosure comparability.
- `src/worldenergydata/cost/calibration/cost_predictor.py` already contains one deterministic comparability precedent: inflation/base-year adjustment to 2020 via a fixed 3% escalation rate.
- `tests/unit/cost/test_cost_predictor.py` is the current predictor guardrail around the existing 2020-base-year / 3% escalation precedent.
- `tests/unit/cost/test_proxy_comparison.py` is a current downstream cost-calibration regression boundary that must remain unaffected.
- `tests/unit/cost/test_calibration_schema.py` is an existing schema validation boundary for the sanction-side dataset and should remain unchanged.

### Documents consulted
- Issue #336 — normalization/comparability while preserving as-reported values.
- Parent issue #334 and approved plan — v1 disclosure layer intentionally preserves as-reported values only and defers normalization.

### Gaps identified
- No annual-disclosure normalization policy exists.
- No explicit comparable-money output shape exists that preserves raw values.
- No tests define how non-comparable rows should be represented.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-22-issue-336-currency-normalization-and-comparability-policy-for-annual-disclosures.md` |
| Existing as-reported sanction dataset | `src/worldenergydata/cost/data_collection/public_dataset.py` |
| Existing comparability precedent | `src/worldenergydata/cost/calibration/cost_predictor.py` |
| Existing data-collection exports | `src/worldenergydata/cost/data_collection/__init__.py` |
| Predictor guardrails | `tests/unit/cost/test_cost_predictor.py` |
| Sanction schema regression boundary | `tests/unit/cost/test_calibration_schema.py` |
| Downstream regression boundary | `tests/unit/cost/test_proxy_comparison.py` |

---

## Deliverable

An additive annual-disclosure normalization/comparability contract that preserves original amount/currency/unit/magnitude-scale and `as_reported_metric_name` fields unchanged, emits separate normalized comparable money fields when policy prerequisites are satisfied, and leaves the existing sanctioned-project dataset and current predictor/proxy-calibration behavior unchanged.

---

## Scope Boundaries

### In scope now
- Define normalization policy for annual disclosure monetary rows
- The deterministic v1 policy will use USD outputs, a default 2020 base year, a required caller-supplied annual escalation/de-escalation rate and evidence with no default, and a static versioned local FX table committed in-repo
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
function normalize_disclosure_money(record, fx_table, escalation_rate, escalation_source, base_year=2020):
    preserve raw amount/currency/unit/magnitude_scale/as_reported_metric_name unchanged
    if missing amount or currency or magnitude_scale or fiscal_year:
        return explicit not_comparable result with normalized fields None
    if escalation_rate is None or escalation_source is absent or blank:
        return explicit not_comparable result with normalized fields None
    if currency not in fx_table or fiscal_year not in fx_table[currency]:
        return explicit not_comparable result with normalized fields None
    usd_nominal = convert reported amount using static in-repo FX table for fiscal year
    usd_base_year = adjust to base year using the supplied annual escalation/de-escalation rate
    return record + normalized_amount, normalized_currency='USD', normalized_base_year=base_year, normalization_method='fx_then_base_year_adjustment_v1', comparability_status='comparable'

function load_normalized_annual_disclosures(raw_records, fx_table, escalation_rate, escalation_source, base_year=2020):
    return [normalize_disclosure_money(r, fx_table, escalation_rate, escalation_source, base_year) for r in raw_records]
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
- [ ] Deterministic v1 policy will use a static in-repo FX table, USD normalized currency, a default 2020 base year and a required evidenced annual escalation/de-escalation rate with no default
- [ ] Missing or unsupported policy inputs produce explicit non-comparable rows rather than silent coercion
- [ ] Existing sanctioned dataset tests still pass without weakened assertions
- [ ] Existing predictor and proxy-comparison behavior remain unchanged

---

## Risks and Open Questions

- #336 depends on #334 disclosure schema/loader being present first.
- The v1 normalization policy will use a static in-repo FX table, normalized USD outputs and a default 2020 base year; the annual rate and source will be explicit required inputs so that an unsupported empirical assumption will not become a default.
- Future work may supply a qualified escalation series; until then, examples and tests will label the supplied 3.0% rate as an assumption rather than measured inflation.
- Must avoid drifting into linkage semantics (#335) or consumer-facing analytics/views (#338).

---

## Complexity: T2

**T2** — bounded schema/policy/test work if implemented as an additive normalization layer isolated from existing sanction calibration and downstream analytics surfaces.
