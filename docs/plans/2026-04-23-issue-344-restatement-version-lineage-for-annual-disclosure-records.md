# Plan for #344: restatement/version lineage for annual disclosure records

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-04-23
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/344
> **Review artifacts:** scripts/review/results/2026-04-23-plan-344-codex.md | scripts/review/results/2026-04-23-plan-344-gemini.md

---

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` currently models disclosure rows with a single citation block and business-key conflict classification, but it has no fields for revision identity, supersession lineage, or amended-statement handling.
- `src/worldenergydata/cost/disclosure_analytics.py` currently builds simple year-over-year views and assumes one effective raw record per operator/project/year grouping. It does not distinguish original versus revised disclosure rows.
- `src/worldenergydata/cost/data_collection/__init__.py` currently exports disclosure ingest and linkage primitives only; no versioning/restatement contract exists.

### Documents and issues consulted
- Issue #344 body
- #334 scope note excluding restatements/versioning from the v1 disclosure foundation
- #337 ingest-contract implementation
- #338 disclosure analytics implementation
- Adversarial review artifacts:
  - `scripts/review/results/2026-04-23-plan-344-codex.md`
  - `scripts/review/results/2026-04-23-plan-344-gemini.md`

### Gaps identified
- No additive schema exists for disclosure revision identity or supersession lineage.
- No ingest behavior is defined for how amended disclosures should coexist with original records.
- No analytics rule distinguishes current-effective values from historical/original values when revisions exist.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-23-issue-344-restatement-version-lineage-for-annual-disclosure-records.md` |
| Current disclosure ingest contract | `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` |
| Current disclosure exports | `src/worldenergydata/cost/data_collection/__init__.py` |
| Current derived analytics | `src/worldenergydata/cost/disclosure_analytics.py` |
| Current ingest contract tests | `tests/unit/cost/test_disclosure_ingest_contract.py` |
| Current analytics tests | `tests/unit/cost/test_disclosure_analytics.py` |
| Codex review artifact | `scripts/review/results/2026-04-23-plan-344-codex.md` |
| Gemini review artifact | `scripts/review/results/2026-04-23-plan-344-gemini.md` |

---

## Deliverable

An additive disclosure versioning/restatement contract in a dedicated companion module that allows original and revised annual-statement records to coexist with explicit append-only lineage, clear ingest semantics, and explicit analytics APIs for current-effective versus historical rows, without overwriting the original evidence trail.

---

## Scope Boundaries

### In scope now
- Create a dedicated companion module for revision/restatement semantics:
  - `src/worldenergydata/cost/data_collection/disclosure_revision_contract.py`
- Define a concrete revision metadata contract with this minimum shape:
  - `logical_disclosure_key: str` — stable identity shared by all versions of the same logical disclosure point
  - `version_id: str` — unique identity for one specific version
  - `supersedes_version_id: Optional[str]` — append-only pointer to the immediately prior version; no `superseded_by` field in v1
  - `publication_date: date` — required for revised rows, optional for original rows if unavailable
  - `effective_date: Optional[date]` — optional override when the filing explicitly states a different effective date
  - `revision_classification: Literal['original','amended','restated']`
- Define nullability/consistency rules:
  - original rows: must have `logical_disclosure_key`, `version_id`, `revision_classification='original'`, and no `supersedes_version_id`
  - amended/restated rows: must have `logical_disclosure_key`, `version_id`, non-null `supersedes_version_id`, and `revision_classification in {'amended','restated'}`
- Define the explicit distinction between identity layers:
  - `disclosure_business_key` remains the raw business grouping used by the existing ingest contract
  - `logical_disclosure_key` groups multiple versions of the same disclosure point across revisions
  - version-aware ingest must branch on `logical_disclosure_key`/`version_id` before applying duplicate/conflict semantics
- Define append-only ingest behavior:
  - original rows are preserved
  - revised rows append new versions and point backward via `supersedes_version_id`
  - non-revision rows continue through the existing ingest path unchanged
- Define analytics APIs explicitly in `src/worldenergydata/cost/disclosure_analytics.py`:
  - `load_current_effective_disclosure_rows(...)`
  - `load_disclosure_revision_history(...)`
- Define current-effective precedence explicitly:
  1. highest reachable version within a lineage chain
  2. if competing candidates remain, later `effective_date`
  3. then later `publication_date`
  4. then deterministic lexical tie-break on `version_id`
