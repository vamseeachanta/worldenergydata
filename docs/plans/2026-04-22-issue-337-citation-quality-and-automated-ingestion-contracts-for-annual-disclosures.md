# Plan for #337: citation quality and automated ingestion contracts for annual disclosures

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-22
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/337
> **Review artifacts:** scripts/review/results/2026-04-22-plan-337-codex.md | scripts/review/results/2026-04-22-plan-337-gemini.md

---

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/cost/data_collection/public_dataset.py` is the current sanction dataset and preserves provenance only as a freeform `source` string plus `confidence`; it is not the right primary target for annual-disclosure ingestion contracts.
- `src/worldenergydata/cost/data_collection/calibration_schema.py` is a sanction-point schema surface and does not model annual-disclosure fields such as `fiscal_year`, `scope`, `source_title`, `source_url`, `page_reference`, or `quoted_text`.
- Parent plan `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md` defines the disclosure-layer boundary and names the future disclosure-specific files:
  - `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py`
  - `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py`
  - `tests/unit/cost/test_operator_disclosures.py`
- `src/worldenergydata/cost/data_collection/__init__.py` is the correct data-collection export surface once disclosure-specific contract helpers exist.
- `tests/unit/cost/test_calibration_schema.py` and `tests/unit/cost/test_proxy_comparison.py` are regression boundaries that should remain unchanged; #337 must not retrofit the sanction dataset to satisfy annual-disclosure citation rules.

### Documents consulted
- Issue #337 — citation quality requirements and future ingestion contract for annual operator disclosures.
- Parent issue #334 and approved plan — row-level provenance is required for annual disclosures, but automation implementation is deferred.
- Review artifacts `scripts/review/results/2026-04-22-plan-337-codex.md` and `...-gemini.md` — both MAJOR reviews agreed the prior draft was mis-grounded because it targeted sanction files instead of disclosure-layer files and would force forbidden backfill in `public_dataset.py`.

### Gaps identified
- No disclosure-specific citation/provenance validator exists yet.
- No disclosure-specific ingest contract exists for annual disclosure rows.
- No duplicate/conflict classification contract exists for annual disclosure ingest.
- No tests currently prove annual-disclosure citation quality is enforceable on disclosure-layer surfaces.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-22-issue-337-citation-quality-and-automated-ingestion-contracts-for-annual-disclosures.md` |
| Parent disclosure schema target | `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py` |
| Parent disclosure dataset target | `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py` |
| Data-collection export surface | `src/worldenergydata/cost/data_collection/__init__.py` |
| Disclosure contract module (new) | `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` |
| Disclosure contract tests (new) | `tests/unit/cost/test_disclosure_ingest_contract.py` |
| Parent disclosure tests | `tests/unit/cost/test_operator_disclosures.py` |
| Sanction-dataset regression boundary | `tests/unit/cost/test_calibration_schema.py` |
| Sanction-calibration regression boundary | `tests/unit/cost/test_proxy_comparison.py` |

---

## Deliverable

A disclosure-layer contract module in `worldenergydata.cost.data_collection` that standardizes row-level citation/provenance requirements and defines how annual operator disclosure rows are validated and classified as accepted, duplicate, conflict, or invalid during future ingest, without modifying the legacy sanction dataset or implementing scraper/XBRL automation.

---

## Scope Boundaries

### In scope now
- Define minimum row-level citation requirements for disclosure rows:
  - `source_title`
  - `source_url`
  - `page_reference`
  - `quoted_text`
  - `confidence`
- Define source-priority hierarchy for annual disclosure ingest
- Define annual-disclosure ingest contract rules for:
  - required fields
  - validation outcomes
  - duplicate detection key
  - conflict detection behavior
- Add tests for citation completeness, source-priority behavior, and duplicate/conflict classification
- Keep the work on disclosure-layer files and helpers only

### Explicitly out of scope for this issue
- Any modification of the legacy sanction dataset in `public_dataset.py`
- Any widening of `CostDataPoint` / `calibration_schema.py` to annual-disclosure citation fields
- Scraper/parser/SEC/XBRL implementation
- Broad historical backfill or citation retrofitting across sanction records
- Downstream analytics or economics integration
- Currency normalization or linkage redesign
- Package-root API expansion outside `worldenergydata.cost.data_collection`

### Dependency boundary
- This issue depends on #334 landing the disclosure-layer schema/dataset surface first.
- #337 defines disclosure ingest/citation contracts on top of that disclosure boundary.
- #337 must not re-open or replace the parent disclosure schema; it adds validation/classification contracts around it.

---

## Pseudocode

