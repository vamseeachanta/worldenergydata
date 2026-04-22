# Adversarial Plan Review Request: Issue #335

You are an independent adversarial reviewer. Findings only. Do not praise or restate.

Target
- Repo: vamseeachanta/worldenergydata
- Issue #335: disclosure-to-CostDataPoint linkage model
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

A derived-only linkage contract in `worldenergydata.cost.data_collection` that formalizes exact `(operator, project_name)` resolution of disclosure project rows against existing `CostDataPoint` sanction records and returns explicit `linked`, `unlinked`, or `ambiguous` outcomes without changing sanction data content or downstream economics consumers.

---

## Scope Boundaries

### In scope now
- Define linkage status/result shape
- Preserve exact `(operator, project_name)` as the only deterministic rule
- Define explicit semantics for exact single match, no match, and multiple exact matches
- Add focused tests around exact, unmatched, and ambiguous outcomes
- Export linkage contract/helper from `worldenergydata.cost.data_collection`

### Explicitly out of scope for this issue
- Fuzzy matching, alias tables, or canonical-name normalization
- Currency normalization or comparability policy
- Any changes to FDAS / lower_tertiary / analytics consumers
- Any stored foreign-key-style `CostDataPoint` reference field
- Restatement/versioning behavior

---

## Pseudocode

```text
class LinkageStatus(Enum):
    LINKED = "linked"
    UNLINKED = "unlinked"
    AMBIGUOUS = "ambiguous"

class CostDataPointLinkResult(BaseModel):
    status
    match_key_operator
    match_key_project_name
    matched_record
    matched_count
    candidates

function resolve_cost_datapoint_link(operator, project_name, sanctioned_records=None):
    records = sanctioned_records or load_public_dataset()
    exact_candidates = records where rec.operator == operator and rec.project_name == project_name
    if len(exact_candidates) == 0: return UNLINKED result
    if len(exact_candidates) == 1: return LINKED result with matched record
    return AMBIGUOUS result with candidates only
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Modify | `src/worldenergydata/cost/data_collection/calibration_schema.py` | add linkage enum/result model |
| Modify | `src/worldenergydata/cost/data_collection/public_dataset.py` | add deterministic linkage helper against sanction dataset |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export linkage primitives/helpers |
| Modify | `tests/unit/cost/test_calibration_schema.py` | TDD coverage for exact/no-match/ambiguous behavior |
| Verify only | `tests/unit/cost/test_field_integration.py` | regression boundary |
| Verify only | `tests/unit/cost/test_proxy_comparison.py` | regression boundary |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_linkage_status_enum_exposes_linked_unlinked_ambiguous` | contract has three canonical states | enum import | expected values |
| `test_resolve_link_returns_linked_for_exact_single_match` | exact match resolves deterministically | matching operator/project | linked result |
| `test_resolve_link_returns_unlinked_for_no_exact_match` | unmatched rows remain unresolved | non-matching operator/project | unlinked result |
| `test_resolve_link_returns_ambiguous_for_multiple_exact_matches` | helper never silently guesses | duplicated exact key set | ambiguous result |
| `test_ambiguous_result_has_no_single_matched_record` | ambiguous outcomes stay unresolved | ambiguous case | no matched record |
| `test_link_result_preserves_match_key_and_match_count` | result is debuggable/consumable | any result | keys + counts present |
| `test_helper_uses_load_public_dataset_by_default` | default sanctioned source works | no explicit records arg | valid result |
| `test_helper_accepts_injected_records_for_testing` | deterministic injectable behavior | custom sanctioned list | valid result |
| `test_data_collection_exports_linkage_contract` | public API exists | import check | names resolve |

---

## Acceptance Criteria

- [ ] Explicit `linked`, `unlinked`, and `ambiguous` outcomes exist
- [ ] Exact `(operator, project_name)` remains the only deterministic rule
- [ ] Ambiguous exact-key collisions are surfaced, never auto-resolved
- [ ] Unmatched rows are represented explicitly rather than via exceptions or silent null behavior
- [ ] Linkage remains derived-only; no stored `CostDataPoint` reference field is added
- [ ] `worldenergydata.cost.data_collection` exports the linkage contract/helper
- [ ] Existing sanction dataset loading behavior remains unchanged
- [ ] Existing field integration and proxy comparison tests still pass unchanged

---

## Risks and Open Questions

- `CostDataPoint` has no stronger stable identifier than domain fields, so ambiguous exact-key collisions cannot be disambiguated here.
- Future disclosure naming variants/phases may require a separate alias-governance follow-up rather than expanding this issue.
- The helper/result contract should stay narrow enough that later hardening can extend it without breaking consumers.

---

## Complexity: T2

**T2** — small code surface, but semantically important because it defines the safe future join boundary for disclosure-to-sanction matching.
