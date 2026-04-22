# Adversarial Plan Review Request: Issue #337

You are an independent adversarial reviewer. Findings only. Do not praise or restate.

Target
- Repo: vamseeachanta/worldenergydata
- Issue #337: citation quality and automated ingestion contracts for annual disclosures
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

A contract-first enhancement in `worldenergydata.cost.data_collection` that standardizes row-level citation/provenance requirements and defines a future annual-disclosure ingestion contract, including validation outcomes and duplicate/conflict handling, without implementing automated ingestion itself.

---

## Scope Boundaries

### In scope now
- Define minimum row-level citation requirements
- Define source-priority hierarchy for future ingest
- Define ingest-contract rules for required fields, validation outcomes, duplicate detection key, and conflict behavior
- Add tests for citation completeness and failure modes
- Keep work inside `cost.data_collection`

### Explicitly out of scope for this issue
- Scraper/parser/SEC/XBRL implementation
- Broad dataset backfill
- Downstream analytics or economics integration
- Currency normalization or linkage redesign
- Package-root API expansion

---

## Pseudocode

```text
function validate_citation(row):
    require source_title
    require source_url
    require page_reference
    require quoted_text
    require confidence
    require absolute source_url
    return validated row

function ingestion_business_key(row):
    return (operator, fiscal_year, scope, normalized_metric_name, optional project_name)

function classify_ingest(existing_rows, new_row):
    if same business_key and same value/citation payload: duplicate
    elif same business_key and different value/citation payload: conflict
    else: new

function ingest_contract(raw_rows):
    validate required disclosure fields
    validate citation contract
    partition rows into accepted, duplicate, conflict, invalid
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Modify | `src/worldenergydata/cost/data_collection/calibration_schema.py` | add or host reusable provenance/citation validators and ingest-contract primitives |
| Modify | `src/worldenergydata/cost/data_collection/public_dataset.py` | align representative source rows/docs with stricter provenance contract if needed |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export new contract primitives from existing boundary |
| Modify | `tests/unit/cost/test_calibration_schema.py` | validator tests for citation completeness and failures |
| Modify | `tests/unit/cost/test_dataset_size.py` | dataset-level provenance and duplicate/conflict guardrails |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_source_string_alone_is_not_enough_for_disclosure_ingest_contract` | freeform provenance is insufficient | legacy-like row | validation failure |
| `test_citation_contract_requires_title_url_page_quote_and_confidence` | minimum citation fields are mandatory | missing fields | validation failure |
| `test_citation_contract_rejects_blank_fields` | whitespace-only values fail | blank citation values | validation failure |
| `test_citation_contract_requires_absolute_source_url` | malformed URLs fail | relative/invalid URL | validation failure |
| `test_confidence_must_use_declared_enum` | confidence stays typed | invalid confidence | validation failure |
| `test_source_priority_values_are_explicit_and_ordered` | ingest can reason about preferred source classes | priority enum/order | deterministic contract |
| `test_duplicate_detection_returns_duplicate_for_identical_payload` | exact duplicates are recognized | same business key + same payload | duplicate |
| `test_conflict_detection_returns_conflict_for_same_business_key_different_value` | conflicting values surface | same key, different value | conflict |
| `test_conflict_detection_returns_conflict_for_same_business_key_different_citation` | citation disagreement surfaces | same key, different citation | conflict |
| `test_ingest_contract_returns_partitioned_result_sets` | ingest outcome is structured | mixed rows | accepted/duplicate/conflict/invalid |

---

## Acceptance Criteria

- [ ] Reusable citation/provenance contract exists in `worldenergydata.cost.data_collection`
- [ ] Contract requires row-level `source_title`, `source_url`, `page_reference`, `quoted_text`, and `confidence`
- [ ] Source-priority hierarchy is explicitly defined
- [ ] Duplicate and conflict handling behavior is explicitly defined and unit-tested
- [ ] Tests cover both success and rejection cases for citation validation
- [ ] Existing sanction-dataset tests continue to pass unchanged
- [ ] Work remains contract-definition only; no automation implementation is added

---

## Risks and Open Questions

- Current repo only has freeform `source`, so there is a schema-shape gap to bridge carefully.
- Need to decide whether citation validators belong directly on current cost schema objects or a disclosure-specific contract.
- Duplicate business keys depend on annual-disclosure fields that do not yet exist in current code, so this issue must stay contract-first.

---

## Complexity: T2

**T2** — moderate because file count is small but the contract must be precise enough to support later automation without accidentally implementing it now.
