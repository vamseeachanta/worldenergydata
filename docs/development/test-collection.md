# Test collection

The root `pyproject.toml` is the sole pytest configuration. Tests use
`--import-mode=importlib` so independent files can share a basename. Collection
has no `--maxfail` cutoff. This cleanup addresses issue #313; it does not change
engineering calculations or their acceptance limits.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Document collection rules and a reproducible duplicate-name example. |
| 1 | 2026-11-16 | Separate matrix collection evidence from runtime outcomes. |
| 2 | 2026-11-18 | Keep parallel runtime tests running after collection fails. |

## Package imports

Use `worldenergydata.sodir.*`, `worldenergydata.bsee.*`, and
`worldenergydata.well_production_dashboard.*` in tests and mock targets.
Shared test helpers use qualified `tests.*` imports; pytest adds the repository
root to its Python path so these work from any working directory.
Install the workspace packages before running tests; adding only the root
`src` directory does not expose domains contributed by workspace members.

The BSEE member already contains `type_curves/blasingame.py`, `fetkovich.py`,
and `models.py`. The compatibility redirect supports the old
`worldenergydata.modules.bsee` imports. Tests exercise the canonical modules
and confirm that the compatibility imports resolve to the same objects.

The root distribution requires the FDAS member, whose runtime dependencies
include `numpy-financial`. This dependency is available without development
extras; a regression checks the dependency chain and imports the financial module.

SODIR HTTP mocks target `worldenergydata.sodir.transport.requests.Session.get`,
where requests are made. Router tests mock data collection rather than requesting
live data. The absent cost proxy-comparison implementation has no supported
import target; its orphaned test is removed rather than inventing an API.

## Worked example: duplicate basenames

Inputs are independent directories, each containing `test_end_to_end.py` with
one test function. The expected result is **two passing tests**: one function
in each directory, counted directly. No engineering equation or physical
coefficient is involved.

After installing the test dependencies, run:

```bash
uv run python -m pytest tests/ci/test_collection_contract.py \
  -k duplicate_basenames_collect -p no:cacheprovider
```

The regression writes the two files into pytest's temporary directory, copies
the real root configuration there, and starts a child pytest process. It asserts
that both functions execute. With the former `prepend` import mode the second
file collides with the first in `sys.modules`; with `importlib` both pass.

The behavior and the expected outcome follow the
[pytest import mechanisms documentation](https://docs.pytest.org/en/stable/explanation/pythonpath.html#import-modes):
`importlib` derives unique module names and does not require unique test filenames.
The example is also an independent hand count, not an output calculated by the
implementation under test.

## Checks and limits

Collection regressions also check that repaired targets are excluded neither by
configuration nor by the collection hook. Unrelated archive, missing-dependency,
and missing-fixture exclusions remain separate maintenance work.

Successful collection establishes importability, not correctness of every
legacy assertion. Runtime failures in older SODIR and dashboard tests require
separate API and fixture reconciliation. A local check does not establish a
passing hosted Python matrix.

## Daily matrix collection evidence

The existing `full-suite` job in `main-full-run.yml` collects tests separately
on Python 3.10, 3.11 and 3.12 after dependency installation and before execution.
The parallel target expression is evaluated once and shared by collection and
execution. Collection adds the sequential `tests/integration tests/performance`
targets, retains the root pytest configuration and disables the pytest cache.
It uses no parallel workers and adds no exclusions or skips.

Each interpreter uploads `collection-evidence-<version>` containing
`collection.log` and `summary.txt`. Both files are written under `runner.temp`,
outside the checkout, to respect the test tree-preservation guard.
The summary records the source revision, actual interpreter version, selected
test count, pytest return status and step status. A missing count is recorded
as `unknown`; an unknown or zero count cannot turn a successful command into
accepted collection. Nonzero pytest status is preserved. The upload runs even
on failure, and the original failure still fails the job. Dependency setup
failure skips collection, so missing evidence does not claim a collection result.

The existing `tests/ci/test_collection_contract.py` also runs independently of
the target expression, including after a collection failure. It guards the
repaired imports, runtime dependency chain and duplicate test basenames.
The runtime test selections and arguments remain the same.
When target selection succeeds and the job is not cancelled, parallel runtime
tests run even if collection or the collection contract fails. The collection
failure still fails the job.
Coverage is not uploaded to Codecov when collection fails.

`tests/workflows/test_collection_evidence.py` checks the matrix, target sharing,
step order and artifact location. Synthetic suites exercise successful, broken
and empty collection with real pytest; altered workflows demonstrate detection
of omitted interpreters, hidden targets, failure masking and a missing runtime
condition.

Local regressions establish the workflow contract, not a passing hosted matrix.
The final matrix criterion requires all three hosted collection steps to finish
with status zero and positive selected counts. Runtime correctness remains a
separate result. Existing optional-dependency and legacy collection problems
remain visible for follow-up rather than being excluded to obtain success.
