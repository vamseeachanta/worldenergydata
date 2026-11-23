Adversarial cross-review complete for the draft plan.

Verdicts
- Codex: MAJOR
- Gemini: MINOR

Shared outcome
- Not ready for plan-review yet because Codex returned MAJOR.

Main blockers from review
1. The deterministic FX/base-year/escalation policy is still unresolved, so expected normalized outputs are not approval-ready.
2. Correct repo-grounding: some cited regression tests do not exist and file targets are still too vague.
3. Keep this issue tightly limited to normalization/comparability only, without leakage into linkage (#335) or consumer views (#338).
4. Preserve all parent disclosure fields, not just amount/currency/unit.

Artifacts
- `scripts/review/results/2026-04-22-plan-336-codex.md`
- `scripts/review/results/2026-04-22-plan-336-gemini.md`
