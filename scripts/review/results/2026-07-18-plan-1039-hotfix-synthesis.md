# [#1039](https://github.com/vamseeachanta/worldenergydata/issues/1039) manifest-lineage hotfix plan review — synthesis

**Stage:** plan review

**Review scale:** T3, three independent adversarial runtime reviewers

**Initial consensus:** NOT APPROVED

**Post-remediation verdict:** READY FOR USER APPROVAL

The current runtime exposed parallel subagents but not distinct external-provider identities. The three reviewers therefore attacked separate provenance, standards/TDD, and governance axes; this artifact does not misrepresent them as Claude/Codex/Gemini provider consensus. The implementation plan still requires the repository's named three-provider code/artifact review before merge, with documented degradation if a provider is unavailable.

## Finding disposition

| Finding class | Resolution in reviewed plan |
|---|---|
| Missing worktree environment | `uv sync --all-extras`; all execution uses `uv run`; Black 25.9.0 is verified |
| Missing hostile lineage tests | New focused test file exercises orphaned feature, fabricated 40-hex, existing non-ancestor, and missing-origin cases through real Git |
| Existing 400-line test file | Remains unchanged; focused lineage coverage moves to a new bounded file |
| Missing reproduction evidence | Resource Intelligence records the failing run, all three Python jobs, prior-run control, ancestry failure, and builder hash |
| Mutable reviewed base | Worktree creation asserts exact merge SHA and stops for re-review if `main` advances |
| Legal scan timing | Scan runs before the test-first commit and again before the manifest commit |
| Stale approval authorization | Explicit hotfix-plan approval hard stop plus plan-specific marker |
| Generalized lineage deferral | [#1048](https://github.com/vamseeachanta/worldenergydata/issues/1048) will receive a linked scope amendment covering squash/rebase, shallow clones, and deleted branches |
| Review/CI closeout ambiguity | Exact provider artifact paths, degradation record, PR checks, merge SHA, run ID, and failed-log grep are specified |

## Residual gate

No implementation is authorized by this review. The user must approve the exact reviewed plan before `status:plan-approved` and `.planning/plan-approved/1039-hotfix.md` may be applied.
