# Adversarial plan review — #1040 replan — R3 inline synthesis

**Reviewed base:** `5b2cf22` plus the R1/R2 patches on `chore/1040-plan-hotfix`
**Verdict:** APPROVE FOR USER DECISION

The main session rechecked every R1/R2 finding against the final HTML plan. The plan now:

- freezes v1 behind an independent manifest SHA and verifies its closed executable producer set;
- requires explicit, provenance-bearing owner approval for taxonomy/accounting/portfolio reuse while deferring scenario shares;
- persists stable project, award, and requirement keys plus canonical source locators and an append-only lifecycle ledger;
- separates per-award scope components, link edges, resolution summaries, counting decisions, and raw accounting rows;
- fails closed on coarse classes, unknown CAPEX bases, missing currencies, and the GranMorgu `point`/unequal-bounds anomaly;
- defines exact coverage sets, denominators, zero behavior, and bundle de-duplication;
- enumerates implementation/test paths, literal TDD nodes, hostile rendering/CSV/URL cases, and enforced size limits; and
- splits code and publication PRs so the final manifest points to a durable squash commit, including depth-one trusted-main hydration and independent hostile lineage fixtures.

Claude and Gemini were unavailable and are recorded separately. The available review was performed through three independent Codex defect-hunting lanes plus main-session R3 closure. Because this is not three-provider consensus, the plan remains `status:plan-review` until the user evaluates and approves the explicit decision; no production implementation is authorized.
