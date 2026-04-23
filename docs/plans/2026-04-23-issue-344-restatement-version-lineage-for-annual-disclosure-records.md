# Plan for #344: restatement/version lineage for annual disclosure records

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-04-23
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/344
> **Review artifacts:** pending

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

---

## Deliverable

An additive disclosure versioning/restatement contract that allows original and revised annual-statement records to coexist with explicit lineage, clear ingest semantics, and explicit analytics rules for current-effective versus historical rows, without overwriting the original evidence trail.

---

## Scope Boundaries

### In scope now
- Define typed revision/restatement metadata for annual disclosure rows
- Represent original-versus-revised relationships explicitly (`version_id`, `supersedes`, `superseded_by`, publication/effective dates, revision classification)
- Define ingest behavior for accepting a revised row without destroying the original record
- Define analytics behavior for year-over-year views when multiple versions exist for the same logical disclosure point
- Add tests that prove original and revised records can coexist and remain auditable

### Explicitly out of scope for this issue
- Full-scale backfill of historical restatements across many operators
- Automated amended-filing discovery pipelines
- Currency normalization/comparability rules from #336
- Building dashboards or UI products for revision browsing

---

## Pseudocode

```text
define additive revision metadata contract for disclosure rows
when ingesting a disclosure row:
    if no revision metadata:
        treat as original/current row under existing rules
    if revision metadata present:
        preserve original row
        attach explicit lineage links between versions
        mark effective/current semantics without deleting prior evidence
for derived analytics:
    expose rule to choose current-effective row per logical key
    preserve access to historical/original rows for audit views
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Modify or create | `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` or a new companion module | add typed revision/restatement metadata and ingest semantics |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export new versioning/restatement surface |
| Modify | `src/worldenergydata/cost/disclosure_analytics.py` | define current-effective versus historical row handling |
| Modify | `tests/unit/cost/test_disclosure_ingest_contract.py` | add revision-lineage ingest coverage |
| Modify | `tests/unit/cost/test_disclosure_analytics.py` | add analytics behavior coverage for revised rows |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_original_and_revised_rows_can_coexist` | revisions do not overwrite originals | original + revised rows | both preserved |
| `test_revision_metadata_requires_consistent_lineage_fields` | lineage contract is structurally valid | partial revision metadata | validation error |
| `test_ingest_marks_revised_rows_as_superseding_without_deleting_original` | ingest semantics preserve audit trail | original + revised row | explicit lineage |
| `test_current_effective_selector_prefers_latest_revision` | analytics can choose current-effective row | multiple versions same logical row | latest effective row |
| `test_historical_view_retains_original_row` | auditability is preserved | multiple versions | original still queryable |
| `test_revision_conflicts_do_not_collapse_into_plain_duplicate` | version-aware ingest differs from current duplicate logic | revised row with same business key | version-aware classification |
| `test_non_revision_rows_follow_existing_ingest_behavior` | additive change does not break current contract | ordinary row | existing behavior unchanged |

---

## Acceptance Criteria

- [ ] Disclosure contract can represent original and revised annual-statement rows distinctly
- [ ] Ingest semantics preserve original evidence instead of silently overwriting it
- [ ] Analytics behavior for current-effective versus historical rows is explicit and test-covered
- [ ] Existing non-revision ingest behavior remains unchanged for ordinary rows
- [ ] Revision lineage fields are documented and exported cleanly

---

## Risks and Open Questions

- Current `disclosure_business_key` and conflict-reason logic in #337 may need a companion logical-key concept so revisions are not misclassified as plain duplicates/conflicts.
- Analytics may need both a current-effective selector and a full-history selector; collapsing both into one view would hide auditability.
- This work should ideally follow broader source-registry and raw-disclosure maturation so version semantics are attached to a stable raw record shape.

---

## Complexity: T3

**T3** — schema, ingest, and analytics behavior all need coordinated additive changes, and careless design could break duplicate/conflict semantics from #337 or YoY analytics assumptions from #338.
