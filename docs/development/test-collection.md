# Test collection

The root `pyproject.toml` is the sole pytest configuration. Tests use
`--import-mode=importlib` so independent files can share a basename. Collection
has no `--maxfail` cutoff. This cleanup addresses issue #313; it does not change
engineering calculations or their acceptance limits.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Document collection rules and a reproducible duplicate-name example. |

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
