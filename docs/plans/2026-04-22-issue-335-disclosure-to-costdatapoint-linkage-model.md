# Plan for #335: disclosure-to-CostDataPoint linkage model

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-22
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/335
> **Review artifacts:** scripts/review/results/2026-04-22-plan-335-codex.md | scripts/review/results/2026-04-22-plan-335-gemini.md

---

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/cost/data_collection/public_dataset.py` is the current sanction-record corpus and exposes `load_public_dataset()` returning `list[CostDataPoint]`; no linkage helper exists today.
- `src/worldenergydata/cost/data_collection/calibration_schema.py` defines `CostDataPoint` and supporting enums but no linkage status/result model or stable linkage contract.
- `src/worldenergydata/cost/data_collection/__init__.py` exports only `CostDataPoint` and `load_public_dataset()`.
- `tests/unit/cost/test_calibration_schema.py` validates schema/data loading only; it does not test exact-match linkage, no-match, or ambiguity handling.
- `tests/unit/cost/test_proxy_comparison.py` is a regression boundary that depends on current `load_public_dataset()` behavior and should remain unchanged.
- Parent plan `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md` fixes the disclosure-side invariant that only project-scope disclosure rows are linkable and linkage remains derived-only exact `(operator, project_name)`.

### Documents consulted
- Issue #335 — linkage hardening between annual disclosure rows and sanction-point records.
- Parent issue #334 and approved plan — disclosure linkage in v1 is derived-only exact-match for project rows only; operator rows never link; no stored foreign-key-style `CostDataPoint` reference field is allowed.
- Review artifacts `scripts/review/results/2026-04-22-plan-335-codex.md` and `...-gemini.md` — current blockers are missing #334 dependency framing, weak operator-row non-linkability coverage, empty-list fallback bug risk, and questionable module placement.

### Gaps identified
- No canonical `linked` / `unlinked` / `ambiguous` result contract exists.
- No deterministic helper exists for exact-match resolution.
- No tests define how ambiguity must be surfaced rather than guessed.
- No disclosure-side helper currently consumes the approved invariant that operator rows are never linkable.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-22-issue-335-disclosure-to-costdatapoint-linkage-model.md` |
| Existing sanction schema | `src/worldenergydata/cost/data_collection/calibration_schema.py` |
| Existing sanction dataset loader | `src/worldenergydata/cost/data_collection/public_dataset.py` |
| Public data-collection exports | `src/worldenergydata/cost/data_collection/__init__.py` |
| New linkage helper/result module | `src/worldenergydata/cost/data_collection/linkage.py` |
| Primary test target | `tests/unit/cost/test_linkage.py` |
| Regression boundary | `tests/unit/cost/test_calibration_schema.py` |
| Regression boundary | `tests/unit/cost/test_proxy_comparison.py` |
| Parent dependency | `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md` |

---

## Deliverable

A derived-only linkage contract in `worldenergydata.cost.data_collection.linkage` that formalizes exact `(operator, project_name)` resolution of project-scope disclosure rows against existing `CostDataPoint` sanction records and returns explicit `linked`, `unlinked`, or `ambiguous` outcomes without changing sanction data content, adding stored reference fields, or widening into alias/fuzzy matching.

---

## Scope Boundaries

### In scope now
- Define linkage status/result shape
- Preserve exact `(operator, project_name)` as the only deterministic rule
- Carry the parent invariant explicitly: only project-scope disclosure rows participate in linkage; operator-scope rows are never linkable
- Define explicit semantics for exact single match, no match, and multiple exact matches
- Add focused tests around exact, unmatched, ambiguous, and operator-row-non-linkable outcomes
- Export linkage contract/helper from `worldenergydata.cost.data_collection`

### Explicitly out of scope for this issue
- Fuzzy matching, alias tables, trimming/case-normalization heuristics, or canonical-name normalization
- Currency normalization or comparability policy
- Any changes to FDAS / lower_tertiary / analytics consumers
- Any stored foreign-key-style `CostDataPoint` reference field
- Restatement/versioning behavior
- Redefining disclosure schema fields from #334

