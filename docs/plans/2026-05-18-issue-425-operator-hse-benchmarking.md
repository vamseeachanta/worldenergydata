# Plan for #425: feat(analysis): operator-aggregate HSE benchmarking

> **Status:** plan-review
> **Complexity:** T2 — analysis + HTML + strictest aggregation discipline of the pipeline
> **Date:** 2026-05-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/425
> **Parent**: [#423](https://github.com/vamseeachanta/worldenergydata/issues/423)
> **Review:** Inline T1 self-review

---

## Resource Intelligence Summary

### Existing repo code and artifacts
- Found: `data/modules/hse/hse_incidents.db` (97,993 rows; per [#416](https://github.com/vamseeachanta/worldenergydata/issues/416) Phase 0 — 66.5K BSEE INC + 312 INCINV + 29K OSHA)
- Found: `src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py` — produces 14-activity / 74-subactivity codes
- Found: [`reports/hse/wrk013_hse_mishap_analysis.md`](../../reports/hse/wrk013_hse_mishap_analysis.md) — taxonomy methodology
- Gap: no existing aggregation tooling that enforces n≥10 cell minimum AND anonymizes operators to quartile distributions

### Standards consulted
- Operator Aggregation Contract from [#416 plan](2026-05-18-issue-416-intervention-hse-patterns.md) — must inherit and strengthen for this issue
- `aceengineer-website/docs/marketing/PORTFOLIO_CAPABILITIES.md` — "Energy Companies" value-prop language

### Documents consulted
- [#420](https://github.com/vamseeachanta/worldenergydata/issues/420) operator-aggregation deny-list — HARD blocker. Must land first.
- [#416](https://github.com/vamseeachanta/worldenergydata/issues/416) intervention HSE — Phase 1A must land first (proves source-prefix filter + classifier reuse)
- [#418](https://github.com/vamseeachanta/worldenergydata/issues/418) reusable module extraction — Phase 2 of intervention HSE; this issue depends on it

### Gaps identified
- No quartile / anonymization tooling exists
- No reverse-identifiability test surface in the codebase

### Evidence
**Issue statuses**:
- `#425` — OPEN
- `#420` — OPEN (BLOCKER for this issue)
- `#416` — OPEN (Phase 1A in flight; partial blocker)
- `#418` — OPEN (preferred dependency)

---

## Deliverable

`reports/hse/operator-hse-benchmarking-2026-XX-XX.md` + interactive HTML at `reports/hse/operator-hse-benchmarking-2026-XX-XX.html` presenting peer-group quartile distributions of HSE incident rates across operators with NO operator names anywhere in the artifact. Stats sidecar contains anonymized operator IDs (`OP_A`, `OP_B`, ...) for reproducibility but the mapping is never published.

## Pseudocode

```
1. SOURCE-FILTER hse_incidents to BSEE-only (per #416 source-prefix finding)
2. CLASSIFY via IncidentClassifier(source='bsee')
3. NORMALIZE operator names (#420 deny-list + dedup)
4. CALCULATE per-operator per-activity-code incident rates
   - Denominator: BSEE production-volume + WAR activity-days proxy
5. ANONYMIZE: assign operators random IDs (OP_A, OP_B, ...); reseed daily for non-reproducibility across runs
6. AGGREGATE: per-activity-code quartile distributions (Q1, median, Q3, count)
7. PEER-GROUP: cluster operators by activity portfolio (deepwater-heavy vs shelf-heavy vs mixed)
8. WIDE-SPREAD IDENTIFICATION: per peer-group per activity, flag where IQR is wide → improvement opportunity
9. REVERSE-IDENTIFIABILITY TEST (mandatory pre-publish):
   - Could any combination of (peer-group, activity, rate-stratum, sample-size) uniquely identify an operator?
   - If yes: merge cells until uniqueness disappears
10. HTML REPORT
   - Box-and-whisker per peer-group per activity
   - Methodology section explicit about anonymization
   - NO operator names, NO field names, NO lease numbers
11. PRE-COMMIT SCAN
   - Workspace-hub legal-deny-list
   - #420 operator-aggregation deny-list
   - Plus regex sanity for `[A-Z][a-z]+ Oil|[A-Z][a-z]+ Energy|[A-Z][a-z]+ Petroleum` accidental leakage
```

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `scripts/exploration/operator_hse_benchmark_explore.py` | Anonymized quartile build |
| Create | `reports/hse/operator-hse-benchmarking-2026-XX-XX.md` | Memo |
| Create | `reports/hse/operator-hse-benchmarking-2026-XX-XX.html` | HTML report |
| Create | `reports/hse/operator-hse-benchmarking-2026-XX-XX-stats.json` | Stats sidecar (anonymized IDs only) |
| Update | `docs/plans/README.md` | Plan index |

## TDD Test List

| Test | Verifies |
|---|---|
| `test_anonymization_reseed` | OP_X mapping differs across runs (no stable mapping in artifact) |
| `test_min_cell_size` | every published cell has n≥10 |
| `test_no_operator_name_leak` | regex scan of artifact catches accidental leaks |
| `test_reverse_identifiability` | given the published data, can a synthetic adversary triangulate an operator? |

## Acceptance Criteria

- [ ] Quartile-based peer-group analysis with min cell size n≥10
- [ ] NO operator names in any committed artifact
- [ ] Reverse-identifiability test passes (no unique-cell identification)
- [ ] Operator-aggregation deny-list ([#420](https://github.com/vamseeachanta/worldenergydata/issues/420)) scanner passes
- [ ] Workspace-hub legal-deny-list scanner passes
- [ ] HTML report variant
- [ ] Methodology section explicit about anonymization technique + reverse-identifiability mitigation

## Adversarial Review Summary

**T1 inline self-review (Claude r1):**

1. **MAJOR — Anonymization reversibility risk**: even with random IDs, if a sophisticated reader knows total operator count + per-operator activity portfolio, they can de-anonymize via auxiliary public data. Mitigation: drop sample-size column from published artifact; show only quartile boundaries.
2. **MINOR — Denominator volatility**: production-volume denominators fluctuate year-to-year; rate calculations need explicit time-window normalization.
3. **MINOR — Peer-group definition is subjective**: deepwater-heavy / shelf-heavy / mixed is one cut; alternative cuts (size, age) may produce different stories. Mitigation: publish the chosen cut with rationale; acknowledge alternatives in methodology.
4. **MINOR — Multi-year vs single-year**: which window? Multi-year smooths noise but may mask recent trends. Mitigation: 3-yr trailing window, sensitivity-tested at 1-yr and 5-yr.

**Overall**: 1 MAJOR (anonymization reversibility) requires explicit mitigation BEFORE execution. If not mitigated, this piece should NOT ship.

## Risks and Open Questions

- **Risk (high)**: anonymization reversibility — see Adversarial Review #1
- **Risk**: this is the riskiest portfolio piece for backlash. If an operator triangulates their identity and disputes the methodology, A&CE bears reputational cost.
- **Open**: should the report explicitly invite operator engagement to contextualize patterns?
- **Open**: defer this issue until #416 and #420 land, OR start exploratory work on the anonymization tooling in parallel?

## Complexity: T2

Multi-file with non-trivial anonymization logic and reverse-identifiability testing. Among the pipeline pieces, this requires the strictest discipline.
