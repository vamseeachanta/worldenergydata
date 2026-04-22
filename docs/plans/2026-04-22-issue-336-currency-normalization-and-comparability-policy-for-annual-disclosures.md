# Plan for #336: currency normalization and comparability policy for annual disclosures

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-22
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/336
> **Review artifacts:** scripts/review/results/2026-04-22-plan-336-codex.md | scripts/review/results/2026-04-22-plan-336-gemini.md

---

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/cost/data_collection/public_dataset.py` preserves as-reported cost data and does not normalize annual disclosure rows.
- `src/worldenergydata/cost/data_collection/calibration_schema.py` uses a single normalized money field for sanction-era points, not annual disclosure comparability.
- `src/worldenergydata/cost/calibration/cost_predictor.py` already contains one deterministic comparability precedent: inflation/base-year adjustment to 2020 via a fixed 3% escalation rate.
- `tests/unit/cost/test_dataset_size.py` and `tests/unit/cost/test_cost_predictor.py` are current guardrails around sanctioned-project dataset and predictor behavior.
- `tests/unit/cost/test_field_integration.py` is a downstream regression boundary that should remain unaffected.

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
| Sanction dataset guardrails | `tests/unit/cost/test_dataset_size.py` |
| Predictor guardrails | `tests/unit/cost/test_cost_predictor.py` |
| Downstream regression boundary | `tests/unit/cost/test_field_integration.py` |

---

## Deliverable

An additive annual-disclosure normalization/comparability contract that preserves original amount/currency/unit fields unchanged, emits separate normalized comparable money fields when policy prerequisites are satisfied, and leaves the existing sanctioned-project dataset and downstream field-cost integrations unchanged.

---

## Scope Boundaries

### In scope now
- Define normalization policy for annual disclosure monetary rows
- Preserve original as-reported values alongside normalized comparable values
- Define minimum metadata for comparability: currency, amount, scale, fiscal year, normalization method/version
- Add deterministic utility/view behavior for normalization and comparability
- Add focused tests proving reproducible normalization and explicit non-comparable outcomes

### Explicitly out of scope for this issue
- Changing meaning of `CostDataPoint.cost_usd_mm`
- Rewriting sanctioned public dataset into mixed sanction/disclosure store
- Broad automated FX ingestion or live rate pipelines
- Dashboards, benchmark products, or consumer redesign
- Linkage-model redesign from #335

---

## Pseudocode

```text
function normalize_disclosure_money(record):
    preserve raw amount/currency/unit fields unchanged
    if missing required comparability inputs:
        return not_comparable result with normalized fields None
    usd_nominal = convert reported amount using deterministic FX policy for fiscal year
    usd_base_year = adjust to base year using deterministic policy
    return record + normalized_amount, normalized_currency, normalized_base_year, normalization_method, comparability_status

function load_normalized_annual_disclosures():
    raw = load annual disclosure records from #334
    return [normalize_disclosure_money(r) for r in raw]
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export normalization/comparability surface |
| Add/modify | `src/worldenergydata/cost/data_collection/` | host annual-disclosure normalization schema/utility/view beside disclosure layer |
| Avoid/minimal | `src/worldenergydata/cost/data_collection/public_dataset.py` | sanctioned as-reported dataset should remain unchanged |
| Avoid/minimal | `src/worldenergydata/cost/calibration/cost_predictor.py` | reuse as policy precedent, not main implementation home |
| Add tests | `tests/unit/cost/` | normalization/comparability tests |
| Verify only | `tests/unit/cost/test_dataset_size.py` | sanctioned dataset unchanged |
| Verify only | `tests/unit/cost/test_field_integration.py` | downstream behavior unchanged |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_as_reported_values_are_preserved_after_normalization` | raw values are untouched | comparable disclosure row | raw preserved |
| `test_normalized_value_is_stored_in_separate_fields` | additive comparable layer only | comparable disclosure row | normalized fields populated separately |
| `test_same_input_produces_same_normalized_output` | deterministic behavior | repeated same row | same normalized output |
| `test_normalization_method_metadata_is_recorded` | comparable output is auditable | comparable row | method/base year present |
| `test_missing_currency_marks_record_not_comparable` | incomplete row stays valid but unnormalized | row missing currency | not comparable |
| `test_missing_fiscal_year_marks_record_not_comparable` | no silent year assumptions | row missing fiscal_year | not comparable |
| `test_scale_is_applied_before_normalization` | million/billion scale handled explicitly | scaled row | expected normalized amount |
| `test_cross_currency_rows_can_be_compared_when_policy_inputs_exist` | policy can compare currencies deterministically | two rows different currencies | comparable normalized outputs |
| `test_existing_public_dataset_loader_behavior_is_unchanged` | sanctioned dataset unaffected | current loader | unchanged |

---

## Acceptance Criteria

- [ ] Normalization is additive, not destructive of as-reported values
- [ ] Every normalized record preserves original amount/currency/unit fields
- [ ] Comparable outputs use separate named normalized fields and include method metadata
- [ ] Missing policy inputs produce explicit non-comparable rows rather than silent coercion
- [ ] Existing sanctioned dataset tests still pass without weakened assertions
- [ ] Existing field integration behavior remains unchanged

---

## Risks and Open Questions

- #336 depends on #334 disclosure schema/loader being present first.
- Need explicit decision on whether normalization adopts the same 2020 base year / 3% escalation rule as `cost_predictor.py` or a separately versioned rule.
- Need deterministic baseline FX source/table location for v1.
- Must avoid drifting into metric-comparability or dashboard logic.

---

## Complexity: T2

**T2** — bounded schema/policy/test work if implemented as an additive layer isolated from the existing sanction calibration path.
