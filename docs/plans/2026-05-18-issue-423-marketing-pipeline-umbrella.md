# Plan for #423: epic(marketing): Engineering Analytics from Public Regulatory Data — long-term marketing pipeline

> **Status:** plan-review
> **Complexity:** T1 — umbrella / governance only; no analysis or code execution at this level
> **Date:** 2026-05-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/423
> **Review artifacts:** Inline T1 self-review (per `feedback_always_adversarial_review_scale_depth`)

---

## Resource Intelligence Summary

### Existing repo code and artifacts
- Found: existing intervention dashboards at `reports/bsee/intervention/*` (Feb 2026) — market intel cuts
- Found: `reports/gtm/2026-05-04-bsee-field-analysis-comprehensive.html` — LT field economics analog
- Found: `reports/hse/wrk012_hse_data_audit.md` + `wrk013_hse_mishap_analysis.md` — foundational HSE coverage + classifier
- Found: `src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py` — 89.2% confidence rule-based classifier
- Found: `src/worldenergydata/bsee/analysis/intervention/` — 9-module analysis package
- Gap: no umbrella tracking how these analytical pieces tie together as a marketing pipeline

### Standards / wiki / docs consulted
- `aceengineer-website/docs/marketing/PORTFOLIO_CAPABILITIES.md` — describes the in-place capability ecosystem
- `worldenergydata/docs/HTML_REPORTING_STANDARDS.md` — output format contract for human-facing reports
- `worldenergydata/CLAUDE.md` — "Data attribution + timestamp required | All visualizations: interactive HTML"

### Documents consulted
- Issue [#416](https://github.com/vamseeachanta/worldenergydata/issues/416) — intervention HSE umbrella (first child of this pipeline)
- Issue [#403](https://github.com/vamseeachanta/worldenergydata/issues/403) — hurricane mooring (parallel pipeline thread, status:working)
- Children filed in this batch: [#424](https://github.com/vamseeachanta/worldenergydata/issues/424), [#425](https://github.com/vamseeachanta/worldenergydata/issues/425), [#426](https://github.com/vamseeachanta/worldenergydata/issues/426), [#427](https://github.com/vamseeachanta/worldenergydata/issues/427)

### Gaps identified
- No published umbrella ties intervention dashboards + field economics + #403 + #416 into a coherent marketing pipeline
- No committed cross-piece contracts (Operator Aggregation Contract is currently inside #416's plan, not pipeline-level)

### Evidence
**Issue statuses** (verified 2026-05-18 via `gh issue view`):
- `#423` — OPEN — this issue
- `#424-#427` — OPEN — children filed in same batch
- `#416` — OPEN — first child of pipeline, in flight
- `#403` — OPEN — parallel thread, status:working

**No reproduction proof needed** — this is governance / umbrella tracking, not an alleged failure.

---

## Deliverable

This umbrella issue itself executes **no analytical work** — it tracks the pipeline. The deliverable IS this issue: a single durable landing page tying child issues, shared infrastructure, and shared contracts together.

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create (this) | `docs/plans/2026-05-18-issue-423-marketing-pipeline-umbrella.md` | This plan |
| Update | `docs/plans/README.md` | Index entry for this + 4 children |
| (Future child) | each #424-#427 lands its own report at `reports/hse/*` or `reports/gtm/*` | Tracked separately |
| (Future) | `aceengineer-website/docs/marketing/PORTFOLIO_CAPABILITIES.md` | Cross-link to landed pieces; updated as each child ships |

## Pseudocode

Not applicable — umbrella scope is structural, not code.

## TDD Test List

Not applicable.

## Acceptance Criteria

Per the issue body — umbrella-level:
- [ ] 5+ analytical artifacts published in `reports/` by 2026Q3 end
- [ ] Reusable `worldenergydata.bsee.analysis.intervention_hse` module ([#418](https://github.com/vamseeachanta/worldenergydata/issues/418)) extracted by 2026Q3 end
- [ ] Operator-aggregation deny-list policy ([#420](https://github.com/vamseeachanta/worldenergydata/issues/420)) ratified before any operator-aggregate piece ships
- [ ] All artifacts pass legal-sanity-scan
- [ ] Each artifact cross-linked from aceengineer-website portfolio

## Adversarial Review Summary

**T1 inline self-review (Claude r1):**

| Provider | Verdict | Key findings |
|---|---|---|
| Claude (self, r1) | MINOR | See below |

1. **MINOR — Umbrella issues drift**: 5+ artifact target is calendar-bound but the dependency graph (each child blocks on its own prerequisites) may slip. Mitigation: track via `gh issue list` weekly comment on this issue.
2. **MINOR — No code ownership at umbrella level**: this could become a wishlist if no child carries ownership. Mitigation: explicit child plans + status labels per child track real progress.
3. **MINOR — Aceengineer-website cross-link coordination**: if multiple children land at different times, the portfolio doc could update incrementally. Acceptable; each child's PR opens a small portfolio-doc update.

**Overall**: MINOR — umbrella plans typically have minor surface; the real review burden falls on each child.

---

## Risks and Open Questions

- **Risk**: portfolio drift if children execute opportunistically without portfolio-level coordination. Mitigation: this umbrella + a weekly `gh issue list` audit comment.
- **Risk**: shared contracts (Operator Aggregation Contract from #416) need promotion from child-plan-scope to pipeline-scope. Open question: codify as `.claude/rules/marketing-public-data-analysis.md` or keep in #416's plan with cross-links? Recommend codifying once 2+ children adopt it.
- **Open**: pacing — do we target steady-state 1 child per 2-3 weeks, or burst-execute when capacity opens?

## Complexity: T1

Umbrella scope is structural / governance. No analysis, no code, no TDD. Plan exists primarily to capture the cross-piece contracts and dependency graph for reviewers.
