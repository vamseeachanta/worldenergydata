# Plan for #416: feat(analysis): intervention-activity HSE patterns + day-to-day operational recommendations

> **Status:** plan-review
> **Complexity:** T1 (Phase 1) — synthesis memo, single new file in `reports/hse/`. Phase 2 (code module) deferred to a separate issue.
> **Date:** 2026-05-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/416
> **Review artifacts:** Inline T1 self-review (see Adversarial Review Summary below). Per `feedback_permission_gate_blocks_cross_review` — this session lacks dispatch permission; cross-provider review will run if user requests during approval.

---

## Resource Intelligence Summary

### Existing repo code and artifacts

- **Found**: `src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py` — `IncidentClassifier` class produced WRK-013's 89.2% mean confidence taxonomy across 482,629 records. Programmatically reusable.
- **Found**: `src/worldenergydata/bsee/analysis/intervention/` — 9-module package: `activity_aggregator.py`, `comprehensive_analyzer.py`, `dashboard.py`, `drilling_report.py`, `enrichment_engine.py`, `field_visualization.py`, `insight_generator.py`, `intervention_detail_report.py`, `well_design_analyzer.py`. Drives the 3 existing intervention dashboards.
- **Found**: `data/modules/hse/hse_incidents.db` — SQLite HSE incidents store.
- **Found**: `data/modules/marine_safety/marine_safety.db` (60 MB) and `data/modules/marine_safety/database/marine_safety.db` — marine safety incidents (USCG, TSB, MAIB, IMO, NOAA).
- **Found**: `data/modules/bsee/current/`, `data/modules/bsee/.local/war/`, `data/modules/bsee/.local/rig_fleet/` — BSEE WAR (well activity reports), borehole data, rig fleet data — the source for intervention-activity classification.
- **Found**: `reports/hse/wrk012_hse_data_audit.md` (19,234 bytes, 2026-02-08) — coverage audit; BSEE FY2007-2018 XLSX gap explicitly documented (15 of 17 files are 53KB stubs; only CY2019 + CY2021 have full data).
- **Found**: `reports/hse/wrk013_hse_mishap_analysis.md` (27,394 bytes, 2026-02-08) — cross-source HSE mishap classification with 14-activity, 74-subactivity taxonomy; DRILL activity includes workover/well-control subactivities relevant to intervention.
- **Found**: `reports/bsee/intervention/intervention_dashboard.html`, `intervention_by_service.html`, `drilling_analysis.html` (Feb 2026 generated, ~5 MB each) — **market intelligence cuts, not HSE primary axis** — keyword scan: only 9 HSE-related hits per ~5 MB report.
- **Gap**: No existing synthesis that joins intervention activity from WAR data → HSE incident classification from WRK-013 → operational-controls-level recommendations. This plan fills that gap.

### Standards
Not applicable — this is a synthesis/analysis memo, not standards implementation. Optional citation per `.claude/rules/calc-citation-contract.md` is N/A because no standards-derived constants are emitted.

### LLM Wiki pages consulted
- `knowledge/wikis/engineering/wiki/concepts/` — no existing intervention-HSE concept page (gap noted in `feedback_llm_wiki_concept_pages_need_public_references`); not consulted because this memo cites public BSEE data, not standards.

