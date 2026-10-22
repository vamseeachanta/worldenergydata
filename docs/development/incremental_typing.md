# Incremental typing

The typing cleanup in issue #316 uses module-by-module annotation fixes: fully
check selected shared modules, retain the existing global mypy settings, and
expand the checked set as each later module is ready. This increment covers
`worldenergydata.common.exceptions`, `worldenergydata.common.logging` and
`worldenergydata.common.types`. Their source files live in
`packages/worldenergydata-core/src/worldenergydata/common/`.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-20 | Document the first checked common modules and their consumer example. |

## Policy

- Annotate every function signature in a selected module, including constructor
  returns. Preserve runtime behavior and public call signatures.
- Keep `disallow_untyped_defs`, `warn_return_any` and `warn_unused_configs`
  enabled. Do not add blanket `ignore_errors` overrides or suppress individual
  diagnostics to declare a module clean.
- Keep `Any` at the existing heterogeneous payload boundaries: error context,
  logging keyword arguments and record metadata. It does not replace known
  scalar types such as logger names, success flags or page counts.
- Check the selected implementations directly. `--follow-imports=silent` limits
  diagnostics from imports outside the selected set; it still analyzes those
  imports. `--ignore-missing-imports` matches the existing CI invocation and does
  not excuse errors in the explicitly checked source files.
- Add valid consumer calls and invalid argument checks alongside runtime tests.
  A negative test must fail on its intended argument, rather than an import or
  implementation error.
- Expand the explicit CI file list when another module and its tests are ready.
  The existing full-tree diagnostic step remains in place.

The module imports must resolve from the root namespace and the core workspace
member when running without an installed workspace:

```bash
export PYTHONPATH=src:packages/worldenergydata-core/src
export MYPYPATH="$PYTHONPATH"
uv run mypy --explicit-package-bases --follow-imports=silent \
  --ignore-missing-imports \
  packages/worldenergydata-core/src/worldenergydata/common/exceptions.py \
  packages/worldenergydata-core/src/worldenergydata/common/logging.py \
  packages/worldenergydata-core/src/worldenergydata/common/types.py \
  examples/typed_common.py
uv run python -m pytest --noconftest -o addopts='' -p no:cacheprovider \
  tests/unit/common/test_typing_contracts.py \
  tests/unit/common/test_exceptions.py \
  tests/unit/common/test_logging.py \
  tests/unit/common/test_types.py
```

The pytest command uses explicit test files and clears repository-wide coverage
output options so this focused check does not create report artifacts.

## Worked example

Run `uv run python examples/typed_common.py` with the same `PYTHONPATH`.
The inputs are three synthetic records named north, south and west, with a page
size of two. These are illustrative inputs, not engineering constants or limits.

The method keeps north and south on the first page, counts those records,
and reports the number of pages needed for all input records. The existing
`PaginatedResult.total_pages` contract uses integer ceiling division:
`(total_count + page_size - 1) // page_size` for a positive page size, and returns
zero for a nonpositive page size. This increment does not change that formula.
Its source is the existing implementation in `common/types.py`; the independent
hand calculation for this example is two records on one page and one remaining
record on another page, hence two pages.

The example also serializes an error with a nested list of missing fields and
merges adapter context with call context. The call's `source` replaces the
adapter's `source`; `task` remains from the adapter. The expected answer is:

```json
{
  "record_count": 2,
  "total_pages": 2,
  "error": {
    "error": "WorldEnergyDataError",
    "code": "WED_ERROR",
    "message": "Missing date",
    "context": {"fields": ["date"]}
  },
  "context": {"source": "call", "task": "sample"}
}
```

`test_documented_example` compares this complete answer to the executable example.
The other consumer tests check acceptance of arbitrary logging messages and
mutable mappings, and rejection of incorrect exception, logger and result
argument types. Existing tests cover serialization, logging output, aliases,
protocols, empty results, pagination boundaries and nonpositive page sizes.

## Sources and limits

- [Python 3.10 logging reference, LoggerAdapter objects](https://docs.python.org/3.10/library/logging.html#loggeradapter-objects):
  the adapter processes the message and keyword arguments before delegating.
- [Python 3.10 logging reference, LogRecord objects](https://docs.python.org/3.10/library/logging.html#logrecord-objects):
  a log message can be an arbitrary object.
- [Python 3.10 typing reference](https://docs.python.org/3.10/library/typing.html):
  annotations, heterogeneous dictionaries and mutable mapping types.
- [Mypy documentation, using mypy with an existing codebase](https://mypy.readthedocs.io/en/stable/existing_code.html):
  incremental adoption and import-following behavior.

Annotations do not add runtime validation. The repository-wide error count in
issue #316 is historical and is not a current measurement. This increment does
not claim that all common modules, legacy helpers or other workspace packages
are type clean. Their cleanup remains for later increments.
