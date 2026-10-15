# Flaky-test register

The informational register at `.github/ci/flaky-register.yml` records suspected
or confirmed intermittent failures and their evidence. It never deselects,
skips, or quarantines tests. Runtime test code does not consume the register;
only its schema contract test reads it.

During the daily main-health loop, add or update entries from run evidence;
close an entry with its fix PR by setting `status: fixed`, recording the PR
number in `fix_issue`, and updating `last_seen` to the latest observed failure.

Each entry contains:

- `id`: a unique test node ID or check identifier.
- `kind`: `retry-pass`, `same-tree-mismatch`, or `signal-exit`.
- `first_seen` and `last_seen`: quoted ISO dates of observed failures.
- `evidence`: a non-empty list of GitHub Actions run or job URLs.
- `cause`: the observed failure mechanism, with uncertainty stated explicitly.
- `fix_issue`: a positive fix PR number, or `pending` until one exists.
- `status`: `open` or `fixed`.

The initial tracker entry is a `retry-pass` candidate: concurrent initialization
failed at the WAL journal switch with `database is locked`. A successful retry
has not been established; the entry does not assert one or change CI outcomes.
