Adversarial cross-review complete for the draft plan.

Verdicts
- Codex: MAJOR
- Gemini: APPROVE

Shared outcome
- This plan is not ready for plan-review yet because a single MAJOR blocks approval readiness.

Main blockers from review
1. Make the dependency on #334 explicit; current repo main does not yet contain the disclosure-layer surfaces this plan assumes.
2. Carry the parent invariant more explicitly: only project-scope disclosure rows are linkable; operator rows are never linkable.
3. Fix the helper contract so injected empty lists do not fall back to `load_public_dataset()`.
4. Reconsider or better justify placing linkage result types in `calibration_schema.py`.
5. Add negative exactness tests and direct regression checks for `load_public_dataset()` behavior.

Artifacts
- `scripts/review/results/2026-04-22-plan-335-codex.md`
- `scripts/review/results/2026-04-22-plan-335-gemini.md`
