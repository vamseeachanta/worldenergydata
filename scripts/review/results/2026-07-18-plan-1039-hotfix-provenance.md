# [#1039](https://github.com/vamseeachanta/worldenergydata/issues/1039) manifest-lineage hotfix plan review — provenance and attacks

**Stage:** plan review, round 1

**Stance:** default non-approval

**Initial verdict:** NOT APPROVED

## Findings

1. **Important — executable environment was absent.** The draft created a fresh worktree but invoked `.venv/bin/*` without provisioning `.venv`.
2. **Important — hostile identity coverage was overstated.** The draft did not use real Git to reject an orphaned feature commit, a fabricated 40-hex commit, and an existing non-ancestor.
3. **Important — runtime reproduction intelligence was not captured.** The draft needed the failing CI run, cross-version node, prior-run comparison, ancestry result, and builder-blob evidence.
4. **Minor — reviewed-base drift was not fail-closed.** Worktree creation needed to stop if `origin/main` moved beyond the reviewed merge SHA.

## Required disposition

The plan will provision with `uv sync --all-extras`, pin worktree creation to `66ce9d6808492a01f6a7cac60415304bcc6e6ef5`, record the captured evidence, and create focused real-Git lineage attacks. The current 400-line hardening file will remain untouched.
