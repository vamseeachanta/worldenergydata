# Plan for #343: major-operator annual statement source registry and yearly coverage tracker

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-23
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/343
> **Review artifacts:** pending

---

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/cost/data_collection/public_dataset.py` already cites operator annual reports, SEC filings, regulator documents, and operator announcements as sanction-data provenance, but it stores those citations as freeform strings embedded per project datapoint.
- `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` defines row-level disclosure provenance fields (`source_title`, `source_url`, `page_reference`, `quoted_text`, `confidence`, `source_priority`) but does not provide an operator-level source registry or year coverage tracker.
- `src/worldenergydata/cost/disclosure_analytics.py` provides derived year-over-year views once raw records exist, but it assumes input records are already sourced and available.

### Documents and issues consulted
- Issue #343 body
- Parent/foundation issues #334, #337, #338
- Existing sanction dataset source inventory embedded in `public_dataset.py`

### Gaps identified
- No machine-readable operator source registry exists for annual statements, filing channels, or year coverage.
- No durable structure tracks which fiscal years have verified annual statements per operator.
- No registry-level validation exists to keep annual-statement discovery reproducible over time.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-23-issue-343-major-operator-annual-statement-source-registry-and-yearly-coverage-tracker.md` |
| Existing sanction source evidence | `src/worldenergydata/cost/data_collection/public_dataset.py` |
| Existing disclosure provenance contract | `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py` |
| Existing derived YoY analytics | `src/worldenergydata/cost/disclosure_analytics.py` |

---

## Deliverable

An additive, machine-readable registry of major operators and their annual-statement discovery surfaces, including bounded seed coverage by fiscal year, validation tests, and enough metadata for future annual disclosure backfill work to discover and track statement availability year over year.

---

## Scope Boundaries

### In scope now
- Define a typed registry contract for operator annual-statement sources and yearly coverage metadata
- Seed a bounded high-value operator set already represented in the cost evidence base (for example BP, Chevron, Shell, Equinor, Aker BP, TotalEnergies, ExxonMobil, Murphy Oil, Hess)
- Track per-operator discovery metadata: investor-relations / annual-report landing page, filing channels, URL pattern/discovery notes, earliest covered year, latest verified year, and per-year coverage status
- Add validation tests to ensure registry completeness and stable required fields
- Document how downstream ingestion/backfill workflows should consume the registry

### Explicitly out of scope for this issue
- Downloading or scraping every annual report automatically
- Parsing annual reports into disclosure rows
- FX normalization and comparability policy (#336)
- Restatement/version lineage (#344)
- Consumer-facing dashboards or benchmark products

---

## Pseudocode

```text
define typed registry row for operator annual-statement source metadata
for each seeded operator:
    record canonical operator name
    record primary annual-report / investor-relations source
    record filing channels and discovery notes
    record earliest/latest verified fiscal year
    record per-year coverage status map
validate registry rows for required fields and bounded status vocabulary
expose loader/accessor for future ingest workflows
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/operator_statement_registry.py` | machine-readable registry contract + seed data |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export registry loader/types |
| Create | `tests/unit/cost/test_operator_statement_registry.py` | validate required fields, coverage map shape, and seed operator set |
| Create or modify | `docs/research/fdas-quick-reference.md` or a new nearby cost/disclosure doc | short operator-facing usage note for future backfill workflows |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_registry_loader_returns_seed_rows` | registry is loadable and non-empty | no input | seeded rows |
| `test_registry_rows_require_discovery_fields` | required source metadata is present | each row | valid required fields |
| `test_registry_tracks_year_coverage_bounds` | earliest/latest year align with year-status map | each row | consistent bounds |
| `test_registry_coverage_status_values_are_bounded` | per-year statuses stay machine-usable | year map | allowed vocabulary only |
| `test_registry_includes_high_value_operator_seed_set` | initial scope is meaningful | loaded registry | expected operator subset present |
| `test_registry_urls_are_absolute_http_sources` | discovery links are valid web sources | row URLs | absolute http(s) |
| `test_registry_notes_do_not_replace_required_urls` | notes are additive, not substitutes | rows with notes | required URLs still present |

---

## Acceptance Criteria

- [ ] A machine-readable annual-statement source registry exists for a bounded major-operator set
- [ ] Registry rows include stable discovery metadata and year coverage information
- [ ] Per-year coverage status is explicit enough to support year-over-year tracking
- [ ] Validation tests cover required fields, URL shape, and coverage-map consistency
- [ ] Documentation explains how future ingestion/backfill issues should use the registry

---

## Risks and Open Questions

- Need to choose a coverage-status vocabulary that is specific enough for operations (`verified`, `missing`, `known-unavailable`, etc.) without overfitting future automation.
- Some operators publish annual reports across different IR, SEC, and sustainability channels; the registry should capture that plurality without becoming a full crawler specification.
- Seed scope must stay bounded; broad historical backfill belongs to later execution issues.

---

## Complexity: T2

**T2** — bounded data-contract and seed-registry work, provided the issue remains focused on durable source tracking rather than live scraping or broad historical backfill.
