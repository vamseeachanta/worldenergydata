# Plan for #376: cross-field analytics — technology, operator, HSE, cost benchmarking

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-05-03
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/376
> **Parent epic:** https://github.com/vamseeachanta/worldenergydata/issues/373
> **Depends on:** #375 (per-field economics provides the comparison baseline)

---

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/lower_tertiary/production_classifier.py` already classifies wells by dev system; reusable.
- `src/worldenergydata/marine_safety/cross_database.py` shows the pattern for cross-cutting analytics — consume per-field results and emit aggregated views.
- `src/worldenergydata/fdas/api.py:DisclosureAnalyticsQuery` — `benchmark()`, `operator_capex()`, `project_revision()` already shipped via #338. Returns `None` unless comparable disclosures exist.
- `src/worldenergydata/hse/` — incident database; query API not yet exposed (tracked under #363). Phase 3 must work with what's available.
- `reports/lower_tertiary_field_summary.md:"Production by Development System"` already breaks down by Subsea 15K / Tieback 15K / Dry Tree / Subsea 20K — useful baseline for technology-generation analysis.

### Documents and issues consulted
- Issue #376 body
- Parent epic #373
- Predecessor: #375 per-field economics
- HSE substrate: #366 (HSE bulk dedup + ingest)
- Disclosure surface: #338 (analytics views)
- Operator registry companion: #343

### Gaps identified
- HSE incident data per field requires either (a) #366 to land first, or (b) a minimum-viable version using current BSEE-incidents-in-repo. Phase 3 must explicitly state which version is being delivered.
- Cost benchmarking via #338 needs operators with disclosure records. Major LT operators (Chevron, Shell, BP, Equinor, TotalEnergies) are the seed set for #343 but coverage is sparse for LT-specific projects.
- "Operator concentration" is meaningful at portfolio level; current code computes per-field metrics in isolation.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-05-03-issue-376-cross-field-analytics-lt.md` |
| New module | `src/worldenergydata/lower_tertiary/portfolio_analytics.py` |
| Tests | `tests/unit/lower_tertiary/test_portfolio_analytics.py` |
| Output (technology) | `results/lower_tertiary/technology_generation_2026.csv` |
| Output (operator) | `results/lower_tertiary/operator_concentration_2026.csv` |
| Output (HSE) | `results/lower_tertiary/hse_per_field_2026.csv` |
| Output (cost benchmark) | `results/lower_tertiary/cost_benchmark_2026.csv` |
| Pattern reference | `src/worldenergydata/marine_safety/cross_database.py` |

---

## Deliverable

`PortfolioAnalytics` API + CLI producing four cross-cutting analyses in CSV form, ready for inclusion in the Phase 4 report. Each analysis emits a citations + caveats sidecar so missing inputs (e.g., #366 not yet landed) are explicit, not silently elided.

---

## Scope Boundaries

### In scope now
- **3a. Technology generation** — group fields by dev system, compute capex intensity ($M / MMbbl recoverable using yaml `capex.total_mm_usd` / yaml `production_profile`), time-to-first-oil from yaml `first_oil`, comparison table.
- **3b. Operator concentration** — working-interest-weighted production using yaml `partners` × per-field cum production, HHI, top-3 concentration share.
- **3c. HSE incident overlay (minimum-viable version)** — use BSEE current incidents data already in-repo; per-field incident counts and severities. Tag the output `data_completeness: minimum_viable` and reference #366 as the path to full coverage.
- **3d. Cost benchmark** — for each LT field, look up the operator's annual disclosures via `DisclosureAnalyticsQuery.benchmark`. Where the result is `None` (no comparable disclosure), record `benchmark_status: no_data` rather than dropping the field.
- All four analyses share a single `PortfolioAnalyticsRun` dataclass that carries: input data freshness timestamps, missing-input flags per analysis, the LT roster used.
- CLI: `worldenergydata lower-tertiary portfolio-analytics --section <technology|operator|hse|cost|all>`
- Tests assert: (a) each section runs against fixtures, (b) missing-input flags are surfaced (do not silently skip), (c) totals match the per-field economics in #375.

### Out of scope (deferred)
- Full HSE coverage requires #366; minimum-viable version is intentional under-scoping.
- Real-time disclosure backfill is operations work, not analytics — track as separate issue if needed.
- Operator handover history (e.g., North Platte Equinor → TotalEnergies) belongs in the Phase 4 narrative, not the analytics layer.

---

## Steps

1. **Read** `marine_safety/cross_database.py` for the cross-cutting analytics pattern.
2. **Design** `PortfolioAnalyticsRun` dataclass shape; document each section's inputs + outputs + missing-input semantics.
3. **Implement 3a (technology)** — group → aggregate → emit CSV. Pure-config; no live data required.
4. **Implement 3b (operator)** — same shape; uses yaml `partners` × #375 production output.
5. **Implement 3c (HSE minimum-viable)** — query BSEE incidents in-repo; aggregate per field/lease; flag `data_completeness: minimum_viable`.
6. **Implement 3d (cost benchmark)** — call `DisclosureAnalyticsQuery.benchmark` per field; record `benchmark_status` per result.
7. **Wire CLI** with section flags.
8. **Tests** — fixtures cover each section's happy path AND each section's missing-input path.
9. **Black + ruff + mypy** clean.
10. **PR through gates.**

---

## Adversarial review checklist

- [ ] Does HSE 3c actually reach the in-repo BSEE incidents data, or does it need #366's path resolution? If it depends on #366, this plan must hold until #366 lands.
- [ ] Does cost benchmark 3d use the actual disclosure dataset, or fabricate inputs? If the disclosure dataset is empty for LT operators, the output must say `no_data`, not `delta=0%`.
- [ ] Are operator working interests in 3b consistent across all 10 yamls' `partners` blocks? If one yaml uses fractions and another uses percentages, the aggregation will be wrong by 100×. Verify with a test.
- [ ] Does technology 3a's "capex intensity" denominator use *recoverable* MMbbl or *cumulative produced* MMbbl? These differ by factor of 2–3× for early-life fields and the comparison breaks if mixed. Pick one explicitly and document.
- [ ] Are the four CSVs joinable on `field_id`? Inconsistent ID schemes will block Phase 4 assembly.
- [ ] Does each section have a "citations + caveats" sidecar, or is provenance lost between sections?

---

## Verification

After implementation:
- `uv run worldenergydata lower-tertiary portfolio-analytics --section all` produces all four CSVs
- Each CSV includes a `field_id` column matching the #374 roster constant
- HSE section's output explicitly tags `data_completeness: minimum_viable` rows
- Cost benchmark section returns rows for all 10 fields (with `no_data` where applicable), not just fields with disclosures
- `uv run pytest tests/unit/lower_tertiary/test_portfolio_analytics.py -v` → green
- All four sections cite their input sources via a sidecar JSON