- Add tests that prove original and revised records can coexist and remain auditable.

### Explicitly out of scope for this issue
- Full-scale backfill of historical restatements across many operators
- Automated amended-filing discovery pipelines
- Currency normalization/comparability rules from #336
- Building dashboards or UI products for revision browsing
- Broad rewrites of existing non-revision duplicate/conflict semantics beyond the version-aware branch needed for revised rows

---

## Pseudocode

```text
create disclosure_revision_contract.py

def validate_revision_metadata(row):
    enforce required fields by revision_classification
    allow only backward pointer supersedes_version_id
    reject inconsistent original/amended/restated combinations

when ingesting a disclosure row:
    if row has no revision metadata:
        route through existing #337 ingest behavior unchanged
    else:
        group by logical_disclosure_key
        append new version by version_id
        link backward via supersedes_version_id
        bypass plain duplicate/conflict collapse for valid lineage-linked revisions

for analytics:
    load_current_effective_disclosure_rows(...) selects one row per logical_disclosure_key
        using lineage chain, then effective_date, then publication_date, then version_id
    load_disclosure_revision_history(...) returns the full ordered version trail
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/disclosure_revision_contract.py` | add typed revision/restatement metadata and append-only ingest semantics |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export the revision/restatement surface |
| Modify minimally | `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` | integrate version-aware branching while preserving non-revision behavior |
| Modify | `src/worldenergydata/cost/disclosure_analytics.py` | add explicit current-effective and revision-history APIs |
| Create | `tests/unit/cost/test_disclosure_revision_contract.py` | validate revision schema, lineage, and ingest branching |
| Modify | `tests/unit/cost/test_disclosure_analytics.py` | add analytics behavior coverage for revised rows |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_original_revision_metadata_requires_expected_fields` | original-row schema is concrete | original row metadata | valid contract |
| `test_revised_revision_metadata_requires_backward_pointer` | amended/restated rows require append-only linkage | revised metadata missing `supersedes_version_id` | validation error |
| `test_original_and_revised_rows_can_coexist` | revisions do not overwrite originals | original + revised rows | both preserved |
| `test_version_aware_ingest_bypasses_plain_duplicate_collapse` | revised rows are not treated as plain duplicates | revised row with same business key | version-aware branch |
| `test_non_revision_rows_follow_existing_ingest_behavior` | additive change does not break current contract | ordinary row | existing behavior unchanged |
| `test_current_effective_selector_uses_defined_precedence` | selector precedence is deterministic | multiple versions in one lineage | expected chosen row |
| `test_revision_history_returns_full_ordered_lineage` | audit history is preserved | multiple versions | ordered lineage trail |
| `test_bidirectional_linkage_is_not_required` | v1 stays append-only-safe | revised row with only backward pointer | valid |
| `test_logical_disclosure_key_is_distinct_from_business_key` | identity layers are explicit | rows sharing business key across versions | stable logical grouping |

---

## Acceptance Criteria

- [ ] A dedicated module `src/worldenergydata/cost/data_collection/disclosure_revision_contract.py` exists and defines the revision metadata contract
- [ ] The revision schema fixes required fields, nullability, and allowed combinations for `original`, `amended`, and `restated` rows
- [ ] Version-aware ingest uses `logical_disclosure_key` / `version_id` / `supersedes_version_id` to preserve originals and append revisions
- [ ] Existing non-revision ingest behavior remains unchanged for ordinary rows
- [ ] `src/worldenergydata/cost/disclosure_analytics.py` exposes explicit APIs for current-effective rows and revision-history rows
- [ ] Current-effective selection precedence is deterministic and test-covered
- [ ] Revision lineage is append-only and does not require bidirectional linkage in v1

---

## Risks and Open Questions

- Future work may still need richer graph semantics if operators publish parallel competing amendments, but v1 intentionally uses a backward-pointer chain to keep ingest append-only and deterministic.
- Current-effective selection may need stronger domain rules later if real filings expose more nuanced revision timing; this issue fixes only the first deterministic precedence contract.
- This work should ideally follow broader source-registry and raw-disclosure maturation so version semantics are attached to a stable raw record shape.

---

## Complexity: T3

**T3** — schema, ingest branching, and analytics API behavior all need coordinated additive changes, and careless design could break duplicate/conflict semantics from #337 or YoY analytics assumptions from #338.
