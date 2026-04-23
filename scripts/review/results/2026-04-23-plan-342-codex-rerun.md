# Plan Review Artifact — Issue #342 — Codex (rerun)

- Verdict: MAJOR
- Retrieval adequacy: adequate

Key findings
- The revised draft still does not identify the exact proxy-rate source, canonical internal proxy keys, or the one-to-one mapping from sanctioned dataset region labels to those keys.
- The plan still leaves a compatibility decision open in `Risks and Open Questions` by saying it may need to decide whether to wrap or rewrite the test, contradicting the stated restore strategy.
- The public API surface is still underspecified beyond symbol names; constructor shape, required fields, return ordering/stability, and explicit compatibility expectations are not pinned tightly enough.
- Some TDD items remain too vague (`valid confidence values`, `multiple normalized regions covered`, `required fields present`) and need exact expectations.
- The plan still allows minimal test modification without explicitly forbidding weakening or retargeting the regression boundary.
- Unfitted-predictor behavior is in TDD but not acceptance-gated.

Main blockers to fix
1. Lock the adapter design: specify the exact proxy-rate source, explicit sanctioned-label-to-proxy-key mapping, and whether the adapter computes directly from sanction-layer data or wraps a named existing implementation.
2. Tighten the compatibility contract: define dataclass fields/call signatures, enumerate valid confidence values and region expectations, require unfitted-predictor support in acceptance criteria, and forbid test weakening/retargeting as part of the restore.
