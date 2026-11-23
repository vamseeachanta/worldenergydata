# Plan for #424: feat(analysis): decommissioning market outlook — 5-yr GoM forecast

> **Status:** plan-review
> **Complexity:** T2 — analysis + HTML report; multi-file but single-author
> **Date:** 2026-05-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/424
> **Parent**: [#423](https://github.com/vamseeachanta/worldenergydata/issues/423)
> **Review:** Inline T1 self-review

---

## Resource Intelligence Summary

### Existing repo code and artifacts
- Found: `reports/gtm/2026-05-04-bsee-field-analysis-comprehensive.html` — methodology analog for HTML field-economics report
- Found: `data/modules/bsee/current/completions/completion_summary.csv` — completion-level data feed
- Found: `data/modules/bsee/.local/borehole/` — borehole/well status raw data (BoreholeRawData.zip, 300MB+ per repo conventions)
- Found: `src/worldenergydata/bsee/analysis/intervention/` — analytical infrastructure for activity-cut reporting
- Gap: no committed forecasting module for forward-looking decommissioning volumes

### Standards consulted
- `worldenergydata/docs/HTML_REPORTING_STANDARDS.md` — output format
- `aceengineer-website/docs/marketing/PORTFOLIO_CAPABILITIES.md` — value-prop framing for "Energy Data & Economics" section

### Documents consulted
- [#423](https://github.com/vamseeachanta/worldenergydata/issues/423) — umbrella pipeline scope
- [#416](https://github.com/vamseeachanta/worldenergydata/issues/416) — Operator Aggregation Contract (apply at operator-aggregate sections)
- 2026-05-04 LT field analysis — methodology pattern to extend

### Gaps identified
- No existing forecasting tool for well-status → P&A wave projection
- No vendor-capacity gap analysis combining intervention dashboards' service-type breakdown with forecast volume

### Evidence
**File existence** (verified 2026-05-18):
- EXISTS: `reports/gtm/2026-05-04-bsee-field-analysis-comprehensive.html` — analog
- EXISTS: `data/modules/bsee/current/completions/completion_summary.csv`
- MISSING (this plan creates): `reports/gtm/decommissioning-market-outlook-2026-05-XX.html`
- MISSING (this plan creates): `scripts/exploration/decom_market_explore.py`

**Issue statuses**:
- `#424` — OPEN — this issue
- `#423` — OPEN — umbrella

---

## Deliverable

An HTML report at `reports/gtm/decommissioning-market-outlook-2026-05-XX.html` forecasting GoM P&A wave volume + timing for 2026-2030 with operator-aggregate vendor-capacity analysis. Backed by a stats JSON sidecar with matched well-IDs and assumption-sensitivity tables.

## Pseudocode

```
1. INVENTORY GoM wells from BSEE borehole/completion data
   - Status buckets: active / shut-in / P&A-pending / P&A-complete
   - Stratify by water depth (shelf / deepwater / ultra-deepwater)
   - Stratify by completion type (vertical / horizontal / SS / SS-HXT)

2. ESTIMATE end-of-life per well
   - Operating-life distributions per stratum from historical P&A timing
   - Bayesian update with field-specific exhaustion curves if available
   - Capture sensitivity: ±2 years on mean life expectancy

3. FORECAST forward P&A volumes 2026-2030
   - Wells reaching estimated EoL per year per stratum
   - Cumulative + annual flow

4. COST MODEL
   - P&A unit cost per stratum (shelf vs deepwater; vertical vs horizontal)
   - Sensitivity range from public-reported P&A costs (regulator filings)
   - Total market $ per year

5. VENDOR-CAPACITY GAP
   - Per-year P&A demand vs current intervention/workover capacity per service type
   - Identify capacity-strained service categories

6. HTML REPORT ASSEMBLY (per HTML_REPORTING_STANDARDS)
   - Header w/ data-as-of timestamp
   - 5 sections (inventory, forecast, cost, capacity, methodology)
   - Plotly charts for time-series + sensitivity
   - Operator-aggregate compliance scan before publish
```

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `scripts/exploration/decom_market_explore.py` | Data inventory + forecast script |
| Create | `reports/gtm/decommissioning-market-outlook-2026-05-XX.html` | Final HTML report |
| Create | `reports/gtm/decommissioning-market-outlook-2026-05-XX-stats.json` | Stats sidecar |
| Update | `docs/plans/README.md` | Plan index entry |

## TDD Test List

T2 scope. Tests live with the analysis code:

| Test | Verifies |
|---|---|
| `test_well_inventory_strata` | water-depth + completion-type buckets sum to total |
| `test_eol_estimator_sanity` | operating-life estimates fall in 15-50 year window |
| `test_forecast_volume_nonnegative` | forecast volumes never go negative |
| `test_operator_aggregate_compliance` | no operator names in final HTML |

## Acceptance Criteria

- [ ] HTML report at `reports/gtm/decommissioning-market-outlook-2026-05-XX.html`
- [ ] 5-year forward forecast with explicit assumptions section
- [ ] Sensitivity analysis on operating-life mean (±2 yr) and P&A unit cost (±30%)
- [ ] Operator-aggregate only — pass legal-deny-list + operator-aggregation deny-list scans
- [ ] Methodology section + data-as-of clearly stated
- [ ] Cross-link from `aceengineer-website/docs/marketing/PORTFOLIO_CAPABILITIES.md`

## Adversarial Review Summary

**T1 inline self-review (Claude r1):**

1. **MINOR — Operating-life estimation is fragile**: historical P&A timing in GoM is biased by economic-driven shut-ins, not pure technical exhaustion. Forecast must call this out as an assumption.
2. **MINOR — P&A unit cost varies by 5x** between shelf (~$1-3M/well) and deepwater (~$10-50M/well). Cost model must stratify.
3. **MINOR — Vendor-capacity assumption**: assumes current vendor capacity is the right denominator, but vendor capacity is also forecast-dependent (vendors may scale). Frame as snapshot-vs-snapshot, not equilibrium.

**Overall**: MINOR — methodologically tight if assumptions are explicit.

## Risks and Open Questions

- **Risk**: Hermes parallel work on `data/modules/bsee/current/` paths during borehole data refresh
- **Risk**: Per-stratum sample size for ultra-deepwater P&A may be too small for confident EoL estimation (<20 wells P&A'd to date)
- **Open**: Should the report include any operator-revealed deals (capacity announcements, contract awards)? Recommend: NO — keep purely BSEE-data-derived
- **Open**: Methodology peer-review desired before publication? Recommend: yes — circulate draft to user before publish

## Complexity: T2

Multi-file (script + report + sidecar). Requires forecasting math + HTML report assembly. Aligns with worldenergydata's existing 2026-05-04 LT field economics methodology.
