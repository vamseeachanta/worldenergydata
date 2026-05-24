# Plan for #427: feat(analysis): seasonal intervention risk windows — hurricane × WAR × ops

> **Status:** plan-review
> **Complexity:** T2 — combines two existing pipelines (#403 hurricane + #416 WAR/HSE)
> **Date:** 2026-05-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/427
> **Parent**: [#423](https://github.com/vamseeachanta/worldenergydata/issues/423)
> **Sibling**: [#403](https://github.com/vamseeachanta/worldenergydata/issues/403), [#416](https://github.com/vamseeachanta/worldenergydata/issues/416)
> **Review:** Inline T1 self-review

---

## Resource Intelligence Summary

### Existing repo code and artifacts
- Found: [`docs/plans/2026-05-12-issue-403-hurricane-mooring-risk-infographic.md`](2026-05-12-issue-403-hurricane-mooring-risk-infographic.md) — hurricane metric contract + matched-IDs pattern to reuse
- Found: `reports/modules/marketing/hurricane_mooring_safety_infographic.html` — visual style baseline
- Found: `data/modules/marine_safety/input/*.csv` — incident pathway data
- Found: `data/modules/bsee/.local/war/` — WAR data for intervention timing
- Found: `src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py` — HSE classifier
- Gap: no analysis that joins hurricane-season timing × WAR intervention scheduling × HSE incident rate

### Standards consulted
- `worldenergydata/docs/HTML_REPORTING_STANDARDS.md`
- Operator Aggregation Contract from #416 plan
- Metric Contract pattern from #403 plan

### Documents consulted
- [#403](https://github.com/vamseeachanta/worldenergydata/issues/403) hurricane mooring infographic plan — reusable infrastructure
- [#416](https://github.com/vamseeachanta/worldenergydata/issues/416) intervention HSE — WAR loaders + classifier reuse
- [#423](https://github.com/vamseeachanta/worldenergydata/issues/423) umbrella

### Gaps identified
- Hurricane season × intervention scheduling joint analysis doesn't exist
- Operational decision-support framing ("optimal scheduling windows") is novel angle

### Evidence
**File existence**:
- EXISTS: `docs/plans/2026-05-12-issue-403-hurricane-mooring-risk-infographic.md`
- EXISTS: `data/modules/bsee/.local/war/` (per #416 Phase 0)
- MISSING (this plan creates): `reports/gtm/seasonal-intervention-risk-windows-2026-XX-XX.html`

**Issue statuses**:
- `#427` — OPEN
- `#403` — OPEN, status:working — preferred dependency for hurricane data shape
- `#416` — OPEN — preferred dependency for WAR+HSE join logic

---

## Deliverable

Interactive HTML at `reports/gtm/seasonal-intervention-risk-windows-2026-XX-XX.html` providing operational decision support: which seasonal windows are optimal for which intervention types, with quantified risk gradients from public data.

## Pseudocode

```
1. WAR ACTIVITY by month — aggregate intervention-hours per service type per calendar month
2. HISTORICAL HURRICANE TRACK overlay — NOAA HURDAT2 GoM tracks 1900-2025, season May-Nov peak Aug-Sep
3. METOCEAN CURRENTS/WAVES seasonality — average + worst-case per month
4. HSE INCIDENTS by month from #416-classified subset
5. JOINT ANALYSIS:
   s1: intervention activity rate by month (which months see most intervention work currently)
   s2: HSE incident rate by month for intervention-period rows
   s3: storm-track-density-weighted operational risk by month
   s4: optimal-window identification per intervention type:
       - "Wireline operations completed Mar-May show X% lower HSE rate than Aug-Oct"
       - "Snubbing operations recommended Mar-Apr or Nov to avoid peak hurricane + winter storms"
6. SENSITIVITY: how robust are recommendations across years (decade-by-decade trend)
7. HTML ASSEMBLY:
   - Calendar heatmap (intervention type × month × risk score)
   - Hurricane season overlay
   - Decision-tree visualization (when to schedule X intervention type)
8. SCAN before publish
```

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `scripts/exploration/seasonal_risk_window_explore.py` | Joint analysis script |
| Create | `reports/gtm/seasonal-intervention-risk-windows-2026-XX-XX.html` | Final HTML |
| Create | `reports/gtm/seasonal-intervention-risk-windows-2026-XX-XX-stats.json` | Sidecar |
| Update | `docs/plans/README.md` | Plan index |

## TDD Test List

| Test | Verifies |
|---|---|
| `test_monthly_activity_aggregation` | per-month aggregates sum to annual totals |
| `test_hurricane_track_overlay` | known major storms (Katrina 2005, Ida 2021) appear in correct cells |
| `test_optimal_window_logic` | recommendation generator produces non-contradictory advice across intervention types |

## Acceptance Criteria

- [ ] HTML report at `reports/gtm/seasonal-intervention-risk-windows-2026-XX-XX.html`
- [ ] Calendar heatmap viz
- [ ] 4+ optimal-window recommendations per intervention type with quantified risk gradient
- [ ] Sensitivity over decades section
- [ ] Aggregate-only (no specific incident or operator naming)
- [ ] Methodology section + data-as-of clearly stated
- [ ] Cross-links to #403 and #416 in the report

## Adversarial Review Summary

**T1 inline self-review (Claude r1):**

1. **MINOR — Causality vs correlation**: "X% lower HSE rate in Mar-May" may reflect operator self-selection (better operators schedule risky work in safer windows), not the window's intrinsic safety. Mitigation: caveat as observational, not causal.
2. **MINOR — Decade-by-decade trend may be confounded** by operational practice improvements (modern intervention safety is genuinely better than 2005). Mitigation: separate "structural improvement" trend from "seasonal" effect.
3. **MINOR — Hurricane track density** is a coarse proxy — Cat-5 vs Cat-1 matter very differently to operations. Mitigation: weight by intensity, not just count.

**Overall**: MINOR — methodologically interesting work; risk is over-interpretation of observational data.

## Risks and Open Questions

- **Risk**: data joinability — WAR is per-day per-well, hurricane tracks are per-6-hour positions, HSE incidents are per-day. Date-resolution mismatch needs normalization.
- **Risk**: deepwater intervention is seasonally less constrained than shelf (different rig capabilities). Findings should stratify.
- **Open**: scope to GoM only, or extend to Gulf-of-Mexico-Mexico + North Sea for cross-basin comparison? Recommend GoM only for V1.
- **Open**: include offshore wind installation seasons (East Coast) as a sibling figure? Recommend defer to V2.

## Complexity: T2

Multi-source join with operational decision-support framing. Reuses #403 + #416 infrastructure, lowering net complexity.
