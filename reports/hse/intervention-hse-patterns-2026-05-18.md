# Intervention-HSE Patterns — Phase 0 Findings & Re-Scope

> **Issue**: [#416](https://github.com/vamseeachanta/worldenergydata/issues/416)
> **Branch**: `feat/issue-416-phase1a-intervention-hse-service-type`
> **Data as of**: 2026-05-18
> **Status**: Phase 0 (exploration) complete. Phase 1A pattern-mining DEFERRED — see "Re-scope" section.

---

## What this document is

A Phase 0 exploration report against the [#416 plan](../../docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md). It inventories the data surface, surfaces feasibility constraints the original plan didn't anticipate, and recommends a re-scoped Phase 1A path.

This is **NOT** the pattern-mining memo the original plan called for. The exploration revealed data constraints that block the full pattern set; this document captures those constraints so the next step is an informed re-plan, not a hand-waved analysis.

## Caveat block

> Data sources: `data/modules/hse/hse_incidents.db` (60 MB, 97,993 rows, cross-source: BSEE + EPA TRI + OSHA + PHMSA implied by 16,200 distinct operators). Coverage gap: BSEE FY2007-2018 offshore incident XLSX files are stub-sized (15 of 17 — only CY2019 + CY2021 contain full data per [WRK-012 audit](./wrk012_hse_data_audit.md)). All operator-level patterns are aggregate; no individual operator is named. This memo represents engineering-analysis interpretation of public regulatory data and is not a regulatory finding.

## Headline findings

### Data inventory (`hse_incidents.db`)

| Surface | Value | Implication |
|---|---|---|
| Total rows | 97,993 | Same as WRK-013 reported |
| Date range | 1948-01-03 → 2026-01-29 | Effective coverage: 2017-2024 (~1,500-2,000 rows/year) |
| Distinct operators | 16,200 | Cross-source contamination — BSEE alone wouldn't be this high |
| Distinct field names | **0** | `field_name` field is EMPTY in all rows |
| Distinct leases | 946 | Sparse — only ~1% of rows have a lease number |
| Rows with `operator + lease_number + incident_date` together | **1,932** | <2% have the full join key the plan assumed |
| Rows with `latitude + longitude` | **0** | Spatial join via coordinates is impossible |

### Incident type distribution

| incident_type | count | % |
|---|---:|---:|
| violation | 91,527 | 93.4% |
| injury | 4,709 | 4.8% |
| equipment_failure | 1,293 | 1.3% |
| spill | 464 | 0.5% |

**Implication**: this DB is dominated by INC (Incident of Non-Compliance) notices, not operational incidents. The 5,000 non-violation rows are where intervention-period operational HSE patterns would live.

### Severity distribution

| severity | count | % |
|---|---:|---:|
| minor | 85,235 | 87.0% |
| recordable | 8,130 | 8.3% |
| fatality | 3,765 | 3.8% |
| near_miss | 829 | 0.8% |
| lost_time | 34 | <0.1% |

**Implication**: the 3,765 "fatality" count is implausibly high for BSEE GoM alone — confirms cross-source contamination (likely includes PHMSA pipeline + OSHA + EPA fatalities). Any fatality-rate claim against intervention activity needs source-filtering FIRST.

### Intervention keyword hits in `description` + `incident_type`

| keyword | hits |
|---|---:|
| workover | 9 |
| well control | 11 |
| well work | 6 |
| wireline | 4 |
| P&A | 3 |
| snubbing | 1 |
| intervention | 0 |
| coil tubing | 0 |
| plug and abandon | 0 |

**Total intervention-keyword hits**: ~34 records (with overlap). Out of 97,993 rows = 0.035%. **The current DB free-text does NOT carry intervention-activity labels in any volume.** The WRK-013 `IncidentClassifier`'s 89.2% confidence on BSEE-source data must have come from a different text surface (likely `bsee_accident_type` in a separate table not present in `hse_incidents.db`).

### WAR data confirmed present

| Path | Size | Format |
|---|---:|---|
| `data/modules/bsee/.local/war/eWellWARRawData.zip` | 127.9 MB | Raw ZIP (un-extracted) |
| `data/modules/bsee/.local/war/war_borehole_view.pkl` | 6.0 MB | Processed pickle |
| `data/modules/bsee/.local/rig_fleet/rig_fleet_full.bin` | (binary) | Processed |

So WAR + rig fleet data IS available locally, but it's not in git (`.local/` is gitignored per `worldenergydata/CLAUDE.md`'s "BSEE binary ~300MB not in git"). Running `make data` would refresh; the existing local files suffice for Phase 1.

## Re-scope: what Phase 1A can actually deliver

The original plan's patterns p1-p4 assumed a join surface that doesn't exist in the volumes implied. Honest re-scope:

| Original pattern | Feasible? | Why |
|---|---|---|
| p1: incident rate per intervention service type | ⚠️ Partial | Requires WAR-service-type → HSE-incident join. Possible on the 1,932-row join-key subset, but tiny sample for 7 service types (Bonferroni-corrected detection power weak). |
| p2: by water depth strata | ❌ Blocked | Requires water_depth, which would have to come from BSEE field master via field_name — but `hse_incidents.field_name` is empty in all rows. |
| p3: by intervention duration | ⚠️ Partial | Possible via WAR start/end → HSE join, again on the small 1,932 subset. |
| p4: severity intervention vs non | ⚠️ Partial | Possible on the 1,932 subset; severity-level sparsity (only 34 lost_time rows total) limits cross-tab cells. |

**Feasible Phase 1A patterns (re-scoped)**:

1. **HSE incident type distribution during periods of BSEE-WAR-recorded operator+lease activity vs. periods without**. Surface: the 1,932 join-key subset overlapped to WAR. Output: 2×4 cross-tab (in-window × incident_type), chi-square, Cramér's V.
2. **Severity distribution during in-window vs. out-of-window periods**. Same join subset, 2×5 cross-tab.
3. **Temporal pattern of in-window vs. out-of-window HSE incidents per year** (2017-2024 full-coverage window).
4. **INC (`incident_type='violation'`) sub-pattern**: which violation_type values appear disproportionately during WAR activity windows.

That's 4 patterns, fewer than the original 8. With Bonferroni correction at 0.05/4 = 0.0125, statistical power on the small 1,932 subset will be moderate.

**Honest expected outcome**: 1-2 of these 4 will yield defensible patterns. The memo will explicitly mark each as "exploratory hypothesis" rather than "confirmed pattern" if data sparsity warrants.

## Blockers for full Phase 1B (operator-aggregate) work

Phase 1B as planned needs:

1. **Operator-name normalization across 16,200 variants** — current state requires non-trivial deduplication work. This may overlap with [#366](https://github.com/vamseeachanta/worldenergydata/issues/366) (HSE bulk dedup ingest).
2. **Source filtering to BSEE-only rows** — the 16,200 operator count signals cross-agency contamination. Need a reliable `data_source` discriminator column that isn't currently in the schema we inspected.
3. **`field_name` repopulation** — the field is structurally present but empty. Joining HSE incidents to BSEE fields needs this OR a `lease_number → field_name` lookup.

Phase 1B should NOT be planned in detail until #366 (HSE bulk dedup) is closer to landing. Mark Phase 1B as blocked.

## Recommended next steps (for user decision)

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Proceed with re-scoped Phase 1A** | Run the 4 feasible patterns on the 1,932-row subset; ship a defensible-but-modest memo | Forward momentum; honest scope | Smaller than originally promised; may not produce a strong portfolio piece |
| **B. Wait for #366 + #365 to land first** | Defer Phase 1A until HSE bulk dedup + BSEE binary tier decompression ship; then re-explore | Higher-quality result | Multi-week delay; loses Wednesday-prep momentum |
| **C. Pivot to INC-pattern memo** | Focus on the 66,561 violation rows (INC notices) — analyze regulatory non-compliance patterns by inferred operation type, not by intervention specifically | Larger sample (66K vs 1.9K); INC data may carry implicit activity labels | Re-frames the question; not what was originally asked |
| **D. Pivot to taxonomy refresh first** | Re-run WRK-013 `IncidentClassifier` against the current `hse_incidents.db` to produce a fresh activity-code column. Then Phase 1A becomes feasible on the 5,000 non-violation rows | Restores join feasibility; preserves original framing | Adds 1-2 hours of upstream work before Phase 1A starts |

**Recommended**: D, then A. Re-classify (~1 hour), then re-explore (~30 min), then run Phase 1A (~2-3 hours) on the newly classified data. Total ~4 hours for a defensible memo.

## Artifacts produced in Phase 0

| Path | Purpose |
|---|---|
| `scripts/exploration/intervention_hse_phase1a_explore.py` | Re-runnable exploration script |
| `reports/hse/intervention-hse-patterns-2026-05-18-explore.json` | Inventory JSON (4 KB) — full data shapes |
| `reports/hse/intervention-hse-patterns-2026-05-18.md` (this file) | Phase 0 findings + re-scope recommendation |

## Update 2026-05-18 (post-initial-write): source-prefix discovery

A second exploration pass on the `bsee_incident_id` column (which turns out to be misnamed — it holds external IDs from multiple sources) reveals the actual source breakdown:

| Source prefix | Count | % | Interpretation |
|---|---:|---:|---|
| `INC-YYYYMMDD-NNNNN-WARNING` | 66,561 | 67.9% | BSEE Incidents of Non-Compliance (regulatory bookkeeping) |
| `OSHA-INSP-*` | 24,966 | 25.5% | OSHA inspections (mostly onshore — not GoM-relevant) |
| `OSHA-INJ-*` | 2,604 | 2.7% | OSHA injuries |
| `OSHA-ACC-*` | 1,878 | 1.9% | OSHA accidents |
| `INCINV-*` | 312 | 0.3% | **BSEE Incident Investigations (the deep operational incident records)** |
| Other | ~1,672 | 1.7% | Miscellaneous |

### Refined picture

- **BSEE-relevant subset is ~67K rows** (66,561 INC + 312 INCINV), not the 1,932 I cited above. The earlier 1,932 figure was because OSHA records lack `lease_number` (they use NAICS/SIC codes instead).
- **The 312 INCINV records are the gold** — these are the deep accident investigations where WRK-013's 89.2% BSEE classification confidence likely came from. Rich free-text. Small sample but per-record analytical value is high.
- **The 66.5K INC notices** are regulatory bookkeeping — terser text but high volume, suitable for INC-pattern analysis (option C of the re-scope menu, which intersects with this finding).
- **OSHA's ~29K rows are mostly onshore** — not relevant to GoM offshore intervention work. Should be filtered out at source-prefix level.

### Revised Phase 1A approach

The Option D → A path from above is still recommended, but now refined:

1. **Source-prefix filter** to BSEE subset (~67K rows) before any analysis
2. **Re-classify ONLY the INCINV subset (312 rows)** for operational-incident patterns — this is what WRK-013's classifier was probably built for
3. **Separately, descriptive analysis of INC notices** (~66K rows) for regulatory non-compliance patterns during intervention-relevant violation types
4. **Run 4-pattern Phase 1A on INCINV + WAR join** — small sample (312 incidents × WAR overlap) but defensible per-pattern

This is a smaller-output Phase 1A but a credible one — exactly the kind of "honest about what data lets us say" memo that earns trust.

## Cross-references

- Plan: [`docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md`](../../docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md) — needs revision per this findings doc
- Issue: [#416](https://github.com/vamseeachanta/worldenergydata/issues/416)
- Sibling issues: [#418](https://github.com/vamseeachanta/worldenergydata/issues/418) (Phase 2 code module), [#419](https://github.com/vamseeachanta/worldenergydata/issues/419) (Phase 1B operator-aggregate), [#420](https://github.com/vamseeachanta/worldenergydata/issues/420) (deny-list policy)
- Upstream dependency: [#366](https://github.com/vamseeachanta/worldenergydata/issues/366) (HSE bulk dedup ingest) — its delivery would unblock #419 (Phase 1B) and improve Phase 1A signal density
- Prior work: [WRK-012 HSE Data Audit](./wrk012_hse_data_audit.md), [WRK-013 HSE Mishap Analysis](./wrk013_hse_mishap_analysis.md)
