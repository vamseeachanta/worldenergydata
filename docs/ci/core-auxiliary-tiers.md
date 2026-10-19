# Core and auxiliary CI test tiers

## Summary

The PR domain workflow uses an explicit core selector. Broad integration and
performance suites run in the existing full matrix on main, nightly, manual
runs, and PRs carrying `ci-full`. Reporting publication contracts remain core.
This implements test routing and post-merge failure reporting from issue #466;
it does not change repository rulesets or establish a merge-time improvement.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Separate auxiliary targets from the core selector and report failures without adding a PR dependency. |

## Selection contract

[`select_test_targets.py`](../../scripts/ci/select_test_targets.py) keeps its
historical full selection by default. Its `--tier core` option removes broad
sequential integration/performance targets from both flat and matrix output.
It preserves every unit domain, other parallel suites, exact contract routes,
and the existing always-on contracts. Shared-code changes still fan out all
unit domains; this change does not exclude an entire unit domain.

[`select_core_test_targets.py`](../../scripts/ci/select_core_test_targets.py)
adapts the reusable workflow's selector interface to this option. The PR caller
sets its `selector` input to the adapter, without changing the shared workflow.
Both selectors keep the existing output keys, shard modes and scope names.
The core adapter fixes the tier even when another tier is supplied in arguments.
Edits under `tests/ci/` select that suite so routing regressions test themselves.

`tests/integration/reporting` is an explicit core exception because the existing
always-on policy treats publication contracts as blocking checks. Shared-code
changes include that directory once rather than collecting broad integration.
General integration-module edits still run the always-on core contracts; their
integration suites run after merge or in an explicitly requested full run.

## Auxiliary failure reporting

The full test commands and Python matrix in
[`ci.yml`](../../.github/workflows/ci.yml) remain unchanged. A separate reporting
job depends only on that matrix. On a failed main push, scheduled run, or manual
main run, it creates an issue titled `Auxiliary CI test failure` with the run,
commit and branch. An existing open issue with that title prevents duplicates;
later failures remain visible in workflow history. Pull requests with the same
title do not suppress reports. API failures remain visible as reporting errors.
Reporting jobs serialize the lookup and creation to avoid concurrent duplicates.

The reporting job alone has issue-write permission. It does not run on PRs or
feature-branch manual runs and is not a dependency of any gate. Existing nightly
workflow reporting is unchanged, so a separate nightly failure may still create
its existing notification.

## Evidence and limits

The policy source is issue #466's core/auxiliary update, with the single aggregate
gate described in #526 and the reusable selector interface described in #530.
The public [github-script documentation](https://github.com/actions/github-script#readme)
documents the injected API clients and pagination used by failure reporting.

The routing tests use independently enumerated target sets in synthetic test
trees. The reporting tests execute the workflow's JavaScript with fake API
clients and an explicit event/result truth table. No live issue is created by
these tests, and no speedup or runtime threshold is assumed.

The following remain later slices:

- Audit slow, live and data-backed tests inside otherwise core directories.
  This selector classifies test targets, not individual test requirements.
- Make lint/type/security/docs change-aware and confirm the required-check set.
  Those existing checks and their gate wrappers are unchanged here.
- Configure and validate merge queue support or relax the up-to-date rule.
  No repository setting changes are included, and queue events are not enabled.
- Measure end-to-end merge time on a representative hosted PR after rollout.
  Local routing tests do not measure the up-to-date rerun cascade.
- Confirm issue-write permissions and deduplication during an actual failed
  auxiliary run. API behavior is tested with fixtures only.