```text
class SourcePriority(Enum):
    OPERATOR_ANNUAL_REPORT
    SEC_FILING
    REGULATOR_DOCUMENT
    INVESTOR_PRESENTATION
    PRESS_RELEASE
    SECONDARY_OPERATOR_CONFIRMED

class DisclosureIngestStatus(Enum):
    ACCEPTED
    DUPLICATE
    CONFLICT
    INVALID

function validate_disclosure_citation(row):
    require source_title
    require source_url
    require page_reference
    require quoted_text
    require confidence
    require absolute http/https source_url
    return validated row

function disclosure_business_key(row):
    return (
        row.operator,
        row.fiscal_year,
        row.scope_type,
        row.normalized_metric_name,
        optional row.project_name,
    )

function classify_disclosure_row(existing_rows, new_row):
    if same business_key and same value/citation payload:
        return DUPLICATE
    if same business_key and different value or citation payload:
        return CONFLICT
    return ACCEPTED

function ingest_contract(raw_rows, existing_rows):
    validate required disclosure fields
    validate citation contract
    classify each row as accepted/duplicate/conflict/invalid
    return partitioned result with reasons
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` | dedicated disclosure-only citation/provenance and ingest classification contract |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export new disclosure contract primitives from the existing data-collection boundary |
| Verify dependency only | `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py` | parent-owned disclosure schema surface that this issue builds on |
| Verify dependency only | `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py` | parent-owned disclosure dataset surface that this issue validates/classifies |
| Create | `tests/unit/cost/test_disclosure_ingest_contract.py` | direct TDD coverage for citation completeness, source priority, duplicate/conflict behavior |
| Verify dependency only | `tests/unit/cost/test_operator_disclosures.py` | parent disclosure test surface should remain compatible |
| Verify only | `tests/unit/cost/test_calibration_schema.py` | sanction-schema behavior remains unchanged |
| Verify only | `tests/unit/cost/test_proxy_comparison.py` | sanction-calibration behavior remains unchanged |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_citation_contract_requires_title_url_page_quote_and_confidence` | disclosure citation minimum is mandatory | missing citation fields | invalid result |
| `test_citation_contract_rejects_blank_fields` | whitespace-only values fail | blank citation values | invalid result |
| `test_citation_contract_requires_absolute_http_source_url` | malformed or unsupported URLs fail | relative/non-http URL | invalid result |
| `test_confidence_must_use_declared_enum` | confidence remains typed | invalid confidence | invalid result |
| `test_source_priority_values_are_explicit_and_ordered` | source priority is deterministic | source priority enum | expected order |
| `test_duplicate_classification_for_identical_business_key_and_payload` | exact duplicates are recognized | same key + same payload | duplicate |
| `test_conflict_classification_for_same_business_key_different_value` | value conflicts surface | same key + different value | conflict |
| `test_conflict_classification_for_same_business_key_different_citation` | citation conflicts surface | same key + different citation | conflict |
| `test_ingest_contract_returns_partitioned_result_sets` | ingest result is structured | mixed rows | accepted/duplicate/conflict/invalid |
| `test_source_priority_affects_conflict_reasoning` | priority order is not just decorative | conflicting higher/lower priority rows | deterministic conflict annotation |
| `test_parent_disclosure_surface_remains_compatible` | contract fits the disclosure-layer schema rather than sanction schema | disclosure row shape | valid contract behavior |
| `test_legacy_sanction_schema_is_unchanged` | #337 does not contaminate sanction schema | current sanction schema path | unchanged behavior |

---

## Acceptance Criteria

- [ ] Disclosure-specific citation/provenance contract exists in `worldenergydata.cost.data_collection`
- [ ] Contract requires disclosure-row `source_title`, `source_url`, `page_reference`, `quoted_text`, and `confidence`
- [ ] Source-priority hierarchy is explicitly defined and affects conflict reasoning deterministically
- [ ] Duplicate and conflict handling behavior is explicitly defined and unit-tested on disclosure-layer rows
- [ ] Tests cover both success and rejection cases for citation validation
- [ ] #337 does not require modifying `public_dataset.py` or widening `CostDataPoint` to annual-disclosure fields
- [ ] Sanction-schema and sanction-calibration regression tests continue to pass unchanged
- [ ] Work remains contract-definition only; no automation implementation or historical backfill is added

---

## Risks and Open Questions

- #337 depends on #334 disclosure files landing first; until then this plan is a dependent child plan, not immediately executable.
- Need to define how conflict reasons are encoded in the ingest result (enum, string code, structured payload) without over-designing the future ingestion pipeline.
- Need to decide whether source-priority affects only conflict annotation or also final row selection in future automation; this issue should keep that behavior explicit and bounded.
- Web-native disclosures may use non-page locators (section/table identifiers), so `page_reference` should be treated as a general locator field, not strictly a PDF page number.

---

## Complexity: T2

**T2** — moderate because the work is contract-heavy rather than code-heavy, but it is now correctly anchored to the disclosure-layer boundary instead of the legacy sanction dataset surface.