### Dependency boundary
- This issue depends on #334 landing the disclosure-side schema/loader surface first.
- #335 defines the sanction-side linkage helper/result contract and the disclosure-side linkage invariants that future consumers must respect.
- #335 must not attempt to implement the disclosure schema itself.

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
    if sanctioned_records is None:
        records = load_public_dataset()
    else:
        records = sanctioned_records

    exact_candidates = [
        rec for rec in records
        if rec.operator == operator and rec.project_name == project_name
    ]

    if len(exact_candidates) == 0:
        return UNLINKED result with matched_record=None, matched_count=0, candidates=[]
    if len(exact_candidates) == 1:
        return LINKED result with matched_record=exact_candidates[0], matched_count=1, candidates=[exact_candidates[0]]
    return AMBIGUOUS result with matched_record=None, matched_count=len(exact_candidates), candidates=exact_candidates

function disclosure_row_is_linkable(scope_type):
    return scope_type == "project"
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/linkage.py` | dedicated linkage helper/result module keeps disclosure-linkage concerns out of `calibration_schema.py` |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export linkage primitives/helpers |
| Create | `tests/unit/cost/test_linkage.py` | direct TDD coverage for exact/no-match/ambiguous/operator-row behaviors |
| Verify only | `src/worldenergydata/cost/data_collection/public_dataset.py` | sanctioned dataset remains the source for exact-match lookup but is not otherwise redesigned |
| Verify only | `tests/unit/cost/test_calibration_schema.py` | existing sanction-schema behavior remains unchanged |
| Verify only | `tests/unit/cost/test_proxy_comparison.py` | regression boundary for current dataset loader behavior |

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
| `test_helper_respects_injected_empty_record_list` | injected empty list does not fall back to loader | `sanctioned_records=[]` | unlinked result |
| `test_helper_accepts_injected_records_for_testing` | deterministic injectable behavior | custom sanctioned list | valid result |
| `test_negative_exactness_case_changes_stay_unlinked` | no hidden case/whitespace normalization sneaks in | case/spacing variant names | unlinked result |
| `test_operator_scope_rows_are_never_linkable` | parent invariant is carried explicitly | operator-scope row metadata | false / rejected from linkage path |
| `test_data_collection_exports_linkage_contract` | public API exists | import check | names resolve |
| `test_load_public_dataset_shape_is_unchanged` | sanction dataset loader remains unchanged | current loader | same shape/type semantics |

---

## Acceptance Criteria

- [ ] Explicit `linked`, `unlinked`, and `ambiguous` outcomes exist
- [ ] Exact `(operator, project_name)` remains the only deterministic rule
- [ ] Operator-scope disclosure rows are explicitly treated as never linkable
- [ ] Ambiguous exact-key collisions are surfaced, never auto-resolved
- [ ] Unmatched rows are represented explicitly rather than via exceptions or silent null behavior
- [ ] Linkage remains derived-only; no stored `CostDataPoint` reference field is added
- [ ] Injected empty record lists do not fall back to `load_public_dataset()`
- [ ] `worldenergydata.cost.data_collection` exports the linkage contract/helper
- [ ] Existing sanction dataset loading behavior remains unchanged
- [ ] Existing calibration/proxy regression tests still pass unchanged
- [ ] Plan and comments explicitly state this issue depends on #334 landing first

---

## Risks and Open Questions

- `CostDataPoint` has no stronger stable identifier than domain fields, so ambiguous exact-key collisions cannot be disambiguated here.
- Exact `(operator, project_name)` may still be fragile for selected seed rows if naming variants exist; alias handling remains future work.
- Need to decide whether `disclosure_row_is_linkable()` lives in the linkage module or only in disclosure-side adapter code after #334 lands.
- If future consumers need stronger keys than `(operator, project_name)`, a later identifier/uniqueness issue will be required.

---

## Complexity: T2

**T2** — small code surface, but semantically important because it defines the safe future join boundary for disclosure-to-sanction matching while carefully respecting the parent/sibling boundaries.
