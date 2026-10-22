# Reusing the domain-matrix selector

The CI workflow already calls a shared reusable workflow. The portable
`scripts/ci/domain_matrix.py` engine supplies its selector protocol without
installing the application. Repository-specific paths remain in
`scripts/ci/select_test_targets.py`; the engine can be copied unchanged beside
another repository's adapter.

This implements the selector and template part of issue #530. It does not
change workflow jobs, required checks, quarantine entries or branch protection.

## Selection contract

`SelectionRules` describes always-on test targets, shared paths requiring a
full run, regular expressions mapping changed source paths to domains, exact
contract routes, and registry paths already covered by always-on tests.
The first capture group of each regular expression is the domain directory
name. Multiple matching routes are combined and targets are deduplicated.

The layout is `<tests_root>/unit/<domain>` and
`<tests_root>/integration/modules/<domain>`, with optional other test trees
and root-level `test_*.py` files. `tests_root` defaults to `tests`.
Source layout is configurable, including workspace members that map to a
different domain name; see the existing adapter for examples.

| Change | Scope | Matrix |
| --- | --- | --- |
| Shared path | `full` | Each unit domain with pytest files, other test trees, root files, integration and performance |
| Domain or exact contract route | `modules` | Always-on targets plus existing touched targets |
| Documentation or empty diff | `skip` | Always-on targets |

Unit and other parallel suites use `mode=xdist`; integration and performance
use `mode=seq`. Full selection omits support directories without `test_*.py`
or `*_test.py` files. Missing narrow targets are omitted, as in the original
selector. Configure a real always-on suite: an empty matrix raises an error
instead of emitting a gate with no test jobs. `skip` means narrow testing,
not absence of testing.

The shared workflow invokes the adapter with:

```sh
python3 scripts/ci/select_test_targets.py --emit-matrix --files-from changed-files.txt
```

It consumes these output lines:

```text
scope=modules
matrix={"include": [{"name": "unit-alpha", "targets": "tests/unit/alpha", "mode": "xdist"}]}
```

The matrix above illustrates one shard's shape; a normal narrow selection
also includes the configured always-on shard. `--files-from -` reads stdin,
positional arguments accept changed paths directly, and `--root` overrides
the repository root. Without `--emit-matrix`, the adapter retains the flat
`scope`, `xdist_targets` and `seq_targets` outputs.

## Adapter template

Copy these files into a target repository:

| Source | Destination |
| --- | --- |
| `scripts/ci/domain_matrix.py` | `scripts/ci/domain_matrix.py` |
| `docs/ci/templates/select_test_targets.py` | `scripts/ci/select_test_targets.py` |

Replace `sample` in the template with the import package name. Configure
shared code prefixes, contract suites, integration routes and workspace-member
patterns to match that repository. Keep `pyproject.toml` classified as shared:
the current reusable workflow uses it to request a full run when no diff base
is available. Keep adapter, engine, selector tests and caller workflow changes
classified as shared too. Register any non-module tests explicitly so they
cannot disappear from narrow selections.

The template is exercised as a standalone subprocess after both files are
copied into a synthetic repository. It has no dependency on this repository's
application or on its source layout.

## Workflow adoption

Use the existing `domain-tests` job in `.github/workflows/ci.yml` as the caller
template. Select a reviewed revision of the shared workflow according to the
target repository's policy. Its `selector` input is a script path, with the
default `scripts/ci/select_test_targets.py`; arguments belong in the adapter,
not in that input. Its other inputs configure Python provisioning,
dependency installation, pytest invocation, concurrency and the quarantine
file. Existing defaults stay in the shared workflow rather than this engine.

Before adoption, check these cases with a fixture tree and literal expected
targets derived from its layout:

- Documentation and an empty diff keep the always-on suite.
- A source change selects its unit domain, including each workspace alias.
- An integration change selects a sequential shard.
- A shared or selector change selects every test domain.
- Contract routes select their test files or suites.
- Missing always-on tests cause empty-matrix discovery to fail.

Inspect the aggregate check name on a trial pull request before updating
branch protection. Preserve the existing single aggregate check until the new
caller has been reviewed. A reusable workflow prefixes its job check names
with the caller job name, so copying a caller does not prove check-name
compatibility. Retire overlapping legacy workflows only after reviewing their
coverage and required-check names in the target repository.

Quarantine and empty pytest-shard handling remain the shared workflow's
responsibility. This selector never executes test commands, hides failures or
implements a per-domain command registry. Repositories with another domain
layout can retain their own selector while adopting the same output protocol.

## Sources and verification

- Issue #530 and its linked domain-matrix implementation #531 define reusable
  selection, per-domain isolation and a single aggregate check.
- `.github/workflows/ci.yml` identifies the currently used reusable workflow;
  its `workflow_call` interface defines `scope`, `include`, `name`, `targets`
  and `mode` and retains quarantine and aggregate behavior.
- [GitHub reusable workflow documentation](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
  describes caller jobs and workflow inputs.
- `tests/ci/test_select_test_targets.py` guards repository-specific routing;
  `tests/ci/test_domain_matrix.py` contains independent fixture enumerations,
  alternate-layout examples and template subprocess checks.

There are no engineering equations, coefficients or acceptance limits in this
change. Expected test targets come from the fixture directories and declared
routes, with the derivation written in the test docstrings.

Later slices are cross-repository adoption, a curated domain/command registry,
and deduplication of legacy workflows after required-check inspection. Those
changes need validation in their respective repositories.
