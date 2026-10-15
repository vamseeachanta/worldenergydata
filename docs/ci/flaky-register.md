# Flaky-test register

The informational register at `.github/ci/flaky-register.yml` records suspected
or confirmed intermittent failures and their evidence. It never deselects,
skips, or quarantines tests. Runtime test code does not consume the register;
only its schema contract test reads it. A contract test checks that no file
under `.github/workflows/`, `scripts/ci/`, or any `conftest.py` references it.

During the daily main-health loop, add or update entries from run evidence;
close an entry with its fix reference by setting `status: fixed`, recording the
issue or pull request number in `fix_issue`, and updating `last_seen` to the
latest observed failure. A fixed entry requires a positive integer reference.

Each entry contains:

- `id`: a unique test node ID or check identifier.
- `kind`: `retry-pass`, `same-tree-mismatch`, or `signal-exit`.
- `first_seen` and `last_seen`: quoted ISO dates of observed failures.
- `evidence`: a non-empty list of Actions URLs in this repository, including at
  least one job URL of the exact form
  `https://github.com/vamseeachanta/worldenergydata/actions/runs/<digits>/job/<digits>`.
  A run URL may provide extra context but cannot suffice alone.
- `seen_on`: `main` or `pull_request`.
- `main_run` and `main_job`: positive integer identifiers of the observed main
  failure, with that exact job URL in `evidence`; both are explicitly `null`
  when `seen_on` is `pull_request`.
- `unrelated_because`: a non-empty plain-words reason that a failure observed on
  a pull request is unrelated to that change; explicitly `null` for `main`.
- `cause`: the observed failure mechanism, with uncertainty stated explicitly.
- `fix_issue`: a positive issue or pull request number, or `pending` while open.
- `status`: `open` or `fixed`.

The kinds describe the observed evidence:

- `retry-pass`: the failing test or check passed on a subsequent attempt with
  the same tree and job configuration.
- `same-tree-mismatch`: the same test or check has both a failure and a pass
  on the same tree in distinct jobs or configurations.
- `signal-exit`: the process terminated with a signal rather than an ordinary
  test assertion, with the signal recorded in the evidence.

The initial tracker entry is a `same-tree-mismatch`: concurrent initialization
failed at the WAL journal switch with `database is locked` under Python 3.11,
while the same commit passed under Python 3.12. No retry has been observed;
the entry does not change CI outcomes.
