# Plan for #375: per-field economic analysis for all 10 LT fields

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-05-03
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/375
> **Parent epic:** https://github.com/vamseeachanta/worldenergydata/issues/373
> **Depends on:** #374 (configs must exist for all 10 fields)

---

## Resource Intelligence Summary

### Existing repo code
- `src/worldenergydata/fdas/api.py:EconomicsQuery.all_metrics` returns NPV/IRR/MIRR/payback in a single call (Excel-validated; 100% match against legacy benchmarks).
- `src/worldenergydata/lower_tertiary/npv.py` has a per-field NPV pipeline already, but its tests indicate it is the v30-reproducer flavour, not the lease-NPV pattern from #372.
- `src/worldenergydata/lower_tertiary/wti_prices.py:load_wti_series` provides EIA + FRED WTI history for the price deck.
- `notebooks/lease_npv_walkthrough.py` (landed via #372) is the canonical pattern: load wells → classify dev system → resolve assumptions → build cashflow → compute metrics → emit citations.
- `config/analysis/lower_tertiary/economic_assumptions.yml` carries portfolio-level parameters (discount rate, fiscal terms).

### Documents and issues consulted
- Issue #375 body
- Parent epic #373
- Predecessor pattern: notebook landed by #372
- Field summary: `reports/lower_tertiary_field_summary.md` (cum production, lease counts)
- Configs: `config/analysis/lower_tertiary/fields/*.yml`

### Gaps identified
- The current `lower_tertiary/npv.py` flow doesn't emit a citations sidecar. Phase 2 needs the citation pattern adopted at field level.
- For producing fields (6), real BSEE OGOR aggregation gives a defensible cashflow. For Pre-FID fields (4), only documented decline-curve assumptions are available; the citations panel must distinguish these.
- No portfolio-comparison output exists today. Each field's NPV is computed in isolation.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-05-03-issue-375-per-field-economics-10-lt-fields.md` |
| Pattern source | `notebooks/lease_npv_walkthrough.py` |
| Existing per-field NPV | `src/worldenergydata/lower_tertiary/npv.py` |
| Price deck loader | `src/worldenergydata/lower_tertiary/wti_prices.py` |
| Field configs | `config/analysis/lower_tertiary/fields/*.yml` |
| Output (machine) | `results/lower_tertiary/per_field_economics_2026.csv` |
| Output (presentable) | `results/lower_tertiary/per_field_economics_2026.html` |
| New module | `src/worldenergydata/lower_tertiary/portfolio_economics.py` |
| Tests | `tests/unit/lower_tertiary/test_portfolio_economics.py` |

---

## Deliverable

A `PortfolioEconomicsRun` API + CLI that computes NPV/IRR/MIRR/payback + breakeven + 5-point oil-price sensitivity for all 10 LT fields in a single call, writes both a CSV and an HTML output, and emits a citations panel covering every numeric input across all fields.

---

## Scope Boundaries

### In scope now
- New module `lower_tertiary/portfolio_economics.py` with:
  - `run_portfolio(field_ids, *, discount_rate, oil_price_deck, ...)` returning a typed result per field
  - `to_csv()` and `to_html()` helpers
  - Per-field citation builder reusing the pattern from #372
- Sensitivity sweep: 5 oil prices ($50/$60/$70/$80/$100/bbl) × 10 fields = 50 NPV computations
- Producing fields cashflow: BSEE OGOR aggregation via existing `bsee/analysis` if reachable; otherwise documented assumption fallback with `confidence: assumption` in citation
- Pre-FID fields cashflow: documented assumption only with `confidence: preliminary` in citation
- HTML output uses the same template aesthetic as `reports/lower_tertiary_field_summary.html`
- Tests assert: (a) all 10 fields produce non-null metrics, (b) sensitivity table has 5 columns, (c) citations dataframe has at least 8 rows per field
- CLI: `worldenergydata lower-tertiary portfolio-economics --output-csv ... --output-html ...`

### Out of scope (deferred)
- Citation schema migration to the workspace-hub `Citation` contract — #361
- Real-time WTI price fetch (uses cached EIA series via existing `load_wti_series`) — operational, not analytical
- Cross-field comparison sections (technology, operator, HSE, cost benchmarking) — Phase 3 / #376

---

## Steps

1. **Read** `notebooks/lease_npv_walkthrough.py` and `lower_tertiary/npv.py` side by side; identify the cleanest reusable shape.
2. **Design** `PortfolioEconomicsRun` dataclass — fields per-field-result + citations + run metadata (timestamp, price deck revision, etc.).
3. **Implement** `run_portfolio()` over the roster constant from #374.
4. **Implement** `to_csv()` writing per-field rows + sensitivity columns.
5. **Implement** `to_html()` with embedded citation panels per field.
6. **Wire CLI** subcommand under existing `lower-tertiary` group.
7. **Tests** — full portfolio run on test fixtures; assert all 10 fields × 5 sensitivities × ≥8 citations.
8. **Verify locally** against current configs (after #374 merges, all 10 yamls present).
9. **Black + ruff + mypy** clean.
10. **PR through gates.**

---

## Adversarial review checklist

- [ ] Are the producing-field cashflows actually grounded in BSEE OGOR data, or did the implementation fall back to documented assumptions silently? The citation panel must mark each cashflow source unambiguously.
- [ ] Does the discount rate / fiscal terms come from `economic_assumptions.yml` or from hardcoded literals? Hardcoded literals are a regression vs. the existing pattern.
- [ ] What happens for Pre-FID fields where capex is a range, not a point estimate? Does the run pick the midpoint silently, or does it surface the range?
- [ ] Is the oil price deck the same across all 10 field comparisons in a single run, or does each field get a different deck? They should be portfolio-uniform for comparability — confirm.
- [ ] Does the HTML output's citations panel render every input, or does it elide inputs that match a default? Buyer-grade output must not elide.
- [ ] Does `run_portfolio` fail-loud or fail-quiet when a field's config is missing? Per #374's roster constant, missing should be impossible — but the runtime guard should still exist.
- [ ] How does this module's output relate to `lower_tertiary/npv.py`'s existing per-field outputs? Is there duplication, or does this module wrap the existing one? Avoid two parallel cashflow constructors.

---

## Verification

After implementation:
- `uv run worldenergydata lower-tertiary portfolio-economics --output-csv /tmp/p.csv --output-html /tmp/p.html` exits 0
- The CSV has 10 rows × (NPV, IRR, MIRR, payback, breakeven, NPV@$50, NPV@$60, NPV@$70, NPV@$80, NPV@$100) ≥ 10 columns
- The HTML renders 10 per-field sections each with a citations table
- `uv run pytest tests/unit/lower_tertiary/test_portfolio_economics.py -v` → green
