# Plan for #426: feat(analysis): drilling HSE patterns

> **Status:** plan-review
> **Complexity:** T2 — direct re-use of #416 methodology with activity-code re-cut
> **Date:** 2026-05-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/426
> **Parent**: [#423](https://github.com/vamseeachanta/worldenergydata/issues/423)
> **Sibling**: [#416](https://github.com/vamseeachanta/worldenergydata/issues/416)
> **Review:** Inline T1 self-review

---

## Resource Intelligence Summary

### Existing repo code and artifacts
- Found: `data/modules/hse/hse_incidents.db` — same DB as #416 (97,993 rows; 66.5K INC + 312 INCINV + 29K OSHA)
- Found: `src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py` — produces DRILL.* subactivity codes
- Found: `data/modules/bsee/.local/war/` — WAR data for drilling-activity window identification
- Found: existing `reports/bsee/intervention/drilling_analysis.html` (Feb 2026, 4.95 MB) — market intel cut, NOT HSE
- Gap: no HSE-axis drilling pattern report

### Standards consulted
- Operator Aggregation Contract from [#416 plan](2026-05-18-issue-416-intervention-hse-patterns.md) — inherited
- `worldenergydata/docs/HTML_REPORTING_STANDARDS.md`

### Documents consulted
- [#416](https://github.com/vamseeachanta/worldenergydata/issues/416) Phase 1A — direct methodology source
- [#418](https://github.com/vamseeachanta/worldenergydata/issues/418) reusable module — preferred dependency
- [#423](https://github.com/vamseeachanta/worldenergydata/issues/423) umbrella

### Gaps identified
- Drilling-specific HSE cross-cut doesn't exist as a published artifact
- Existing `drilling_analysis.html` covers market structure (rig counts, vendor share) but not HSE

### Evidence
**File existence**:
- EXISTS: `reports/bsee/intervention/drilling_analysis.html` (market intel, not HSE — only 9 incidental HSE-keyword hits per #416 Phase 0)
- MISSING (this plan creates): `reports/hse/drilling-hse-patterns-2026-XX-XX.md`

---

## Deliverable

`reports/hse/drilling-hse-patterns-2026-XX-XX.md` + HTML report variant focusing on DRILL.drilling / DRILL.completion / DRILL.well_control subactivity codes. Uses identical methodology as [#416 Phase 1A](2026-05-18-issue-416-intervention-hse-patterns.md) re-cut for drilling activities.

## Pseudocode

```
1. SOURCE-FILTER hse_incidents to BSEE-only (INC + INCINV prefixes)
2. CLASSIFY via IncidentClassifier(source='bsee')
3. FILTER to DRILL.drilling, DRILL.completion, DRILL.well_control subcodes
4. WAR JOIN to identify drilling-period operational context
5. PATTERN MINING (4 patterns, Bonferroni p<0.0125):
   d1: incident severity distribution: well-control events vs. routine drilling
   d2: water depth × drilling-phase incident rate
   d3: equipment-failure subtype frequency during drilling (cite WRK-013 subactivities)
   d4: temporal pattern across 2017-2024 (well-control event frequency vs rig count)
6. RECOMMENDATIONS (engineering-controls level):
   - Pre-spud audit-trail rigor on kick-detection equipment
   - Crew-fatigue management for extended-reach wells
   - etc.
7. MEMO + HTML ASSEMBLY (Operator Aggregation Contract + caveat block)
8. PRE-COMMIT SCAN
```

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `scripts/exploration/drilling_hse_explore.py` | Drilling-cut exploration |
| Create | `reports/hse/drilling-hse-patterns-2026-XX-XX.md` | Memo |
| Create | `reports/hse/drilling-hse-patterns-2026-XX-XX.html` | HTML variant |
| Create | `reports/hse/drilling-hse-patterns-2026-XX-XX-stats.json` | Stats sidecar |
| Update | `docs/plans/README.md` | Plan index |

## TDD Test List

Reuses #416 / #418 module if available. New tests:

| Test | Verifies |
|---|---|
| `test_drilling_subcode_filter` | classifier output filters to DRILL.* correctly |
| `test_well_control_subset_size` | sample size adequate for d1 statistical power |
| `test_operator_aggregate_compliance` | scanner clean before publish |

## Acceptance Criteria

- [ ] Memo at `reports/hse/drilling-hse-patterns-2026-XX-XX.md`
- [ ] 4 patterns with Bonferroni p<0.0125
- [ ] Each pattern paired with engineering-controls-level recommendation
- [ ] HTML report variant per HTML_REPORTING_STANDARDS.md
- [ ] Operator Aggregation Contract compliance verified
- [ ] Cross-linked from aceengineer-website portfolio

## Adversarial Review Summary

**T1 inline self-review (Claude r1):**

1. **MINOR — Sample sizes for well-control events may be small**: BSEE INCINV records are 312 total; the well-control subset will be <100 likely. Bonferroni-corrected detection power limited.
2. **MINOR — Drilling vs intervention overlap**: some "DRILL.workover" rows could be classified into either drilling or intervention; care needed to avoid double-counting with #416.
3. **MINOR — Existing `drilling_analysis.html` redundancy risk**: must explicitly call out that this report is HSE-cut, not market-intel-cut, so readers don't think we're rebuilding existing work.

**Overall**: MINOR — leveraging #416 methodology de-risks most concerns.

## Risks and Open Questions

- **Risk**: dependency on [#416 Phase 1A](https://github.com/vamseeachanta/worldenergydata/issues/416) landing — if 1A scope changes substantially, this plan may need re-write
- **Risk**: dependency on [#418 reusable module](https://github.com/vamseeachanta/worldenergydata/issues/418) — if module API differs, re-work needed
- **Open**: split drilling-HSE between exploration phase (deepwater wells) and shelf drilling, or treat as unified report?

## Complexity: T2

Methodology re-application of #416 with activity-code re-cut. Lower complexity than #416 itself because the methodology is now proven.
