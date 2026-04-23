# Plan for #343: major-operator annual statement source registry and yearly coverage tracker

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-23
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/343
> **Review artifacts:** scripts/review/results/2026-04-23-plan-343-codex.md | scripts/review/results/2026-04-23-plan-343-gemini.md

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
- Adversarial review artifacts:
  - `scripts/review/results/2026-04-23-plan-343-codex.md`
  - `scripts/review/results/2026-04-23-plan-343-gemini.md`

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
| Codex review artifact | `scripts/review/results/2026-04-23-plan-343-codex.md` |
| Gemini review artifact | `scripts/review/results/2026-04-23-plan-343-gemini.md` |

---

## Deliverable

An additive, machine-readable registry of major operators and their annual-statement discovery surfaces, using a fixed seed operator set and a fixed 2020–2024 operator-year coverage window, with typed filing-channel metadata, explicit operator-year status semantics (`verified`, `missing`, `known_unavailable`), validation tests, and enough metadata for future annual disclosure backfill work to discover and track statement availability year over year.

---

## Scope Boundaries

### In scope now
- Define a typed registry contract for operator annual-statement sources and yearly coverage metadata.
- Seed this exact initial operator set, bounded to names already represented in the current cost evidence base:
  - BP
  - Chevron
  - Shell
  - Equinor
  - Aker BP
  - TotalEnergies
  - ExxonMobil
  - Murphy Oil
  - Hess
- Track year coverage at the operator-year level, not the per-channel-year level, using this fixed vocabulary:
  - `verified` = at least one primary annual-statement source URL for that operator-year has been manually verified and recorded in the registry
  - `missing` = the operator-year is within the bounded seed window but no qualifying source has yet been verified
  - `known_unavailable` = the operator-year is intentionally recorded as not publicly available or not found after bounded manual review
- Bound the initial year-coverage window to fiscal years 2020–2024 only; broader historical backfill is out of scope.
- Represent filing channels as a typed list drawn from this fixed allowed set:
  - `annual_report`
  - `sec_10k`
  - `sec_20f`
  - `investor_relations`
  - `sustainability_report`
- Track per-operator discovery metadata: investor-relations / annual-report landing page, filing-channel list, URL pattern/discovery notes, earliest covered year, latest verified year, and operator-year coverage status map.
- Add validation tests to ensure registry completeness and stable required fields.
- Document how downstream ingestion/backfill workflows should consume the registry.

### Explicitly out of scope for this issue
- Downloading or scraping every annual report automatically
- Parsing annual reports into disclosure rows
- FX normalization and comparability policy (#336)
- Restatement/version lineage (#344)
- Consumer-facing dashboards or benchmark products
- Broad historical backfill outside the bounded 2020–2024 seed window

---

## Pseudocode

```text
define typed registry row with:
    canonical_operator_name
    primary_landing_page_url
    filing_channels: list[allowed channel enum values]
    discovery_notes
    earliest_covered_year
    latest_verified_year
    coverage_by_year: dict[int, coverage_status enum]
for each seeded operator in the fixed initial set:
    record annual-report / investor-relations source metadata
    record bounded 2020-2024 operator-year coverage statuses
validate registry rows for required fields, bounded filing-channel values, absolute URLs, and bounded status vocabulary
expose loader/accessor for future ingest workflows
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/data_collection/operator_statement_registry.py` | machine-readable registry contract + seed data |
| Modify | `src/worldenergydata/cost/data_collection/__init__.py` | export registry loader/types |
| Create | `tests/unit/cost/test_operator_statement_registry.py` | validate required fields, coverage map shape, bounded vocabulary, and exact seed operator set |
| Create | `docs/research/annual-statement-source-registry.md` | operator-facing usage note for future disclosure backfill workflows |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_registry_loader_returns_seed_rows` | registry is loadable and non-empty | no input | seeded rows |
| `test_registry_uses_exact_seed_operator_set` | initial scope is exact and bounded | loaded registry | exact expected operator set |
| `test_registry_rows_require_discovery_fields` | required source metadata is present | each row | valid required fields |
| `test_registry_tracks_year_coverage_bounds` | earliest/latest year align with year-status map | each row | consistent bounds |
| `test_registry_coverage_status_values_are_bounded` | per-year statuses stay machine-usable | year map | only `verified`, `missing`, `known_unavailable` |
| `test_registry_year_window_is_bounded_to_2020_2024` | historical scope cannot silently expand | coverage map | only years 2020–2024 |
| `test_registry_filing_channels_are_bounded` | filing channel plurality is typed and constrained | channel list | allowed values only |
| `test_registry_urls_are_absolute_http_sources` | discovery links are valid web sources | row URLs | absolute http(s) |
| `test_registry_notes_do_not_replace_required_urls` | notes are additive, not substitutes | rows with notes | required URLs still present |
| `test_registry_operator_names_are_unique` | canonical naming avoids duplicate operator rows | loaded registry | unique operator names |

---

## Acceptance Criteria

- [ ] A machine-readable annual-statement source registry exists for exactly the nine seeded operators listed in this plan
- [ ] Registry rows include typed filing-channel metadata and bounded operator-year coverage statuses
- [ ] Coverage tracking is explicitly defined at the operator-year level for the 2020–2024 seed window
- [ ] Validation tests cover required fields, URL shape, bounded filing-channel values, bounded status vocabulary, exact seed set, and coverage-map consistency
- [ ] Documentation exists at `docs/research/annual-statement-source-registry.md` and explains how future ingestion/backfill issues should use the registry

---

## Risks and Open Questions

- The initial operator-year semantics intentionally collapse multiple filing channels into one operator-year status; future work may need a lower-level channel-year inventory if operational needs grow.
- Some operators publish annual reports across IR, SEC, and sustainability channels; this issue records channel metadata but does not attempt full cross-channel coverage auditing.
- Broad historical backfill and automated report discovery remain deliberately deferred.

---

## Complexity: T2

**T2** — bounded data-contract and seed-registry work, provided the issue remains focused on durable source tracking rather than live scraping or broad historical backfill.
