# Drilling-HSE Patterns — Phase 1A Findings

> **Issue**: [#426](https://github.com/vamseeachanta/worldenergydata/issues/426) (child of [#423](https://github.com/vamseeachanta/worldenergydata/issues/423), sibling of [#416](https://github.com/vamseeachanta/worldenergydata/issues/416))
> **Branch**: `feat/autorun-2026-06-19`
> **Data as of**: 2026-06-19
> **Status**: Phase 1A descriptive pattern findings on the **DRILL.\*** (drilling activity) cut.

---

## What this document is

A re-application of the [#416 intervention-HSE methodology](./intervention-hse-patterns-2026-05-18.md) onto **drilling-phase** incident codes. Same data source, same shared classifier, same INCINV-anchored approach — but cut to the **DRILLING** activity (`DRILL.*`: drilling operations, completion, workover, well control, well testing, casing/cementing, tripping, logging) instead of #416's intervention/well-servicing cut.

This is a descriptive pattern memo grounded entirely in the **real local BSEE source**. No numbers are fabricated; every count below traces to the re-runnable analysis script and its JSON sidecar.

## Caveat block

> **Data source**: BSEE INCINV (accident-investigation) raw source — `data/modules/hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt` (1,987 records, resolved via the HSE module's `external_data_root`). **Why the raw source, not the db**: the assembled `data/modules/hse/hse_incidents.db` that #416 profiled (97,993 rows) is **not materialized in this environment** (0-byte stub; `make data` not run here). The INCINV file IS the operational-incident surface #416 explicitly named as "the gold" — the deep accident records the WRK-013 `IncidentClassifier` was built for — so re-classifying it directly is the faithful, reproducible cut. **Coverage**: INCINV records span 1996–2021 (effective drilling-event coverage). **Drilling-phase derivation**: BSEE `ACCIDENT_TYPE` encodes the incident KIND (Fire, Crane, Blowout, Injury), not the operational phase; the drilling-phase label is *derived* by the shared classifier (`Blowout` → DRILL/well_control direct-map; drilling-keyword hits map the rest). This memo represents engineering-analysis interpretation of public regulatory data and is **not** a regulatory finding. Operator names are not surfaced (Operator Aggregation Contract — aggregate-only).

## Methodology (mirror of #416)

| #416 step | This memo (DRILL.\*) |
|---|---|
| Anchor on BSEE INCINV operational records | Same — 1,987 INCINV records |
| Re-classify with shared `IncidentClassifier` | Same `src/worldenergydata/safety_analysis/taxonomy/` classifier, `source='bsee'` |
| Cut to intervention/well-servicing subactivities | **Cut to `activity == "DRILL"`** (the drilling-phase taxonomy) |
| Descriptive pattern mining on the subset | Same — type / severity-proxy / temporal / geography / phase split |

**DRILL.\* filter (precise)**: `IncidentClassifier(source='bsee').classify(record).activity == "DRILL"`. The classifier reaches DRILL via two mechanisms — (1) **direct BSEE-type map**: `ACCIDENT_TYPE` containing "Blowout" → DRILL/well_control at confidence 0.95; (2) **keyword match**: drilling vocabulary (drill, casing, cement, completion, kick, bop, well control, wireline, top drive…) hit on the accident-type text. Records with no drilling signal classify to other activities and are excluded — identical mechanism to #416's cut.

## Headline findings

### Activity footprint across all INCINV records

| Activity | INCINV records | Note |
|---|---:|---|
| PERS (personnel safety) | 616 | injuries / LTA / fatalities |
| PSAFE (process safety) | 529 | fire / explosion |
| ENV (environmental) | 379 | pollution / spill |
| CRANE (lifting) | 191 | crane / other lifting device |
| **DRILL (drilling)** | **85** | **this memo's cut — 4.28%** |
| OTHER | 85 | unclassified |
| MARINE | 70 | collision / vessel |
| CONST / ELEC / PROD / PIPE | 21 / 4 / 4 / 3 | tail |

**Implication**: drilling-phase incidents are a small but high-consequence slice (4.28% of investigated incidents) — consistent with BSEE INCINV being dominated by personnel and process-safety events, while drilling events are rarer but heavily weighted toward well-control consequence.

### DRILL.\* subactivity (drilling-phase) distribution

| Drilling phase (subactivity) | Count | % of DRILL.\* |
|---|---:|---:|
| `well_control` | 68 | 80.0% |
| `drilling_operations` | 6 | 7.1% |
| `unknown` | 6 | 7.1% |
| `casing_cementing` | 4 | 4.7% |
| `logging` | 1 | 1.2% |
| **Total** | **85** | **100%** |

**Pattern P1 — Well control dominates investigated drilling incidents.** 68 of 85 (80%) of drilling-phase investigated incidents are well-control events (kicks, blowouts, loss of well control). This is the strongest pattern in the cut: when a drilling incident is serious enough to trigger a BSEE accident investigation, it is overwhelmingly a well-control event.

### Incident-type composition (top ACCIDENT_TYPE values within DRILL.\*)

| ACCIDENT_TYPE | Count |
|---|---:|
| - Blowout | 25 |
| - Blowout - Pollution | 6 |
| - Blowout - Fire | 5 |
| - Top Drive Unplanned Descent | 2 |
| - Blowout - Well Control on Prince TLP | 1 |
| - Loss well control/H2S release | 1 |
| - Blowout - Fire - KICK WITH GAS | 1 |
| - Extended Kick Control | 1 |
| (… 51 distinct accident-type strings total) | |

**Pattern P2 — Blowout/kick is the modal drilling incident-type.** "Blowout" appears in the ACCIDENT_TYPE of the plurality of DRILL.\* records. Compound types (`Blowout - Fire`, `Blowout - Pollution`, `Blowout - Injury - Fatality`) show well-control failures cascading into fire, pollution, and personnel consequences.

### Severity proxy distribution

Severity is proxied from BSEE composite ACCIDENT_TYPE semantics (no explicit severity field on INCINV):

| Severity proxy | Count | % |
|---|---:|---:|
| major (blowout / explosion) | 56 | 65.9% |
| other | 25 | 29.4% |
| fatality | 2 | 2.4% |
| evacuation/muster | 1 | 1.2% |
| serious (fire/pollution/collision/>$25K) | 1 | 1.2% |

**Pattern P3 — Drilling incidents skew high-consequence.** Two-thirds (65.9%) of investigated drilling incidents carry the "major" proxy (blowout/explosion); 2 carry a fatality flag. This confirms drilling-phase events, though rare, are disproportionately severe — the opposite of the broad incident pool, which #416 found skews minor.

### Temporal trend

DRILL.\* incidents by year of occurrence (1996–2021):

| Window | DRILL.\* incidents |
|---|---:|
| 1996–2000 | 31 |
| 2001–2005 | 35 |
| 2006–2010 | 8 |
| 2011–2015 | 6 |
| 2016–2021 | 5 (peak 2017 = 3) |

**Pattern P4 — Investigated drilling incidents decline sharply post-2005.** From a 1996–2005 plateau of ~6–9/yr, DRILL.\* investigated incidents fall to ≤3/yr from 2006 onward. This aligns with the post-2010 (Macondo) regulatory tightening of well-control standards (BOP, SEMS) — investigated drilling incidents drop as well-control practice matured, though the data cannot establish causation and INCINV ingestion completeness for recent years is a confound.

### Geographic concentration (BSEE area codes)

Top GoM areas for DRILL.\* incidents: **ST** (South Timbalier, 13), **EI** (Eugene Island, 12), **MC** (Mississippi Canyon, 8), **SS** (Ship Shoal, 8), **MP** (Main Pass, 6), **GC** (Green Canyon, 6). 80 distinct leases across the 85 incidents — near one-incident-per-lease, indicating drilling incidents are spatially dispersed, not concentrated in a few problem leases.

## Classification provenance (honest sourcing)

| Match method | Records | Confidence |
|---|---:|---|
| `bsee_accident_type` (direct Blowout map) | 58 | 0.95 |
| `keyword_match` | 27 | 0.35–0.75 |

58 of 85 (68%) DRILL.\* records are high-confidence direct-code maps (Blowout → well_control); the remaining 27 are keyword-derived (lower confidence). The 6 `unknown`-subactivity records are DRILL-activity but couldn't be pinned to a specific phase. Readers should treat the keyword-derived tail as **exploratory** rather than confirmed, exactly as #416 flagged for its keyword-matched subset.

## Limitations (mirroring #416's honesty discipline)

1. **Source is INCINV only**, not the assembled 97,993-row `hse_incidents.db` (not materialized here). The cross-source INC/OSHA/PHMSA rows the db carries are out of scope for this cut.
2. **No native drilling-phase field** — phase is classifier-derived from incident-type text, so phase resolution is coarse (well_control captures most signal; finer phases like tripping/well_testing under-detect because INCINV ACCIDENT_TYPE rarely names them).
3. **Small N (85)** — sufficient for descriptive patterns P1–P4 but not for operator-level or Bonferroni-corrected cross-tabs at the originally-planned `p<0.0125`. The full inferential pattern set in the issue AC awaits the materialized db + WAR join (Phase 1B).
4. **Recent-year completeness** — apparent post-2005 decline is partly real (regulatory) and partly an INCINV recency/ingestion artifact; not separable here.

## Artifacts produced

| Path | Purpose |
|---|---|
| `scripts/exploration/drilling_hse_patterns_analysis.py` | Re-runnable analysis (stdlib; loads shared classifier by path) |
| `reports/hse/drilling-hse-patterns-2026-06-19.json` | Stats sidecar — all counts above |
| `reports/hse/drilling-hse-patterns-2026-06-19.html` | Interactive Plotly render (per `HTML_REPORTING_STANDARDS.md`) |
| `reports/hse/drilling-hse-patterns-2026-06-19.md` | This memo |

## Cross-references

- Sibling memo: [Intervention-HSE Patterns (#416)](./intervention-hse-patterns-2026-05-18.md) — the methodology this memo mirrors
- Shared classifier: `src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py` + `activity_definitions.py` (DRILL activity)
- Prior work: [WRK-012 HSE Data Audit](./wrk012_hse_data_audit.md), [WRK-013 HSE Mishap Analysis](./wrk013_hse_mishap_analysis.md)
- Issue: [#426](https://github.com/vamseeachanta/worldenergydata/issues/426) — umbrella [#423](https://github.com/vamseeachanta/worldenergydata/issues/423)
