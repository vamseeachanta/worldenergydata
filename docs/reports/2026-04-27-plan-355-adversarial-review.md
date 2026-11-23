# Adversarial Plan Review — Issue #355

Verdict: MAJOR (resolved by plan revision before plan-review handoff)

## Findings

1. Plan was directionally correct but left Phase 3/4/5 as menus instead of decisions.
2. Test strategy could pass on string mentions instead of structured doc coverage.
3. Scope overlap with #354 around `worldenergydata info` and taxonomy needed an explicit boundary.
4. Smoke contract included unverified runtime commands and did not choose script vs pytest.
5. Notebook scope was ambiguous.
6. LLM guardrail remediation needed exact target files and minimal opt-in behavior.
7. Audit had 14 vs 15 wording inconsistencies; implementation should use `cli/main.py` as source of truth.

## Required plan fixes applied

- Decide `docs/COMMANDS.md` handling: add disambiguating banner, no delete/rename in this issue.
- Decide stale examples handling: quarantine in `examples/README.md`; direct rewrites are deferred unless trivial and test-backed.
- Decide smoke vehicle: static pytest/docs tests first; runtime smoke optional/pending #353.
- Declare `worldenergydata info` implementation is owned by #354; #355 may mention it only as cross-reference.
- Declare notebooks out of implementation scope except for documentation cross-reference to existing quickstarts.
- Define LLM example target files and minimal opt-in guard (`WORLDENERGYDATA_RUN_LLM_EXAMPLES=1` or equivalent) before model load.
- Tighten tests to parse CLI registrations from `cli/main.py` and assert structured docs rows/classifications.