### Documents and data consulted
- Issue [#416](https://github.com/vamseeachanta/worldenergydata/issues/416) — created 2026-05-18T19:36:58Z; this is the implementation-tracking issue.
- Issue [#403](https://github.com/vamseeachanta/worldenergydata/issues/403) — `feat(marketing): hurricane mooring risk-avoidance infographic from incident data` — status:working — closest pattern analog (same shape: incident-data-derived public artifact). Plan at `docs/plans/2026-05-12-issue-403-hurricane-mooring-risk-infographic.md` provides the metric-contract / matched-IDs / caveats template used here.
- Issue [#363](https://github.com/vamseeachanta/worldenergydata/issues/363) — `feat(api): public Python query API for HSE module — parity with marine_safety surface` — plan-approved. Upstream of this work but NOT blocking — Phase 1 reads from current DB schema directly.
- Issue [#366](https://github.com/vamseeachanta/worldenergydata/issues/366) — `feat(data): HSE bulk deduplication + ingest pipeline (unlocks 6.8 GB at /mnt/ace)` — plan-approved. When #366 ships, Phase 2 can re-run against expanded dataset; Phase 1 ships with current data and a "data-as-of" caveat.
- `data/modules/bsee/DATA_DICTIONARY.md` and `schema.yaml` — BSEE table/column conventions.
- WRK-013 mishap analysis (above) — taxonomy definitions used in this memo.

### Gaps identified
- No committed `reports/hse/intervention-hse-patterns-*` artifact exists.
- No script that runs the specific intervention-activity → HSE-classification join used here exists; Phase 1 uses ad-hoc SQL/pandas. Phase 2 (separate issue) would extract a reusable module.
- No public-repo policy doc defines operator-aggregate framing rules for HSE analysis; this plan's "Operator Aggregation Contract" (below) codifies the rule for this memo and may seed a future `.claude/rules/hse-public-framing.md`.

### Evidence (embedded verification)

**Issue status** (verified 2026-05-18T19:36:58Z via `gh issue view`):
- `#416` — OPEN — `feat(analysis): intervention-activity HSE patterns + day-to-day operational recommendations` — labels: `enhancement`, `cat:engineering`, `priority:medium`, `cat:data`
- `#403` — OPEN — `feat(marketing): hurricane mooring risk-avoidance infographic from incident data` — labels include `status:working`
- `#363`, `#366`, `#365`, `#367` — all OPEN with `status:plan-approved`

**File existence** (verified 2026-05-18 in this session):
- EXISTS: `reports/hse/wrk012_hse_data_audit.md` (19,234 bytes)
- EXISTS: `reports/hse/wrk013_hse_mishap_analysis.md` (27,394 bytes)
- EXISTS: `reports/bsee/intervention/intervention_dashboard.html` (4,930,186 bytes)
- EXISTS: `reports/bsee/intervention/intervention_by_service.html` (5,014,498 bytes)
- EXISTS: `reports/bsee/intervention/drilling_analysis.html` (4,953,419 bytes)
- EXISTS: `data/modules/hse/hse_incidents.db`
- EXISTS: `data/modules/marine_safety/marine_safety.db` (60 MB at `data/modules/marine_safety/database/`)
- EXISTS: `src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py`
- EXISTS: `src/worldenergydata/bsee/analysis/intervention/` (9 .py modules)
- MISSING (this plan creates): `reports/hse/intervention-hse-patterns-2026-05-18.md`

**Dashboard HSE-keyword scan** (`grep -ciE '(HSE|safety|incident|injury|spill|mishap|fatalit|hazard)' reports/bsee/intervention/*.html` 2026-05-18):
- intervention_dashboard.html → 9
- intervention_by_service.html → 9
- drilling_analysis.html → 9

Interpretation: HSE is incidental in current intervention dashboards (likely "Risk Factors" sub-section only). Confirms the gap is real, not duplicative.

**Parallel work scan** (`ps -eo pid,etime,cmd | grep hermes`):
- 5 Hermes processes active at plan creation. Phase 1 is markdown-only — no race risk. Phase 2 (code module) MUST use a worktree+branch per `feedback_hermes_active_preflight_check`.

**Reproduction proofs**: N/A — this is a synthesis-from-existing-data analysis request, not an alleged runtime bug. Per `issue-planning-mode` Step 1.5 skip-allowed for documentation/governance issues.

(Distinct sources counted: issue #416 body + WRK-012 + WRK-013 + dashboards + HSE DB + #403 plan + #363/#366 issues + classifier code = 8 sources. Exceeds 3-source minimum.)

---

## Operator Aggregation Contract

This memo is for a **public** repo (`worldenergydata` confirmed PUBLIC at plan creation). Per the user's instruction "public from the start" and the deny-list discipline established for `aceengineer-website`, this contract applies to every claim:

1. **No operator names in pattern claims**. Aggregate framings ("operators using 15k VXT systems show X% lower incident rate during RLWI than 10k HXT operators") are allowed; named-and-shamed claims ("Operator X had Y incidents") are forbidden.
2. **Minimum cell size = 5**. Any cross-tab where a single cell has fewer than 5 incidents and the cell would uniquely identify an operator MUST be suppressed or merged with neighboring buckets.
3. **No specific lease/well identifiers in claims**. Lease block aggregation is allowed (e.g., "Walker Ridge area"); individual lease numbers are not.
4. **BSEE coverage gap caveat REQUIRED** at memo top and at any longitudinal claim — WRK-012 documented FY2007-2018 XLSX stubs (only CY2019 + CY2021 full).
5. **Recommendations framed as engineering-controls-level only** — "audit-trail rigor on WCP pressure-test protocols" is acceptable; "BSEE should issue more INCs" is not.
6. **Data-as-of timestamp** — memo header must include `Data as of: YYYY-MM-DD` and a list of source DB modification times.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md` |
| Issue body | https://github.com/vamseeachanta/worldenergydata/issues/416 |
| Phase 1 deliverable (memo) | `reports/hse/intervention-hse-patterns-2026-05-18.md` |
| Phase 1 supporting data (computed counts, matched IDs) | `reports/hse/intervention-hse-patterns-2026-05-18-stats.json` |
| Plans index update | `docs/plans/README.md` |
| Plan review — Claude self-review (T1) | Inline below |
| Plan review — Codex (if user requests T2) | `scripts/review/results/2026-05-18-plan-416-codex.md` |
| Plan review — Gemini (if user requests T3) | `scripts/review/results/2026-05-18-plan-416-gemini.md` |
| Phase 2 deliverable (deferred to separate issue) | `src/worldenergydata/bsee/analysis/intervention_hse/` |

---

## Deliverable (Phase 1)

A synthesis memo at `reports/hse/intervention-hse-patterns-2026-05-18.md` joining intervention activity from BSEE WAR data to HSE incident classification from WRK-013, surfacing 5-8 candidate patterns with statistical sanity checks, and pairing each pattern with at least one engineering-controls-level day-to-day operational recommendation — all framed per the Operator Aggregation Contract above.

---

## Metric Contract

| Metric | Definition | Traceability requirement |
|---|---|---|
| `intervention_activity_records` | Count of intervention-activity rows from BSEE WAR data classified under DRILL.workover or DRILL.well_control or related subactivities. | Matched WAR record IDs in `*-stats.json`. |
| `hse_incident_records` | Count of HSE incidents from `data/modules/hse/hse_incidents.db` classified by `IncidentClassifier` into DRILL-related activity codes. | Matched incident IDs in `*-stats.json`; classifier confidence per record. |
| `intervention_period_overlap_rate` | Of HSE incidents in DRILL activity codes, fraction occurring during a window where the same operator+lease had an active intervention WAR record. | Operator/lease/date join logic documented; matched ID pairs. |
| `service_type_incident_rate` | For each intervention service type (wireline, coil tubing, lift boat, snubbing, workover rig, support vessel, pumping) per intervention_by_service.html: HSE incidents per 1,000 intervention-days. | Stratified counts + denominator (intervention-days). |
| `pattern_confidence` | For each surfaced pattern: chi-square or Fisher's exact (categorical) OR ANOVA (continuous) p-value; effect size where applicable (Cramér's V or eta-squared). | Test name + statistic + p-value + sample sizes. |

**Mandatory caveat block** at top of memo (verbatim):
> Data sources: BSEE WAR (well activity reports), BSEE INCs, BSEE Accidents/Investigations 2009-2024. Coverage gap: BSEE FY2007-2018 offshore incident XLSX files are stub-sized (15 of 17 — only CY2019 + CY2021 contain full data per WRK-012). Longitudinal claims use only the full-coverage window. All operator-level patterns are aggregate; no individual operator is named. This memo represents engineering-analysis interpretation of public regulatory data and is not a regulatory finding.

---

## Pseudocode

```
PHASE 1 — synthesis memo (T1, no new module)

1. LOAD
   - war_df = load WAR data (existing intervention dashboard loader)
   - hse_df = SELECT * FROM hse_incidents
   - bsee_acc = SELECT * FROM BSEE accidents/investigations CSV
   - classifier = IncidentClassifier()

2. CLASSIFY (already done in WRK-013, re-verify by sampling)
   - hse_df["activity_code"] = classifier.classify(hse_df)
   - bsee_acc["activity_code"] = classifier.classify(bsee_acc)
   - Filter to intervention-relevant codes (DRILL.workover, DRILL.well_control,
     CRANE.* subset, PERS.* subset where related to intervention ops)

3. JOIN (operator + lease + temporal window)
   - intervention_periods = war_df groupby (operator, lease, type) -> [start, end]
   - hse_in_window = hse_df where (operator, lease, date) overlaps intervention_periods
   - non_intervention_hse = hse_df NOT in window

4. PATTERN MINING (candidates, pre-statistical)
   p1: incident rate per intervention service type (7 types)
   p2: incident rate by water depth strata (shelf vs deepwater vs ultra-deepwater)
   p3: incident rate by intervention duration (short < 7d, medium 7-30d, long > 30d)
   p4: incident severity distribution intervention-period vs non-intervention-period
   p5: incident activity-subcategory mix during intervention (PERS vs PSAFE vs CRANE)
   p6: seasonal pattern (hurricane season vs non) of intervention-period HSE
   p7: rig-fleet age correlation with intervention HSE rate (if rig_fleet data joinable)
   p8: vendor-aggregated patterns (anonymized — vendor type, not vendor name)

5. STATISTICAL SANITY CHECK (per pattern)
   - Apply chi-square / Fisher / ANOVA per Metric Contract
   - Suppress any cell with n < 5 per Operator Aggregation Contract rule 2
   - Drop patterns where p > 0.10 OR effect size negligible

6. RECOMMENDATION DRAFTING (per surviving pattern)
   - Frame as engineering-controls (audit cadence, procedure rigor, vendor-qualification
     criteria, equipment-class selection guidance)
   - NOT as regulatory criticism
   - Cite each recommendation back to the pattern + the WRK-013 taxonomy code

7. MEMO ASSEMBLY
   - Top: caveat block (verbatim from Metric Contract)
   - Methodology section
   - 5-8 patterns × {data line, sample size, statistic, confidence caveat, recommendation}
   - Limitations + future work
   - Appendix: matched-ID JSON sidecar reference

8. PUBLIC-REPO POLICY CHECK
   - Grep memo for operator names against a deny-list union (workspace-hub
     .legal-deny-list.yaml ∪ common GoM operator names)
   - If hit: rewrite to aggregate
   - Block commit if any hit remains
```

---

## Files to Change (Phase 1)

| Action | Path | Reason |
|---|---|---|
| Create | `reports/hse/intervention-hse-patterns-2026-05-18.md` | Phase 1 deliverable |
| Create | `reports/hse/intervention-hse-patterns-2026-05-18-stats.json` | Computed counts + matched IDs sidecar |
| Update | `docs/plans/README.md` | Add this plan to index |
| Update | `docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md` | This plan — status transitions to plan-approved on user gate, then to implemented post-execution |

No code module changes in Phase 1. No tests in Phase 1 (synthesis memo).

---

## TDD Test List (Phase 1)

T1 scope = synthesis memo, not code. No new TDD tests.

**Phase 2 (deferred to separate issue)** would extract the queries into a `worldenergydata.bsee.analysis.intervention_hse` module with full TDD coverage — that issue will carry its own test list.

For Phase 1, manual acceptance gates apply (see Acceptance Criteria below).

---

## Acceptance Criteria (Phase 1)

- [ ] Memo at `reports/hse/intervention-hse-patterns-2026-05-18.md` exists with explicit methodology section
- [ ] Caveat block at top matches Metric Contract verbatim text
- [ ] 5-8 candidate patterns surfaced, each with: data-source citation, sample size, statistical test name + statistic + p-value, confidence caveats
- [ ] Each surviving pattern paired with at least one engineering-controls-level recommendation
- [ ] Stats sidecar at `reports/hse/intervention-hse-patterns-2026-05-18-stats.json` contains matched WAR + HSE record IDs for each pattern
- [ ] BSEE coverage gap explicitly noted in limitations section
- [ ] Cross-references back to WRK-012 / WRK-013 taxonomy codes
- [ ] **Operator Aggregation Contract compliance verified**: deny-list grep returns 0 hits for operator names in pattern claims
- [ ] Minimum cell size n ≥ 5 honored across all reported cross-tabs
- [ ] Public-repo policy check passed before commit
- [ ] Plan status transitioned to `implemented` and memo cross-linked

---

## Adversarial Review Summary

**T1 inline self-review (Claude r1)** per `feedback_always_adversarial_review_scale_depth` and `feedback_permission_gate_blocks_cross_review`:

| Provider | Verdict | Key findings |
|---|---|---|
| Claude (self, r1) | MINOR | See findings below |

**Findings (defect-hunting stance per `feedback_adversarial_review_stance`):**

1. **MINOR — Operator/lease join logic is hand-waved**. Pseudocode step 3 says "where (operator, lease, date) overlaps intervention_periods" but BSEE WAR uses operator codes, lease/area codes, and date stamps with format quirks (different files use different ID conventions). The plan should commit to a single normalization function before claiming the join works. **Mitigation**: add to Open Questions; resolve at Phase 1 implementation start before running pattern mining.

2. **MINOR — `intervention-days` denominator is undefined**. Metric Contract defines `service_type_incident_rate` per 1,000 intervention-days, but doesn't specify how an "intervention-day" is counted (calendar day of activity? sum of crew-shifts? overlap-aware?). **Mitigation**: per-pattern denominator definition must be stated in the memo; flag as open question.

3. **MINOR — Pattern selection bias**. With 8 candidate patterns and per-pattern statistical tests at p<0.10, multiple-comparisons risk applies. Bonferroni or false-discovery-rate correction should be considered. **Mitigation**: add Bonferroni correction (effective threshold p<0.0125 for 8 patterns) OR explicitly mark this as exploratory hypothesis-generation, not confirmatory.

4. **MINOR — `IncidentClassifier` reuse confidence-quality assumption**. Plan assumes WRK-013's 89.2% mean confidence on BSEE classification holds at the subactivity level for intervention-specific subcategories. WRK-013 reported confidence at activity level, not subactivity. **Mitigation**: re-verify subactivity-level confidence on intervention-relevant codes during implementation; degrade-gracefully if confidence drops.

5. **MINOR — Hermes parallel-work race for Phase 1?**. Phase 1 is markdown-only and adds two new files in `reports/hse/`. Hermes pickup-queue typically doesn't compete on `reports/hse/` paths, but worth confirming: search Hermes routing config for any rule that would target this path. **Mitigation**: include a Hermes-routing-check as a pre-implementation gate.

6. **MINOR — No public-repo-safe operator deny-list yet**. Plan references "deny-list union (workspace-hub .legal-deny-list.yaml ∪ common GoM operator names)" but the "common GoM operator names" half doesn't exist as a committed list. **Mitigation**: codify the operator-name list in `data/modules/bsee/operator-aggregation-denylist.yaml` as part of Phase 1, OR explicitly downscope Phase 1 to use only the existing legal-deny-list and accept residual risk on common-name catches.

7. **MAJOR? — Does Phase 1 actually need the operator-lease join, or is service-type aggregation sufficient?**. Patterns p1, p2, p3, p4 don't require the operator-lease join — they only need the intervention activity classification + the HSE activity classification. The operator-lease join is only needed for p5, p6, p7, p8. The plan could be split: Phase 1A (service-type patterns, no join) → Phase 1B (operator-aggregate patterns, with join). **Mitigation**: User decides during approval whether to scope down Phase 1 to 1A only and defer 1B.

**Overall verdict**: MINOR — proceed if user accepts the Open Questions resolution path during approval. No MAJOR blockers other than the optional Phase-1A/1B split.

**Revisions made based on self-review:**
- None yet — surfaced for user approval. The user gate is exactly the moment to incorporate these.

---

## Risks and Open Questions

- **Risk (Hermes parallel work)**: 5 Hermes processes active at plan creation. Phase 1 is markdown-only so the risk is low, but per `feedback_hermes_active_preflight_check`: implementation start should `pgrep hermes` again and confirm none of the active sessions are working on intervention or HSE-routed scope.
- **Risk (classifier confidence at subactivity level)**: WRK-013 reported 89.2% at activity level; subactivity confidence may be lower. Implementation must spot-check 20 random intervention-coded records before pattern mining proceeds.
- **Risk (multiple-comparisons inflation)**: 8 candidate patterns × 0.10 threshold = high false-positive risk. Bonferroni correction recommended, OR explicit "exploratory" framing.
- **Risk (longitudinal claims pre-2019)**: BSEE coverage gap blocks any longitudinal claim spanning FY2007-2018 except where based on the partial CY2019/CY2021 data. Memo must filter.
- **Risk (public-repo blowback)**: Even with aggregate framing, an operator who recognizes their pattern profile could push back. Mitigation: the Operator Aggregation Contract's rule 1+2+3, plus a closing note that engagement is welcome for operators who want to dispute or contextualize patterns.
- **Open — Phase 1 scope-split**: should we scope to Phase 1A (service-type only, no operator-lease join) and defer Phase 1B (operator-aggregate, with join) to a follow-on plan? See self-review finding #7.
- **Open — Bonferroni correction or exploratory framing?** See self-review finding #3.
- **Open — Stats sidecar JSON schema**: should it match the #403 pattern (matched_incident_ids + excluded_incident_ids + denominator labels)?
- **Open — Cross-link in aceengineer-website?**: if the memo passes, should we add a link from `aceengineer-website/docs/marketing/PORTFOLIO_CAPABILITIES.md` to the published memo? Asks the user to decide pre-implementation so the cross-link is part of Phase 1 acceptance.

---

## Complexity: T1

**T1** — Phase 1 is a single new markdown file (plus stats sidecar JSON) in `reports/hse/`. No code modules added. No tests required. Single-author inline self-review per `feedback_always_adversarial_review_scale_depth` is appropriate at this scope. Phase 2 (code module extraction) would be T2 and carry its own plan with TDD + cross-provider review.

---

## Status transitions

```
draft → adversarial-reviewed (T1 self-review inline above) → plan-review (this commit)
       → USER APPROVES (label: status:plan-approved) → implemented (post-execution)
```

Per must-fire rule `feedback_never_offer_to_self_label_plan_approved`: this plan will NOT self-apply `status:plan-approved`. User-in-loop is load-bearing.
