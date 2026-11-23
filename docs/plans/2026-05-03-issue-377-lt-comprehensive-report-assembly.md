# Plan for #377: comprehensive Lower Tertiary report assembly

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-05-03
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/377
> **Parent epic:** https://github.com/vamseeachanta/worldenergydata/issues/373
> **Depends on:** #374 (configs), #375 (per-field economics), #376 (cross-field analytics)

---

## Resource Intelligence Summary

### Existing repo code
- `reports/lower_tertiary_field_summary.md` — current report; covers 6 producing fields fully, 4 pre-FID fields in summary table only. Will be **superseded** by this work.
- `reports/lower_tertiary_field_summary.html` — current HTML rendering pattern.
- `reports/hse/wrk013_hse_mishap_analysis.md` — example of a long-form analytical narrative report with embedded findings.
- `notebooks/lease_npv_walkthrough.py` — citations panel pattern landed via #372.
- `data:md-to-pdf` skill — Markdown to styled PDF via Chrome headless. Available for the PDF deliverable.

### Documents and issues consulted
- Issue #377 body
- Parent epic #373
- Predecessor sub-issues #374, #375, #376
- Existing report: `reports/lower_tertiary_field_summary.md`
- HSE narrative reference: `reports/hse/wrk013_hse_mishap_analysis.md`

### Gaps identified
- Current `lower_tertiary_field_summary.md` is asymmetric — full treatment for 6 producing fields, table-only for 4 pre-FID. Buyer-grade report needs symmetric depth across all 10.
- No assembly script exists — the existing summary was authored by hand. Phase 4 needs a regeneration pipeline driven by #375 and #376 outputs so the report stays in sync with future data refreshes.
- HTML and PDF outputs need to be regenerable from Markdown source — Chrome-headless via `data:md-to-pdf` skill.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-05-03-issue-377-lt-comprehensive-report-assembly.md` |
| New assembly script | `scripts/reporting/assemble_lt_comprehensive.py` |
| Output (markdown) | `reports/lower_tertiary/comprehensive_2026.md` |
| Output (HTML) | `reports/lower_tertiary/comprehensive_2026.html` |
| Output (PDF) | `reports/lower_tertiary/comprehensive_2026.pdf` |
| Superseded | `reports/lower_tertiary_field_summary.md` (deprecate, do not delete) |
| Tests | `tests/integration/reporting/test_lt_comprehensive.py` |
| Inputs (from #375) | `results/lower_tertiary/per_field_economics_2026.csv` |
| Inputs (from #376) | `results/lower_tertiary/{technology,operator,hse,cost_benchmark}_2026.csv` |

---

## Deliverable

A regenerable comprehensive report on the 10 GoM Lower Tertiary fields. Markdown source consolidates outputs from #375 + #376; HTML and PDF derive from the Markdown source. Every numeric input traces to a publisher + revision via an inline citations panel. Supersedes (does not delete) the existing `lower_tertiary_field_summary.md`.

---

## Scope Boundaries

### In scope now
- **Assembly script** `scripts/reporting/assemble_lt_comprehensive.py`:
  - Reads roster from #374, economics CSV from #375, four analytics CSVs from #376
  - Templates a Markdown report with: executive summary → portfolio overview → per-field detail (×10) → cross-field analytics (technology/operator/HSE/cost) → citations panel → data freshness appendix
  - Renders HTML and PDF outputs via the `data:md-to-pdf` skill
- **Per-field detail section template** — consistent depth across all 10 fields (status, dev system, water depth, partners, capex, NPV table, sensitivity, citations, caveats)
- **Executive summary** — one-page top-level narrative with portfolio totals + 5–7 key findings
- **Citations panel** — every numeric input traced to publisher + code_id + revision (per #361 pattern)
- **Caveats appendix** — explicit listing of preliminary inputs (Pre-FID capex ranges, HSE minimum-viable scope, cost-benchmark `no_data` rows)
- **Supersession marker** in `reports/lower_tertiary_field_summary.md` pointing at the new comprehensive report; do not delete the file
- **Integration test** — `pytest tests/integration/reporting/test_lt_comprehensive.py` runs the assembly end-to-end against fixtures and asserts: 10 field sections present, ≥80 citation rows total (8 per field), HTML renders, PDF renders

### Out of scope (deferred)
- Real-time WTI / oil price refresh (uses cached data per #375)
- Migration of citations to the workspace-hub `Citation` schema — #361
- Wiring the report into a public docs site or wiki — separate task if the team wants it

---

## Steps

1. **Read** `reports/lower_tertiary_field_summary.md` to understand the existing structural taxonomy; inventory what to keep vs. expand.
2. **Read** `reports/hse/wrk013_hse_mishap_analysis.md` for narrative-report style conventions.
3. **Design** Markdown template — section IDs, anchor links, executive-summary placeholder structure.
4. **Implement assembly script** that:
   - Loads roster from #374 constant
   - Loads CSVs from #375 + #376
   - Renders Markdown via Jinja2 (already a transitive dep) or Python f-strings
5. **Implement HTML rendering** — pipe through `data:md-to-pdf` skill or equivalent (need to verify what's blessed in this repo for HTML).
6. **Implement PDF rendering** via the `data:md-to-pdf` skill.
7. **Add supersession header** to existing `lower_tertiary_field_summary.md` pointing at the new comprehensive report.
8. **Add integration test** that runs assembly against fixtures.
9. **Black + ruff** clean.
10. **PR through gates.**

---

## Adversarial review checklist

- [ ] Are all 10 fields treated with consistent depth, or did Pre-FID fields get a thinner section silently? Buyer-grade report must be symmetric.
- [ ] Does the assembly script regenerate end-to-end from #375 + #376 outputs, or does it require manual editing? If manual, the report drifts the moment data refreshes.
- [ ] Does the citations panel cover *every* number in the report, or only the ones the script remembered to instrument? Spot-check 5 random numbers in the rendered HTML against the citations panel.
- [ ] Does the executive summary's "key findings" come from the data, or from prose authored independently? If independent prose, it can drift; bind findings to computed thresholds where possible.
- [ ] Does the supersession of `lower_tertiary_field_summary.md` keep history intact (header + redirect, not delete)?
- [ ] Does the PDF export render the citations panel cleanly, or does it overflow / truncate? Verify with `data:md-to-pdf`.
- [ ] Does the report disclaim that Pre-FID economics are based on preliminary capex ranges (not point estimates)? Buyers need that nuance to trust the report.

---

## Verification

After implementation:
- `uv run python scripts/reporting/assemble_lt_comprehensive.py` exits 0
- `reports/lower_tertiary/comprehensive_2026.{md,html,pdf}` all exist
- The HTML renders 10 distinct field sections (one per field in #374's roster constant)
- The citations panel has ≥80 rows (8 inputs × 10 fields, minimum)
- The integration test passes
- The PDF opens cleanly and contains the executive summary, all field sections, and the citations panel
- `reports/lower_tertiary_field_summary.md` carries a supersession header pointing at the new report
