# [#1039](https://github.com/vamseeachanta/worldenergydata/issues/1039) manifest-lineage hotfix plan review — TDD and repository standards

**Stage:** plan review, round 1

**Stance:** default non-approval

**Initial verdict:** NOT APPROVED

## Findings

1. **Important — fresh-worktree commands were not runnable.** Ignored virtual environments do not transfer to Git worktrees; Black 25.9.0 also needed verification from the locked environment.
2. **Important — the squash fixture did not exercise the deleted feature producer.** Branch deletion alone did not prove rejection.
3. **Important — legal scanning occurred after the test commit.** The diff-only scanner would therefore miss the committed test file.

## Required disposition

The plan will use `uv run` consistently, verify Black 25.9.0, test the deleted feature commit directly, and run the legal scan before committing the test-first change.
